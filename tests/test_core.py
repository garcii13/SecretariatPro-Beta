from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from secretariat_core.match_clock import format_seconds, parse_match_clock
from secretariat_core.ocr_store import OCRConfigStore, ScoreFileStore
from secretariat_core.services.powerplay import (
    advance_powerplay,
    burn_powerplay_block,
    end_powerplay,
    start_powerplay,
)
from secretariat_core.settings_store import SettingsStore
from secretariat_core.state_store import StateStore


class CoreTests(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(parse_match_clock("12:34"), 754)
        self.assertEqual(parse_match_clock("9.05"), 545)
        self.assertIsNone(parse_match_clock("09:99"))
        self.assertEqual(format_seconds(125), "2:05")

    def test_state_backfill_and_atomic_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text('{"team1":{"name":"CEV"}}', encoding="utf-8")
            store = StateStore(path)
            state = store.load()
            self.assertEqual(state["team1"]["name"], "CEV")
            self.assertIn("powerplay", state)
            self.assertEqual(len(state["penalty_shootout"]["team1"]), 5)
            store.save(state)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["team1"]["name"], "CEV")

    def test_settings_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app_settings.json"
            path.write_text('{"language":"en","obs":{"port":4466}}', encoding="utf-8")
            settings = SettingsStore(path).load()
            self.assertEqual(settings["language"], "en")
            self.assertEqual(settings["obs"]["port"], 4466)
            self.assertIn("host", settings["obs"])

    def test_score_files_and_ocr_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scores = ScoreFileStore(root / "scores")
            scores.write_readings({"time": "12:01", "team1_score": "3", "team2_score": ""})
            self.assertEqual(scores.read("time"), "12:01")
            self.assertEqual(scores.read("team1_score"), "3")
            cfg = OCRConfigStore(root / "ocr.json").load()
            self.assertIn("time", cfg["regions"])

    def test_powerplay_two_plus_two(self):
        info = {}
        start_powerplay(
            info, current_seconds=100, player_id="p1", player_number=7,
            penalty_type="2+2", serving_player_id="p1", serving_player_number=7,
        )
        self.assertTrue(info["status"])
        self.assertEqual(info["total_blocks"], 2)
        self.assertTrue(advance_powerplay(info, 220))
        self.assertEqual(info["current_block"], 2)
        self.assertEqual(info["remaining_seconds"], 120)
        self.assertEqual(burn_powerplay_block(info, 230), "ended")
        self.assertFalse(info["status"])
        end_powerplay(info)
        self.assertEqual(info["remaining_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
