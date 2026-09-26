from __future__ import annotations

import sys
from unittest.mock import Mock, patch

import numpy as np

import obs_projector_video
from obs_controller import OBSController
from secretariat_core.led_temporal import ReadingConsensus, fuse_led_crops


def test_projector_selection_uses_exact_native_window_id():
    windows = [
        obs_projector_video.ProjectorWindow(101, "OBS — Program Projector", (0, 0, 800, 450)),
        obs_projector_video.ProjectorWindow(202, "OBS — Program Projector", (20, 20, 800, 450)),
    ]
    assert obs_projector_video.select_projector_window(windows, "window:202") is windows[1]
    assert obs_projector_video.select_projector_window(windows, "window:999") is None


def test_macos_projector_capture_targets_window_not_visible_rectangle():
    window = obs_projector_video.ProjectorWindow(202, "OBS — Program Projector", (20, 20, 800, 450))
    exact = np.full((4, 5, 3), 77, dtype=np.uint8)
    window_capture = Mock()
    window_capture.capture_window.return_value = (exact, window.rect)
    with patch.object(obs_projector_video, "SYSTEM", "Darwin"), \
            patch.dict(sys.modules, {"window_capture": window_capture}), \
            patch.object(obs_projector_video, "_screen_capture") as screen_capture:
        result = obs_projector_video.capture_window(window)
    window_capture.capture_window.assert_called_once_with(202)
    screen_capture.assert_not_called()
    assert np.array_equal(result, exact)


def test_obs_socket_failure_clears_stale_connected_state():
    client = Mock()
    client.get_scene_list.side_effect = OSError("socket closed")
    controller = OBSController()
    controller.connected = True
    controller._client = client

    try:
        controller.snapshot()
    except RuntimeError as exc:
        assert "Se perdió" in str(exc)
    else:
        raise AssertionError("snapshot debía informar del cierre del WebSocket")

    assert controller.connected is False
    assert controller._client is None
    assert "socket closed" in controller.last_error
    client.disconnect.assert_called_once()


def test_led_burst_recovers_segments_from_different_refresh_phases():
    first = np.zeros((3, 3, 3), dtype=np.uint8)
    second = np.zeros_like(first)
    first[0, 1] = (0, 0, 210)
    second[2, 1] = (0, 0, 230)
    fused = fuse_led_crops([first, second])
    assert tuple(fused[0, 1]) == (0, 0, 210)
    assert tuple(fused[2, 1]) == (0, 0, 230)


def test_reading_consensus_blocks_single_frame_glitches():
    consensus = ReadingConsensus(confirmations=2)
    assert consensus.observe("time", "02:21") is None
    assert consensus.observe("time", "08:27") is None
    assert consensus.observe("time", "02:21") is None
    assert consensus.observe("time", "02:21") == "02:21"
    assert consensus.observe("time", "02:22") is None
    assert consensus.observe("time", "02:22") == "02:22"
