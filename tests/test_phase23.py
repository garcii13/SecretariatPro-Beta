from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.settings_store import AccountSettingsStore, default_settings, system_language

if "supabase" not in sys.modules:
    supabase_stub = types.ModuleType("supabase")
    supabase_stub.Client = object
    supabase_stub.create_client = lambda *_args, **_kwargs: None
    sys.modules["supabase"] = supabase_stub

from supabase_client import APP_SETTINGS_METADATA_KEY, ScoreboardSupabaseClient

ROOT = Path(__file__).resolve().parents[1]


class FakeAccount:
    user_id = "operator-1"
    user_email = "operator@example.com"


class FakeUser:
    id = "cloud-user"
    email = "cloud@example.com"
    user_metadata = {"existing": "value"}


class FakeAuth:
    def __init__(self):
        self.payload = None

    def update_user(self, payload):
        self.payload = payload
        class Response:
            user = FakeUser()
        Response.user.user_metadata = payload["data"]
        return Response()


class FakeSupabaseConnection:
    def __init__(self):
        self.auth = FakeAuth()


class Phase23SettingsTests(unittest.TestCase):
    def test_first_run_uses_supported_system_language(self):
        with patch("secretariat_core.settings_store.locale.getlocale", return_value=("de_DE", "UTF-8")):
            self.assertEqual(system_language(), "de")
            self.assertEqual(default_settings()["language"], "de")
        with patch("secretariat_core.settings_store.locale.getlocale", return_value=("fr_FR", "UTF-8")), \
             patch.dict("os.environ", {"LANG": "fr_FR.UTF-8"}, clear=True):
            self.assertEqual(system_language(), "en")

    def test_fullscreen_settings_and_no_drawer(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="view-settings"', html)
        self.assertNotIn('data-view="settings"', html)
        self.assertIn('id="settings-button"', html)
        self.assertIn('id="settings-back-button"', html)
        self.assertIn('id="settings-appearance-card"', html)
        self.assertNotIn('id="settings-drawer"', html)
        self.assertNotIn('id="drawer-scrim"', html)

    def test_ocr_coordinates_textarea_removed(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('id="ocr-regions"', html)
        self.assertNotIn('$("#ocr-regions")', js)
        self.assertIn('id="save-ocr"', html)
        self.assertNotIn('class="card ocr-config-card"', html)

    def test_app_light_mode_is_not_exported_to_overlay(self):
        app_css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        overlay_css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn('html[data-app-theme="light"]', app_css)
        self.assertNotIn('data-app-theme="light"', overlay_css)

    def test_language_and_appearance_reach_overlay(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("refreshOverlaySettings", script)
        self.assertIn("applyOverlayLanguage", script)
        self.assertIn("applyOverlayAppearance", script)
        self.assertIn('/api/settings', script)
        self.assertIn("applyOverlayLanguage(overlayLanguage)", script)

    def test_account_profile_isolated_by_user_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountSettingsStore(Path(tmp) / "accounts.json")
            one = default_settings()
            one["language"] = "en"
            two = default_settings()
            two["language"] = "es"
            store.save("one", one, "one@example.com")
            store.save("two", two, "two@example.com")
            self.assertEqual(store.load("one")["language"], "en")
            self.assertEqual(store.load("two")["language"], "es")

    def test_runtime_saves_obs_and_appearance_to_active_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.supabase = FakeAccount()
            settings = runtime.settings_store.load()
            settings["obs"]["host"] = "10.0.0.4"
            settings["appearance"]["app_theme"] = "light"
            runtime.save_current_settings(settings)
            profile = runtime.account_settings_store.load("operator-1")
            self.assertEqual(profile["obs"]["host"], "10.0.0.4")
            self.assertEqual(profile["appearance"]["app_theme"], "light")

    def test_supabase_metadata_sync_excludes_obs_password(self):
        client = ScoreboardSupabaseClient.__new__(ScoreboardSupabaseClient)
        client.user = FakeUser()
        client.client = FakeSupabaseConnection()
        settings = default_settings()
        settings["obs"]["host"] = "192.168.1.10"
        settings["obs"]["password"] = "do-not-upload"
        client.save_user_app_settings(settings)
        cloud = client.client.auth.payload["data"][APP_SETTINGS_METADATA_KEY]
        self.assertEqual(cloud["obs"]["host"], "192.168.1.10")
        self.assertNotIn("password", cloud["obs"])
        self.assertEqual(client.user_app_settings()["obs"]["host"], "192.168.1.10")

    def test_legacy_unused_overlay_palette_is_removed(self):
        settings = default_settings()
        self.assertNotIn("overlay", settings["appearance"])


class Phase23VisualTests(unittest.TestCase):
    def test_titles_are_not_rotated(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".production-compact-header .card-kicker", css)
        self.assertIn("transform: none !important", css)
        self.assertNotIn('.text-button, .eyebrow, .card-kicker, \n.icon-button:hover', css)

    def test_bottom_bar_has_continuous_sections_and_responsive_match_drawer(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("PHASE 26 — CANONICAL CONTINUOUS GOAL BOTTOM BAR", css)
        self.assertIn("border-radius: clamp(14px, 1.25vw, 20px)", css)
        self.assertIn("font-size: clamp(32px, 3vw, 48px)", css)
        self.assertIn("grid-template-columns: clamp(138px, 14vw, 174px)", css)
        self.assertNotIn("margin-left: -18px", css)
        self.assertEqual(css.count("\n#bottom-bar {"), 1)

    def test_phase23_cache_and_version(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("app.js?v=phase36", html)
        self.assertIn("styles.css?v=phase55", html)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("secretariatpro-phase36-v1", sw)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
