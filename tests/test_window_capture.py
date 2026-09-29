import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import obs_projector_video
import window_capture
from secretariat_core.macos_window_capture import MacWindowCapture, WindowCaptureError


class WindowIdentityTests(unittest.TestCase):
    def test_missing_explicit_id_does_not_match_another_window_by_title(self):
        window = window_capture.WindowInfo(101, 'Same title', 'OBS', (0, 0, 800, 450))
        self.assertIsNone(window_capture.find_window([window], '202', window.label))
        self.assertIs(window_capture.find_window([window], '101', 'old title'), window)

    def test_legacy_label_requires_unique_match(self):
        first = window_capture.WindowInfo(101, 'Same title', 'OBS', (0, 0, 800, 450))
        second = window_capture.WindowInfo(202, 'Same title', 'OBS', (0, 0, 800, 450))
        self.assertIsNone(window_capture.find_window([first, second], label=first.label))
        self.assertIsNone(window_capture.find_window([first, second], label='Same'))
        self.assertIs(window_capture.find_window([first], label='Same'), first)

    def test_invalid_window_ids_never_reach_native_capture(self):
        with patch.object(window_capture, '_capture_macos_quartz') as legacy:
            for value in (None, '', 'screen', 0, -1):
                self.assertEqual(window_capture.capture_window(value), (None, None))
            legacy.assert_not_called()

    def test_projector_preserves_black_window_without_desktop_fallback(self):
        frame = np.zeros((12, 20, 3), dtype=np.uint8)
        with patch.object(window_capture, 'capture_window', return_value=(frame, None)) as native:
            result = obs_projector_video.capture_window(obs_projector_video.ProjectorWindow(123, 'OBS', (0, 0, 20, 12)))
        self.assertIs(result, frame)
        native.assert_called_once_with(123)

    def test_projector_propagates_capture_failure_without_other_source(self):
        with patch.object(window_capture, 'capture_window', side_effect=WindowCaptureError('denied')) as native:
            with self.assertRaisesRegex(WindowCaptureError, 'denied'):
                obs_projector_video.capture_window(obs_projector_video.ProjectorWindow(123, 'OBS', (0, 0, 20, 12)))
        native.assert_called_once_with(123)

    def test_duplicate_titles_keep_distinct_native_windows(self):
        quartz = Mock(kCGWindowListOptionOnScreenOnly=1, kCGWindowListExcludeDesktopElements=2, kCGNullWindowID=0)
        quartz.CGWindowListCopyWindowInfo.return_value = [
            {'kCGWindowNumber': value, 'kCGWindowName': 'Same title', 'kCGWindowOwnerName': 'OBS',
             'kCGWindowBounds': {'Width': 800, 'Height': 450}}
            for value in (101, 202, 101)]
        with patch.object(window_capture, 'SYSTEM', 'Darwin'), patch.object(window_capture, 'Quartz', quartz, create=True):
            self.assertEqual([w.window_id for w in window_capture.list_windows()], [101, 202])

    def test_modern_macos_failure_never_calls_legacy_screen_path(self):
        with patch.object(window_capture, 'SYSTEM', 'Darwin'), \
             patch.object(window_capture.platform, 'mac_ver', return_value=('26.0', (), '')), \
             patch.object(window_capture, 'get_window_rect', return_value=(10, 20, 320, 180)), \
             patch('secretariat_core.macos_window_capture.capture.capture_image', side_effect=WindowCaptureError('permission')), \
             patch.object(window_capture, '_capture_macos_quartz') as legacy:
            with self.assertRaisesRegex(WindowCaptureError, 'permission'):
                window_capture.capture_window(123)
            legacy.assert_not_called()


class ScreenCaptureKitTests(unittest.TestCase):
    def test_filter_targets_exact_window_and_retina_dimensions(self):
        selected = Mock()
        selected.windowID.return_value = 202
        other = Mock()
        other.windowID.return_value = 101
        content = Mock()
        content.windows.return_value = [other, selected]
        framework = Mock()
        framework.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_.side_effect = lambda desktop, onscreen, cb: cb(content, None)
        content_filter = framework.SCContentFilter.alloc.return_value.initWithDesktopIndependentWindow_.return_value
        content_filter.contentRect.return_value = SimpleNamespace(size=SimpleNamespace(width=320, height=180))
        content_filter.pointPixelScale.return_value = 2.0
        image = object()
        framework.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_.side_effect = lambda f, c, cb: cb(image, None)
        objc = Mock()
        from contextlib import nullcontext
        objc.autorelease_pool = nullcontext
        backend = MacWindowCapture()
        with patch.dict(sys.modules, {'ScreenCaptureKit': framework, 'objc': objc}):
            self.assertIs(backend.capture_image(202, bounds=(0, 0, 320, 180)), image)
            self.assertIs(backend.capture_image(202, bounds=(0, 0, 320, 180)), image)
            self.assertEqual(framework.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_.call_count, 1)
            self.assertIs(backend.capture_image(202, bounds=(0, 0, 240, 120)), image)
            self.assertEqual(framework.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_.call_count, 2)
            with self.assertRaisesRegex(WindowCaptureError, 'ya no está disponible'):
                backend.capture_image(999)
        content_filter_init = framework.SCContentFilter.alloc.return_value.initWithDesktopIndependentWindow_
        self.assertEqual(content_filter_init.call_count, 3)
        self.assertTrue(all(call.args == (selected,) for call in content_filter_init.call_args_list))
        configuration = framework.SCStreamConfiguration.alloc.return_value.init.return_value
        configuration.setWidth_.assert_called_with(640)
        configuration.setHeight_.assert_called_with(360)
        framework.SCContentFilter.alloc.return_value.initWithDisplay_includingWindows_.assert_not_called()

    def test_timeout_does_not_accumulate_native_requests_or_reuse_late_image(self):
        backend = MacWindowCapture(timeout=0.001)
        callbacks = []
        with self.assertRaises(WindowCaptureError):
            backend._wait(callbacks.append)
        with self.assertRaises(WindowCaptureError):
            backend._wait(callbacks.append)
        self.assertEqual(len(callbacks), 1)
        callbacks[0]('old image', None)
        self.assertEqual(backend._wait(lambda cb: cb('new image', None)), 'new image')

    def test_native_error_is_visible(self):
        error = Mock()
        error.localizedDescription.return_value = 'Screen recording denied'
        with self.assertRaisesRegex(WindowCaptureError, 'Screen recording denied'):
            MacWindowCapture()._wait(lambda cb: cb(None, error))


if __name__ == '__main__':
    unittest.main()
