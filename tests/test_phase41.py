from __future__ import annotations

import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class Phase41Tests(unittest.TestCase):
    def test_competition_uses_same_uploaded_logo_service_as_teams(self):
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        self.assertIn('label: "Logo de la liga", type: "logo", assetKind: "league-logos"', js)
        self.assertIn("competitionLogoMarkup", js)
        self.assertIn("/api/assets/upload", js)

    def test_legacy_local_logo_service_is_removed(self):
        api = (BASE / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        state = (BASE / "secretariat_core" / "state_store.py").read_text(encoding="utf-8")
        self.assertNotIn('app.mount("/logos"', api)
        self.assertNotIn('logos/el_valle', state)
        self.assertNotIn('logos/leganes', state)
        self.assertNotIn('logos/liga_oro', state)
        self.assertFalse((BASE / "logos").exists())

    def test_bundled_state_has_no_local_logo_paths(self):
        raw = (BASE / "data.json").read_text(encoding="utf-8")
        self.assertNotIn('"logos/', raw)
        json.loads(raw)

    def test_manager_uses_application_visual_language_without_changing_shell(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        css = (BASE / "manager_app" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('class="shell"', html)
        self.assertIn('class="sidebar"', html)
        self.assertIn('PHASE 41 — SecretariatPro application visual language', css)
        for token in ('--bg: #090c11', '--accent: #4b7cff', 'backdrop-filter: blur(22px)', '.ambient-one'):
            self.assertIn(token, css)

    def test_release_is_phase41(self):
        release = (BASE / "manager_release.py").read_text(encoding="utf-8")
        launcher = (BASE / "run_manager.py").read_text(encoding="utf-8")
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('MANAGER_RELEASE = "phase41"', release)
        self.assertIn('MANAGER_BUILD = MANAGER_RELEASE', launcher)
        self.assertIn('styles.css?v=phase41', html)
        self.assertIn('app.js?v=phase41', html)


if __name__ == "__main__":
    unittest.main()
