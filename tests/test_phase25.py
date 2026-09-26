from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.settings_store import normalize_settings

ROOT = Path(__file__).resolve().parents[1]


class Phase25OverlaySettingsTests(unittest.TestCase):
    def test_overlay_colours_and_language_are_mirrored_into_data_state(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            settings = runtime.settings_store.load()
            settings["language"] = "de"
            settings["appearance"]["scoreboard"]["background"] = "#112233"
            settings["appearance"]["bottom_bar"]["body"] = "#223344"
            runtime.published_theme = {"config": {"appearance": settings["appearance"]}, "locked": True}
            runtime.save_current_settings(settings)
            payload = runtime.read_state()["overlay_settings"]
            self.assertEqual(payload["language"], "de")
            self.assertEqual(payload["appearance"]["scoreboard"]["background"], "#112233")
            self.assertEqual(payload["appearance"]["bottom_bar"]["body"], "#223344")

    def test_overlay_applies_data_json_settings_as_primary_channel(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("data?.overlay_settings", script)
        self.assertIn("applyOverlayAppearance(data.overlay_settings)", script)
        self.assertIn("secretariat-overlay-palette", script)
        self.assertIn("overlayAppearanceSignature", script)


class Phase25LanguageTests(unittest.TestCase):
    def test_all_six_languages_are_accepted_by_settings(self):
        for language in ("es", "en", "sv", "cs", "fi", "de"):
            with self.subTest(language=language):
                self.assertEqual(normalize_settings({"language": language})["language"], language)

    def test_language_selector_contains_new_languages(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        for value in ("sv", "cs", "fi", "de"):
            self.assertIn(f'<option value="{value}">', html)

    def test_app_and_overlay_have_language_packs(self):
        app_js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        overlay_js = (ROOT / "script.js").read_text(encoding="utf-8")
        for language in ("sv", "cs", "fi", "de"):
            self.assertIn(f"{language}:", app_js)
            self.assertIn(f"{language}:", overlay_js)
        self.assertIn('["es", "en", "sv", "cs", "fi", "de"]', app_js)
        self.assertIn('["es", "en", "sv", "cs", "fi", "de"]', overlay_js)


class Phase25BottomBarTests(unittest.TestCase):
    def test_scorer_only_mode_is_vertically_centred(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn('bottomBar.classList.toggle("no-assistant", !hasAssistant)', script)
        self.assertIn("#bottom-bar.no-assistant .bottom-event-copy", css)
        self.assertIn("align-items: center !important", css)
        self.assertIn("#bottom-bar.no-assistant .bottom-scorer-row", css)

    def test_phase36_cache_and_version(self):
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
