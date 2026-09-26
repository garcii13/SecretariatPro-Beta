from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


class Phase26Tests(unittest.TestCase):
    def test_bottom_bar_alignment_and_team_glow(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("radial-gradient(circle at 7% 50%", css)
        self.assertIn("--bottom-team-color", css)
        self.assertIn("place-content: center", css)
        self.assertIn("#bottom-bar.no-assistant .bottom-scorer-row", css)
        self.assertIn("align-self: center", css)

    def test_light_theme_and_native_select_options(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('html[data-app-theme="light"] {', css)
        self.assertIn("--surface:#ffffff", css)
        self.assertIn('html[data-app-theme="light"] select option', css)
        self.assertIn("background:#ffffff", css)

    def test_login_text_is_larger(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".login-card .modal-brand strong { font-size:23px", css)
        self.assertIn(".login-card .field input", css)
        self.assertIn("font-size:16px", css)

    def test_tablet_qr_ui_and_api(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn('id="tablet-access-qr"', html)
        self.assertIn('id="tablet-access-url"', html)
        self.assertIn("refreshTabletAccess", js)
        self.assertIn("qrcode>=", req.lower())

    def test_tablet_endpoints_return_url_and_svg(self):
        from secretariat_api.main import app, runtime
        from unittest.mock import patch

        with patch.object(runtime, "production_access_allowed", return_value=True), TestClient(app, client=("127.0.0.1", 50000)) as client:
            response = client.get("/api/tablet-access")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["url"].startswith("http://"))
            self.assertIn("#pair=", payload["url"])
            self.assertTrue(payload["qr"].startswith("/api/tablet-qr.svg?code="))

            qr = client.get(payload["qr"])
            self.assertEqual(qr.status_code, 200)
            self.assertIn("image/svg+xml", qr.headers.get("content-type", ""))
            self.assertIn(b"<svg", qr.content)

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
