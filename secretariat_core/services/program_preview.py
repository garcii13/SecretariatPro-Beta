"""Demand-driven OBS previews shared across local monitor connections."""
from __future__ import annotations

import threading
import time


class ProgramPreview:
    def __init__(self, fps: float = 8.0):
        self.interval = 1.0 / fps
        self._lock = threading.Lock()
        self._frame = None
        self._owner = None
        self._captured_at = float("-inf")
        self._scene_at = float("-inf")

    def read(self, obs):
        with self._lock:
            now = time.monotonic()
            if self._owner is obs and self._frame is not None and now - self._captured_at < self.interval:
                return self._frame
            refresh = self._owner is not obs or now - self._scene_at >= 0.5
            # A failed request never returns the previous image as a new frame.
            self._frame = None
            frame = obs.program_screenshot(width=960, image_format="jpg", refresh_scene=refresh)
            self._owner = obs
            self._frame = frame
            self._captured_at = time.monotonic()
            if refresh:
                self._scene_at = self._captured_at
            return frame
