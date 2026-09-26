from __future__ import annotations

import unittest
from pathlib import Path

from manager_api.main import player_rows_to_dataset

BASE = Path(__file__).resolve().parents[1]


class Phase44Tests(unittest.TestCase):
    def test_release_is_phase44(self):
        import manager_release
        self.assertGreaterEqual(int(manager_release.MANAGER_RELEASE.replace("phase", "")), 44)
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"styles.css?v={manager_release.MANAGER_RELEASE}", html)
        self.assertIn(f"app.js?v={manager_release.MANAGER_RELEASE}", html)

    def test_team_columns_are_ignored_but_player_is_extracted(self):
        data = player_rows_to_dataset(
            "Equipos",
            [["Equipo", "Nombre", "Apellidos", "Dorsal", "Competición", "Posición"],
             ["Madrid Floorball", "Ana", "García", 17, "Liga Oro", "Defensa"]],
        )
        self.assertEqual(data["scope"], "players")
        self.assertEqual(data["row_count"], 1)
        self.assertEqual(data["rows"], [{
            "first_name": "Ana", "last_name": "García", "position": "Defensa"
        }])
        self.assertIn("Equipo", data["ignored_headers"])
        self.assertIn("Dorsal", data["ignored_headers"])
        self.assertIn("Competición", data["ignored_headers"])

    def test_sheet_with_only_team_data_is_not_importable(self):
        data = player_rows_to_dataset(
            "Equipos",
            [["Nombre equipo", "Nombre corto", "Color"], ["Madrid", "MAD", "#000000"]],
        )
        self.assertIsNone(data["scope"])
        self.assertEqual(data["row_count"], 0)

    def test_commit_has_defence_in_depth_player_only_filter(self):
        client = (BASE / "supabase_client.py").read_text(encoding="utf-8")
        self.assertIn('if scope != "players":', client)
        self.assertIn('allowed_player_fields = {"player_code", "first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"}', client)


if __name__ == "__main__":
    unittest.main()
