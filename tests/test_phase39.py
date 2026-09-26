from __future__ import annotations

import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class Phase39ManagerTests(unittest.TestCase):
    def test_teams_and_players_are_independent_views(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-view="teams"', html)
        self.assertIn('data-view="players"', html)
        self.assertIn('id="view-teams"', html)
        self.assertIn('id="view-players"', html)
        self.assertNotIn("Equipos y jugadores", html)

    def test_roster_crud_is_exposed_end_to_end(self):
        api = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        client = (BASE / "supabase_client.py").read_text(encoding="utf-8")
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        for endpoint in (
            '/api/teams/{team_id}/rosters', '/api/players/{player_id}/rosters',
            '/api/rosters', '/api/rosters/{roster_id}', '/api/rosters/with-player',
        ):
            self.assertIn(endpoint, api)
        for method in (
            "manager_list_team_rosters", "manager_list_player_rosters", "manager_create_roster",
            "manager_update_roster", "manager_remove_roster", "manager_create_player_and_roster",
        ):
            self.assertIn(f"def {method}", client)
        self.assertIn("validateRosterClient", js)

    def test_team_logos_accept_urls_and_local_uploads(self):
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        api = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('type: "logo"', js)
        self.assertIn('type="text"', js)
        self.assertIn("data-logo-preview", js)
        self.assertIn('/api/assets/upload', api)
        self.assertIn("upload_workspace_asset", (BASE / "supabase_client.py").read_text(encoding="utf-8"))

    def test_visual_identity_matches_secretariat_palette(self):
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        runtime = (BASE / "secretariat_api" / "runtime.py").read_text(encoding="utf-8")
        for name in (
            "background", "name_box", "text", "body", "middle", "secondary_text",
            "surface", "accent", "panels", "bottom_bar", "scoreboard",
        ):
            self.assertIn(name, js)
        self.assertIn("published_visual_theme", runtime)
        self.assertIn("appearance_policy", runtime)
        self.assertIn("_enforce_locked_visual_theme", runtime)

    def test_account_panel_reuses_profile_avatar_and_password_capabilities(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        api = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        for element_id in (
            "profile-avatar", "account-avatar", "account-display-name", "account-avatar-file",
            "account-password", "account-password-confirm",
        ):
            self.assertIn(f'id="{element_id}"', html)
        for endpoint in ('/api/account/profile', '/api/account/password', '/api/account/avatar'):
            self.assertIn(endpoint, api)

    def test_phase39_sql_guards_duplicate_players_and_numbers(self):
        sql = (BASE / "SUPABASE_PHASE39_ROSTERS_ASSETS.sql").read_text(encoding="utf-8")
        self.assertIn("rosters_active_player_unique", sql)
        self.assertIn("rosters_active_number_unique", sql)
        self.assertIn("workspace-assets", sql)
        self.assertIn("10485760", sql)
        self.assertIn("sp_asset_workspace_id", sql)

    def test_phase39_release_markers_remain_compatible(self):
        manager = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        local_api = (BASE / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('RELEASE_ID = "phase39"', manager)
        self.assertIn('APP_VERSION = "3.0.0-alpha"', manager)
        self.assertIn('API_VERSION = "39.0.0-alpha"', local_api)


if __name__ == "__main__":
    unittest.main()
