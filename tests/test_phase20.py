from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime


BASE = Path(__file__).resolve().parents[1]


class FakeProfileClient:
    def get_player_profile_stats(self, player_id: str, competition_id: str):
        return {
            "player": {
                "id": player_id,
                "first_name": "Ana",
                "last_name": "García",
                "birth_date": "2000-05-04",
                "nationality": "ES",
                "position": "forward",
            },
            "played": 7,
            "goals": 5,
            "assists": 3,
        }


class Phase20Tests(unittest.TestCase):
    def test_player_profile_updates_state_and_shows_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.supabase = FakeProfileClient()
            runtime.active_competition = {"id": "c1", "name": "Liga"}
            runtime.active_match = {
                "id": "m1",
                "competition_id": "c1",
                "home_team": {"id": "t1", "logo_url": "logos/home.png"},
                "away_team": {"id": "t2"},
            }
            runtime.rosters = {
                "team1": [{"player_id": "p1", "shirt_number": 9, "member_type": "player", "player": {"id": "p1"}}],
                "team2": [],
            }
            runtime.update_player_profile("team1", "p1", show=True)
            profile = runtime.read_state()["statistics"]["player_profile"]
            self.assertTrue(profile["status"])
            self.assertEqual(profile["name"], "Ana García")
            self.assertEqual(profile["number"], "9")
            self.assertEqual(profile["played"], 7)
            self.assertEqual(profile["goals"], 5)
            self.assertEqual(profile["assists"], 3)
            self.assertEqual(profile["birth_date"], "04/05/2000")

    def test_bottom_bar_restored_and_empty_assist_hidden(self):
        css = (BASE / "styles.css").read_text(encoding="utf-8")
        html = (BASE / "overlay.html").read_text(encoding="utf-8")
        js = (BASE / "script.js").read_text(encoding="utf-8")
        self.assertIn("CANONICAL CONTINUOUS GOAL BOTTOM BAR", css)
        self.assertIn("bottom-assistant-row[hidden]", css)
        self.assertIn('id="bottom-assistant-row" hidden', html)
        self.assertIn("bottomAssistantRow.hidden = !hasAssistant", js)

    def test_statistics_and_deck_expose_player_profiles(self):
        html = (BASE / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (BASE / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="player-profile-player"', html)
        self.assertIn('data-player-profile-team="team1"', html)
        self.assertIn('data-player-profile-team="team2"', html)
        self.assertIn('openProductionWorkflow("profile"', js)
        self.assertIn('/api/player-profile', js)


if __name__ == "__main__":
    unittest.main()
