from __future__ import annotations

import base64
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.ocr_store import ScoreFileStore
from secretariat_core.services.program_preview import ProgramPreview
from video_source import SharedFramePublisher, SharedFrameReader


class CameraPerformanceTests(unittest.TestCase):
    def test_new_frames_only_and_owned_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            publisher = SharedFramePublisher(Path(folder) / "frame")
            reader = SharedFrameReader(publisher.path)
            try:
                publisher.publish(np.full((12, 20, 3), 17, dtype=np.uint8))
                first = reader.read(require_new=True)
                self.assertIsNone(reader.read(require_new=True))
                publisher.publish(np.full((12, 20, 3), 29, dtype=np.uint8))
                second = reader.read(require_new=True)
                self.assertTrue(np.all(first == 17))
                self.assertTrue(np.all(second == 29))
                second[:] = 42
                self.assertTrue(np.all(reader.read() == 29))
            finally:
                publisher.close(remove=True)

    def test_frozen_capture_is_rejected_and_restart_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "frame"
            reader = SharedFrameReader(path)
            publisher = SharedFramePublisher(path)
            with patch("video_source.time.time", return_value=10):
                publisher.publish(np.ones((3, 5, 3), dtype=np.uint8))
            with patch("video_source.time.time", return_value=12):
                self.assertIsNone(reader.read())
            publisher.close(remove=True)
            publisher = SharedFramePublisher(path)
            try:
                publisher.publish(np.ones((7, 9, 3), dtype=np.uint8))
                self.assertEqual(reader.read(require_new=True).shape, (7, 9, 3))
            finally:
                publisher.close(remove=True)


class ScorePerformanceTests(unittest.TestCase):
    def test_repeated_readings_do_not_write_or_touch_mtime(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = ScoreFileStore(folder)
            values = {"time": "12:34", "team1_score": "2", "team2_score": "1"}
            scores.write_external(values)
            files = list(Path(folder).glob("*"))
            mtimes = {p: p.stat().st_mtime_ns for p in files}
            with patch.object(scores, "_atomic_write", wraps=scores._atomic_write) as write, \
                    patch.object(scores._reconciliation, "write", wraps=scores._reconciliation.write) as reconcile:
                for _ in range(50):
                    scores.write_external(values)
                write.assert_not_called()
                reconcile.assert_not_called()
            self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in files})
            # An external edit must not be masked by a stale in-memory cache.
            (Path(folder) / "Home Score.txt").write_text("9")
            scores.write_external({"team1_score": "2"})
            self.assertEqual(scores.read("team1_score"), "2")

    def test_clock_updates_do_not_rewrite_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = ScoreFileStore(folder)
            scores.write_external({"time": "00:01"})
            scores.write_external({"time": "00:02"})
            self.assertEqual(scores.read("time"), "00:02")
            self.assertFalse((Path(folder) / "reconciliation.json").exists())


class PreviewPerformanceTests(unittest.TestCase):
    def test_clients_share_requests_and_scene_refresh_is_time_based(self):
        obs = Mock()
        obs.program_screenshot.side_effect = [b"one", b"two", b"three"]
        preview = ProgramPreview(8)
        with patch("secretariat_core.services.program_preview.time.monotonic", return_value=10):
            self.assertEqual(preview.read(obs), b"one")
            for _ in range(12):
                self.assertEqual(preview.read(obs), b"one")
        self.assertEqual(obs.program_screenshot.call_count, 1)
        with patch("secretariat_core.services.program_preview.time.monotonic", return_value=10.2):
            self.assertEqual(preview.read(obs), b"two")
            self.assertFalse(obs.program_screenshot.call_args.kwargs["refresh_scene"])
        with patch("secretariat_core.services.program_preview.time.monotonic", return_value=10.6):
            self.assertEqual(preview.read(obs), b"three")
            self.assertTrue(obs.program_screenshot.call_args.kwargs["refresh_scene"])

    def test_failed_preview_does_not_reuse_stale_image(self):
        obs = Mock()
        obs.program_screenshot.side_effect = [b"one", OSError("offline"), b"new"]
        preview = ProgramPreview(8)
        with patch("secretariat_core.services.program_preview.time.monotonic", return_value=10):
            preview.read(obs)
        with patch("secretariat_core.services.program_preview.time.monotonic", return_value=11):
            with self.assertRaises(OSError):
                preview.read(obs)
            self.assertEqual(preview.read(obs), b"new")


class SampleDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.runtime = ApplicationRuntime(self.folder.name)
        # Exercise the delivery pass deterministically, without a network or
        # background retry competing with the test.
        self.runtime._ocr_sample_retry_stop.set()
        self.runtime._ocr_sample_wake.set()
        self.runtime._ocr_sample_retry_thread.join(timeout=2)
        self.runtime._ocr_sample_retry_stop.clear()
        self.runtime.supabase = Mock()
        self.runtime.supabase.upload_ocr_sample.return_value = {"uploaded": True, "id": "sample"}
        self.runtime.active_workspace = {"id": "workspace"}
        self.runtime.ocr_consent = {"enabled": True}
        self.payload = {"key": "time", "image_b64": base64.b64encode(b"jpeg").decode()}

    def tearDown(self):
        self.runtime.shutdown()
        self.folder.cleanup()

    def test_persist_before_network_and_remove_only_after_ack(self):
        self.runtime.upload_ocr_sample(self.payload)
        self.runtime.supabase.upload_ocr_sample.assert_not_called()
        self.assertEqual(len(self.runtime._ocr_sample_queue_files()), 1)
        self.runtime.supabase.upload_ocr_sample.side_effect = PermissionError("403 Storage RLS")
        self.assertEqual(self.runtime._flush_ocr_sample_outbox_once(), 0)
        self.assertEqual(len(self.runtime._ocr_sample_queue_files()), 1)
        self.runtime.supabase.upload_ocr_sample.side_effect = None
        self.assertEqual(self.runtime._flush_ocr_sample_outbox_once(), 1)
        self.assertEqual(self.runtime._ocr_sample_queue_files(), [])

    def test_missing_confirmation_keeps_sample(self):
        self.runtime.upload_ocr_sample(self.payload)
        self.runtime.supabase.upload_ocr_sample.return_value = {"uploaded": True}
        self.assertEqual(self.runtime._flush_ocr_sample_outbox_once(), 0)
        self.assertEqual(len(self.runtime._ocr_sample_queue_files()), 1)

    def test_other_workspaces_and_corrupt_file_do_not_starve_active_queue(self):
        for _ in range(9):
            self.runtime.active_workspace = {"id": "other"}
            self.runtime.upload_ocr_sample(self.payload)
        self.runtime.active_workspace = {"id": "workspace"}
        corrupt = self.runtime._ocr_sample_outbox / "broken.json"
        corrupt.write_text("{")
        # Windows can give consecutive writes the same mtime. Make the
        # damaged item oldest explicitly so this tests quarantine before limit.
        os.utime(corrupt, (1, 1))
        self.runtime.upload_ocr_sample(self.payload)
        self.assertEqual(self.runtime._flush_ocr_sample_outbox_once(limit=1), 1)
        self.assertEqual(len(self.runtime._ocr_sample_queue_files()), 9)
        self.assertTrue(corrupt.with_suffix(".invalid").exists())

    def test_disk_failure_is_visible_and_consent_is_respected(self):
        self.runtime.ocr_consent = {"enabled": False}
        self.runtime.upload_ocr_sample(self.payload)
        self.assertEqual(self.runtime._ocr_sample_queue_files(), [])
        self.runtime.ocr_consent = {"enabled": True}
        with patch("secretariat_core.json_store.JSONStore.write", side_effect=OSError("disk full")):
            self.runtime.upload_ocr_sample(self.payload)
        self.assertIn("disk full", self.runtime.ocr_sample_delivery_status()["last_error"])


if __name__ == "__main__":
    unittest.main()
