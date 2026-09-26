"""SP-SCORE v0.2: phase-aware score specialist built from real LEDs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import joblib
import numpy as np
from PIL import Image

from secretariat_core.spocr_v07 import _hog, _resize


DEFAULT_OVERRIDE_CONFIDENCE = 0.91
DEFAULT_EMPTY_FALLBACK_CONFIDENCE = 0.88
DEFAULT_COUNT_CONFIDENCE = 0.92


def _normalise(array: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(array, (2.0, 99.2))
    return np.clip((array - lo) / (hi - lo + 1e-6), 0, 1).astype(np.float32)


def score_channels(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    activation_raw = np.clip(1.12 * red - 0.50 * green - 0.36 * blue, 0, 255)
    luminance_raw = 0.299 * red + 0.587 * green + 0.114 * blue
    return np.stack((
        _normalise(activation_raw),
        _normalise(luminance_raw),
        activation_raw / 255.0,
        luminance_raw / 255.0,
    )).astype(np.float32)


def digit_features(tensor: np.ndarray) -> np.ndarray:
    output = []
    for channel in tensor:
        output.extend(_resize(channel, (16, 24)).ravel())
        output.extend(_hog(channel))
        output.extend(channel.mean(axis=0))
        output.extend(channel.mean(axis=1))
    return np.asarray(output, dtype=np.float32)


def clean_score(value: str) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if not digits:
        return ""
    number = int(digits)
    return str(number) if 0 <= number < 100 else ""


def _count_features(image: Image.Image) -> np.ndarray:
    channels = score_channels(image)
    output = []
    for channel in channels:
        canvas = _resize(channel, (48, 40))
        output.extend(canvas.ravel())
        output.extend(canvas.mean(axis=0))
        output.extend(canvas.mean(axis=1))
    output.extend([
        image.width / max(image.height, 1),
        np.log1p(image.width),
        np.log1p(image.height),
    ])
    return np.asarray(output, dtype=np.float32)


def _score_parts(image: Image.Image, count: int) -> list[np.ndarray]:
    channels = score_channels(image)
    if count == 1:
        return [np.stack([_resize(channel, (24, 32)) for channel in channels])]

    width = channels.shape[2]
    middle = int(round(width * 0.43))
    overlap = max(2, int(round(width * 0.06)))
    return [
        np.stack([
            _resize(channel[:, : min(width, middle + overlap)], (24, 32))
            for channel in channels
        ]),
        np.stack([
            _resize(channel[:, max(0, middle - overlap):], (24, 32))
            for channel in channels
        ]),
    ]


@dataclass
class ScorePrediction:
    value: str
    specialist_value: str
    baseline_value: str
    confidence: float
    count: int
    count_confidence: float
    route: str


class SPScoreV02:
    """Recognize 0-99 as individual digits and conservatively fuse Paddle."""

    def __init__(self, path: str | Path):
        try:
            import numpy.core as numpy_core

            sys.modules.setdefault("numpy._core", numpy_core)
            sys.modules.setdefault("numpy._core.multiarray", numpy_core.multiarray)
        except Exception:
            pass
        payload = joblib.load(path)
        if payload.get("format") != "SP-SCORE-v0.2-digits":
            raise ValueError("Formato de modelo SP-SCORE no compatible")
        self.digit_model = payload["digit_model"]
        self.count_model = payload["count_model"]
        thresholds = payload.get("thresholds") or {}
        self.override_confidence = float(thresholds.get("override", DEFAULT_OVERRIDE_CONFIDENCE))
        self.empty_fallback_confidence = float(thresholds.get("empty", DEFAULT_EMPTY_FALLBACK_CONFIDENCE))
        self.count_confidence = float(thresholds.get("count", DEFAULT_COUNT_CONFIDENCE))

    def predict(self, image: Image.Image | str | Path, baseline: str = "") -> ScorePrediction:
        source = image if isinstance(image, Image.Image) else Image.open(image)
        source = source.convert("RGB")

        count_probability = self.count_model.predict_proba(_count_features(source)[None])[0]
        count_index = int(np.argmax(count_probability))
        count = int(self.count_model.classes_[count_index])
        count_confidence = float(count_probability[count_index])

        digits = []
        confidences = []
        for tensor in _score_parts(source, count):
            probability = self.digit_model.predict_proba(digit_features(tensor)[None])[0]
            index = int(np.argmax(probability))
            digits.append(str(int(self.digit_model.classes_[index])))
            confidences.append(float(probability[index]))

        specialist = clean_score("".join(digits))
        specialist_confidence = min(confidences) if confidences else 0.0
        baseline_value = clean_score(baseline)

        if specialist == baseline_value and baseline_value:
            value, route = baseline_value, "agreement"
        elif not baseline_value:
            if count_confidence >= self.count_confidence and specialist_confidence >= self.empty_fallback_confidence:
                value, route = specialist, "invalid_baseline_fallback"
            else:
                value, route = "", "uncertain_fallback_guard"
        else:
            if count_confidence >= self.count_confidence and specialist_confidence >= self.override_confidence:
                value, route = specialist, "high_confidence_override"
            else:
                value, route = baseline_value, "valid_baseline_guard"

        return ScorePrediction(
            value=value,
            specialist_value=specialist,
            baseline_value=baseline_value,
            confidence=specialist_confidence,
            count=count,
            count_confidence=count_confidence,
            route=route,
        )
