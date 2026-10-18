"""Installed assets, fallback route and source/build agreement for Broadcast Studio."""
import hashlib
import json
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from secretariat_api import main

ROOT = Path(__file__).resolve().parents[1]


class StudioAssetsTests(unittest.TestCase):
    def test_current_obs_url_uses_studio_and_reference_remains_available(self):
        client = TestClient(main.app, client=("127.0.0.1", 50100))
        response = client.get("/overlay.html?cue=example")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, (ROOT / "overlay-studio.html").read_bytes())
        self.assertEqual(client.get("/overlay-studio.html").content, response.content)
        self.assertEqual(client.get("/overlay.html?renderer=legacy&cue=example").content,
                         (ROOT / "overlay.html").read_bytes())
        self.assertEqual(response.headers["cache-control"], "no-cache")

    def test_bundles_are_local_served_and_included_in_installed_application(self):
        client = TestClient(main.app, client=("127.0.0.1", 50100))
        spec = (ROOT / "SecretariatPro_App.spec").read_text()
        self.assertIn('(str(ROOT / "overlay_studio"), "overlay_studio")', spec)
        self.assertIn('(str(ROOT / "overlay-studio.html"), ".")', spec)
        for name, mime in (("studio.js", "application/javascript"), ("studio.css", "text/css"), ("manifest.json", "application/json")):
            response = client.get(f"/overlay_studio/{name}")
            self.assertEqual(response.status_code, 200)
            # Starlette may use text/javascript on some supported platforms.
            if name == "studio.js":
                self.assertIn(response.headers["content-type"].split(";")[0], (mime, "text/javascript"))
            else:
                self.assertTrue(response.headers["content-type"].startswith(mime))
            self.assertEqual(response.content, (ROOT / "overlay_studio" / name).read_bytes())
        self.assertNotIn('src="https://', (ROOT / "overlay-studio.html").read_text())

    def test_committed_assets_match_current_sources_and_built_bytes(self):
        manifest = json.loads((ROOT / "overlay_studio/manifest.json").read_text())
        self.assertEqual(manifest["renderer"], "svelte-svg-gsap")
        required_sources = {str(path.relative_to(ROOT)).replace("\\", "/")
                            for path in (ROOT / "broadcast_renderer/src").rglob("*") if path.is_file()}
        self.assertTrue(required_sources.issubset(manifest["sources"]))
        for name, expected in manifest["sources"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected,
                             f"Rebuild Broadcast Studio after editing {name}")
        for name, expected in manifest["assets"].items():
            self.assertEqual(hashlib.sha256((ROOT / "overlay_studio" / name).read_bytes()).hexdigest(), expected, name)
