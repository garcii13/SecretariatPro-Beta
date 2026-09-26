from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]


class Phase28Tests(unittest.TestCase):
    def test_lineups_palette_does_not_colour_outer_canvas(self):
        script = (BASE / "script.js").read_text(encoding="utf-8")
        self.assertNotIn(".stats-panel, .penalties-panel, .lineups-modal, .player-profile-bar", script)
        self.assertIn('el.classList.add("lineups-exiting")', script)
        self.assertIn('el.classList.remove("lineups-exiting")', script)

    def test_lineups_exit_is_immediately_transparent(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("PHASE 28 — LINEUPS CLEAN EXIT", css)
        self.assertIn(".lineups-modal.lineups-exiting .lineups-panel", css)
        self.assertIn("visibility: hidden !important", css)
        self.assertIn("background-color: transparent !important", css)

    def test_bottom_bar_uses_full_height_centring(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("PHASE 28 — EXACT BOTTOM-BAR VERTICAL ALIGNMENT", css)
        self.assertIn("#bottom-bar > .bottom-event-copy", css)
        self.assertIn("justify-content: center !important", css)
        self.assertIn("#bottom-bar.no-assistant .bottom-event-copy", css)
        self.assertIn("padding-top: 0 !important", css)

    def test_phase36_cache_and_version(self):
        overlay = (BASE / "overlay.html").read_text(encoding="utf-8")
        html = (BASE / "webapp" / "index.html").read_text(encoding="utf-8")
        sw = (BASE / "webapp" / "sw.js").read_text(encoding="utf-8")
        main = (BASE / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("styles.css?v=phase55", html)
        self.assertIn("app.js?v=phase36", html)
        self.assertIn("secretariatpro-phase36-v1", sw)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
