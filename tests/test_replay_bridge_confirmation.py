"""Native hotkey confirmations must wait past a previous command's error."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from secretariat_core.services.replay_plugin_bridge import ReplayPluginBridge


class ReplayBridgeConfirmationTests(unittest.TestCase):
    def bridge(self, snapshots):
        control = SimpleNamespace(connected=True, trigger_hotkey_by_name=Mock())
        bridge = ReplayPluginBridge(control)
        bridge.status = Mock(side_effect=snapshots)
        return bridge

    @patch("secretariat_core.services.replay_plugin_bridge.time.sleep")
    def test_previous_error_does_not_reject_successful_buffer_activation(self, _sleep):
        previous = {"available": True, "buffers_active": False, "error": "Old composition failed"}
        active = {"available": True, "buffers_active": True, "error": ""}
        bridge = self.bridge([previous, previous, active])
        self.assertEqual(bridge.set_buffers_active(True), active)
        bridge.obs.trigger_hotkey_by_name.assert_called_once_with(bridge.HOTKEYS["toggle"])

    @patch("secretariat_core.services.replay_plugin_bridge.time.sleep")
    def test_each_hotkey_waits_past_its_existing_error(self, _sleep):
        for method, arguments, before, after in (
            ("take", (), {"playing": False}, {"playing": True}),
            ("out", (), {"playing": True}, {"playing": False}),
            ("switch_camera", ("next",), {"active_camera": 0}, {"active_camera": 1}),
        ):
            with self.subTest(method=method):
                previous = {**before, "error": "Previous command failed"}
                confirmed = {**after, "error": ""}
                bridge = self.bridge([previous, previous, confirmed])
                self.assertEqual(getattr(bridge, method)(*arguments), confirmed)

    def test_new_error_is_reported_without_waiting_for_timeout(self):
        previous = {"available": True, "buffers_active": False, "error": "Old failure"}
        bridge = self.bridge([previous, {**previous, "error": "Encoder unavailable"}])
        with self.assertRaisesRegex(RuntimeError, "Encoder unavailable"):
            bridge.set_buffers_active(True)

    @patch("secretariat_core.services.replay_plugin_bridge.time.sleep")
    @patch("secretariat_core.services.replay_plugin_bridge.time.monotonic", side_effect=[0, 0, 1])
    def test_persistent_error_is_reported_if_confirmation_never_arrives(self, _clock, _sleep):
        previous = {"available": True, "buffers_active": False, "error": "Unresolved failure"}
        bridge = self.bridge([previous, previous, previous])
        with self.assertRaisesRegex(RuntimeError, "Unresolved failure"):
            bridge.set_buffers_active(True, timeout=.5)


if __name__ == "__main__":
    unittest.main()
