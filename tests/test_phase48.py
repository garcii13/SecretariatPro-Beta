from pathlib import Path
import tempfile
import unittest
import json

import ocr_engine
from secretariat_core.ocr_store import OCRConfigStore

ROOT = Path(__file__).resolve().parents[1]


class Phase48StableOCRTests(unittest.TestCase):
    def test_stable_model_restored(self):
        info = ocr_engine.active_model_info()
        self.assertEqual(info["model_name"], "en_PP-OCRv4_mobile_rec")
        self.assertEqual(info["min_confidence"], 0.25)
        self.assertFalse(info["custom"])

    def test_old_cleanup_behavior_restored(self):
        self.assertEqual(ocr_engine.clean_score("08"), "8")
        self.assertEqual(ocr_engine.clean_score("O8"), "8")  # O is discarded, not remapped
        self.assertEqual(ocr_engine.clean_time("1234"), "12:34")
        self.assertEqual(ocr_engine.clean_time("934"), "9:34")

    def test_existing_v5_config_is_migrated_back_to_stable_v4(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ocr_config.json"
            path.write_text(json.dumps({
                "window_title": "Demo", "poll_ms": 150, "regions": {},
                "model": {"model_name": "PP-OCRv5_mobile_rec", "model_dir": "models/ocr_active", "min_confidence": 0.34}
            }), encoding="utf-8")
            config = OCRConfigStore(path).load()
            self.assertEqual(config["model"], {
                "model_name": "en_PP-OCRv4_mobile_rec", "model_dir": "", "min_confidence": 0.25
            })

    def test_phase48_keeps_perspective_and_privacy(self):
        worker = (ROOT / "ocr_worker.py").read_text(encoding="utf-8")
        html = (ROOT / "webapp" / "index.html").read_text(encoding="utf-8")
        self.assertIn("apply_perspective", worker)
        self.assertIn('id="settings-ocr-sharing"', html)

    def test_api_release(self):
        api = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn('API_VERSION = "64.0.0-beta-rc"', api)


if __name__ == "__main__":
    unittest.main()
