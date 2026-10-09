import tempfile
import unittest
from pathlib import Path

from secretariat_core.windows_ocr import MODEL_NAME, recognition_options


class WindowsModelAssetsTests(unittest.TestCase):
    def test_installer_without_base_model_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError, "Modelo PaddleOCR incompleto"):
                recognition_options(root, frozen=True)

    def test_development_can_download_first_run_model(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(recognition_options(root, frozen=False), {})

    def test_complete_model_uses_local_path_for_both_graph_formats(self):
        for graph in ("inference.json", "inference.pdmodel"):
            with self.subTest(graph=graph), tempfile.TemporaryDirectory() as root:
                model = Path(root) / "models" / MODEL_NAME
                model.mkdir(parents=True)
                for name in (graph, "inference.yml", "inference.pdiparams"):
                    (model / name).write_bytes(b"fixture")
                self.assertEqual(recognition_options(root, frozen=True), {"model_dir": str(model)})

    def test_partial_local_model_never_silently_downloads(self):
        with tempfile.TemporaryDirectory() as root:
            model = Path(root) / "models" / MODEL_NAME
            model.mkdir(parents=True)
            for name in ("inference.yml", "inference.pdiparams"):
                (model / name).write_bytes(b"fixture")
            with self.assertRaisesRegex(RuntimeError, "Falta el grafo"):
                recognition_options(root, frozen=False)


if __name__ == "__main__":
    unittest.main()
