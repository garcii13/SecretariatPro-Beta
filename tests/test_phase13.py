from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Phase13Tests(unittest.TestCase):
    def test_production_view_is_forced_visible(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("#view-production.is-visible", css)
        self.assertIn("opacity: 1", css)
        self.assertIn("transform: none", css)

    def test_direct_graphics_preview_uses_fit_frame(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="overlay-fit-frame"'), 2)
        self.assertIn('id="graphics-cue-preview"', html)
        production = html[html.index('id="view-production"'):html.index('id="view-team"')]
        self.assertNotIn('overlay-fit-frame', production)
        self.assertIn('id="production-program-video"', production)

    def test_resize_observer_fits_complete_overlay(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn("OVERLAY_CANVAS", js)
        self.assertIn("Math.min(width / OVERLAY_CANVAS.width, height / OVERLAY_CANVAS.height)", js)
        self.assertIn("new ResizeObserver", js)

    def test_phase13_cache_version(self):
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        self.assertRegex(sw, r"secretariatpro-phase(?:13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36)-v1")

if __name__ == "__main__":
    unittest.main()
