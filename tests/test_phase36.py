from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]


def load_run_manager():
    spec = importlib.util.spec_from_file_location("run_manager_current", BASE / "run_manager.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ManagerLauncherAndLoginRegressionTests(unittest.TestCase):
    def test_login_modal_is_above_subscription_gate(self):
        css = (BASE / "webapp" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("#login-modal", css)
        self.assertIn("z-index: 6100", css)
        gate_index = css.rfind(".subscription-gate {")
        login_index = css.rfind("#login-modal")
        self.assertGreater(login_index, gate_index)

    def test_manager_never_reuses_a_stale_server(self):
        module = load_run_manager()
        with patch.object(module, "port_free", side_effect=lambda port: port == 8767):
            port = module.choose_manager_port(8766)
        self.assertEqual(port, 8767)

    def test_manager_uses_requested_port_when_free(self):
        module = load_run_manager()
        with patch.object(module, "port_free", side_effect=lambda port: port == 8766):
            port = module.choose_manager_port(8766)
        self.assertEqual(port, 8766)

    def test_manager_build_is_current(self):
        manager = (BASE / "manager_api" / "main.py").read_text(encoding="utf-8")
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        launcher = (BASE / "run_manager.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "2.0.1-alpha"', manager)
        self.assertIn('BUILD_ID = "phase38"', manager)
        self.assertIn("phase38", html)
        self.assertIn('MANAGER_BUILD = "phase38"', launcher)


if __name__ == "__main__":
    unittest.main()
