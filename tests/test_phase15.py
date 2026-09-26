from __future__ import annotations

import re
import unittest
from pathlib import Path

from secretariat_core.services.event_context import build_goal_bottom_bar

ROOT = Path(__file__).resolve().parents[1]


class Phase15ProductionLayoutTests(unittest.TestCase):
    def test_production_monitor_is_obs_only(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        production = html[html.index('id="view-production"'):html.index('id="view-team"')]
        self.assertIn('id="production-program-video"', production)
        self.assertNotIn('id="production-overlay-preview"', production)
        self.assertNotIn('src="/overlay.html"', production)

    def test_production_panels_have_persistent_resizers(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        for identifier in ("production-resize-top", "production-resize-rows", "production-resize-bottom"):
            self.assertIn(f'id="{identifier}"', html)
        self.assertIn("PRODUCTION_LAYOUT_KEY", js)
        self.assertIn("localStorage.setItem(PRODUCTION_LAYOUT_KEY", js)
        self.assertIn("production-resizer-column", css)
        self.assertIn("production-resizer-row", css)

    def test_pp_cancel_only_appears_for_active_pp(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="production-quick-pp-card" hidden', html)
        self.assertIn('id="production-quick-pp-home" hidden', html)
        self.assertIn('id="production-quick-pp-away" hidden', html)
        self.assertIn("quickTeam.hidden = !Boolean(info.status)", js)
        self.assertIn('row.classList.toggle("has-active-pp", anyActive)', js)

    def test_player_numbers_have_digit_aware_sizing(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('rawNumber.length >= 3 ? "is-three-digits"', js)
        self.assertIn('data-digits="${rawNumber.length || 1}"', js)
        self.assertIn(".production-player-number.is-three-digits", css)
        self.assertIn("white-space: nowrap", css)

    def test_phase15_assets_and_ids(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("app.js?v=phase36", html)
        self.assertIn("styles.css?v=phase55", html)
        self.assertIn("secretariatpro-phase36-v1", sw)
        ids = re.findall(r'\sid="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)))


class Phase15GoalLowerThirdTests(unittest.TestCase):
    def test_goal_builds_rich_bottom_bar(self):
        rosters = {
            "team1": [
                {"player_id": "p1", "shirt_number": 12, "player": {"id": "p1", "first_name": "Ana", "last_name": "García"}},
                {"player_id": "p2", "shirt_number": 7, "player": {"id": "p2", "first_name": "Marta", "last_name": "López"}},
            ],
            "team2": [],
        }
        events = [
            {"event_type": "goal", "player_id": "p1"},
            {"event_type": "goal", "player_id": "p1"},
        ]
        payload = build_goal_bottom_bar(
            team_key="team1",
            scorer_id="p1",
            assistant_id="p2",
            match={"home_team": {"name": "Equipo Local", "logo_url": "logo.png", "primary_color": "#123456"}},
            rosters=rosters,
            events=events,
            team_state={"logo": "local.png", "stripe_color": "#abcdef"},
        )
        self.assertEqual(payload["status"], "show")
        self.assertEqual(payload["scorer_number"], "12")
        self.assertEqual(payload["scorer_last_name"], "GARCÍA")
        self.assertEqual(payload["assistant_number"], "7")
        self.assertEqual(payload["assistant_last_name"], "LÓPEZ")
        self.assertEqual(payload["scorer_match_goals"], 2)
        self.assertEqual(payload["team_logo"], "local.png")
        self.assertEqual(payload["team_color"], "#abcdef")



if __name__ == "__main__":
    unittest.main()
