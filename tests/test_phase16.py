from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase16DirectOBSScenesTests(unittest.TestCase):
    def test_all_obs_scenes_are_direct_deck_keys(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        production = html[html.index('id="view-production"'):html.index('id="view-team"')]
        self.assertIn('id="production-scene-buttons"', production)
        self.assertNotIn('id="production-scene-select"', production)
        self.assertNotIn('id="production-take-scene"', production)
        self.assertIn('button.dataset.obsScene = scene', js)
        self.assertIn('state.textContent = scene === program ? "EN PROGRAMA" : "ESCENA OBS"', js)
        self.assertIn('setProgramScene(sceneButton.dataset.obsScene)', js)

    def test_scene_buttons_share_responsive_grid(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('.production-scene-buttons { display: contents; }', css)
        self.assertIn('function fitProductionActionGrid()', js)
        self.assertIn('grid.style.gridTemplateColumns', js)
        self.assertIn('grid.style.gridTemplateRows', js)
        self.assertIn('new ResizeObserver', js)

    def test_phase16_version_and_cache(self):
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        self.assertIn('version="36.0.0-alpha"', main)
        self.assertIn('app.js?v=phase36', html)
        self.assertIn('styles.css?v=phase55', html)
        self.assertIn('secretariatpro-phase36-v1', sw)
        ids = re.findall(r'\sid="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
