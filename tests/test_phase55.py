from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Phase55RegressionTests(unittest.TestCase):
    def test_pp_only_rounds_bottom_corners(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        block = css.split("PHASE 57 — ISOLATED SCOREBOARD STATUS COMPONENT", 1)[1]
        self.assertIn("border-top-left-radius: 0 !important", block)
        self.assertIn("border-top-right-radius: 0 !important", block)
        self.assertIn("border-bottom-left-radius: 13px !important", block)
        self.assertIn("border-bottom-right-radius: 13px !important", block)
        self.assertIn("sp-status-item--bottom", block)

    def test_live_finish_controls_restored(self):
        html = (ROOT / "webapp/index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp/app.js").read_text(encoding="utf-8")
        self.assertIn('id="finish-match-button"', html)
        self.assertIn('id="finish-match-modal"', html)
        self.assertIn('id="confirm-finish-match"', html)
        self.assertIn('/api/match/finish', js)
        self.assertIn('submitFinishMatch', js)

if __name__ == "__main__":
    unittest.main()
