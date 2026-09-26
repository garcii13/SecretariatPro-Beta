import tempfile
import unittest
from pathlib import Path

import numpy as np

from video_source import SharedFramePublisher, SharedFrameReader


ROOT = Path(__file__).resolve().parents[1]


class Phase58PersistentCameraTests(unittest.TestCase):
    def test_shared_frame_bridge_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "camera_frame.bin"
            publisher = SharedFramePublisher(path)
            reader = SharedFrameReader(path)
            frame = np.arange(5 * 7 * 3, dtype=np.uint8).reshape(5, 7, 3)
            publisher.publish(frame)
            received = reader.read()
            self.assertIsNotNone(received)
            self.assertTrue(np.array_equal(frame, received))
            publisher.close(remove=True)

    def test_worker_uses_shared_camera_stream(self):
        text = (ROOT / "ocr_worker.py").read_text(encoding="utf-8")
        self.assertIn("SharedFrameReader", text)
        self.assertIn("camera_frame_path", text)
        self.assertNotIn("CameraStream(int(source_id))", text)

    def test_preview_uses_persistent_camera_service(self):
        text = (ROOT / "secretariat_api" / "main.py").read_text(encoding="utf-8")
        self.assertIn("runtime.camera_service.activate", text)
        self.assertIn("runtime.camera_service.read", text)
        self.assertIn('/api/ocr/source/activate', text)

    def test_camera_selection_activates_immediately(self):
        text = (ROOT / "webapp" / "app.js").read_text(encoding="utf-8")
        self.assertIn("activateOCRSourceSelection", text)
        self.assertIn("Cámara OCR activa de forma continua", text)


if __name__ == "__main__":
    unittest.main()
