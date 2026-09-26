from pathlib import Path
import unittest
from unittest import mock
import numpy as np
import ocr_engine

ROOT = Path(__file__).resolve().parents[1]

class Phase62RawColourOCRTests(unittest.TestCase):
    def test_prepare_raw_preserves_pixels_shape_and_channels(self):
        src = np.array([[[3, 17, 251], [44, 89, 120]]], dtype=np.uint8)
        out = ocr_engine.prepare_raw(src)
        self.assertEqual(out.shape, src.shape)
        self.assertTrue(np.array_equal(out, src))

    def test_raw_valid_read_does_not_run_legacy_preprocess(self):
        frame = np.zeros((20, 30, 3), dtype=np.uint8)
        roi = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
        with mock.patch.object(ocr_engine, "_recognize", return_value=("08:35", .91)) as rec, \
             mock.patch.object(ocr_engine, "preprocess") as legacy:
            detail = ocr_engine.read_region_detail(frame, roi, allow_colon=True)
        self.assertEqual(detail["value"], "08:35")
        self.assertEqual(detail["pass"], "raw")
        self.assertEqual(rec.call_count, 1)
        legacy.assert_not_called()

    def test_legacy_is_only_rescue_when_raw_fails(self):
        frame = np.zeros((20, 30, 3), dtype=np.uint8)
        roi = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
        with mock.patch.object(ocr_engine, "_recognize", side_effect=[("", .11), ("12", .88)]):
            detail = ocr_engine.read_region_detail(frame, roi, allow_colon=False)
        self.assertEqual(detail["value"], "12")
        self.assertEqual(detail["pass"], "legacy_fallback")

    def test_no_grayscale_or_threshold_in_primary_path_source(self):
        source = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        raw_block = source.split("def prepare_raw",1)[1].split("def preprocess",1)[0]
        self.assertNotIn("cvtColor", raw_block)
        self.assertNotIn("threshold", raw_block)
        self.assertNotIn("resize", raw_block)

if __name__ == "__main__":
    unittest.main()
