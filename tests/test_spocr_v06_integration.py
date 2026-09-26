from pathlib import Path
import unittest

import ocr_engine


ROOT = Path(__file__).resolve().parents[1]


class SPOCRV06IntegrationTests(unittest.TestCase):
    def test_signed_off_artifacts_are_packaged(self):
        self.assertTrue((ROOT / "models" / "spocr_v0.7_hybrid.joblib").is_file())
        self.assertTrue((ROOT / "models" / "spscore_v0.2_digits.joblib").is_file())

    def test_clock_preserves_leading_zero(self):
        self.assertTrue(ocr_engine._valid_clock("02:23"))
        self.assertTrue(ocr_engine._valid_clock("2:23"))
        self.assertEqual(ocr_engine._canonical_clock("02:23"), "02:23")
        self.assertEqual(ocr_engine._canonical_clock("2:23"), "2:23")
        self.assertNotEqual(ocr_engine._canonical_clock("02:23"), ocr_engine._canonical_clock("2:23"))

    def test_specialists_are_field_specific(self):
        source = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        self.assertIn('field_key == "time"', source)
        self.assertIn('{"team1_score", "team2_score"}', source)
        self.assertIn("_apply_clock_hybrid", source)
        self.assertIn("_apply_score_hybrid", source)

    def test_model_info_keeps_paddle_as_stable_base(self):
        ocr_engine.configure(base_dir=ROOT)
        info = ocr_engine.active_model_info()
        self.assertEqual(info["model_name"], "en_PP-OCRv4_mobile_rec")
        self.assertFalse(info["custom"])
        self.assertEqual(info["clock_hybrid"], "SP-OCR v0.7 RC")
        self.assertEqual(info["score_hybrid"], "SP-SCORE v0.2")
        self.assertTrue(info["clock_hybrid_available"])
        self.assertTrue(info["score_hybrid_available"])


if __name__ == "__main__":
    unittest.main()
