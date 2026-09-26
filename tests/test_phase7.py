from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.state_store import StateStore


class Phase7SafeStartupTests(unittest.TestCase):
    def test_startup_clears_previous_match_panels_and_powerplays(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = StateStore(base / "data.json")
            state = store.load()
            state["animation"]["status"] = "show"
            state["bottombar"]["status"] = "show"
            state["prematch"]["status"] = True
            state["intermission"]["status"] = True
            state["statistics"]["lineups"]["status"] = True
            state["statistics"]["lineups"]["team1_status"] = True
            state["penalty_shootout"]["status"] = True
            state["online"].update({
                "competition_id": "c1",
                "competition_name": "Liga",
                "match_id": "m1",
                "match_label": "Partido anterior",
            })
            state["powerplay"]["team1"].update({
                "status": True,
                "player_id": "p1",
                "remaining_seconds": 75,
            })
            store.save(state)

            runtime = ApplicationRuntime(base)
            clean = runtime.read_state()
            self.assertEqual(clean["animation"]["status"], "hide")
            self.assertEqual(clean["bottombar"]["status"], "hide")
            self.assertFalse(clean["prematch"]["status"])
            self.assertFalse(clean["intermission"]["status"])
            self.assertFalse(clean["statistics"]["lineups"]["status"])
            self.assertFalse(clean["penalty_shootout"]["status"])
            self.assertFalse(clean["powerplay"]["team1"]["status"])
            self.assertEqual(clean["online"]["match_id"], "")
            self.assertEqual(clean["online"]["match_label"], "")
            self.assertEqual(runtime.snapshot()["online"]["match"], {})


class Phase7CallUpValidationTests(unittest.TestCase):
    def test_only_saved_called_up_players_are_valid_for_powerplay(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.active_match = {"id": "m1"}
            runtime.rosters = {
                "team1": [
                    {"player_id": "p1", "shirt_number": 8, "member_type": "player"},
                    {"player_id": "p2", "shirt_number": 14, "member_type": "player"},
                    {"player_id": "c1", "shirt_number": None, "member_type": "coach"},
                ],
                "team2": [],
            }
            runtime.set_attendance({"team1": {"p1"}, "team2": set()})
            self.assertEqual(runtime.require_called_up_player("team1", "p1")["shirt_number"], 8)
            with self.assertRaisesRegex(RuntimeError, "no está convocado"):
                runtime.require_called_up_player("team1", "p2")
            with self.assertRaisesRegex(RuntimeError, "no está convocado"):
                runtime.require_called_up_player("team1", "c1")

    def test_snapshot_exposes_saved_attendance(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.set_attendance({"team1": {"p2", "p1"}, "team2": {"q1"}})
            online = runtime.snapshot()["online"]
            self.assertEqual(online["attendance"]["team1"], ["p1", "p2"])
            self.assertEqual(online["attendance"]["team2"], ["q1"])


class Phase7FrontendContractTests(unittest.TestCase):
    def test_frontend_removes_manual_penalty_numbers_and_filters_callups(self):
        base = Path(__file__).resolve().parents[1]
        html = (base / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (base / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("pp-home-manual-number", html)
        self.assertNotIn("pp-away-manual-number", html)
        self.assertIn("Jugador convocado", html)
        self.assertIn("calledUpPlayers", js)
        self.assertIn("Guarda primero la convocatoria", js)
        self.assertIn("El jugador no está convocado", (base / "secretariat_api" / "runtime.py").read_text(encoding="utf-8"))

    def test_overlay_and_match_context_start_neutral(self):
        base = Path(__file__).resolve().parents[1]
        overlay = (base / "overlay.html").read_text(encoding="utf-8")
        js = (base / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('scoreboard-wrapper hidden', overlay)
        self.assertIn('const hasActiveMatch = Boolean(currentMatch.id)', js)
        self.assertIn(': "Seleccionar partido"', js)
        self.assertNotIn('Boolean(state.online?.match_id || currentMatch.id)', js)


if __name__ == "__main__":
    unittest.main()
