from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from secretariat_core.ocr_sampling import encode_private_sample
from ocr_worker import sample_threshold_for

ROOT = Path(__file__).resolve().parents[1]


class Phase47OCRPrivacyTests(unittest.TestCase):
    def test_public_ui_has_opt_in_and_no_training_controls(self):
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="settings-ocr-sharing"', html)
        self.assertIn("Mejora colaborativa del OCR", html)
        self.assertNotIn('id="save-ocr-training-sample"', html)
        self.assertNotIn("Muestras reales", html)

    def test_public_api_has_no_training_sample_route(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn('/api/ocr/training/sample', api)
        self.assertNotIn('/api/ocr/training/stats', api)
        self.assertIn('API_VERSION = "57.0.0-beta-rc"', api)

    def test_public_package_does_not_ship_training_toolchain(self):
        self.assertIn("ocr_training/", (ROOT / ".gitignore").read_text())
        for spec in ROOT.glob("*.spec"):
            self.assertNotIn("ocr_training", spec.read_text())
        self.assertFalse((ROOT / "secretariat_core" / "ocr_training.py").exists())
        self.assertFalse((ROOT / "README_ENTRENAMIENTO_OCR.md").exists())

    def test_sample_encoder_crops_only_requested_roi(self):
        frame = np.zeros((200, 400, 3), dtype=np.uint8)
        sample = encode_private_sample(frame, {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5})
        self.assertIsNotNone(sample)
        self.assertEqual(sample["width"], 200)
        self.assertEqual(sample["height"], 100)
        self.assertLess(len(sample["image_b64"]), 512 * 1024)

    def test_worker_sampling_is_opt_in_and_throttled(self):
        worker = (ROOT / "ocr_worker.py").read_text(encoding="utf-8")
        self.assertIn('share_samples = bool(cfg.get("sample_sharing"))', worker)
        self.assertIn('sample_interval_s', worker)
        self.assertIn('encode_private_sample', worker)
        self.assertIn('difficult = (not value)', worker)

    def test_clock_samples_use_ninety_percent_threshold_only_for_time(self):
        config = {"sample_threshold": 0.72, "sample_thresholds": {"time": 0.90}}
        self.assertEqual(sample_threshold_for("time", config), 0.90)
        self.assertEqual(sample_threshold_for("team1_score", config), 0.72)
        self.assertEqual(sample_threshold_for("team2_score", config), 0.72)

    def test_migration_keeps_sample_bucket_private(self):
        sql = (ROOT / "SUPABASE_PHASE47_OCR_LAB.sql").read_text(encoding="utf-8")
        self.assertIn("'ocr-training-samples'", sql)
        self.assertIn("false,", sql)
        self.assertIn("sp_ocr_samples_opt_in_insert", sql)
        self.assertIn("sp_ocr_consent", sql)
        self.assertNotIn("for select\nto authenticated\nusing (public.sp_is_workspace_member(workspace_id));\n\n-- La aplicación comercial", sql)


if __name__ == "__main__":
    unittest.main()
