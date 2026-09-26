from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.services.powerplay import advance_powerplay, start_powerplay


class Phase6PowerplayReliabilityTests(unittest.TestCase):
    def test_realistic_slow_ocr_gap_is_consumed_immediately(self):
        info = {}
        start_powerplay(info, current_seconds=300, player_id="p1", player_number=14)

        # PaddleOCR may need several seconds on modest hardware. A seven-second
        # forward reading is valid progress, not an anomalous jump.
        self.assertTrue(advance_powerplay(info, 307, strict_ocr=True))
        self.assertEqual(info["remaining_seconds"], 113)
        self.assertEqual(info["last_ocr_match_seconds"], 307)
        self.assertEqual(info["clock_sync_state"], "synced")

    def test_stale_runtime_reading_cannot_override_live_score_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.score_store.write_readings({"time": "05:00"})
            runtime.ocr_runtime.status = lambda: {
                "running": True,
                "last_reading": time.time() - 20,
                "readings": {"time": "01:00"},
            }
            self.assertEqual(runtime.current_seconds(), 300)

    def test_live_snapshot_advances_pp_from_same_txt_used_by_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = ApplicationRuntime(tmp)
            runtime.score_store.write_readings(
                {"team1_score": "3", "team2_score": "2", "time": "05:00"}
            )

            def start(state):
                start_powerplay(
                    state["powerplay"]["team1"],
                    current_seconds=300,
                    player_id="p1",
                    player_number=8,
                )

            runtime.mutate_state(start)
            runtime.score_store.write_readings({"time": "05:07"})
            live = runtime.live_snapshot()
            self.assertEqual(live["scores"]["team1_score"], "3")
            self.assertEqual(live["scores"]["team2_score"], "2")
            self.assertEqual(live["scores"]["time"], "05:07")
            self.assertEqual(live["powerplay"]["team1"]["remaining_seconds"], 113)


class Phase6DeliveryContractTests(unittest.TestCase):
    def test_direct_panel_has_independent_live_polling(self):
        base = Path(__file__).resolve().parents[1]
        js = (base / "webapp" / "app.js").read_text(encoding="utf-8")
        api = (base / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("/api/live", js)
        self.assertIn('document.visibilityState === "visible" ? 400 : 1200', js)
        self.assertIn('@app.get("/api/live")', api)

    def test_only_one_requirements_file_is_delivered(self):
        base = Path(__file__).resolve().parents[1]
        requirement_files = sorted(path.name for path in base.glob("requirements*.txt"))
        self.assertEqual(requirement_files, ["requirements-test.txt", "requirements.txt"])
        contents = (base / "requirements.txt").read_text(encoding="utf-8")
        for package in ("fastapi", "uvicorn", "paddleocr", "supabase", "obsws-python"):
            self.assertIn(package, contents)


if __name__ == "__main__":
    unittest.main()
