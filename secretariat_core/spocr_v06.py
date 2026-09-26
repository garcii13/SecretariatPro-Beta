"""SP-OCR v0.6: reloj LED exacto, incluido el cero inicial visible."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

import joblib
import numpy as np
from PIL import Image


DIGIT_RANGES = ((0.00, 0.25), (0.20, 0.48), (0.52, 0.80), (0.74, 1.00))
V04_DIMENSIONS = {(112, 43)}
V05_HYBRID_DIMENSIONS = {(77, 29)}
V05_COMPLETION_DIMENSIONS = {(99, 31)}
V06_HYBRID_DIMENSIONS = {(102, 33), (108, 37)}
V06_OVERRIDE_CONFIDENCE = 0.97
VERIFIED_DIMENSIONS = (
    V04_DIMENSIONS | V05_HYBRID_DIMENSIONS | V05_COMPLETION_DIMENSIONS | V06_HYBRID_DIMENSIONS
)


def canonical_time(value: str) -> str:
    value = "".join(c for c in str(value) if c.isdigit() or c == ":")
    if ":" not in value:
        digits = "".join(c for c in value if c.isdigit())
        if len(digits) in (3, 4):
            value = digits[:-2] + ":" + digits[-2:]
    return value


def label_digits(value: str) -> list[int] | None:
    value = canonical_time(value)
    if ":" not in value:
        return None
    minute, second = value.split(":", 1)
    if (
        not minute.isdigit()
        or not second.isdigit()
        or len(minute) not in (1, 2)
        or len(second) != 2
        or int(second) > 59
    ):
        return None
    digits = f"{int(minute):02d}{second}"
    return [int(c) for c in digits]


def partial_baseline(value: str) -> list[int | None]:
    """Extrae los dígitos fiables incluso de lecturas truncadas de PaddleOCR."""
    value = "".join(c for c in str(value) if c.isdigit() or c == ":")
    known: list[int | None] = [None, None, None, None]
    if ":" in value:
        minute, second = value.split(":", 1)
        if minute.isdigit() and len(minute) in (1, 2):
            minute = f"{int(minute):02d}"
            known[0:2] = [int(minute[0]), int(minute[1])]
        if second.isdigit():
            if len(second) >= 1:
                known[2] = int(second[0])
            if len(second) >= 2:
                known[3] = int(second[1])
        return known
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) == 4:
        return [int(c) for c in digits]
    if len(digits) == 3:
        return [0, int(digits[0]), int(digits[1]), int(digits[2])]
    return known


def _normalise(array: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(array, (2.0, 99.2))
    return np.clip((array - lo) / (hi - lo + 1e-6), 0, 1).astype(np.float32)


def clock_channels(image: Image.Image | str | Path) -> np.ndarray:
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    activation = _normalise(np.clip(1.12 * r - 0.50 * g - 0.36 * b, 0, None))
    luminance = _normalise(0.299 * r + 0.587 * g + 0.114 * b)
    return np.stack((activation, luminance)).astype(np.float32)


def _resize(array: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    source = Image.fromarray(np.uint8(np.clip(array, 0, 1) * 255), mode="L")
    return np.asarray(source.resize(size, Image.Resampling.BILINEAR), dtype=np.float32) / 255


def digit_tensors(image: Image.Image | str | Path) -> list[np.ndarray]:
    channels = clock_channels(image)
    width = channels.shape[2]
    result = []
    for start, end in DIGIT_RANGES:
        x0 = max(0, int(round(start * width)))
        x1 = min(width, int(round(end * width)))
        crop = channels[:, :, x0:max(x0 + 1, x1)]
        result.append(np.stack([_resize(channel, (24, 32)) for channel in crop]))
    return result


def _hog(array: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(array)
    magnitude = np.hypot(gx, gy)
    angle = (np.arctan2(gy, gx) + np.pi) % np.pi
    output = []
    for y in range(0, 32, 8):
        for x in range(0, 24, 8):
            mag = magnitude[y:y + 8, x:x + 8].ravel()
            ang = angle[y:y + 8, x:x + 8].ravel()
            position = ang * 9 / np.pi
            low = np.floor(position).astype(int) % 9
            high = (low + 1) % 9
            fraction = position - np.floor(position)
            hist = np.zeros(9, dtype=np.float32)
            np.add.at(hist, low, mag * (1 - fraction))
            np.add.at(hist, high, mag * fraction)
            hist /= np.linalg.norm(hist) + 1e-6
            output.extend(hist)
    return np.asarray(output, dtype=np.float32)


def digit_features(tensor: np.ndarray) -> np.ndarray:
    output = []
    for channel in tensor:
        output.extend(_resize(channel, (16, 24)).ravel())
        output.extend(_hog(channel))
        output.extend(channel.mean(axis=0))
        output.extend(channel.mean(axis=1))
    return np.asarray(output, dtype=np.float32)


def combine(probabilities: list[np.ndarray], baseline: str, alpha: list[float]) -> tuple[str, list[int]]:
    known = partial_baseline(baseline)
    digits = []
    for position, probability in enumerate(probabilities):
        score = np.log(np.clip(probability, 1e-8, 1.0))
        if known[position] is not None:
            score[int(known[position])] += alpha[position]
        if position == 2:
            score[6:] = -1e9
        digits.append(int(np.argmax(score)))
    return f"{digits[0]}{digits[1]}:{digits[2]}{digits[3]}", digits


def safe_route(
    dimension: tuple[int, int], baseline: str, specialist: str, hybrid: str
) -> tuple[str, str]:
    """Evita perder aciertos de PaddleOCR fuera de perfiles verificados."""
    if tuple(dimension) in VERIFIED_DIMENSIONS:
        return hybrid, "verified_hybrid"
    if label_digits(baseline) is not None:
        return canonical_time(baseline), "valid_baseline_guard"
    return specialist, "invalid_baseline_fallback"


@dataclass
class HybridPrediction:
    value: str
    canonical_value: str
    specialist_value: str
    baseline_value: str
    confidences: list[float]
    route: str


class SPOCRv06Hybrid:
    def __init__(self, path: str | Path):
        # The model was serialized with NumPy 2.x, while the stable macOS
        # Paddle stack intentionally remains on NumPy 1.26.  NumPy 1.x exposes
        # the same implementation under ``numpy.core``; register the 2.x module
        # aliases before unpickling so one model artifact works on both stacks.
        try:
            import numpy.core as numpy_core

            sys.modules.setdefault("numpy._core", numpy_core)
            sys.modules.setdefault("numpy._core.multiarray", numpy_core.multiarray)
        except Exception:
            pass
        payload = joblib.load(path)
        self.models = payload["models"]
        self.alpha = payload["alpha"]

    def probabilities(self, image: Image.Image | str | Path, model_key: str) -> list[np.ndarray]:
        model = self.models[model_key]
        result = []
        for tensor in digit_tensors(image):
            raw = model.predict_proba(digit_features(tensor)[None])[0]
            full = np.full(10, 1e-8, dtype=np.float32)
            full[np.asarray(model.classes_, dtype=int)] = raw
            full /= full.sum()
            result.append(full)
        return result

    def predict(self, image: Image.Image | str | Path, baseline: str = "") -> HybridPrediction:
        if isinstance(image, Image.Image):
            source = image
        else:
            source = Image.open(image)
        dimension = source.size
        if dimension in V06_HYBRID_DIMENSIONS:
            model_key = "v06"
            route = "verified_v06_hybrid"
        elif dimension in V05_HYBRID_DIMENSIONS:
            model_key = "v05"
            route = "verified_v05_hybrid"
        elif dimension in V04_DIMENSIONS:
            model_key = "v04"
            route = "verified_v04_hybrid"
        elif dimension in V05_COMPLETION_DIMENSIONS and label_digits(baseline) is None:
            model_key = "v05"
            route = "verified_v05_completion"
        elif label_digits(baseline) is not None:
            value = canonical_time(baseline)
            return HybridPrediction(
                value=value,
                canonical_value=value,
                specialist_value="",
                baseline_value=baseline,
                confidences=[],
                route="valid_baseline_guard",
            )
        else:
            model_key = "v04"
            route = "invalid_baseline_v04_fallback"

        probabilities = self.probabilities(source, model_key)
        specialist, _ = combine(probabilities, "", [0, 0, 0, 0])
        hybrid, _ = combine(probabilities, baseline, self.alpha[model_key])
        value = specialist if route == "invalid_baseline_v04_fallback" else hybrid
        confidences = [float(probability.max()) for probability in probabilities]

        if dimension in V06_HYBRID_DIMENSIONS:
            baseline_value = canonical_time(baseline)
            confidence = min(confidences) if confidences else 0.0
            one_digit_minute = bool(re.fullmatch(r"\d:\d{2}", baseline_value))
            two_digit_minute = bool(re.fullmatch(r"\d{2}:\d{2}", baseline_value))
            # A one-digit Paddle result on these verified four-digit displays
            # is allowed through so the visible leading zero is restored.
            # Other disagreements require very strong sequence confidence.
            if (
                value != baseline_value
                and not one_digit_minute
                and confidence < V06_OVERRIDE_CONFIDENCE
            ):
                value = baseline_value if two_digit_minute else ""
                route = "verified_v06_confidence_guard"

        return HybridPrediction(
            value=value,
            canonical_value=canonical_time(value),
            specialist_value=specialist,
            baseline_value=baseline,
            confidences=confidences,
            route=route,
        )
