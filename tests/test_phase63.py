import sys
import types
from unittest.mock import patch

import video_source


class _Device:
    def __init__(self, name, uid):
        self._name = name
        self._uid = uid

    def localizedName(self):
        return self._name

    def uniqueID(self):
        return self._uid


class _CaptureDevice:
    @staticmethod
    def devicesWithMediaType_(_media):
        return [_Device("FaceTime HD Camera", "device-0001"), _Device("iPhone Camera", "device-0002")]


def test_macos_native_enumeration_does_not_probe_opencv():
    fake = types.SimpleNamespace(AVCaptureDevice=_CaptureDevice, AVMediaTypeVideo="video")
    with patch.dict(sys.modules, {"AVFoundation": fake}), patch("platform.system", return_value="Darwin"), patch.object(video_source, "open_camera") as opener:
        rows = video_source.list_cameras()
    assert [r.label for r in rows] == ["FaceTime HD Camera", "iPhone Camera"]
    assert [r.source_id for r in rows] == ["0", "1"]
    opener.assert_not_called()


def test_active_native_camera_keeps_stream_detail():
    fake = types.SimpleNamespace(AVCaptureDevice=_CaptureDevice, AVMediaTypeVideo="video")
    with patch.dict(sys.modules, {"AVFoundation": fake}), patch("platform.system", return_value="Darwin"):
        rows = video_source.list_cameras(active_index=1, active_detail="1920×1080")
    assert rows[1].label == "iPhone Camera"
    assert rows[1].detail == "1920×1080"
