from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase27Tests(unittest.TestCase):
    def test_lineups_do_not_add_fullscreen_backdrop(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        marker = "PHASE 27 — ALINEACIONES SOBRE SEÑAL LIMPIA"
        self.assertIn(marker, css)
        phase = css.split(marker, 1)[1]
        self.assertIn("background: transparent !important", phase)
        self.assertIn("backdrop-filter: none !important", phase)
        self.assertIn(".lineups-panel.team-lineup-panel", css)

    def test_live_view_uses_one_spacing_system(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("--live-inset:", css)
        self.assertIn("--live-gap:", css)
        self.assertIn("--live-control-height: 44px", css)
        self.assertIn("#view-live .penalty-columns", css)
        self.assertIn("margin: var(--live-inset)", css)
        self.assertIn("#view-live .events-list", css)

    def test_live_selects_are_responsive(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("repeat(auto-fit, minmax(min(100%, 180px), 1fr))", css)
        self.assertIn("#view-live select", css)
        self.assertIn("text-overflow: ellipsis", css)
        self.assertIn("max-width: 100%", css)
        self.assertIn("#view-live .penalty-team .form-row label:first-child", css)
        self.assertIn("grid-column: auto", css)

    def test_live_score_card_uses_full_width_below_1100(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 1100px)", css)
        self.assertIn("#view-live .live-side", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css)
        self.assertIn("#view-live .live-side .score-card { width: 100%; }", css)

    def test_phase36_cache_and_version(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("app.js?v=phase36", html)
        self.assertIn("styles.css?v=phase55", html)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("secretariatpro-phase36-v1", sw)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
