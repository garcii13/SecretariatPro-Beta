from __future__ import annotations

import unittest
from pathlib import Path

from secretariat_core.services.event_context import build_goal_bottom_bar

ROOT = Path(__file__).resolve().parents[1]


class Phase30Tests(unittest.TestCase):
    def test_scoreboard_gloss_preserves_phase28_geometry(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("PHASE 30 — GLOSSY ONLY, GEOMETRY LOCKED", css)
        self.assertIn("grid-template-columns:\n    var(--logo-width)\n    var(--team-box-width)\n    var(--center-width)", css)
        self.assertIn(".scoreboard-wrapper {\n  width: min(930px, 96vw) !important;", css)
        block = css.split("PHASE 30 — GLOSSY ONLY, GEOMETRY LOCKED", 1)[1].split("PHASE 32 — PENALTIES WITHOUT EXTERNAL BACKGROUND", 1)[0]
        for forbidden in ("grid-template-columns", "gap:", "width:", "height:", "padding:", "margin:", "transform:"):
            self.assertNotIn(forbidden, block)
        self.assertIn("linear-gradient(180deg", block)
        self.assertIn("box-shadow:", block)

    def test_visitor_goal_uses_visitor_colour_and_identity(self):
        payload = build_goal_bottom_bar(
            team_key="team2",
            scorer_id="away-9",
            assistant_id="",
            match={
                "away_team": {
                    "name": "Visitante",
                    "primary_color": "#112233",
                    "secondary_color": "#d45522",
                    "logo_url": "main.png",
                    "alternate_logo_url": "away.png",
                }
            },
            rosters={
                "team1": [],
                "team2": [
                    {
                        "player_id": "away-9",
                        "shirt_number": 9,
                        "player": {"id": "away-9", "first_name": "Eva", "last_name": "Niemi"},
                    }
                ],
            },
            events=[{"event_type": "goal", "player_id": "away-9"}],
            team_state={},
        )
        self.assertEqual(payload["team_key"], "team2")
        self.assertEqual(payload["team_color"], "#d45522")
        self.assertEqual(payload["team_logo"], "away.png")

    def test_position_translation_covers_all_six_languages(self):
        overlay_js = (ROOT / "script.js").read_text(encoding="utf-8")
        app_js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        for language in ("es", "en", "sv", "cs", "fi", "de"):
            self.assertIn(f"{language}: {{ goalkeeper:", overlay_js)
            self.assertIn(f"{language}: {{ goalkeeper:", app_js)
        self.assertIn("translatePosition(player.position", overlay_js)
        self.assertIn("translatePosition(profile.position)", overlay_js)
        self.assertIn("translatePlayerPosition(player.position)", app_js)

    def test_phase36_cache_and_version(self):
        overlay = (ROOT / "overlay.html").read_text(encoding="utf-8")
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        main = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("styles.css?v=phase57", overlay)
        self.assertIn("script.js?v=phase57", overlay)
        self.assertIn("styles.css?v=phase55", html)
        self.assertIn("app.js?v=phase36", html)
        self.assertIn("secretariatpro-phase36-v1", sw)
        self.assertIn("36.0.0-alpha", main)


if __name__ == "__main__":
    unittest.main()
