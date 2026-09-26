from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from obs_controller import OBSController
from secretariat_core.services.graphics_queue import add_cue, clear_cues, move_cue, take_cue
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.services.replay_plugin_bridge import ReplayPluginBridge
from secretariat_core.settings_store import normalize_settings, period_strip_for_sport


class ProgramMonitorTests(unittest.TestCase):
    def test_program_frame_uses_obs_scene_and_never_desktop_capture(self):
        controller = OBSController()
        controller.connected = True
        controller._client = Mock()
        preview = OBSController()
        preview.connected = True
        preview._client = Mock()
        controller._preview = preview
        preview._client.send.side_effect = [
            {"currentProgramSceneName": "Programa"},
            {"imageData": "data:image/jpeg;base64,Zm90bw=="},
        ]
        self.assertEqual(controller.program_screenshot(refresh_scene=True), b"foto")
        controller._client.send.assert_not_called()
        self.assertEqual(preview._client.send.call_args_list[0].args[0], "GetCurrentProgramScene")
        self.assertEqual(preview._client.send.call_args_list[1].args[0], "GetSourceScreenshot")


class AdvancedGraphicsQueueTests(unittest.TestCase):
    def test_queue_can_be_named_timed_reordered_and_cleared(self):
        state = {}
        first = add_cue(state, "scoreboard", "match", label="Apertura", duration_seconds=8)
        second = add_cue(state, "prematch", "match", label="Previa")
        move_cue(state, second["id"], 0)
        self.assertEqual(state["graphics_queue"][0]["label"], "Previa")
        self.assertEqual(state["graphics_queue"][1]["duration_seconds"], 8)
        taken = take_cue(state, second["id"], "match")
        self.assertEqual(taken["id"], second["id"])
        self.assertEqual(state["graphics_on_air"], {"cue_id": second["id"], "panel": "prematch"})
        self.assertEqual(clear_cues(state), 1)
        self.assertEqual(state["graphics_queue"], [])


class PeriodStripTests(unittest.TestCase):
    def test_period_strip_is_bounded_and_labels_are_completed(self):
        settings = normalize_settings({"appearance": {"period_strip": {"enabled": True, "segments": 4, "labels": ["Q1", "Q2"]}}})
        self.assertEqual(settings["appearance"]["period_strip"], {
            "enabled": True, "show_number": False, "segments": 4, "labels": ["Q1", "Q2", "3", "4"],
            "active_color": "#8cff00", "text_color": "#102000",
        })


class SportPeriodTests(unittest.TestCase):
    def test_handball_has_two_periods_without_changing_theme(self):
        config = normalize_settings({})["appearance"]["period_strip"]
        handball = period_strip_for_sport(config, "handball")
        self.assertEqual(handball["segments"], 2)
        self.assertEqual(handball["labels"], ["1", "2"])
        self.assertEqual(handball["active_color"], config["active_color"])
        self.assertEqual(period_strip_for_sport(config, "floorball")["segments"], 3)
        self.assertEqual(config["segments"], 3)


class ReplayLibraryTests(unittest.TestCase):
    def test_saved_clip_metadata_and_fullhd_highlight_command(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            clip_path = root / "camera-720p.mkv"
            clip_path.write_bytes(b"clip")
            library = ReplayLibrary(root / "library")
            marker = library.create_marker(match_id="m1", label="Gol", match_time="10:22")
            ready = library.complete_marker(marker["id"], str(clip_path))
            self.assertEqual(ready["status"], "ready")

            def fake_run(command, **_kwargs):
                Path(command[-1]).write_bytes(b"highlight")
                return SimpleNamespace(returncode=0, stderr="")

            with patch.object(ReplayLibrary, "_ffmpeg", return_value="/fake/ffmpeg"), patch(
                "secretariat_core.services.replay_library.subprocess.run", side_effect=fake_run
            ) as runner:
                result = library.create_highlights("m1", [marker["id"]], "Entretiempo")
            command = runner.call_args_list[0].args[0]
            self.assertIn("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1", command)
            self.assertEqual(result["method"], "ffmpeg-fullhd-cover")
            self.assertTrue(Path(result["path"]).is_file())

    def test_multicam_marker_keeps_every_camera_angle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = []
            for camera in (1, 2, 3):
                path = root / f"cam-{camera}.mkv"
                path.write_bytes(f"cam{camera}".encode())
                paths.append({"camera": camera, "path": str(path)})
            library = ReplayLibrary(root / "library")
            marker = library.create_marker(match_id="m1", label="Gol")
            ready = library.complete_multicam_marker(marker["id"], paths)
            self.assertEqual(ready["backend"], "multicam-plugin")
            self.assertEqual([row["camera"] for row in ready["angles"]], [1, 2, 3])
            self.assertEqual(library.media_path(marker["id"], 2).name, "cam-2.mkv")


class ReplayPluginBridgeTests(unittest.TestCase):
    def test_reads_plugin_state_and_triggers_standard_obs_hotkey(self):
        with tempfile.TemporaryDirectory() as folder:
            state_path = Path(folder) / "bridge.json"
            state_path.write_text('{"loaded":true,"buffers_active":false,"camera_count":3}', encoding="utf-8")
            obs = SimpleNamespace(connected=True, trigger_hotkey_by_name=Mock())
            bridge = ReplayPluginBridge(obs, state_path)
            self.assertTrue(bridge.status()["available"])
            self.assertEqual(bridge.status()["camera_count"], 3)
            bridge._trigger("mark")
            obs.trigger_hotkey_by_name.assert_called_once_with("secretariatpro_replay_mark")


if __name__ == "__main__":
    unittest.main()
