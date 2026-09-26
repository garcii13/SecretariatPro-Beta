from __future__ import annotations

import unittest
from pathlib import Path

import tinycss2

BASE = Path(__file__).resolve().parents[1]


class Phase21BottomBarTests(unittest.TestCase):
    def test_single_canonical_bottom_bar_implementation(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("PHASE 26 — CANONICAL CONTINUOUS GOAL BOTTOM BAR", css)
        self.assertNotIn(".bottom-bar#bottom-bar", css)
        self.assertNotIn(".bottom-bar {", css)
        self.assertIn("#bottom-bar #bottom-team-block", css)
        self.assertIn("border-radius: clamp(14px, 1.25vw, 20px)", css)
        self.assertNotIn("clip-path: polygon(18px", css)

    def test_css_parses_without_top_level_errors(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        rules = tinycss2.parse_stylesheet(css, skip_comments=False, skip_whitespace=False)
        self.assertFalse([rule for rule in rules if rule.type == "error"])

    def test_no_assist_row_is_forced_off(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        html = (BASE / "overlay.html").read_text(encoding="utf-8")
        js = (BASE / "script.js").read_text(encoding="utf-8")
        self.assertIn('#bottom-bar #bottom-assistant-row[hidden]', css)
        self.assertIn('id="bottom-assistant-row" hidden', html)
        self.assertIn('bottomAssistantRow.hidden = !hasAssistant', js)

    def test_overlay_cache_busted(self):
        html = (BASE / "overlay.html").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=phase57", html)
        self.assertIn("script.js?v=phase57", html)


if __name__ == "__main__":
    unittest.main()
