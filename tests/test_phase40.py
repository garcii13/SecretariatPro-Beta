from pathlib import Path
import unittest
BASE=Path(__file__).resolve().parents[1]
class Phase40Tests(unittest.TestCase):
    def test_match_edit_uses_matches_cache(self):
        js=(BASE/'manager_app/app.js').read_text(encoding='utf-8')
        self.assertIn('type === "match" ? "matches"', js)
    def test_team_roster_hierarchy(self):
        js=(BASE/'manager_app/app.js').read_text(encoding='utf-8')
        for token in ('roster-browser','data-open-team-roster','team-create-roster','roster-members-panel'):
            self.assertIn(token,js)
    def test_multiple_personalizations(self):
        html=(BASE/'manager_app/index.html').read_text(encoding='utf-8')
        js=(BASE/'manager_app/app.js').read_text(encoding='utf-8')
        self.assertIn('id="identity-new"',html)
        self.assertIn('Nueva personalización',js)

    def test_launcher_and_api_share_release_metadata(self):
        release=(BASE/'manager_release.py').read_text(encoding='utf-8')
        launcher=(BASE/'run_manager.py').read_text(encoding='utf-8')
        api=(BASE/'manager_api/main.py').read_text(encoding='utf-8')
        self.assertIn('MANAGER_RELEASE = "phase40"', release)
        self.assertIn('MANAGER_BUILD = MANAGER_RELEASE', launcher)
        self.assertIn('RELEASE_ID = MANAGER_RELEASE', api)

    def test_debug_launchers_are_included(self):
        self.assertTrue((BASE/'INICIAR_MANAGER_DEBUG.bat').exists())
        self.assertTrue((BASE/'INICIAR_MANAGER_DEBUG.command').exists())
    def test_logo_fallback(self):
        js=(BASE/'manager_app/app.js').read_text(encoding='utf-8')
        self.assertIn('normalizedLogoUrl',js)
        self.assertIn('onerror=',js)
if __name__=='__main__': unittest.main()
