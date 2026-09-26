from __future__ import annotations

import unittest
from pathlib import Path

from secretariat_core.services.powerplay import advance_powerplay, start_powerplay


class Phase5PowerplayRobustnessTests(unittest.TestCase):
    def test_small_backward_ocr_error_is_ignored_without_rebasing(self):
        info = {}
        start_powerplay(info, current_seconds=600, player_id="p1", player_number=14)
        self.assertTrue(advance_powerplay(info, 601))
        self.assertEqual(info["remaining_seconds"], 119)

        # Bad OCR frame: 10:01 becomes 09:51. It must consume nothing and must
        # not replace the last accepted baseline.
        self.assertTrue(advance_powerplay(info, 591))
        self.assertEqual(info["remaining_seconds"], 119)
        self.assertEqual(info["last_ocr_match_seconds"], 601)

        # The following correct second consumes exactly one second, not eleven.
        self.assertTrue(advance_powerplay(info, 602))
        self.assertEqual(info["remaining_seconds"], 118)

    def test_large_forward_jump_requires_confirmation(self):
        info = {}
        start_powerplay(info, current_seconds=300, player_id="p1", player_number=8)
        self.assertTrue(advance_powerplay(info, 360, strict_ocr=True))
        self.assertEqual(info["remaining_seconds"], 120)
        self.assertEqual(info["clock_sync_state"], "confirming")

        # A coherent following frame confirms the jump and applies it once.
        self.assertTrue(advance_powerplay(info, 361, strict_ocr=True))
        self.assertEqual(info["remaining_seconds"], 59)
        self.assertEqual(info["last_ocr_match_seconds"], 361)

    def test_period_reset_preserves_remaining_time(self):
        info = {}
        start_powerplay(info, current_seconds=1190, player_id="p1", player_number=22)
        advance_powerplay(info, 1195)
        self.assertEqual(info["remaining_seconds"], 115)
        advance_powerplay(info, 0)
        self.assertEqual(info["remaining_seconds"], 115)
        advance_powerplay(info, 1)
        self.assertEqual(info["remaining_seconds"], 114)

    def test_two_plus_two_remains_ocr_driven(self):
        info = {}
        start_powerplay(
            info,
            current_seconds=100,
            player_id="p1",
            player_number=9,
            penalty_type="2+2",
        )
        # Real OCR flow: the clock advances one accepted second at a time.
        for second in range(101, 226):
            advance_powerplay(info, second, strict_ocr=True)
        self.assertTrue(info["status"])
        self.assertEqual(info["current_block"], 2)
        self.assertEqual(info["remaining_seconds"], 115)


class Phase5FrontendContractTests(unittest.TestCase):
    def test_shootout_uses_direct_choices(self):
        base = Path(__file__).resolve().parents[1]
        js = (base / "webapp" / "app.js").read_text(encoding="utf-8")
        html = (base / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertIn("shootout-choice", js)
        self.assertIn("setPenaltyAttempt", js)
        self.assertNotIn("cyclePenaltyAttempt", js)
        self.assertIn("Selecciona directamente pendiente, gol o fallo", html)

    def test_powerplay_has_sync_feedback_without_manual_number_bypass(self):
        base = Path(__file__).resolve().parents[1]
        html = (base / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="pp-home-manual-number"', html)
        self.assertNotIn('id="pp-away-manual-number"', html)
        self.assertIn('id="pp-home-sync"', html)
        self.assertIn('id="pp-away-sync"', html)


if __name__ == "__main__":
    unittest.main()
