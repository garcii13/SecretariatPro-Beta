from __future__ import annotations

import unittest

from secretariat_core.services.match_context import apply_match_context, match_label
from secretariat_core.services.overlay import hide_all, overlay_summary, set_panel, toggle_panel
from secretariat_core.state_store import default_state


class Phase2ServicesTests(unittest.TestCase):
    def test_overlay_exclusivity(self):
        state = default_state()
        set_panel(state, "prematch", True)
        self.assertTrue(state["prematch"]["status"])
        set_panel(state, "intermission", True)
        self.assertFalse(state["prematch"]["status"])
        self.assertTrue(state["intermission"]["status"])
        toggle_panel(state, "lineups", lineup_team="team2")
        self.assertFalse(state["intermission"]["status"])
        self.assertTrue(state["statistics"]["lineups"]["team2_status"])
        hide_all(state)
        self.assertFalse(any(overlay_summary(state).values()))

    def test_match_context_maps_identity_and_roster(self):
        state = default_state()
        match = {
            "id": "m1", "competition_id": "c1", "match_date": "2026-07-27T16:00:00+02:00",
            "venue": "Pabellón", "status": "scheduled",
            "home_team": {"id": "h", "name": "Home Club", "short_name": "HOM", "primary_color": "#112233", "secondary_color": "#ddeeff", "logo_url": "home.png"},
            "away_team": {"id": "a", "name": "Away Club", "short_name": "AWY", "primary_color": "#aa0000", "secondary_color": "#222222", "logo_url": "away.png", "alternate_logo_url": "away-alt.png"},
        }
        competition = {"id": "c1", "name": "Liga Test", "logo_url": "league.png"}
        standings = [
            {"team_id": "h", "position": 1, "points": 6, "wins": 3, "draws": 0, "losses": 0, "goals_for": 20, "goals_against": 5},
            {"team_id": "a", "position": 2, "points": 4, "wins": 2, "draws": 0, "losses": 1, "goals_for": 15, "goals_against": 8},
        ]
        home_roster = [{"player_id": "p1", "shirt_number": 7, "member_type": "player", "player": {"first_name": "Ana", "last_name": "López", "position": "forward"}}]
        away_roster = [{"player_id": "p2", "shirt_number": 1, "member_type": "coach", "player": {"display_name": "Coach Away"}}]
        apply_match_context(state, match=match, competition=competition, standings=standings, home_roster=home_roster, away_roster=away_roster)
        self.assertEqual(state["team1"]["name"], "HOM")
        self.assertEqual(state["team2"]["logo"], "away-alt.png")
        self.assertEqual(state["prematch"]["team1_points"], "6")
        self.assertEqual(state["statistics"]["lineups"]["team1_players"][0]["position"], "DEL")
        self.assertEqual(state["statistics"]["lineups"]["team2_coaches"][0]["name"], "Coach Away")
        self.assertIn("HOM - AWY", match_label(match))


if __name__ == "__main__":
    unittest.main()
