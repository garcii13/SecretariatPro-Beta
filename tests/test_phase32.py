from __future__ import annotations

import unittest
from pathlib import Path

from secretariat_core.services.event_context import build_goal_bottom_bar

ROOT = Path(__file__).resolve().parents[1]


class Phase32Tests(unittest.TestCase):
    def test_penalties_have_no_external_background(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        block = css.split("PHASE 32 — PENALTIES WITHOUT EXTERNAL BACKGROUND", 1)[1]
        self.assertIn("#penalties-modal.penalties-modal", block)
        self.assertIn("background: transparent !important", block)
        self.assertIn("#penalties-modal .penalties-panel", block)
        self.assertIn("box-shadow: none !important", block)
        self.assertNotIn(".stats-panel, .penalties-panel, .player-profile-bar", script)

    def test_visitor_colour_is_authoritative_even_with_stale_state(self):
        payload = build_goal_bottom_bar(
            team_key="team2",
            scorer_id="away-7",
            assistant_id=None,
            match={
                "away_team": {
                    "name": "Away",
                    "primary_color": "#101010",
                    "secondary_color": "#e07a22",
                    "logo_url": "main.png",
                    "alternate_logo_url": "away-alt.png",
                }
            },
            rosters={
                "team1": [],
                "team2": [{
                    "player_id": "away-7",
                    "shirt_number": 7,
                    "player": {"id": "away-7", "first_name": "Ada", "last_name": "Niemi"},
                }],
            },
            events=[{"event_type": "goal", "player_id": "away-7"}],
            team_state={"stripe_color": "#00ff00", "logo": "stale.png"},
        )
        self.assertEqual(payload["team_key"], "team2")
        self.assertEqual(payload["team_color"], "#e07a22")
        self.assertEqual(payload["team_logo"], "away-alt.png")

    def test_browser_prefers_goal_payload_colour(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn('const teamColor = bar.team_color || stateTeamColor || "#555b66";', script)

    def test_phase36_cache_and_version(self):
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        app_html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        tablet_html = (ROOT / "tablet" / "index.html").read_text(encoding="utf-8")
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("styles.css?v=phase55", app_html)
        self.assertIn("app.js?v=phase36", app_html)
        self.assertIn("tablet.css?v=phase74", tablet_html)
        self.assertIn("tablet.js?v=phase74", tablet_html)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
