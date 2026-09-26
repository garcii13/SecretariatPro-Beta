from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from obs_controller import OBSController

ROOT = Path(__file__).resolve().parents[1]


class Phase12ProductionConsoleTests(unittest.TestCase):
    def test_direct_monitor_matches_score_panel_and_source_has_spacing(self):
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".preview-card,\n.live-side,\n.live-side .score-card { min-height: 560px; }", css)
        self.assertIn(".score-source-strip { margin: 14px 14px 0; }", css)

    def test_production_is_fixed_and_contains_all_fast_controls(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        production = html[html.index('id="view-production"'):html.index('id="view-team"')]
        self.assertIn("production-monitor-stage", production)
        self.assertIn("production-score-main", production)
        self.assertIn("production-pp-summary", production)
        self.assertIn('id="production-scene-buttons"', production)
        self.assertNotIn('id="production-scene-select"', production)
        self.assertNotIn('id="production-take-scene"', production)
        self.assertGreaterEqual(production.count("production-action-key"), 12)
        self.assertIn('data-register-goal="team1"', production)
        self.assertIn('data-register-goal="team2"', production)
        self.assertIn('data-pp-context="production"', production)
        self.assertIn("body.production-mode { overflow: hidden; }", css)
        self.assertIn("#view-production.is-visible", css)
        self.assertIn("overflow: hidden;", css)

    def test_production_penalties_still_use_called_up_players(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('const prefixes = [`pp-${side}`, `production-pp-${side}`]', js)
        self.assertIn("const players = calledUpPlayers(teamKey);", js)
        self.assertIn('context === "production"', js)

    def test_html_ids_remain_unique(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        ids = re.findall(r'\sid="([^"]+)"', html)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(duplicates, [])


class Phase12OBSSceneTests(unittest.TestCase):
    def test_controller_changes_program_scene(self):
        client = Mock()
        controller = OBSController()
        controller.connected = True
        controller._client = client
        controller.set_program_scene("Cámara principal")
        client.set_current_program_scene.assert_called_once_with("Cámara principal")

    def test_api_exposes_program_scene_endpoint(self):
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        schemas = (ROOT / "secretariat_api" / "schemas.py").read_text(encoding="utf-8")
        self.assertIn('@app.post("/api/obs/scenes/program")', main)
        self.assertIn("runtime.obs.set_program_scene", main)
        self.assertIn("class OBSSceneRequest", schemas)


if __name__ == "__main__":
    unittest.main()
