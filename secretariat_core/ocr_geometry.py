from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np

PERSPECTIVE_KEYS = ("top_left", "top_right", "bottom_right", "bottom_left")


def default_perspective() -> dict[str, Any]:
    return {
        "enabled": False,
        "points": {
            "top_left": {"x": 0.0, "y": 0.0},
            "top_right": {"x": 1.0, "y": 0.0},
            "bottom_right": {"x": 1.0, "y": 1.0},
            "bottom_left": {"x": 0.0, "y": 1.0},
        },
    }


def normalize_perspective(value: Any) -> dict[str, Any]:
    base = default_perspective()
    if not isinstance(value, dict):
        return base
    base["enabled"] = bool(value.get("enabled", False))
    source = value.get("points") if isinstance(value.get("points"), dict) else {}
    for key in PERSPECTIVE_KEYS:
        point = source.get(key)
        if not isinstance(point, dict):
            continue
        try:
            x = max(0.0, min(1.0, float(point.get("x", base["points"][key]["x"]))))
            y = max(0.0, min(1.0, float(point.get("y", base["points"][key]["y"]))))
        except (TypeError, ValueError):
            continue
        base["points"][key] = {"x": x, "y": y}
    return base


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def perspective_pixel_points(frame: np.ndarray, perspective: dict[str, Any]) -> np.ndarray:
    height, width = frame.shape[:2]
    normalized = normalize_perspective(perspective)
    points = normalized["points"]
    return np.array(
        [
            [points["top_left"]["x"] * (width - 1), points["top_left"]["y"] * (height - 1)],
            [points["top_right"]["x"] * (width - 1), points["top_right"]["y"] * (height - 1)],
            [points["bottom_right"]["x"] * (width - 1), points["bottom_right"]["y"] * (height - 1)],
            [points["bottom_left"]["x"] * (width - 1), points["bottom_left"]["y"] * (height - 1)],
        ],
        dtype=np.float32,
    )


def perspective_is_valid(frame: np.ndarray, perspective: dict[str, Any]) -> bool:
    if frame is None or frame.size == 0:
        return False
    normalized = normalize_perspective(perspective)
    if not normalized.get("enabled"):
        return False
    pts = perspective_pixel_points(frame, normalized)
    area = abs(float(cv2.contourArea(pts)))
    height, width = frame.shape[:2]
    # Reject crossed/degenerate quadrilaterals and selections too small to be useful.
    if area < max(400.0, width * height * 0.01):
        return False
    if not cv2.isContourConvex(pts.astype(np.int32)):
        return False
    return True


def apply_perspective(frame: np.ndarray, perspective: dict[str, Any] | None) -> np.ndarray:
    """Rectify a user-selected scoreboard quadrilateral.

    Points are normalized against the captured source so calibration survives
    window resizing. The returned image is the coordinate space used by OCR ROI.
    """
    if frame is None or frame.size == 0:
        return frame
    normalized = normalize_perspective(perspective)
    if not perspective_is_valid(frame, normalized):
        return frame

    tl, tr, br, bl = perspective_pixel_points(frame, normalized)
    width = int(round(max(_distance(tr, tl), _distance(br, bl))))
    height = int(round(max(_distance(bl, tl), _distance(br, tr))))
    src_h, src_w = frame.shape[:2]
    width = max(64, min(width, max(src_w * 2, 64)))
    height = max(48, min(height, max(src_h * 2, 48)))
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype=np.float32), destination)
    return cv2.warpPerspective(
        frame,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
