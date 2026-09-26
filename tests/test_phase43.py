from __future__ import annotations

import unittest
from pathlib import Path

from manager_api.main import TEMPLATE_SHEETS, rows_to_dataset

BASE = Path(__file__).resolve().parents[1]


class Phase43Tests(unittest.TestCase):
    def test_release_is_phase43(self):
        import manager_release
        self.assertGreaterEqual(int(manager_release.MANAGER_RELEASE.replace("phase", "")), 43)
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"styles.css?v={manager_release.MANAGER_RELEASE}", html)
        self.assertIn(f"app.js?v={manager_release.MANAGER_RELEASE}", html)

    def test_import_template_only_contains_players(self):
        self.assertEqual(TEMPLATE_SHEETS, {
            "Jugadores": ["player_code", "first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"]
        })

    def test_spanish_player_headers_map_to_player_fields(self):
        data = rows_to_dataset("Jugadores", [["Nombre", "Apellidos", "Posición"], ["Ana", "García", "Defensa"]])
        self.assertEqual(data["scope"], "players")
        self.assertEqual(data["rows"][0]["first_name"], "Ana")
        self.assertEqual(data["rows"][0]["last_name"], "García")

    def test_delete_endpoints_and_buttons_exist(self):
        api = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        client = (BASE / "supabase_client.py").read_text(encoding="utf-8")
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        for entity in ("seasons", "competitions", "teams", "players", "matches", "members", "themes"):
            self.assertIn(f'@app.delete("/api/{entity}/', api)
        for method in ("manager_delete_season", "manager_delete_competition", "manager_delete_team",
                       "manager_delete_player", "manager_delete_match", "manager_delete_member",
                       "manager_delete_theme"):
            self.assertIn(f"def {method}", client)
        self.assertIn("data-delete", js)
        self.assertIn("deleteEntity", js)


if __name__ == "__main__":
    unittest.main()
