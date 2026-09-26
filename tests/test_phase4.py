from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.services.powerplay import advance_powerplay, start_powerplay
from secretariat_core.services.shootout import reset_shootout, set_attempt
from secretariat_core.state_store import default_state


class Phase4PowerplayTests(unittest.TestCase):
    def test_powerplay_follows_only_ocr_clock_progress(self):
        info = {}
        start_powerplay(
            info,
            current_seconds=300,
            player_id="p1",
            player_number=14,
            penalty_type="2",
        )
        self.assertEqual(info["remaining_seconds"], 120)
        self.assertFalse(advance_powerplay(info, 300))
        self.assertEqual(info["remaining_seconds"], 120)
        self.assertTrue(advance_powerplay(info, 301))
        self.assertEqual(info["remaining_seconds"], 119)
        self.assertFalse(advance_powerplay(info, 301))
        self.assertEqual(info["remaining_seconds"], 119)
        self.assertTrue(advance_powerplay(info, 310))
        self.assertEqual(info["remaining_seconds"], 110)

    def test_powerplay_survives_period_clock_reset(self):
        info = {}
        start_powerplay(
            info,
            current_seconds=1195,
            player_id="p1",
            player_number=14,
            penalty_type="2",
        )
        advance_powerplay(info, 1200)
        self.assertEqual(info["remaining_seconds"], 115)
        advance_powerplay(info, 0)
        self.assertEqual(info["remaining_seconds"], 115)
        advance_powerplay(info, 1)
        self.assertEqual(info["remaining_seconds"], 114)

    def test_two_plus_two_crosses_blocks_from_ocr_delta(self):
        info = {}
        start_powerplay(
            info,
            current_seconds=100,
            player_id="p1",
            player_number=9,
            penalty_type="2+2",
        )
        advance_powerplay(info, 225)
        self.assertTrue(info["status"])
        self.assertEqual(info["current_block"], 2)
        self.assertEqual(info["remaining_seconds"], 115)

    def test_ocr_runtime_callback_updates_persisted_powerplay(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.score_store.write_readings({"time": "05:00"})

            def mutate(state):
                start_powerplay(
                    state["powerplay"]["team1"],
                    current_seconds=300,
                    player_id="p1",
                    player_number=14,
                    penalty_type="2",
                )

            runtime.mutate_state(mutate)
            runtime.ocr_runtime.handle_payload({"type": "reading", "key": "time", "value": "05:01"})
            self.assertEqual(runtime.read_state()["powerplay"]["team1"]["remaining_seconds"], 119)


class Phase4ShootoutTests(unittest.TestCase):
    def test_penalty_attempts_are_normalized_and_reset(self):
        state = default_state()
        set_attempt(state, "team1", 0, "goal")
        set_attempt(state, "team1", 1, "miss")
        self.assertEqual(state["penalty_shootout"]["team1"][:2], ["goal", "miss"])
        self.assertEqual(len(state["penalty_shootout"]["team1"]), 5)
        reset_shootout(state)
        self.assertEqual(state["penalty_shootout"]["team1"], [None] * 5)
        self.assertEqual(state["penalty_shootout"]["team2"], [None] * 5)


if __name__ == "__main__":
    unittest.main()
