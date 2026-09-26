from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase14ProductionWorkflowTests(unittest.TestCase):
    def test_production_has_goal_and_penalty_workflows(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        production = html[html.index('id="view-production"'):html.index('id="view-team"')]
        self.assertIn('id="production-workflow-card"', production)
        self.assertIn('id="production-workflow-grid"', production)
        self.assertIn('data-register-goal="team1"', production)
        self.assertIn('data-register-goal="team2"', production)
        self.assertIn('data-pp-start="team1" data-pp-context="production"', production)
        self.assertIn('data-pp-start="team2" data-pp-context="production"', production)

    def test_workflow_uses_called_up_players_and_large_numbers(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("kind === \"profile\" ? profilePlayers(teamKey) : calledUpPlayers(teamKey)", js)
        self.assertIn("flow.kind === \"profile\" ? profilePlayers(flow.team) : calledUpPlayers(flow.team)", js)
        self.assertIn("production-player-number", js)
        self.assertIn("font-size: clamp(25px, 3.2vw, 52px)", css)

    def test_penalty_type_is_selected_before_player(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('step: kind === "penalty" ? "penalty_type" : kind === "profile" ? "profile_player" : "goal_scorer"', js)
        self.assertIn('flow.step = "penalty_player"', js)
        self.assertIn('flow.step = "penalty_serving"', js)
        self.assertIn('flow.penaltyType === "2+10"', js)

    def test_goal_flow_selects_scorer_then_assistant(self):
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn('flow.step = "goal_assistant"', js)
        self.assertIn('data-flow-action="goal-no-assist"', js)
        self.assertIn('assistant_id: assistantId || null', js)

    def test_responsive_blocks_and_no_duplicate_ids(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("repeat(auto-fit", css)
        self.assertIn("--picker-columns", css)
        self.assertIn("overflow: hidden", css)
        ids = re.findall(r'\sid="([^"]+)"', html)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(duplicates, [])

    def test_phase14_cache_version(self):
        sw = (ROOT / "webapp" / "sw.js").read_text(encoding="utf-8")
        index = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertRegex(sw, r"secretariatpro-phase(?:14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36)-v1")
        self.assertRegex(index, r"app\.js\?v=phase(?:14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36)")


if __name__ == "__main__":
    unittest.main()
