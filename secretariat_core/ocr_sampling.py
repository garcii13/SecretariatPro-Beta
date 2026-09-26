from __future__ import annotations

import base64
import hashlib
from typing import Any

import cv2


def crop_roi(full_img, roi: dict[str, float] | None):
    if full_img is None or getattr(full_img, "size", 0) == 0 or not roi:
        return None
    height, width = full_img.shape[:2]
    try:
        x = max(0, min(width - 1, int(round(float(roi["x"]) * width))))
        y = max(0, min(height - 1, int(round(float(roi["y"]) * height))))
        w = max(1, int(round(float(roi["w"]) * width)))
        h = max(1, int(round(float(roi["h"]) * height)))
    except (KeyError, TypeError, ValueError):
        return None
    crop = full_img[y:min(height, y + h), x:min(width, x + w)]
    return crop if getattr(crop, "size", 0) else None


def encode_private_sample(full_img, roi: dict[str, float] | None, *, quality: int = 88) -> dict[str, Any] | None:
    """Return a minimised JPEG crop suitable for the opt-in OCR dataset.

    Only the configured OCR ROI is encoded. No full frame, audio, team name,
    player information, match identifier or venue is included in the payload.
    """
    crop = crop_roi(full_img, roi)
    if crop is None:
        return None
    ok, encoded = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        return None
    raw = encoded.tobytes()
    return {
        "image_b64": base64.b64encode(raw).decode("ascii"),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "width": int(crop.shape[1]),
        "height": int(crop.shape[0]),
        "content_type": "image/jpeg",
    }
