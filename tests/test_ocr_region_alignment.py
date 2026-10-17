import ctypes
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import numpy as np

from secretariat_core.ocr_store import OCRConfigStore, ScoreFileStore
from secretariat_core.services.ocr_runtime import OCRRuntimeManager
from secretariat_core.settings_store import SettingsStore


@unittest.skipUnless(sys.platform == "win32", "Win32 capture regression")
class WindowsRegionAlignmentTests(unittest.TestCase):
    def test_preview_and_worker_capture_identical_pixels_across_dpi_contexts(self):
        import win32gui
        import win32con
        import window_capture
        from ocr_engine import crop_roi
        from secretariat_core.ocr_sampling import encode_private_sample
        setter = ctypes.windll.user32.SetThreadDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = ctypes.c_void_p
        getter = ctypes.windll.user32.GetThreadDpiAwarenessContext
        getter.restype = ctypes.c_void_p
        original = setter(-4)
        def paint(hwnd, dc, flags):
            # A hidden window has no compositor surface. Supply a deterministic
            # pattern while retaining real Win32 geometry, DCs and DPI scaling.
            win32gui.FillRect(dc, (0, 0, 800, 500), win32gui.GetStockObject(win32con.WHITE_BRUSH))
            for x in (60, 320, 600):
                win32gui.FillRect(dc, (x, 80, x + 90, 150), win32gui.GetStockObject(win32con.BLACK_BRUSH))
            return 1
        hwnd = win32gui.CreateWindowEx(0, "STATIC", "OCR test pattern",
                                      win32con.WS_OVERLAPPEDWINDOW,
                                      100, 100, 800, 500, 0, 0, 0, None)
        try:
            captures = []
            for context in (-1, -2, -4):
                setter(context)
                before = getter()
                with patch.object(window_capture, "_print_window", side_effect=paint):
                    frame, _ = window_capture.capture_window(hwnd)
                self.assertIsNotNone(frame)
                self.assertEqual(getter(), before, "Capture must restore pooled thread DPI")
                captures.append(frame)
            self.assertGreater(np.count_nonzero(captures[0]), 0)
            for frame in captures[1:]:
                np.testing.assert_array_equal(frame, captures[0])
                for roi in ({"x": .05, "y": .02, "w": .3, "h": .12},
                            {"x": .6, "y": .4, "w": .2, "h": .2}):
                    preview_crop = crop_roi(captures[0], roi)
                    worker_crop = crop_roi(frame, roi)
                    np.testing.assert_array_equal(worker_crop, preview_crop)
                    sample = encode_private_sample(worker_crop, {"x": 0, "y": 0, "w": 1, "h": 1})
                    self.assertEqual((sample["height"], sample["width"]), preview_crop.shape[:2])
        finally:
            win32gui.DestroyWindow(hwnd)
            setter(original)


class RunningRegionUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.manager = OCRRuntimeManager(base_dir=base,
            config_store=OCRConfigStore(base / "ocr.json"),
            score_store=ScoreFileStore(base / "scores"),
            settings_store=SettingsStore(base / "settings.json"))
        self.config = self.manager.config_store.load()
        self.config["regions"]["time"] = {"x": .2, "y": .2, "w": .4, "h": .1}
        self.manager.config_store.save(self.config)

    def test_changed_regions_restart_active_reader_with_saved_configuration(self):
        self.manager._process = Mock()
        self.manager._process.poll.return_value = None
        self.config["regions"]["time"]["x"] = .5
        with patch.object(self.manager, "stop") as stop, patch.object(self.manager, "start") as start:
            self.manager.apply_configuration(self.config)
            stop.assert_called_once()
            start.assert_called_once()
            self.assertEqual(self.manager.config_store.load()["regions"]["time"]["x"], .5)

    def test_unchanged_save_does_not_interrupt_active_reader(self):
        self.manager._process = Mock()
        self.manager._process.poll.return_value = None
        with patch.object(self.manager, "stop") as stop:
            self.manager.apply_configuration(self.config)
            stop.assert_not_called()

    def test_clearing_regions_stops_without_restarting(self):
        self.manager._process = Mock()
        self.manager._process.poll.return_value = None
        self.config["regions"] = {}
        with patch.object(self.manager, "stop") as stop, patch.object(self.manager, "start") as start:
            self.manager.apply_configuration(self.config)
            stop.assert_called_once()
            start.assert_not_called()

    def test_stopped_reader_stays_stopped_when_regions_are_saved(self):
        self.config["regions"]["time"]["x"] = .5
        with patch.object(self.manager, "start") as start:
            self.manager.apply_configuration(self.config)
            start.assert_not_called()

    def test_superseded_reader_cannot_write_old_readings_or_stop_new_reader(self):
        old = Mock()
        old.stdout = io.StringIO('OCRMSG ' + json.dumps({"type": "reading", "key": "time", "value": "09:59"}) + '\n')
        current = Mock()
        self.manager._process = current
        self.manager._status["running"] = True
        with patch.object(self.manager, "handle_payload") as handle:
            self.manager._reader_loop(old)
            handle.assert_not_called()
        self.assertIs(self.manager._process, current)
        self.assertTrue(self.manager._status["running"])

    @unittest.skipUnless(sys.platform == "win32", "Windows one-file worker lifecycle")
    def test_stop_terminates_worker_child_as_well_as_bootloader(self):
        import psutil
        code = ('import subprocess, sys, time; '
                'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(45)"]); '
                'print(child.pid, flush=True); time.sleep(45)')
        process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                                   text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        child = None
        try:
            child = psutil.Process(int(process.stdout.readline().strip()))
            self.manager._process = process
            self.manager.stop()
            self.assertIsNotNone(process.poll())
            self.assertFalse(child.is_running())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if child is not None and child.is_running():
                child.kill()
            process.stdout.close()


class RegionConfigurationAPITests(unittest.IsolatedAsyncioTestCase):
    async def test_saving_regions_applies_them_to_reader(self):
        from secretariat_api import main
        from secretariat_api.schemas import OCRConfigPayload
        runtime = Mock()
        payload = OCRConfigPayload(source_type="window", source_id="123",
                                   regions={"time": {"x": .2, "y": .3, "w": .4, "h": .1}})
        with patch.object(main, "runtime", runtime), \
             patch.object(main, "broadcast_state", new=AsyncMock(return_value={"ok": True})):
            self.assertEqual(await main.put_ocr_config(payload), {"ok": True})
        runtime.ocr_runtime.apply_configuration.assert_called_once()
        saved = runtime.ocr_runtime.apply_configuration.call_args.args[0]
        self.assertEqual(saved["regions"]["time"], payload.regions["time"])
        runtime.ocr_store.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
