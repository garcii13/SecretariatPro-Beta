from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Phase64OCRApiCompatibilityTests(unittest.TestCase):
    def test_mac_detects_paddleocr_major_before_legacy_constructor(self):
        src = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        mac = src.split("if _is_apple_silicon_mac():", 1)[1].split("# Other platforms", 1)[0]
        self.assertIn("_installed_paddleocr_major()", mac)
        self.assertIn("major >= 3", mac)
        self.assertIn("TextRecognition", mac)
        self.assertIn('device="cpu"', mac)

    def test_v3_mac_path_never_passes_use_gpu(self):
        src = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        block = src.split("if major is not None and major >= 3:", 1)[1].split("from paddleocr import PaddleOCR", 1)[0]
        self.assertNotIn("use_gpu", block)

    def test_recognizer_accepts_mac_v3_compat_kind(self):
        src = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        self.assertIn('startswith("v3_text_recognition")', src)

    def test_mac_setup_recreates_venv_and_verifies_versions(self):
        setup = (ROOT / "PREPARAR_MAC_BETA.command").read_text(encoding="utf-8")
        self.assertIn("rm -rf .venv", setup)
        self.assertIn('startswith("2.6.2")', setup)
        self.assertIn('startswith("2.7.3")', setup)

    def test_mac_diagnostic_exists(self):
        self.assertTrue((ROOT / "DIAGNOSTICO_OCR_MAC.command").exists())

if __name__ == "__main__":
    unittest.main()
