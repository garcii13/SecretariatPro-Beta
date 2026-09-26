"""SP-SCORE v0.1: score specialist built from real SecretariatPro LEDs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

from secretariat_core.spocr_v06 import _resize, clock_channels, digit_features


SINGLE_OVERRIDE_CONFIDENCE = 0.90
DOUBLE_OVERRIDE_CONFIDENCE = 0.92
EMPTY_FALLBACK_CONFIDENCE = 0.80
COUNT_CONFIDENCE = 0.90


def clean_score(value: str) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if not digits:
        return ""
    number = int(digits)
    return str(number) if 0 <= number < 100 else ""


def _count_features(image: Image.Image) -> np.ndarray:
    channels = clock_channels(image)
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
    channels = clock_channels(image)
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


class SPScoreV01:
    """Recognize 0-99 as individual digits and conservatively fuse Paddle."""

    def __init__(self, path: str | Path):
        payload = joblib.load(path)
        if payload.get("format") != "SP-SCORE-v0.1-digits":
            raise ValueError("Formato de modelo SP-SCORE no compatible")
        self.digit_model = payload["digit_model"]
        self.count_model = payload["count_model"]

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
            if count_confidence >= COUNT_CONFIDENCE and specialist_confidence >= EMPTY_FALLBACK_CONFIDENCE:
                value, route = specialist, "invalid_baseline_fallback"
            else:
                value, route = "", "uncertain_fallback_guard"
        else:
            threshold = SINGLE_OVERRIDE_CONFIDENCE if count == 1 else DOUBLE_OVERRIDE_CONFIDENCE
            if count_confidence >= COUNT_CONFIDENCE and specialist_confidence >= threshold:
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
