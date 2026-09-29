import tempfile
import threading
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import video_source


class CameraStartupTests(unittest.TestCase):
    def test_camera_waits_for_native_permission_result(self):
        framework = Mock(AVAuthorizationStatusAuthorized=3, AVAuthorizationStatusNotDetermined=0, AVMediaTypeVideo='video')
        framework.AVCaptureDevice.authorizationStatusForMediaType_.return_value = 0
        framework.AVCaptureDevice.requestAccessForMediaType_completionHandler_.side_effect = lambda media, cb: cb(True)
        with patch.object(video_source.sys, 'platform', 'darwin'), patch.dict(sys.modules, {'AVFoundation': framework}):
            video_source.ensure_camera_permission(timeout=.01)
            framework.AVCaptureDevice.requestAccessForMediaType_completionHandler_.assert_called_once()

    def test_denied_camera_permission_is_not_reported_as_disconnected(self):
        framework = Mock(AVAuthorizationStatusAuthorized=3, AVAuthorizationStatusNotDetermined=0, AVMediaTypeVideo='video')
        framework.AVCaptureDevice.authorizationStatusForMediaType_.return_value = 2
        with patch.object(video_source.sys, 'platform', 'darwin'), patch.dict(sys.modules, {'AVFoundation': framework}):
            with self.assertRaisesRegex(RuntimeError, 'denegado el acceso'):
                video_source.ensure_camera_permission()
        framework.AVCaptureDevice.requestAccessForMediaType_completionHandler_.assert_not_called()

    def test_frozen_macos_camera_uses_live_not_the_ocr_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            frame = np.zeros((4, 6, 3), dtype=np.uint8)
            process = Mock()
            process.poll.return_value = None
            with patch.object(video_source.sys, 'frozen', True, create=True), \
                 patch.object(video_source.sys, 'platform', 'darwin'), \
                 patch.object(video_source.sys, 'executable', '/Applications/SecretariatPro Live.app/Contents/MacOS/SecretariatPro Live'), \
                 patch.object(video_source.subprocess, 'Popen', return_value=process) as popen, \
                 patch.object(video_source, 'SharedFrameReader') as reader:
                reader.return_value.read.return_value = frame
                stream = video_source.IsolatedCameraStream(1, Path(folder) / 'frames.bin')
                self.assertEqual(popen.call_args.args[0][:3], [video_source.sys.executable, '--camera', '1'])
                self.assertIn('Starting camera 1', stream.path.with_suffix('.log').read_text())
                stream.close()

    def test_simultaneous_selection_and_preview_share_one_camera_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            service = video_source.PersistentCameraService(Path(folder) / 'frames.bin')
            opened, proceed = threading.Event(), threading.Event()
            frame = np.zeros((4, 6, 3), dtype=np.uint8)
            stream = Mock()
            stream.read.return_value = frame
            results, errors = [], []

            def start(*args):
                opened.set()
                if not proceed.wait(2):
                    raise RuntimeError('test startup timed out')
                return stream

            def activate():
                try:
                    results.append(service.activate(1))
                except Exception as exc:
                    errors.append(exc)

            with patch.object(video_source, 'IsolatedCameraStream', side_effect=start) as factory, \
                 patch.object(service, '_capture_loop', side_effect=lambda source, stop: stop.wait(5)):
                first = threading.Thread(target=activate)
                second = threading.Thread(target=activate)
                try:
                    first.start()
                    self.assertTrue(opened.wait(1))
                    second.start()
                    proceed.set()
                    first.join(3)
                    second.join(3)
                    self.assertFalse(errors)
                    self.assertEqual(len(results), 2)
                    factory.assert_called_once()
                    self.assertTrue(all(row['active'] for row in results))
                finally:
                    proceed.set()
                    service.close()
                    first.join(3)
                    if second.ident:
                        second.join(3)
