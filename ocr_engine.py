"""OCR híbrido estable de SecretariatPro para marcadores digitales.

Fase 48 restaura deliberadamente el motor probado de la Fase 45:
``en_PP-OCRv4_mobile_rec`` en PaddleOCR 3.x y el pipeline clásico de
PaddleOCR 2.x como fallback. La corrección de perspectiva se realiza antes
de llegar a este módulo, por lo que el reconocimiento conserva exactamente
el preprocesado, limpieza y umbral que funcionaban antes de las Fases 46/47.

SP-OCR v0.7 se ejecuta después de PaddleOCR sobre la región del reloj y
SP-SCORE v0.2 hace lo mismo, con un modelo independiente, sobre los dos
marcadores. Ambos aplican compuertas conservadoras y conservan PaddleOCR ante
dudas. Si un modelo no está disponible o no puede cargarse, el flujo estable
continúa sin ningún cambio.
"""
from __future__ import annotations

import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

_engine = None
_engine_kind = None
MIN_CONFIDENCE = 0.25
STABLE_MODEL_NAME = "en_PP-OCRv4_mobile_rec"
SPOCR_MODEL_NAME = "SP-OCR v0.7 RC"
SPOCR_MODEL_FILENAME = "spocr_v0.7_hybrid.joblib"
SPSCORE_MODEL_NAME = "SP-SCORE v0.2"
SPSCORE_MODEL_FILENAME = "spscore_v0.2_digits.joblib"
_spocr_model_path = Path(__file__).resolve().parent / "models" / SPOCR_MODEL_FILENAME
_spscore_model_path = Path(__file__).resolve().parent / "models" / SPSCORE_MODEL_FILENAME
_spocr_engine = None
_spocr_load_attempted = False
_spocr_error = ""
_spscore_engine = None
_spscore_load_attempted = False
_spscore_error = ""


def configure(model_config: dict[str, Any] | None = None, *, base_dir=None) -> None:
    """Configure the optional SP-OCR clock specialist.

    PaddleOCR remains fixed to the stable Fase 45 recognizer.  The commercial
    app only loads the signed-off v0.7 artifact shipped in ``models``; arbitrary
    OCR Lab candidates are never loaded here.
    """
    global _spocr_model_path, _spocr_engine, _spocr_load_attempted, _spocr_error
    global _spscore_model_path, _spscore_engine, _spscore_load_attempted, _spscore_error
    root = Path(base_dir).resolve() if base_dir else Path(__file__).resolve().parent
    _spocr_model_path = root / "models" / SPOCR_MODEL_FILENAME
    _spscore_model_path = root / "models" / SPSCORE_MODEL_FILENAME
    _spocr_engine = None
    _spocr_load_attempted = False
    _spocr_error = ""
    _spscore_engine = None
    _spscore_load_attempted = False
    _spscore_error = ""


def _get_spocr():
    """Load the specialist lazily and fail closed to PaddleOCR."""
    global _spocr_engine, _spocr_load_attempted, _spocr_error
    if _spocr_load_attempted:
        return _spocr_engine
    _spocr_load_attempted = True
    if not _spocr_model_path.exists():
        _spocr_error = f"No se encontró {_spocr_model_path.name}"
        return None
    try:
        from secretariat_core.spocr_v07 import SPOCRv07Hybrid

        _spocr_engine = SPOCRv07Hybrid(_spocr_model_path)
        _spocr_error = ""
    except Exception as exc:
        _spocr_engine = None
        _spocr_error = f"{type(exc).__name__}: {exc}"[:300]
    return _spocr_engine


def _get_spscore():
    """Load the independent score specialist lazily and fail to PaddleOCR."""
    global _spscore_engine, _spscore_load_attempted, _spscore_error
    if _spscore_load_attempted:
        return _spscore_engine
    _spscore_load_attempted = True
    if not _spscore_model_path.exists():
        _spscore_error = f"No se encontró {_spscore_model_path.name}"
        return None
    try:
        from secretariat_core.spscore_v02 import SPScoreV02

        _spscore_engine = SPScoreV02(_spscore_model_path)
        _spscore_error = ""
    except Exception as exc:
        _spscore_engine = None
        _spscore_error = f"{type(exc).__name__}: {exc}"[:300]
    return _spscore_engine


def _is_apple_silicon_mac() -> bool:
    return sys.platform == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}


def _force_cpu_runtime() -> None:
    """Force Paddle onto CPU without relying on OCR-version-specific kwargs."""
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    try:
        import paddle
        paddle.set_device("cpu")
    except Exception:
        # Import/initialisation errors are reported later by the OCR constructor.
        pass


def _installed_paddleocr_major() -> int | None:
    try:
        import paddleocr
        version = str(getattr(paddleocr, "__version__", "") or "")
        match = re.match(r"\s*(\d+)", version)
        return int(match.group(1)) if match else None
    except Exception:
        return None


def _legacy_paddleocr(PaddleOCR):
    """Build PaddleOCR 2.x while tolerating patch-level constructor changes.

    We only retry when the exception is explicitly about an unsupported
    argument. Runtime/model errors must propagate instead of being hidden.
    """
    candidates = [
        dict(lang="en", use_angle_cls=False, show_log=False, use_gpu=False,
             enable_mkldnn=False, cpu_threads=1),
        dict(lang="en", use_angle_cls=False, show_log=False,
             enable_mkldnn=False, cpu_threads=1),
        dict(lang="en", use_angle_cls=False, enable_mkldnn=False, cpu_threads=1),
        dict(lang="en", use_angle_cls=False),
    ]
    last_exc = None
    for kwargs in candidates:
        try:
            return PaddleOCR(**kwargs)
        except Exception as exc:
            message = str(exc).lower()
            if not any(token in message for token in (
                "unknown argument", "unexpected keyword", "unexpected argument",
                "got an unexpected keyword",
            )):
                raise
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    return PaddleOCR(lang="en", use_angle_cls=False)


def get_ocr():
    global _engine, _engine_kind
    if _engine is not None:
        return _engine

    _force_cpu_runtime()

    # macOS / Apple Silicon normally runs the pinned PaddleOCR 2.x stack.
    # If the user launches the project with a different interpreter and a
    # PaddleOCR 3.x installation is found, do NOT pass legacy `use_gpu` args:
    # switch to TextRecognition(device="cpu") instead. This compatibility path
    # keeps Live usable while PREPARAR_MAC_BETA.command can recreate the stable
    # environment.
    if _is_apple_silicon_mac():
        major = _installed_paddleocr_major()
        if major is not None and major >= 3:
            from paddleocr import TextRecognition
            _engine = TextRecognition(
                model_name=STABLE_MODEL_NAME,
                device="cpu",
                cpu_threads=1,
                enable_mkldnn=False,
            )
            _engine_kind = "v3_text_recognition_mac_compat"
            return _engine

        from paddleocr import PaddleOCR
        _engine = _legacy_paddleocr(PaddleOCR)
        _engine_kind = "v2_pipeline_mac_stable"
        return _engine

    # Other platforms retain the current recognition API, but inference is
    # intentionally single-threaded for deterministic live operation.
    try:
        from paddleocr import TextRecognition
        _engine = TextRecognition(
            model_name=STABLE_MODEL_NAME,
            device="cpu",
            cpu_threads=1,
            enable_mkldnn=False,
        )
        _engine_kind = "v3_text_recognition"
        return _engine
    except (ImportError, TypeError, ValueError):
        pass

    from paddleocr import PaddleOCR
    _engine = _legacy_paddleocr(PaddleOCR)
    _engine_kind = "v2_pipeline"
    return _engine

def active_model_info() -> dict[str, Any]:
    return {
        "kind": _engine_kind or "pending",
        "model_name": STABLE_MODEL_NAME,
        "model_dir": "",
        "custom": False,
        "min_confidence": MIN_CONFIDENCE,
        "stable_restored": True,
        "apple_silicon_mac": _is_apple_silicon_mac(),
        "clock_hybrid": SPOCR_MODEL_NAME,
        "clock_hybrid_available": _spocr_model_path.exists(),
        "clock_hybrid_loaded": _spocr_engine is not None,
        "clock_hybrid_error": _spocr_error,
        "score_hybrid": SPSCORE_MODEL_NAME,
        "score_hybrid_available": _spscore_model_path.exists(),
        "score_hybrid_loaded": _spscore_engine is not None,
        "score_hybrid_error": _spscore_error,
    }


def crop_roi(full_img: np.ndarray, roi: dict[str, float]):
    if full_img is None or not roi:
        return None
    height, width = full_img.shape[:2]
    x = max(0, min(width, int(round(float(roi["x"]) * width))))
    y = max(0, min(height, int(round(float(roi["y"]) * height))))
    w = max(1, int(round(float(roi["w"]) * width)))
    h = max(1, int(round(float(roi["h"]) * height)))
    return full_img[y:min(height, y + h), x:min(width, x + w)]


def prepare_raw(img_crop: np.ndarray):
    """Return the OCR ROI exactly as captured, in colour, without enhancement.

    OpenCV frames are already uint8 BGR arrays, which PaddleOCR accepts directly.
    We only ensure a contiguous memory layout; pixel values and geometry are not
    modified at all.
    """
    if img_crop is None or img_crop.size == 0:
        return None
    if img_crop.dtype != np.uint8:
        img_crop = np.clip(img_crop, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(img_crop)


def preprocess(img_crop: np.ndarray, target_height: int = 64):
    """Legacy Fase 45 preparation, retained only as a rescue fallback.

    This path does NOT convert to grayscale or threshold/binarize either. It only
    resizes the colour crop and adds black padding. Phase 62 no longer uses it
    for the primary OCR attempt.
    """
    if img_crop is None or img_crop.size == 0:
        return None

    height, width = img_crop.shape[:2]
    target_width = max(32, int(target_height * (width / max(height, 1))))
    resized = cv2.resize(img_crop, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(resized, 8, 8, 12, 12, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def _result_payload(result: Any) -> dict:
    if result is None:
        return {}
    if isinstance(result, dict):
        payload = result
    else:
        try:
            payload = result.json
            if callable(payload):
                payload = payload()
        except Exception:
            payload = {}
    if isinstance(payload, dict) and isinstance(payload.get("res"), dict):
        return payload["res"]
    return payload if isinstance(payload, dict) else {}


def _parse_v2(result: Any):
    candidates = []

    def walk(obj):
        if isinstance(obj, dict):
            text = obj.get("rec_text") or obj.get("text")
            score = obj.get("rec_score") or obj.get("score") or 0.0
            if text is not None:
                candidates.append((str(text), float(score or 0.0)))
            for value in obj.values():
                walk(value)
        elif isinstance(obj, (list, tuple)):
            if len(obj) >= 2 and isinstance(obj[0], str) and isinstance(obj[1], (int, float)):
                candidates.append((obj[0], float(obj[1])))
            else:
                for value in obj:
                    walk(value)

    walk(result)
    return max(candidates, key=lambda item: item[1]) if candidates else ("", 0.0)


def _recognize(processed: np.ndarray):
    engine = get_ocr()

    if (_engine_kind or "").startswith("v3_text_recognition"):
        results = engine.predict(input=processed, batch_size=1)
        for result in results:
            payload = _result_payload(result)
            text = str(payload.get("rec_text") or "")
            confidence = float(payload.get("rec_score") or 0.0)
            if text:
                return text, confidence
        return "", 0.0

    result = engine.ocr(processed, det=False, cls=False)
    return _parse_v2(result)


def clean_score(text: str):
    digits = re.sub(r"[^0-9]", "", str(text or ""))
    if not digits:
        return ""
    value = int(digits)
    return str(value) if 0 <= value < 100 else ""


def clean_time(text: str):
    value = re.sub(r"[^0-9:.]", "", str(text or "")).strip()
    if not value:
        return ""
    if ":" not in value and value.count(".") == 1:
        value = value.replace(".", ":")
    if ":" not in value and "." not in value and value.isdigit():
        if len(value) == 4:
            value = f"{value[:2]}:{value[2:]}"
        elif len(value) == 3:
            value = f"{value[:1]}:{value[1:]}"
    return value


def _clean_candidate(text: str, confidence: float, allow_colon: bool):
    value = clean_time(text) if allow_colon else clean_score(text)
    if confidence < MIN_CONFIDENCE:
        value = ""
    return value


def _valid_clock(value: str) -> bool:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value or "").strip())
    return bool(match and int(match.group(2)) <= 59)


def _canonical_clock(value: str) -> str:
    """Keep the display width: ``02:23`` and ``2:23`` are distinct outputs."""
    return clean_time(value)


def _apply_clock_hybrid(crop, baseline_detail: dict[str, Any]) -> dict[str, Any]:
    """Apply SP-OCR to one clock crop while preserving the Paddle fallback."""
    global _spocr_error
    engine = _get_spocr()
    if engine is None or crop is None or getattr(crop, "size", 0) == 0:
        return baseline_detail
    try:
        from PIL import Image

        rgb = cv2.cvtColor(np.ascontiguousarray(crop), cv2.COLOR_BGR2RGB)
        prediction = engine.predict(Image.fromarray(rgb), baseline=str(baseline_detail.get("value") or ""))
        value = clean_time(prediction.value)
        if not _valid_clock(value):
            return baseline_detail

        baseline_value = str(baseline_detail.get("value") or "")
        changed = _canonical_clock(value) != _canonical_clock(baseline_value)
        confidence = float(baseline_detail.get("confidence") or 0.0)
        if changed and prediction.confidences:
            # Sequence confidence is deliberately conservative: the weakest
            # digit determines whether the corrected crop returns to OCR Lab.
            confidence = float(min(prediction.confidences))
        return {
            "value": value,
            "confidence": max(0.0, min(1.0, confidence)),
            "raw": baseline_detail.get("raw", ""),
            "pass": f"spocr_v07_{prediction.route}",
            "spocr_route": prediction.route,
            "baseline_value": baseline_value,
        }
    except Exception as exc:
        _spocr_error = f"{type(exc).__name__}: {exc}"[:300]
        return baseline_detail


def _apply_score_hybrid(crop, baseline_detail: dict[str, Any]) -> dict[str, Any]:
    """Apply SP-SCORE to one score crop while preserving the Paddle fallback."""
    global _spscore_error
    engine = _get_spscore()
    if engine is None or crop is None or getattr(crop, "size", 0) == 0:
        return baseline_detail
    try:
        from PIL import Image

        rgb = cv2.cvtColor(np.ascontiguousarray(crop), cv2.COLOR_BGR2RGB)
        baseline_value = clean_score(baseline_detail.get("value") or "")
        prediction = engine.predict(Image.fromarray(rgb), baseline=baseline_value)
        value = clean_score(prediction.value)
        if not value:
            return baseline_detail

        changed = value != baseline_value
        confidence = float(baseline_detail.get("confidence") or 0.0)
        if changed:
            confidence = float(prediction.confidence)
        return {
            "value": value,
            "confidence": max(0.0, min(1.0, confidence)),
            "raw": baseline_detail.get("raw", ""),
            "pass": f"spscore_v02_{prediction.route}",
            "spscore_route": prediction.route,
            "baseline_value": baseline_value,
            "digit_count": prediction.count,
        }
    except Exception as exc:
        _spscore_error = f"{type(exc).__name__}: {exc}"[:300]
        return baseline_detail


def _apply_field_hybrid(crop, detail: dict[str, Any], field_key: str | None) -> dict[str, Any]:
    if field_key == "time":
        return _apply_clock_hybrid(crop, detail)
    if field_key in {"team1_score", "team2_score"}:
        return _apply_score_hybrid(crop, detail)
    return detail


def read_crop_detail(crop, allow_colon=False, field_key=None):
    """Recognize the untouched colour ROI first; legacy preparation is fallback.

    Direct glare can collapse useful differences when an image is rescaled or
    otherwise normalized. The production path therefore feeds PaddleOCR the
    original perspective-corrected ROI with no grayscale, threshold, contrast,
    resize or padding. The old Fase 45 colour resize/padding path runs only when
    the raw image does not yield an accepted value.
    """
    raw_crop = prepare_raw(crop)
    if raw_crop is None:
        return {"value": "", "confidence": 0.0, "raw": "", "pass": "none"}

    raw_text, raw_confidence = _recognize(raw_crop)
    raw_value = _clean_candidate(raw_text, raw_confidence, allow_colon)
    if raw_value:
        detail = {
            "value": raw_value,
            "confidence": raw_confidence,
            "raw": raw_text,
            "pass": "raw",
        }
        return _apply_field_hybrid(raw_crop, detail, field_key)

    legacy = preprocess(crop)
    if legacy is None:
        return {"value": "", "confidence": raw_confidence, "raw": raw_text, "pass": "raw"}
    legacy_text, legacy_confidence = _recognize(legacy)
    legacy_value = _clean_candidate(legacy_text, legacy_confidence, allow_colon)
    if legacy_value:
        detail = {
            "value": legacy_value,
            "confidence": legacy_confidence,
            "raw": legacy_text,
            "pass": "legacy_fallback",
        }
        return _apply_field_hybrid(raw_crop, detail, field_key)

    # Preserve the most informative failed attempt for telemetry/debugging.
    if legacy_confidence > raw_confidence:
        detail = {"value": "", "confidence": legacy_confidence, "raw": legacy_text, "pass": "legacy_fallback"}
    else:
        detail = {"value": "", "confidence": raw_confidence, "raw": raw_text, "pass": "raw"}
    return _apply_field_hybrid(raw_crop, detail, field_key)


def read_region_detail(full_img, roi, allow_colon=False, field_key=None):
    crop = crop_roi(full_img, roi)
    return read_crop_detail(crop, allow_colon=allow_colon, field_key=field_key)


def read_region(full_img, roi, allow_colon=False, field_key=None):
    return read_region_detail(full_img, roi, allow_colon=allow_colon, field_key=field_key)["value"]


def read_scoreboard(full_img, regions):
    output = {}
    for key, roi in regions.items():
        output[key] = read_region(full_img, roi, allow_colon=(key == "time"), field_key=key) if roi else ""
    return output
