"""Small, model-independent helpers for multiplexed LED scoreboards."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

import numpy as np


def fuse_led_crops(crops: list[np.ndarray]) -> np.ndarray | None:
    """Combine a short burst by keeping the strongest red LED sample per pixel.

    The burst is captured before OCR and spans only a few camera frames. This
    recovers segments missed by LED multiplexing while preserving the original
    BGR colour of the winning pixel instead of globally brightening the crop.
    """
    valid = [np.ascontiguousarray(crop) for crop in crops if crop is not None and getattr(crop, "size", 0)]
    if not valid:
        return None
    shape = valid[0].shape
    valid = [crop for crop in valid if crop.shape == shape and crop.ndim == 3 and crop.shape[2] >= 3]
    if len(valid) < 2:
        return valid[0].copy() if valid else None

    stack = np.stack(valid).astype(np.float32)
    blue, green, red = stack[..., 0], stack[..., 1], stack[..., 2]
    energy = 1.12 * red - 0.50 * green - 0.36 * blue
    winner = np.argmax(energy, axis=0)
    rows, columns = np.indices(winner.shape)
    return np.stack(valid)[winner, rows, columns].copy()


@dataclass
class ReadingConsensus:
    """Require consecutive agreement before a new OCR value reaches output."""

    confirmations: int = 2
    _pending: dict[str, tuple[str, int]] = field(default_factory=dict)
    _emitted: dict[str, str] = field(default_factory=dict)
    _clock_sample: tuple[int, float, float] | None = None

    def observe(self, key: str, value: str, *, captured_at: float | None = None,
                confidence: float = 0.0) -> str | None:
        value = str(value or "").strip()
        if not value:
            self._pending.pop(key, None)
            if key == "time":
                self._clock_sample = None
            return None
        progressing = False
        if key == "time":
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
            current = None
            if match and int(match[2]) < 60 and captured_at is not None:
                seconds = int(match[1]) * 60 + int(match[2])
                current = (seconds, captured_at, confidence)
                if self._clock_sample is not None:
                    previous_seconds, previous_at, previous_confidence = self._clock_sample
                    elapsed = captured_at - previous_at
                    delta = abs(seconds - previous_seconds)
                    # A running clock need not repeat a value on a slower PC.
                    # Accept two confident samples whose movement agrees with
                    # capture time, in either clock direction. Large jumps and
                    # weak readings still require exact repeated agreement.
                    progressing = (
                        min(confidence, previous_confidence) >= 0.75
                        and 0 < elapsed <= 10
                        and delta > 0 and abs(delta - elapsed) <= 1.0
                    )
            self._clock_sample = current
        if self._emitted.get(key) == value:
            if key == "time" and captured_at is not None:
                self._pending[key] = (value, max(1, self.confirmations))
            else:
                self._pending.pop(key, None)
            return value

        previous, count = self._pending.get(key, ("", 0))
        count = count + 1 if previous == value or progressing else 1
        self._pending[key] = (value, count)
        if count < max(1, int(self.confirmations)):
            return None

        self._emitted[key] = value
        if key == "time" and captured_at is not None:
            self._pending[key] = (value, max(1, self.confirmations))
        else:
            self._pending.pop(key, None)
        return value
