from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Phase54RegressionTests(unittest.TestCase):
    def test_status_stack_is_rebuilt(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "script.js").read_text(encoding="utf-8")
        html = (ROOT / "overlay.html").read_text(encoding="utf-8")
        self.assertIn("PHASE 57 — ISOLATED SCOREBOARD STATUS COMPONENT", css)
        self.assertIn("sp-status-item--bottom", css)
        self.assertIn("animateStatusEntry", js)
        self.assertIn("animateStatusExit", js)
        self.assertIn("sp-team-status-stack", html)
        self.assertNotIn('id="team1-powerplay"', html)

    def test_manager_sidebar_and_system_theme(self):
        html = (ROOT / "manager_app" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "manager_app" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "manager_app" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="sidebar-toggle"', html)
        self.assertIn('id="sidebar-scrim"', html)
        self.assertIn('<option value="system">Sistema</option>', html)
        self.assertIn("sidebar-collapsed", css)
        self.assertIn("sidebar-open", css)
        self.assertIn("setSidebarState", js)
        self.assertIn("resolveThemePreference", js)

    def test_live_obs_window_picker_and_system_theme(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        settings = (ROOT / "secretariat_core" / "settings_store.py").read_text(encoding="utf-8")
        self.assertIn('id="settings-projector-window"', html)
        self.assertIn('id="refresh-obs-windows"', html)
        self.assertIn('<option value="system">Sistema</option>', html)
        self.assertIn('/api/obs/projector-windows', js)
        self.assertIn("refreshOBSProjectorWindows", js)
        self.assertIn("resolveAppTheme", js)
        self.assertIn('{"dark", "light", "system"}', settings)

if __name__ == "__main__":
    unittest.main()
