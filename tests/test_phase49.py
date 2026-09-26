from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Phase49RegressionTests(unittest.TestCase):
    def test_top_scorers_uses_resolved_identity(self):
        runtime = (ROOT / "secretariat_api" / "runtime.py").read_text()
        self.assertIn('competition_logo = match_state.get("logo")', runtime)
        self.assertIn('"team_logo": team_state.get("logo") or fallback_logo', runtime)
        self.assertIn('fallback_logo = team.get("alternate_logo_url") or team.get("logo_url")', runtime)

    def test_stats_overlay_refreshes_before_toggle(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text()
        self.assertIn('panel in {"top_scorers", "standings"}', api)
        self.assertIn('runtime.refresh_statistics', api)

    def test_live_view_has_container_responsiveness(self):
        css = (ROOT / "webapp" / "styles.css").read_text()
        self.assertIn('container-name: liveview', css)
        self.assertIn('@container liveview (max-width: 760px)', css)
        self.assertIn('@container liveview (max-width: 500px)', css)
        self.assertIn('grid-template-columns: repeat(auto-fit, minmax(min(100%, 145px), 1fr))', css)

    def test_phase49_version(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text()
        runtime = (ROOT / "secretariat_api" / "runtime.py").read_text()
        html = (ROOT / "webapp" / "index.html").read_text()
        self.assertIn('API_VERSION = "57.0.0-beta-rc"', api)
        self.assertIn('"app_release": "57.0.0-beta-rc"', runtime)
        self.assertIn('styles.css?v=phase55', html)
        self.assertIn('app.js?v=phase55', html)

if __name__ == '__main__':
    unittest.main()
