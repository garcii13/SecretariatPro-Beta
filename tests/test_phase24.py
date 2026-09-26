from __future__ import annotations

import unittest
from pathlib import Path

from secretariat_core.settings_store import default_settings, normalize_settings

ROOT = Path(__file__).resolve().parents[1]


class Phase24SettingsAndOCRTests(unittest.TestCase):
    def test_settings_open_from_gear_not_main_navigation(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="settings-button"', html)
        self.assertIn('id="settings-back-button"', html)
        self.assertNotIn('data-view="settings"', html)
        self.assertIn('switchView("settings")', js)

    def test_colour_customisation_is_overlay_only(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        settings = default_settings()
        self.assertIn("Colores del overlay", html)
        self.assertNotIn('data-appearance-path="app.', html)
        self.assertNotIn('data-appearance-path="deck.', html)
        self.assertNotIn("app", settings["appearance"])
        self.assertNotIn("deck", settings["appearance"])
        self.assertIn("app_theme", settings["appearance"])

    def test_legacy_app_and_deck_colours_are_removed(self):
        normalized = normalize_settings({
            "appearance": {
                "app_theme": "light",
                "app": {"primary": "#ff0000"},
                "deck": {"key": "#00ff00"},
                "scoreboard": {"background": "#101010"},
            }
        })
        self.assertEqual(normalized["appearance"]["app_theme"], "light")
        self.assertNotIn("app", normalized["appearance"])
        self.assertNotIn("deck", normalized["appearance"])
        self.assertEqual(normalized["appearance"]["scoreboard"]["background"], "#101010")

    def test_ocr_save_is_below_source_and_no_empty_config_card(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        window_index = html.index('id="ocr-window"')
        save_index = html.index('id="save-ocr"')
        toolbar_index = html.index('class="ocr-editor-toolbar"')
        self.assertLess(window_index, save_index)
        self.assertLess(save_index, toolbar_index)
        self.assertNotIn('class="card ocr-config-card"', html)
        self.assertIn('class="ocr-source-settings"', html)


class Phase24OverlayTests(unittest.TestCase):
    def test_overlay_palette_is_injected_after_cached_css(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn('secretariat-overlay-palette', script)
        self.assertIn('document.head.appendChild(style)', script)
        self.assertIn('#bottom-bar .bottom-event-copy', script)
        self.assertIn('.scoreboard .team1-name-box', script)
        self.assertIn('setInterval(refreshOverlaySettings, 1200)', script)

    def test_bottom_bar_is_one_continuous_outer_rounded_block(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        canonical = css.split("PHASE 26 — CANONICAL CONTINUOUS GOAL BOTTOM BAR", 1)[1].split("Phase 26 account overlay palette hooks", 1)[0]
        self.assertEqual(css.count("\n#bottom-bar {"), 1)
        self.assertIn("border-radius: clamp(14px, 1.25vw, 20px)", canonical)
        self.assertIn("overflow: hidden", canonical)
        self.assertIn("grid-template-columns: 11px minmax(0,1fr)", canonical)
        self.assertNotIn("clip-path: polygon", canonical)
        self.assertNotIn("margin-left: -18px", canonical)
        self.assertNotIn("margin: 0 0 0 -18px", canonical)
        self.assertIn("font-size: clamp(32px, 3vw, 48px)", canonical)

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
