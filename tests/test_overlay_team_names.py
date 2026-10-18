import unittest
from secretariat_core.services.match_context import apply_match_context
from secretariat_core.state_store import default_state, normalize_state


class OverlayTeamNamesTests(unittest.TestCase):
    def load(self, state, home, away):
        return apply_match_context(state, match={"home_team": home, "away_team": away},
                                   competition={}, standings=[], home_roster=[], away_roster=[])

    def test_context_keeps_complete_names_separate_from_scoreboard_abbreviations(self):
        state = self.load(default_state(),
                          {"id": "h", "name": "Club Deportivo Unión de Tres Cantos", "short_name": "TRC"},
                          {"id": "a", "name": "Club Unihockey San Lorenzo de El Escorial", "short_name": "ESC"})
        self.assertEqual(state["team1"]["name"], "TRC")
        self.assertEqual(state["team2"]["name"], "ESC")
        self.assertEqual(state["team1"]["full_name"], "Club Deportivo Unión de Tres Cantos")
        self.assertEqual(state["team2"]["full_name"], "Club Unihockey San Lorenzo de El Escorial")
        self.assertEqual(normalize_state(state)["team1"]["full_name"], state["team1"]["full_name"])

    def test_match_switch_replaces_full_names_and_supports_teams_without_both_fields(self):
        state = self.load(default_state(), {"name": "Previous Home", "short_name": "PH"}, {"name": "Previous Away", "short_name": "PA"})
        self.load(state, {"name": "New Complete Club"}, {"short_name": "NEW"})
        self.assertEqual(state["team1"]["name"], "New Complete Club")
        self.assertEqual(state["team1"]["full_name"], "New Complete Club")
        self.assertEqual(state["team2"]["full_name"], "NEW")
        self.load(state, {}, {})
        self.assertEqual(state["team1"]["full_name"], "")
        self.assertEqual(state["team2"]["full_name"], "")
