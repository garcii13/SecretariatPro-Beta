from __future__ import annotations

import unittest
from unittest.mock import patch

import run_app


class Phase8DesktopTests(unittest.TestCase):
    def test_default_port_is_stable_for_obs(self):
        self.assertEqual(run_app.DEFAULT_PORT, 8765)

    def test_health_payload_handles_unavailable_server(self):
        with patch("run_app.urlopen", side_effect=OSError("offline")):
            self.assertIsNone(run_app.health_payload(8765))

    def test_error_page_escapes_content(self):
        page = run_app.error_page("A<B", "x&y")
        self.assertIn("A&lt;B", page)
        self.assertIn("x&amp;y", page)


if __name__ == "__main__":
    unittest.main()
