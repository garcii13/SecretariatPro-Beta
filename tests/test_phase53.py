from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Phase53PolishTests(unittest.TestCase):
    def test_overlay_status_component_is_isolated_from_legacy_offsets(self):
        html = (ROOT / "overlay.html").read_text(encoding="utf-8")
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("sp-team-status-stack--home", html)
        self.assertIn("sp-team-status-stack--away", html)
        self.assertNotIn('id="team1-powerplay"', html)
        self.assertIn("animateStatusEntry", js)
        self.assertIn("Web Animations API", css)

    def test_status_stack_is_glued_and_animated(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn('gap: 0 !important;', css)
        self.assertIn('node.animate([', js)
        self.assertIn('height: "0px"', js)
        self.assertIn('applyStatusGeometry', js)

    def test_penalty_items_have_stable_overlay_ids(self):
        pp = (ROOT / 'secretariat_core' / 'services' / 'powerplay.py').read_text(encoding='utf-8')
        self.assertIn('"overlay_id": uuid4().hex', pp)

    def test_overlay_assets_are_cache_busted(self):
        html = (ROOT / 'overlay.html').read_text(encoding='utf-8')
        self.assertIn('styles.css?v=phase57', html)
        self.assertIn('script.js?v=phase57', html)

    def test_manager_uses_live_blue_cyan_palette_and_readable_sidebar(self):
        css = (ROOT / 'manager_app' / 'styles.css').read_text(encoding='utf-8')
        for token in ('--bg: #03132f;', '--accent: #66d5d9;', '--accent-2: #8ee5e7;'):
            self.assertIn(token, css)
        self.assertIn('color: #c3d8e2;', css)
        self.assertIn('background: linear-gradient(180deg, rgba(5,27,60,.985), rgba(3,18,43,.985));', css)


if __name__ == '__main__':
    unittest.main()
