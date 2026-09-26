"""Small, model-independent helpers for multiplexed LED scoreboards."""
from __future__ import annotations

from dataclasses import dataclass, field

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

    def observe(self, key: str, value: str) -> str | None:
        value = str(value or "").strip()
        if not value:
            return None
        if self._emitted.get(key) == value:
            self._pending.pop(key, None)
            return value

        previous, count = self._pending.get(key, ("", 0))
        count = count + 1 if previous == value else 1
        self._pending[key] = (value, count)
        if count < max(1, int(self.confirmations)):
            return None

        self._emitted[key] = value
        self._pending.pop(key, None)
        return value
