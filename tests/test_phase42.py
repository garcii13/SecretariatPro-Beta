from __future__ import annotations

import unittest
from pathlib import Path

from manager_api.main import rows_to_dataset

BASE = Path(__file__).resolve().parents[1]


class Phase42Tests(unittest.TestCase):
    def test_login_layer_remains_fixed_and_centered(self):
        css = (BASE / "manager_app" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".login-layer {\n  position: fixed;", css)
        self.assertIn("place-items: center;", css)
        self.assertNotIn(".shell, .login-layer { position: relative", css)

    def test_members_title_is_only_users(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-view="members"><span class="nav-icon">◎</span>Usuarios</button>', html)
        self.assertIn('<h1>Usuarios</h1>', html)
        self.assertNotIn('>Usuarios y realizadores</button>', html)
        self.assertNotIn('<h1>Usuarios y realizadores</h1>', html)

    def test_confirmed_import_ui_and_endpoint_exist(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        api = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        client = (BASE / "supabase_client.py").read_text(encoding="utf-8")
        self.assertIn('id="confirm-import"', html)
        self.assertIn('id="import-report"', html)
        self.assertIn('/api/import/scoped/${analysis.kind}/commit', js)
        self.assertIn('@app.post("/api/import/commit")', api)
        self.assertIn('def manager_import_rows', client)

    def test_import_parser_recognizes_team_rows(self):
        data = rows_to_dataset(
            "Equipos",
            [["team_code", "name", "short_name"], ["MAD", "Madrid", "MAD"]],
        )
        self.assertEqual(data["scope"], "teams")
        self.assertEqual(data["row_count"], 1)
        self.assertEqual(data["rows"][0]["team_code"], "MAD")

    def test_release_is_phase42(self):
        release = (BASE / "manager_release.py").read_text(encoding="utf-8")
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('MANAGER_RELEASE = "phase42"', release)
        self.assertIn('styles.css?v=phase42', html)
        self.assertIn('app.js?v=phase42', html)


if __name__ == "__main__":
    unittest.main()
