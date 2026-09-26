from __future__ import annotations

import tempfile
import time
import unittest
from urllib.parse import urlsplit, parse_qs
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from secretariat_api.preflight import build_preflight
from secretariat_api.tablet_access import TabletAccess
from secretariat_core.services.graphics_queue import add_cue, cue_preview, remove_cue, take_cue
from secretariat_core.services.overlay import panel_visible
from secretariat_api.runtime import ApplicationRuntime


class TabletPairingTests(unittest.TestCase):
    def test_invite_is_one_use_scope_bound_and_revocable(self):
        access = TabletAccess()
        code = access.invite("user:workspace")
        with self.assertRaises(PermissionError):
            access.pair(code, "other:workspace")
        session_id, token = access.pair(code, "user:workspace")
        with self.assertRaises(PermissionError):
            access.pair(code, "user:workspace")
        self.assertEqual(access.authenticate(token, "user:workspace"), session_id)
        self.assertIsNone(access.authenticate(token, "other:workspace"))
        self.assertTrue(access.revoke(session_id))
        self.assertIsNone(access.authenticate(token, "user:workspace"))

    def test_remote_cannot_call_admin_api_even_after_pairing(self):
        from secretariat_api.main import app, runtime, tablet_access_control
        tablet_access_control.revoke_all()
        with patch.object(runtime, "production_access_allowed", return_value=True), \
             patch.object(runtime, "snapshot", return_value={"state": {}, "scores": {}, "online": {}, "settings": {}}), \
             TestClient(app, client=("127.0.0.1", 50100)) as desktop, \
             TestClient(app, client=("192.168.1.20", 50101)) as tablet:
            self.assertEqual(tablet.get("/api/state").status_code, 401)
            self.assertEqual(tablet.get("/api/settings").status_code, 401)
            invite = desktop.get("/api/tablet-access").json()
            code = parse_qs(urlsplit(invite["url"]).fragment)["pair"][0]
            self.assertEqual(tablet.post("/api/tablet/pair", json={"code": code}).status_code, 200)
            self.assertEqual(tablet.get("/api/state").status_code, 200)
            self.assertEqual(tablet.get("/api/settings").status_code, 403)
            self.assertEqual(tablet.post("/api/obs/connect", json={}).status_code, 403)
            session = tablet.get("/api/tablet/session").json()
            desktop.delete(f"/api/tablet/sessions/{session['id']}")
            self.assertEqual(tablet.get("/api/state").status_code, 401)
        tablet_access_control.revoke_all()


class ClipboardTests(unittest.TestCase):
    def test_local_clipboard_endpoint_uses_host_clipboard_and_rejects_remote(self):
        from secretariat_api.main import app, runtime
        with patch.object(runtime, "production_access_allowed", return_value=True), \
             patch("secretariat_api.main.copy_text") as native_copy, \
             TestClient(app, client=("127.0.0.1", 50110)) as desktop, \
             TestClient(app, client=("192.168.1.21", 50111)) as tablet:
            response = desktop.post(
                "/api/system/clipboard",
                json={"text": "http://127.0.0.1:8765/overlay.html"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["copied"])
            native_copy.assert_called_once_with("http://127.0.0.1:8765/overlay.html")
            self.assertIn(tablet.post("/api/system/clipboard", json={"text": "blocked"}).status_code, {401, 403})


class GraphicsQueueTests(unittest.TestCase):
    def test_preview_is_off_air_and_take_is_fifo_and_match_bound(self):
        state = {"animation": {"status": "hide"}, "scoreboard": {"status": "hide"}}
        first = add_cue(state, "scoreboard", "match-a")
        second = add_cue(state, "prematch", "match-a")
        self.assertFalse(panel_visible(state, "scoreboard"))
        preview = cue_preview(state, first["id"], "match-a")
        self.assertTrue(panel_visible(preview, "scoreboard"))
        self.assertFalse(panel_visible(state, "scoreboard"))
        with self.assertRaises(ValueError):
            take_cue(state, second["id"], "match-a")
        with self.assertRaises(ValueError):
            take_cue(state, first["id"], "match-b")
        take_cue(state, first["id"], "match-a")
        self.assertTrue(panel_visible(state, "scoreboard"))
        self.assertEqual(state["graphics_queue"][0]["id"], second["id"])
        self.assertTrue(remove_cue(state, second["id"]))


class PreflightTests(unittest.TestCase):
    def test_stale_ocr_blocks_ready_but_manual_fallback_does_not(self):
        now = time.time()
        snapshot = {
            "online": {"access": {"production_allowed": True}, "match": {"id": "m", "label": "Partido"}},
            "state": {"team1": {"name": "A", "logo": "https://a"}, "team2": {"name": "B", "logo": "https://b"}},
            "obs": {"connected": True, "program": "Directo"},
            "ocr": {"source_id": "camera:0"}, "ocr_runtime": {"running": True, "last_reading": now - 20},
            "settings": {"obs": {"projector_window": "OBS"}, "appearance_policy": {"inherited": True}},
            "score_control": {"mode": "ocr"},
        }
        report = build_preflight(snapshot, tablet_count=1, now=now)
        self.assertFalse(report["ready"])
        self.assertEqual(next(x for x in report["checks"] if x["key"] == "reading")["level"], "fail")
        snapshot["score_control"]["mode"] = "manual"
        self.assertTrue(build_preflight(snapshot, tablet_count=1, now=now)["ready"])

    def test_obs_and_tablet_are_optional(self):
        now = time.time()
        snapshot = {
            "online": {"access": {"production_allowed": True}, "match": {"id": "m", "label": "Partido"}},
            "state": {"team1": {"name": "A", "logo": ""}, "team2": {"name": "B", "logo": ""}},
            "obs": {"connected": False},
            "ocr": {},
            "ocr_runtime": {},
            "settings": {"obs": {}, "appearance_policy": {"inherited": False}},
            "score_control": {"mode": "manual"},
        }
        report = build_preflight(snapshot, tablet_count=0, now=now)
        self.assertTrue(report["ready"])
        self.assertEqual(report["counts"]["blocking"], 0)
        for key in ("obs", "tablet"):
            check = next(item for item in report["checks"] if item["key"] == key)
            self.assertEqual(check["level"], "warn")
            self.assertFalse(check["required"])


class LiveThemeTests(unittest.TestCase):
    def test_new_publication_replaces_identity_without_match_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            client = Mock(user_id="user", user_email="u@example.test")
            runtime.supabase = client
            runtime.subscription_access = {"production_allowed": True}
            runtime.active_competition = {"id": "competition-a"}
            theme = {"id": "theme-2", "config": {"appearance": {"elements": {"scoreboard": {"scale": .75, "font": "Georgia"}}}}}
            client.published_visual_theme.return_value = theme
            self.assertTrue(runtime.refresh_published_theme())
            self.assertEqual(runtime.safe_settings()["appearance"]["elements"]["scoreboard"], {"scale": .75, "font": "Georgia"})
            self.assertFalse(runtime.refresh_published_theme())
            client.published_visual_theme.side_effect = RuntimeError("offline")
            self.assertFalse(runtime.refresh_published_theme())
            self.assertEqual(runtime.published_theme["id"], "theme-2")


if __name__ == "__main__":
    unittest.main()
