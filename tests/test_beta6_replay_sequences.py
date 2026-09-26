from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from secretariat_core.services.graphics_sequences import delete_sequence, find_sequence, save_sequence
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.services.replay_plugin_bridge import ReplayPluginBridge
from secretariat_core.settings_store import normalize_settings



class Beta6ReplaySequenceTests(unittest.TestCase):
    def test_graphics_sequences_are_normalized_and_personal_settings_keep_them(self):
        settings = normalize_settings({})
        sequence = save_sequence(settings, {
            "name": "Previa automática",
            "steps": [
                {"panel": "prematch", "duration_seconds": 8, "interval_seconds": 2},
                {"panel": "lineups", "lineup_team": "team2", "duration_seconds": 6},
            ],
        })
        normalized = normalize_settings(settings)
        assert find_sequence(normalized, sequence["id"])["steps"][1]["lineup_team"] == "team2"
        assert delete_sequence(normalized, sequence["id"])


    def test_goal_duration_is_manager_bounded(self):
        assert normalize_settings({"appearance": {"goal_celebration": {"duration_seconds": 99}}})["appearance"]["goal_celebration"]["duration_seconds"] == 30
        assert normalize_settings({"appearance": {"goal_celebration": {"duration_seconds": 0}}})["appearance"]["goal_celebration"]["duration_seconds"] == 1
        assert normalize_settings({"appearance": {"goal_celebration": {"delay_seconds": 99}}})["appearance"]["goal_celebration"]["delay_seconds"] == 30
        assert normalize_settings({"appearance": {"goal_celebration": {"delay_seconds": -2}}})["appearance"]["goal_celebration"]["delay_seconds"] == 0


    def test_replay_composition_is_saved_per_clip(self):
        with TemporaryDirectory() as directory:
            library = ReplayLibrary(directory)
            marker = library.create_marker(match_id="m1", label="Gol")
            media = Path(directory) / "cam1.mkv"
            media.write_bytes(b"video")
            library.complete_multicam_marker(marker["id"], [{"camera": 1, "path": str(media)}])
            clip = library.set_composition(marker["id"], [{"camera": 1, "duration_seconds": 3, "speed_percent": 50}])
            assert clip["composition"] == [{"camera": 1, "duration_seconds": 3, "speed_percent": 50}]
            assert clip["included"] is True


    def test_cleanup_preserves_finished_videos_and_original_sources(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "camera.mkv"
            source.write_bytes(b"camera")
            library = ReplayLibrary(root / "library")
            marker = library.create_marker(match_id="m", label="Goal")
            clip = library.complete_multicam_marker(marker["id"], [{"camera": 1, "path": str(source)}])
            self.assertNotEqual(Path(clip["path"]), source)
            video = library.exports_dir / "event.mp4"
            video.write_bytes(b"finished")
            library.clear_compositor()
            self.assertEqual(library.snapshot()["clips"], [])
            self.assertFalse(Path(clip["path"]).exists())
            self.assertTrue(source.exists())
            self.assertTrue(video.exists())

    def test_plugin_compose_writes_atomic_command_and_waits_for_ack(self):
        with TemporaryDirectory() as directory:
            status_path = Path(directory) / "secretariatpro-bridge.json"
            status_path.write_text('{"loaded":true,"event_ready":true}', encoding="utf-8")
            bridge = ReplayPluginBridge(Mock(connected=True), status_path)
            bridge._wait_for = Mock(side_effect=lambda predicate, timeout, **kwargs: {"last_command_id": __import__("json").loads(status_path.with_name("secretariatpro-command.json").read_text())["command_id"]})
            result = bridge.compose([{"camera": 1, "duration_seconds": 3, "speed_percent": 100}], play_now=True)
            command = __import__("json").loads(status_path.with_name("secretariatpro-command.json").read_text())
            assert command["action"] == "compose" and command["play_now"] is True
            assert result["last_command_id"] == command["command_id"]


    def test_new_live_copy_is_translated_in_every_supported_language(self):
        source = Path("webapp/app.js").read_text(encoding="utf-8")
        for language in ("sv", "cs", "fi", "de"):
            assert f"APP_TRANSLATIONS_BY_LANGUAGE.{language}" in source
        for text in (
            "Secuencias personales",
            "Componer repetición",
            "Repetición del gol",
            "Guardar y lanzar",
            "Continuar sin repetición",
        ):
            assert source.count(f'"{text}"') >= 5, f"Falta {text!r} en algún idioma"
        assert '"Repetición del gol":"Goal replay"' in source
        assert "SecretariatDeck" in Path("webapp/index.html").read_text(encoding="utf-8")

        manager = Path("manager_app/app.js").read_text(encoding="utf-8")
        for text in (
            "Cartel del goleador tras la repetición",
            "Espera sin plugin (segundos)",
            "Tiempo en pantalla (segundos)",
        ):
            assert manager.count(f'"{text}"') == 5, f"Falta {text!r} en algún idioma del Manager"
