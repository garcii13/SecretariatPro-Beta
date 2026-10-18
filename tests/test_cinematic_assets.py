from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from secretariat_api import main

ROOT = Path(__file__).resolve().parents[1]


class CinematicAssetsTests(unittest.TestCase):
    def test_installed_overlay_serves_the_exact_motion_assets(self):
        client = TestClient(main.app, client=("127.0.0.1", 50100))
        for name, mime in (("overlay_motion.js", "application/javascript"), ("overlay_cinematic.css", "text/css")):
            response = client.get("/" + name)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers["content-type"].startswith(mime))
            self.assertEqual(response.content, (ROOT / name).read_bytes())
            self.assertIn(f'(str(ROOT / "{name}"), ".")', (ROOT / "SecretariatPro_App.spec").read_text(encoding="utf-8"))

    def test_controller_loads_before_the_existing_overlay_and_styles_after_base(self):
        html = (ROOT / "overlay.html").read_text(encoding="utf-8")
        self.assertLess(html.index('href="styles.css?'), html.index('href="overlay_cinematic.css?'))
        self.assertLess(html.index('src="overlay_motion.js?'), html.index('src="script.js?'))
