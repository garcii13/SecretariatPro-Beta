from __future__ import annotations

import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class Phase38ModalStartupTests(unittest.TestCase):
    def test_hidden_components_are_forced_out_of_layout(self):
        css = (BASE / "manager_app" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("[hidden]{display:none!important}", css)

    def test_entity_modal_is_hidden_and_accessible_at_startup(self):
        html = (BASE / "manager_app" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="modal-backdrop" hidden aria-hidden="true"', html)

    def test_javascript_resets_and_can_close_modal(self):
        js = (BASE / "manager_app" / "app.js").read_text(encoding="utf-8")
        self.assertIn("closeModal();", js)
        self.assertIn('event.key === "Escape"', js)
        self.assertIn('backdrop.setAttribute("hidden", "")', js)


if __name__ == "__main__":
    unittest.main()
