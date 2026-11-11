"""Adaptive, demand-driven OBS monitoring. Frames never touch the filesystem."""
from __future__ import annotations

import math
import threading
import time

import psutil


class SystemPressure:
    """Host deltas belong to the monitor, even when the worker thread changes."""

    def __init__(self):
        self.previous_cpu = None

    def __call__(self):
        times = psutil.cpu_times()
        total = sum(getattr(times, field, 0) for field in
                    ("user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"))
        idle = times.idle + getattr(times, "iowait", 0)
        cpu = 0.0
        if self.previous_cpu:
            old_total, old_idle = self.previous_cpu
            if total > old_total:
                cpu = max(0, min(100, 100 * (1 - (idle - old_idle) / (total - old_total))))
        self.previous_cpu = total, idle
        memory = psutil.virtual_memory()
        return {"cpu": cpu, "available": memory.available,
                "total": memory.total, "swap_out": psutil.swap_memory().sout}


def number(value, default=0.0):
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else default
    except (TypeError, ValueError):
        return default


class PreviewGovernor:
    """Fast backoff, slow recovery; OBS output always has priority over monitoring."""

    LEVELS = (2, 5, 8, 12, 15, 20, 25, 30, 40, 50, 60)

    def __init__(self, maximum=60):
        self.maximum = max(2, min(60, number(maximum, 60)))
        self.fps = min(15, self.maximum)
        self.paused = False
        self.reason = "warming_up"
        self.healthy_since = None
        self.previous = None
        self.capture_seconds = 0.0

    def capture_finished(self, seconds):
        self.capture_seconds = seconds if not self.capture_seconds else self.capture_seconds * .8 + seconds * .2
        # A slow request must not produce a tight screenshot loop between samples.
        # An occasional screenshot can wait for OBS's next GPU readback. Judge
        # ordinary latency by its moving average, not a single frame hiccup.
        if seconds > .25:
            self.fps = max(2, min(self.fps, .9 / seconds))
            self.healthy_since = None
            self.reason = "capture_busy"

    def sample(self, obs, host, now):
        valid = isinstance(obs, dict) and all(k in obs for k in (
            "active_fps", "render_ms", "render_skipped", "render_total", "output_skipped", "output_total", "target_fps"))
        host_valid = isinstance(host, dict) and all(k in host for k in ("cpu", "available", "total", "swap_out"))
        if not valid or not host_valid:
            self.fps = min(self.fps, 8)
            self.healthy_since = None
            self.reason = "telemetry_unavailable"
            self.previous = None
            if host_valid and (number(host["cpu"]) >= 92 or number(host["available"]) < max(256 * 1024 ** 2, number(host["total"]) * .04)):
                self.paused = True
                self.reason = "system_busy"
            # If already paused, missing telemetry is not proof of recovery.
            return
        target = max(1, number(obs["target_fps"], 30))
        limit = min(self.maximum, target)
        if self.capture_seconds:
            limit = min(limit, max(2, .9 / self.capture_seconds))
        self.fps = min(self.fps, limit)
        cpu = max(number(host["cpu"]), number(obs.get("cpu")))
        free = number(host["available"])
        total = number(host["total"])
        render_ratio = number(obs["render_ms"]) * target / 1000
        active_ratio = number(obs["active_fps"]) / target
        skipped, skipped_ratio, swapping = False, 0.0, False
        previous = self.previous
        if previous is not None:
            old_obs, old_host, old_time = previous
            for stage in ("render", "output"):
                count = number(obs[f"{stage}_skipped"]) - number(old_obs[f"{stage}_skipped"])
                frames = number(obs[f"{stage}_total"]) - number(old_obs[f"{stage}_total"])
                # OBS counters can reset when an output/session restarts.
                if count > 0 and frames > 0:
                    skipped = True
                    skipped_ratio = max(skipped_ratio, count / frames)
            swapping = number(host["swap_out"]) - number(old_host["swap_out"]) > 16 * 1024 ** 2 * max(1, now - old_time)
        self.previous = (dict(obs), dict(host), now)
        critical = (cpu >= 92 or free < max(256 * 1024 ** 2, total * .04)
                    or render_ratio >= .85 or active_ratio < .8 or skipped_ratio >= .02 or swapping)
        busy = critical or skipped or cpu >= 75 or free < max(512 * 1024 ** 2, total * .08) or render_ratio >= .6 or active_ratio < .95
        if busy:
            self.healthy_since = None
            self.reason = "output_busy" if skipped or render_ratio >= .6 or active_ratio < .95 else "system_busy"
            self.fps = max(2, self.fps / 2)
            if critical:
                self.paused = True
            return
        # Require generous headroom before increasing; the middle band holds steady.
        healthy = cpu < 60 and free >= max(768 * 1024 ** 2, total * .12) and render_ratio < .4 and active_ratio >= .98
        if not healthy:
            self.healthy_since = None
            return
        if self.healthy_since is None:
            self.healthy_since = now
        if self.paused:
            if now - self.healthy_since >= 5:
                self.paused = False
                self.fps = min(5, limit)
                self.reason = "recovering"
                self.healthy_since = now
        elif now - self.healthy_since >= 5:
            higher = next((fps for fps in self.LEVELS if fps > self.fps + .1), self.maximum)
            self.fps = min(higher, limit)
            self.reason = "headroom"
            self.healthy_since = now


class ProgramPreview:
    MAX_FRAME_BYTES = 4 * 1024 ** 2

    def __init__(self, fps: float = 60.0, pressure_probe=None):
        self.maximum = fps
        self.governor = PreviewGovernor(fps)
        self._pressure_probe = pressure_probe or SystemPressure()
        self._lock = threading.Lock()
        self._frame = None
        self._owner = None
        self._captured_at = float("-inf")
        self._scene_at = float("-inf")
        self._sample_at = float("-inf")
        self._clients = 0
        self._status = {"fps": 0, "paused": False, "reason": "idle", "frame_bytes": 0, "clients": 0}

    @property
    def interval(self):
        return 1.0 if self.governor.paused else 1.0 / self.governor.fps

    def status(self):
        # Immutable replacement on the writer: diagnostics never wait for OBS.
        return dict(self._status)

    def _publish_status(self):
        self._status = {"fps": 0 if self.governor.paused else round(self.governor.fps, 1),
                        "paused": self.governor.paused, "reason": self.governor.reason,
                        "frame_bytes": len(self._frame or b""), "clients": self._clients}

    def subscribe(self):
        with self._lock:
            self._clients += 1

    def unsubscribe(self):
        with self._lock:
            self._clients = max(0, self._clients - 1)
            if self._clients:
                self._publish_status()
                return
            owner = self._owner
            self._frame = None
            self._owner = None
            self._captured_at = self._scene_at = self._sample_at = float("-inf")
            self.governor = PreviewGovernor(self.maximum)
            self._status = {"fps": 0, "paused": False, "reason": "idle", "frame_bytes": 0, "clients": 0}
            if owner is not None:
                owner.release_program_preview()

    def read(self, obs):
        # Record before waiting so concurrent viewers share a slow capture.
        now = time.monotonic()
        with self._lock:
            if self._owner is obs and self._frame is not None and now - self._captured_at < self.interval:
                return self._frame
            if self._owner is not obs:
                if self._owner is not None:
                    self._owner.release_program_preview()
                self._frame = None
                self._sample_at = self._scene_at = float("-inf")
                self.governor = PreviewGovernor(self.maximum)
                self._owner = obs
            if now - self._sample_at >= 1:
                self._sample_at = now
                try:
                    metrics = obs.preview_metrics()
                except Exception:
                    metrics = None
                try:
                    host = self._pressure_probe()
                except Exception:
                    host = None
                self.governor.sample(metrics, host, now)
            self._frame = None
            if self.governor.paused:
                self._publish_status()
                return None
            refresh = now - self._scene_at >= .5
            started = time.perf_counter()
            try:
                frame = obs.program_screenshot(width=960, image_format="jpg", refresh_scene=refresh)
                if not isinstance(frame, bytes) or not frame or len(frame) > self.MAX_FRAME_BYTES:
                    raise ValueError("OBS devolvió una preview vacía o demasiado grande")
                self.governor.capture_finished(time.perf_counter() - started)
                self._frame = frame
                self._captured_at = now
                if refresh:
                    self._scene_at = now
                return frame
            finally:
                self._publish_status()
