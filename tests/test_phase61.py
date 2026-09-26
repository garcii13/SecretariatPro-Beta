from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Phase61MacOCRStabilityTests(unittest.TestCase):
    def test_macos_pins_legacy_paddle_stack(self):
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn('paddlepaddle==2.6.2 ; sys_platform == "darwin"', req)
        self.assertIn('paddleocr==2.7.3 ; sys_platform == "darwin"', req)

    def test_mac_uses_legacy_pipeline_and_one_cpu_thread(self):
        engine = (ROOT / "ocr_engine.py").read_text(encoding="utf-8")
        self.assertIn('v2_pipeline_mac_stable', engine)
        self.assertIn('cpu_threads=1', engine)

    def test_worker_disables_pir_and_mkldnn_paths(self):
        worker = (ROOT / "ocr_worker.py").read_text(encoding="utf-8")
        self.assertIn('FLAGS_enable_pir_api', worker)
        self.assertIn('FLAGS_use_mkldnn', worker)

    def test_native_sigsegv_is_contained_and_restart_limited(self):
        runtime = (ROOT / "secretariat_core" / "services" / "ocr_runtime.py").read_text(encoding="utf-8")
        self.assertIn('exit_code == -11', runtime)
        self.assertIn('_restart_after_native_crash', runtime)
        self.assertIn('len(self._native_crash_times) < 2', runtime)

    def test_mac_setup_uses_project_venv(self):
        setup = (ROOT / "PREPARAR_MAC_BETA.command").read_text(encoding="utf-8")
        launcher = (ROOT / "INICIAR_APP.command").read_text(encoding="utf-8")
        self.assertIn('python -m venv .venv', setup.replace('"$PYTHON_BIN"', 'python'))
        self.assertIn('.venv/bin/python', launcher)


if __name__ == "__main__":
    unittest.main()
