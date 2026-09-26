from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import ocr_engine
from secretariat_core.ocr_geometry import apply_perspective, normalize_perspective, perspective_is_valid
from secretariat_core.ocr_store import OCRConfigStore

ROOT = Path(__file__).resolve().parents[1]


class Phase46OCRTests(unittest.TestCase):
    def test_perspective_defaults_are_safe(self):
        value = normalize_perspective(None)
        self.assertFalse(value["enabled"])
        self.assertEqual(value["points"]["top_left"], {"x": 0.0, "y": 0.0})
        self.assertEqual(value["points"]["bottom_right"], {"x": 1.0, "y": 1.0})

    def test_perspective_rectifies_valid_quadrilateral(self):
        frame = np.zeros((300, 500, 3), dtype=np.uint8)
        cv2.rectangle(frame, (80, 50), (430, 250), (255, 255, 255), 3)
        perspective = {
            "enabled": True,
            "points": {
                "top_left": {"x": 0.16, "y": 0.17},
                "top_right": {"x": 0.86, "y": 0.10},
                "bottom_right": {"x": 0.90, "y": 0.85},
                "bottom_left": {"x": 0.12, "y": 0.80},
            },
        }
        self.assertTrue(perspective_is_valid(frame, perspective))
        corrected = apply_perspective(frame, perspective)
        self.assertGreater(corrected.shape[0], 100)
        self.assertGreater(corrected.shape[1], 200)
        self.assertNotEqual(corrected.shape[:2], frame.shape[:2])

    def test_disabled_perspective_is_passthrough(self):
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        self.assertIs(apply_perspective(frame, {"enabled": False}), frame)

    def test_ocr_config_migrates_model_and_perspective(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr_config.json"
            path.write_text(json.dumps({"window_title": "Demo", "poll_ms": 150, "regions": {}}), encoding="utf-8")
            config = OCRConfigStore(path).load()
            self.assertIn("perspective", config)
            self.assertIn("model", config)
            self.assertEqual(config["model"]["model_name"], "en_PP-OCRv4_mobile_rec")

    def test_scoreboard_cleanup(self):
        self.assertEqual(ocr_engine.clean_score("O8"), "8")
        self.assertEqual(ocr_engine.clean_time("1235"), "12:35")
        self.assertEqual(ocr_engine.clean_time("12:99"), "12:99")

    def test_phase46_perspective_survives_phase47_privacy_refactor(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('id="edit-ocr-perspective"', html)
        self.assertIn("apply_perspective", api)
        self.assertIn("ocrPerspectiveDraft", js)
        self.assertIn('API_VERSION = "57.0.0-beta-rc"', api)


if __name__ == "__main__":
    unittest.main()
