from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.ocr_store import OCRConfigStore, ScoreFileStore
from secretariat_core.services.event_context import build_intermission_events
from secretariat_core.services.ocr_runtime import OCRRuntimeManager
from secretariat_core.settings_store import SettingsStore, default_settings


class Phase3ScoreSourceTests(unittest.TestCase):
    def test_default_result_source_is_ocr(self):
        self.assertEqual(default_settings()["score_control"]["mode"], "ocr")

    def test_manual_mode_blocks_unintended_api_score_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            with self.assertRaises(RuntimeError):
                runtime.write_score("team1", 3)
            runtime.set_score_mode("manual")
            runtime.write_score("team1", 3)
            self.assertEqual(runtime.scores()["team1_score"], "3")
            self.assertTrue(runtime.snapshot()["score_control"]["editable"])

    def test_manual_mode_ignores_ocr_scores_but_keeps_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            settings = SettingsStore(base / "app_settings.json")
            config = OCRConfigStore(base / "ocr_config.json")
            scores = ScoreFileStore(base / "scores")
            settings.save({"score_control": {"mode": "manual"}})
            scores.write_readings({"team1_score": "4", "team2_score": "2", "time": "08:00"})
            manager = OCRRuntimeManager(
                base_dir=base,
                config_store=config,
                score_store=scores,
                settings_store=settings,
            )

            manager.handle_payload({"type": "reading", "key": "team1_score", "value": "5"})
            manager.handle_payload({"type": "reading", "key": "time", "value": "08:01"})

            self.assertEqual(scores.read("team1_score"), "4")
            self.assertEqual(scores.read("time"), "08:01")
            self.assertEqual(manager.status()["readings"]["team1_score"], "5")


    def test_events_are_mapped_for_intermission_without_changing_ocr_score(self):
        match = {
            "home_team": {"id": "home"},
            "away_team": {"id": "away"},
        }
        rosters = {
            "team1": [{"player_id": "p1", "shirt_number": 9, "player": {"last_name": "Local"}}],
            "team2": [{"player_id": "p2", "shirt_number": 7, "player": {"last_name": "Away"}}],
        }
        rows = [
            {"id": "g1", "team_id": "home", "player_id": "p1", "event_type": "goal", "match_time": "02:10", "created_at": "1", "player": {"last_name": "Local"}},
            {"id": "a1", "team_id": "home", "player_id": "p2", "event_type": "assist", "related_event_id": "g1", "created_at": "2", "player": {"last_name": "Away"}},
        ]
        result = build_intermission_events(rows, match=match, rosters=rosters)
        self.assertEqual(result[0]["score"], "1–0")
        self.assertEqual(result[0]["number"], "9")
        self.assertEqual(result[0]["assistant_number"], "7")

    def test_ocr_mode_persists_ocr_score_readings(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            settings = SettingsStore(base / "app_settings.json")
            config = OCRConfigStore(base / "ocr_config.json")
            scores = ScoreFileStore(base / "scores")
            settings.save({"score_control": {"mode": "ocr"}})
            manager = OCRRuntimeManager(
                base_dir=base,
                config_store=config,
                score_store=scores,
                settings_store=settings,
            )
            manager.handle_payload({"type": "reading", "key": "team2_score", "value": "7"})
            self.assertEqual(scores.read("team2_score"), "7")


if __name__ == "__main__":
    unittest.main()
