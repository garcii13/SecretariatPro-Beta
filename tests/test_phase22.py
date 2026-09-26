from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase22NativeDesktopTests(unittest.TestCase):
    def test_launcher_uses_native_resizable_window(self) -> None:
        source = (ROOT / "run_app.py").read_text(encoding="utf-8")
        self.assertIn("frameless=False", source)
        self.assertIn("resizable=True", source)
        self.assertIn("maximized=not args.windowed", source)
        self.assertNotIn("class DesktopWindowAPI", source)
        self.assertNotIn("window.expose(", source)

    def test_custom_titlebar_and_resize_grips_are_removed(self) -> None:
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn("desktop-titlebar", html)
        self.assertNotIn("desktop-resize-handle", html)
        self.assertNotIn("bindDesktopWindowControls", js)
        self.assertNotIn("desktop-resize-handle", css)

    def test_app_icon_is_wired_to_launcher_and_build(self) -> None:
        launcher = (ROOT / "run_app.py").read_text(encoding="utf-8")
        spec = (ROOT / "SecretariatPro_App.spec").read_text(encoding="utf-8")
        self.assertTrue((ROOT / "assets" / "secretariatpro.ico").exists())
        self.assertTrue((ROOT / "assets" / "secretariatpro.png").exists())
        self.assertIn("ICON_ICO", launcher)
        self.assertIn('icon=str(icon_path)', spec)


class Phase22BottomBarTests(unittest.TestCase):
    def test_team_accent_and_logo_share_one_gapless_grid(self) -> None:
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: 11px minmax(0,1fr)", css)
        self.assertIn("column-gap: 0", css)
        self.assertIn("grid-column: 1", css)
        self.assertIn("grid-column: 2", css)
        self.assertIn("background: var(--bottom-team-color)", css)

    def test_only_one_bottom_bar_implementation_remains(self) -> None:
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"(?m)^#bottom-bar\s*\{", css)), 1)
        self.assertNotIn("Phase 17 overlay bottom-bar fixes", css)
        self.assertNotIn("Phase 20 — CANONICAL RESPONSIVE BEVELLED GOAL BOTTOM BAR", css)


class Phase22CleanupAndPerformanceTests(unittest.TestCase):
    def test_obsolete_desktop_gui_and_old_phase_docs_are_removed(self) -> None:
        self.assertFalse((ROOT / "scoreboard_gui.py").exists())
        old_readmes = [path for path in ROOT.glob("PHASE_[0-9]*_README.md") if path.name != "PHASE_31_README.md"]
        self.assertEqual(old_readmes, [])

    def test_legacy_hidden_pp_controls_are_removed(self) -> None:
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn("legacy-production-pp-controls", html)
        self.assertNotIn("legacy-production-pp-controls", css)

    def test_polling_is_adaptive_and_hidden_preview_is_suspended(self) -> None:
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('document.visibilityState === "visible" ? 400 : 1200', js)
        self.assertIn('activateProgramMonitor("")', js)
        self.assertIn('document.addEventListener("visibilitychange", handleDocumentVisibility)', js)

    def test_phase22_cache_and_api_version(self) -> None:
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
