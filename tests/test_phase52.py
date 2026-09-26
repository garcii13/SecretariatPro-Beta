from __future__ import annotations

import unittest
from pathlib import Path

from secretariat_core.services.powerplay import start_powerplay, burn_powerplay_block, advance_powerplay

ROOT = Path(__file__).resolve().parents[1]


class Phase52BetaRCTests(unittest.TestCase):
    def test_required_migration_contains_admin_matches_and_sport_mode(self):
        sql = (ROOT / "SUPABASE_PHASE52_BETA_RC.sql").read_text(encoding="utf-8")
        self.assertIn("broadcast_enabled", sql)
        self.assertIn("sport_mode", sql)
        self.assertIn("handball", sql)
        self.assertIn("floorball", sql)

    def test_admin_matches_are_hidden_from_live(self):
        client = (ROOT / "supabase_client.py").read_text(encoding="utf-8")
        manager = (ROOT / "manager_app" / "app.js").read_text(encoding="utf-8")
        self.assertIn('.eq("broadcast_enabled", True)', client)
        self.assertIn("Solo registro administrativo", manager)
        self.assertIn("events/import-preview", manager)
        self.assertIn("events/finalize", manager)

    def test_event_excel_template_and_direct_download_exist(self):
        api = (ROOT / "manager_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('ws.title = "Eventos"', api)
        for column in ("time", "team", "event_type", "player_number", "assistant_number", "penalty_type", "notes"):
            self.assertIn(column, api)
        self.assertIn('events/template/download', api)
        self.assertIn('manager_finalize_match_act', api)

    def test_live_and_manager_logos_are_distinct_and_present(self):
        live = (ROOT / "webapp" / "sp_logo.png").read_bytes()
        manager = (ROOT / "manager_app" / "sp_logo.png").read_bytes()
        self.assertGreater(len(live), 1000)
        self.assertGreater(len(manager), 1000)
        self.assertNotEqual(live, manager)
        self.assertTrue((ROOT / "assets" / "secretariatpro.ico").exists())
        self.assertTrue((ROOT / "assets" / "manager_icon.ico").exists())

    def test_manager_has_live_visual_tokens_and_responsive_navigation(self):
        css = (ROOT / "manager_app" / "styles.css").read_text(encoding="utf-8")
        for token in ("#090c11", "#4b7cff", "#36d5cc"):
            self.assertIn(token, css)
        self.assertIn("PHASE 52 — Beta RC: Live visual parity + responsive Manager", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("@media (max-width: 1180px)", css)
        self.assertIn("@media (max-width: 680px)", css)

    def test_ocr_accepts_windows_and_cameras(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        worker = (ROOT / "ocr_worker.py").read_text(encoding="utf-8")
        ui = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('/api/ocr/sources', api)
        self.assertIn('source_type == "camera"', api)
        self.assertIn("CameraStream", worker)
        self.assertIn('row.source_type === "camera"', ui)
        self.assertTrue((ROOT / "video_source.py").exists())

    def test_empty_net_controls_and_overlay_exist(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        js = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn('/api/empty-net/{team_key}/toggle', api)
        self.assertIn('data-empty-net="team1"', html)
        self.assertIn('data-empty-net="team2"', html)
        self.assertIn("sp-team-status-stack", overlay)
        self.assertIn("EMPTY NET", js)
        self.assertIn("renderTeamStatusStack", js)

    def test_two_simultaneous_penalties_promote_second(self):
        info = {}
        start_powerplay(info, current_seconds=10, player_id="p1", player_number=5)
        start_powerplay(info, current_seconds=20, player_id="p2", player_number=9)
        self.assertEqual(info["active_count"], 2)
        self.assertEqual(info["player_number"], "5")
        self.assertEqual(burn_powerplay_block(info, 30), "ended")
        self.assertEqual(info["active_count"], 1)
        self.assertEqual(info["player_number"], "9")
        advance_powerplay(info, 140)
        self.assertFalse(info["status"])

    def test_handball_mode_is_owner_only_and_has_seven_slots(self):
        manager_api = (ROOT / "manager_api" / "main.py").read_text(encoding="utf-8")
        manager_js = (ROOT / "manager_app" / "app.js").read_text(encoding="utf-8")
        live_js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('can_set_sport_mode', manager_api)
        self.assertIn('workspace.role !== "owner"', manager_js)
        for slot in ("left_wing", "pivot", "right_wing", "left_back", "center_back", "right_back", "goalkeeper"):
            self.assertIn(slot, live_js)
        self.assertIn('runtime.sport_mode() != "handball"', api)

    def test_release_metadata_is_beta_rc(self):
        import manager_release
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        runtime = (ROOT / "secretariat_api" / "runtime.py").read_text(encoding="utf-8")
        self.assertEqual(manager_release.MANAGER_RELEASE, "phase56")
        self.assertIn('API_VERSION = "57.0.0-beta-rc"', main)
        self.assertIn('"app_release": "57.0.0-beta-rc"', runtime)


if __name__ == "__main__":
    unittest.main()
