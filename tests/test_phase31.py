from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Phase31TabletDeckTests(unittest.TestCase):
    def test_tablet_assets_exist(self):
        tablet = ROOT / "tablet"
        for name in ("index.html", "tablet.css", "tablet.js", "manifest.webmanifest", "sw.js"):
            self.assertTrue((tablet / name).exists(), name)

    def test_tablet_is_streamdeck_only(self):
        html = (ROOT / "tablet" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="deck-grid"', html)
        self.assertIn('id="scene-grid"', html)
        self.assertNotIn("production-program-video", html)
        self.assertNotIn("projector-stream", html)
        self.assertNotIn("Vista del directo", html)
        self.assertNotIn("<iframe", html)

    def test_tablet_uses_shared_backend_obs_connection(self):
        js = (ROOT / "tablet" / "tablet.js").read_text(encoding="utf-8")
        self.assertIn('/api/obs/scenes/program', js)
        self.assertIn('app.snapshot?.obs?.connected', js)
        self.assertNotIn('/api/obs/connect', js)
        self.assertNotIn('settings-obs-password', js)

    def test_tablet_has_full_deck_actions(self):
        html = (ROOT / "tablet" / "index.html").read_text(encoding="utf-8")
        for marker in (
            'data-overlay="scoreboard"', 'data-overlay="prematch"',
            'data-overlay="intermission"', 'data-overlay="lineups"',
            'data-overlay="top_scorers"', 'data-overlay="standings"',
            'data-overlay="penalties"', 'data-overlay="bottom_bar"',
            'data-goal-team="team1"', 'data-goal-team="team2"',
            'data-penalty-team="team1"', 'data-penalty-team="team2"',
            'data-profile-team="team1"', 'data-profile-team="team2"',
            'data-hide-all',
        ):
            self.assertIn(marker, html)

    def test_qr_points_to_tablet_route(self):
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('/tablet/', main)
        self.assertIn('StaticFiles(directory=TABLET_DIR', main)
        self.assertIn('version="36.0.0-alpha"', main)

    def test_tablet_pwa_and_responsive_layout(self):
        manifest = (ROOT / "tablet" / "manifest.webmanifest").read_text(encoding="utf-8")
        css = (ROOT / "tablet" / "tablet.css").read_text(encoding="utf-8")
        self.assertIn('"start_url": "/tablet/"', manifest)
        self.assertIn('"display": "standalone"', manifest)
        self.assertIn('@media (orientation: portrait)', css)
        self.assertIn('--deck-columns', css)


if __name__ == "__main__":
    unittest.main()
