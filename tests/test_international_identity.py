import tempfile
import unittest
from secretariat_core.settings_store import normalize_settings, SettingsStore
from secretariat_core.services.match_context import apply_match_context
from secretariat_api.runtime import ApplicationRuntime


class InternationalIdentityTests(unittest.TestCase):
    def test_flags_round_trip_without_replacing_club_assets(self):
        flags = {"home": "https://assets.test/es.svg", "away": "https://assets.test/fi.png"}
        with tempfile.TemporaryDirectory() as folder:
            store = SettingsStore(folder + "/settings.json")
            store.save({"appearance": {"team_identity": {"international": True, "flags": flags}}})
            self.assertEqual(store.load()["appearance"]["team_identity"], {"international": True, "flags": flags})

    def test_invalid_flag_urls_and_legacy_settings(self):
        for raw in (None, [], "invalid", {"international": "false", "flags": []}):
            self.assertEqual(normalize_settings({"appearance": {"team_identity": raw}})["appearance"]["team_identity"], {"international": False, "flags": {}})
        identity = normalize_settings({"appearance": {"team_identity": {"flags": {"x": "javascript:alert(1)", "y": {}, "z": "https://assets.test/es.png"}}}})["appearance"]["team_identity"]
        self.assertEqual(identity["flags"], {"z": "https://assets.test/es.png"})

    def test_published_flags_reset_when_switching_to_club_competition(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            first = runtime._apply_published_theme({}, {"config": {"appearance": {"team_identity": {"international": True, "flags": {"x": "https://assets.test/es.svg"}}}}})
            self.assertTrue(first["appearance"]["team_identity"]["international"])
            second = runtime._apply_published_theme(first, {})
            self.assertEqual(second["appearance"]["team_identity"], {"international": False, "flags": {}})

    def test_match_keeps_team_ids_and_club_crests(self):
        state = {"team1": {}, "team2": {}}
        match = {"home_team": {"id": "h", "logo_url": "home-crest"}, "away_team": {"id": "a", "logo_url": "away-crest"}}
        apply_match_context(state, match=match, competition={}, standings=[], home_roster=[], away_roster=[])
        self.assertEqual(state["team1"]["id"], "h")
        self.assertEqual(state["team2"]["id"], "a")
        self.assertEqual(state["team1"]["logo"], "home-crest")
        self.assertEqual(state["team2"]["logo"], "away-crest")

    def test_real_runtime_allows_intro_bottom_and_owns_scoreboard(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            def intro(state):
                state["broadcast_flow"] = {"phase": "GOAL_INTRO"}
                state["bottombar"]["status"] = "show"
                state["animation"]["status"] = "show"
            runtime.mutate_state(intro)
            state = runtime.read_state()
            self.assertEqual(state["bottombar"]["status"], "show")
            self.assertEqual(state["animation"]["status"], "hide")

    def test_real_runtime_keeps_bottom_visible_through_reveal(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            def reveal(state):
                state["broadcast_flow"] = {"phase": "GOAL_REVEAL"}
                state["bottombar"]["status"] = "show"
                state["animation"]["status"] = "show"
            runtime.mutate_state(reveal)
            self.assertEqual(runtime.read_state()["bottombar"]["status"], "show")
            self.assertEqual(runtime.read_state()["animation"]["status"], "hide")
