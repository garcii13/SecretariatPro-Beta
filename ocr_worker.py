"""Isolated OCR worker. The GUI watchdog can terminate/restart this process safely."""
# Phase 52 compatibility marker: CameraStream (replaced by SharedFrameReader in Phase 58).
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"

import json
import sys
import time
import traceback
import faulthandler
faulthandler.enable()

PREFIX = "OCRMSG "


def sample_threshold_for(field, config):
    """Return the bounded OCR Lab sampling threshold for one scoreboard field."""
    try:
        default = float(config.get("sample_threshold") or 0.72)
    except (TypeError, ValueError):
        default = 0.72
    default = max(0.05, min(0.99, default))
    overrides = config.get("sample_thresholds") or {}
    try:
        value = float(overrides.get(field, default)) if isinstance(overrides, dict) else default
    except (TypeError, ValueError):
        value = default
    return max(0.05, min(0.99, value))


def emit(payload):
    print(PREFIX + json.dumps(payload, ensure_ascii=False), flush=True)


def main(config_path):
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)
    import window_capture
    import ocr_engine
    import cv2
    cv2.setNumThreads(1)
    from video_source import SharedFrameReader
    from secretariat_core.ocr_geometry import apply_perspective
    from secretariat_core.led_temporal import ReadingConsensus, fuse_led_crops
    from secretariat_core.ocr_sampling import encode_private_sample

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    source_type = str(cfg.get("source_type") or "window").strip().lower()
    source_id = str(cfg.get("source_id") or "").strip()
    window_id = cfg.get("window_id")
    regions = cfg.get("regions", {})
    perspective = cfg.get("perspective") or {}
    ocr_engine.configure(cfg.get("model") or {}, base_dir=base)
    model_info = ocr_engine.active_model_info()
    share_samples = bool(cfg.get("sample_sharing"))
    sample_interval = max(10.0, float(cfg.get("sample_interval_s") or 30.0))
    last_sample_at = {"time": 0.0, "team1_score": 0.0, "team2_score": 0.0}
    last_sample_hash = {"time": "", "team1_score": "", "team2_score": ""}
    poll_s = max(0.08, int(cfg.get("poll_ms", 150)) / 1000.0)
    keys = [k for k in ("time", "team1_score", "team2_score") if regions.get(k)]
    cycle = 0
    camera = None
    phase_recovery = bool(cfg.get("led_phase_recovery", True))
    phase_frames = max(1, min(4, int(cfg.get("led_phase_frames") or 3))) if phase_recovery else 1
    phase_gap_s = max(0.0, min(0.05, float(cfg.get("led_phase_gap_ms") or 22.0) / 1000.0))
    consensus = ReadingConsensus(max(1, min(3, int(cfg.get("reading_confirmations") or 2))))

    def capture_source(wait_s=0.0):
        if source_type == "camera":
            deadline = time.monotonic() + wait_s
            while camera is not None:
                frame = camera.read(require_new=True)
                if frame is not None or time.monotonic() >= deadline:
                    return frame
                time.sleep(0.005)
            return None
        frame, _ = window_capture.capture_window(window_id)
        return frame

    try:
        if source_type == "camera":
            frame_path = str(cfg.get("camera_frame_path") or "").strip()
            if not frame_path:
                raise RuntimeError("No se recibió el stream persistente de la cámara OCR")
            camera = SharedFrameReader(frame_path)

        while True:
            started = time.monotonic()
            emit({"type": "heartbeat", "phase": "capture", "ts": time.time()})
            img = capture_source()
            if img is None:
                emit({"type": "error", "key": "capture", "message": "captura vacía"})
                time.sleep(min(1.0, poll_s))
                continue

            phase_images = [apply_perspective(img, perspective)]
            for _ in range(phase_frames - 1):
                if phase_gap_s:
                    time.sleep(phase_gap_s)
                extra = capture_source(wait_s=0.07)
                if extra is not None:
                    phase_images.append(apply_perspective(extra, perspective))
            img = phase_images[0]

            # Low-latency scheduler: read the clock every cycle and alternate
            # score regions. This is the same scheduling used by the stable OCR.
            ordered = []
            if "time" in keys:
                ordered.append("time")
            score_keys = [k for k in ("team1_score", "team2_score") if k in keys]
            if score_keys:
                ordered.append(score_keys[cycle % len(score_keys)])
            if not ordered and keys:
                ordered.append(keys[cycle % len(keys)])
            cycle += 1

            for key in ordered:
                emit({"type": "heartbeat", "phase": key, "ts": time.time()})
                try:
                    crops = [ocr_engine.crop_roi(frame, regions[key]) for frame in phase_images]
                    phase_crop = fuse_led_crops(crops)
                    detail = ocr_engine.read_crop_detail(
                        phase_crop, allow_colon=(key == "time"), field_key=key
                    )
                    value = detail.get("value")
                    now = time.time()
                    confidence = float(detail.get("confidence") or 0.0)
                    ocr_pass = str(detail.get("pass") or "normal")
                    confirmed_value = consensus.observe(key, value) if value else None
                    if confirmed_value:
                        emit({
                            "type": "reading", "key": key, "value": confirmed_value,
                            "confidence": confidence, "raw": detail.get("raw", ""),
                            "ocr_pass": ocr_pass, "ts": now,
                        })

                    # Opt-in telemetry for the private OCR Lab. Only the tiny
                    # OCR region is encoded, never the full frame.
                    sample_threshold = sample_threshold_for(key, cfg)
                    difficult = (not value) or confidence < sample_threshold or ocr_pass == "legacy_fallback"
                    if share_samples and difficult and now - last_sample_at.get(key, 0.0) >= sample_interval:
                        # Apply the interval even to identical samples; otherwise
                        # a frozen digit would be JPEG-encoded on every cycle.
                        last_sample_at[key] = now
                        # Store the actual fused crop that produced this reading.
                        sample = encode_private_sample(phase_crop, {"x": 0, "y": 0, "w": 1, "h": 1})
                        if sample and sample.get("sha256") != last_sample_hash.get(key):
                            last_sample_hash[key] = str(sample.get("sha256") or "")
                            emit({
                                "type": "sample", "key": key,
                                "predicted_value": value or "", "confidence": confidence,
                                "raw": detail.get("raw", ""), "ocr_pass": ocr_pass,
                                "model_name": model_info.get("model_name") or "",
                                "model_custom": bool(model_info.get("custom")),
                                "model_dir": model_info.get("model_dir") or "",
                                "image_b64": sample.get("image_b64") or "",
                                "image_sha256": sample.get("sha256") or "",
                                "width": sample.get("width") or 0,
                                "height": sample.get("height") or 0,
                                "content_type": sample.get("content_type") or "image/jpeg",
                                "ts": now,
                            })
                except Exception as exc:
                    emit({"type": "error", "key": key, "message": str(exc)[:300]})

            elapsed = time.monotonic() - started
            time.sleep(max(0.02, poll_s - elapsed))
    finally:
        if camera is not None:
            camera.close()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        if sys.argv[1] == "--diagnose-camera":
            import platform
            import numpy
            import cv2
            emit({"type": "camera_runtime_ok", "architecture": platform.machine(),
                  "numpy": numpy.__version__, "opencv": cv2.__version__})
        elif sys.argv[1] == "--diagnose-ocr":
            import ocr_engine
            import paddle
            import paddleocr
            if ocr_engine._get_spocr() is None:
                raise RuntimeError(ocr_engine._spocr_error)
            if ocr_engine._get_spscore() is None:
                raise RuntimeError(ocr_engine._spscore_error)
            emit({"type": "ocr_runtime_ok", "clock": ocr_engine.SPOCR_MODEL_NAME,
                  "scores": ocr_engine.SPSCORE_MODEL_NAME, "paddle": paddle.__version__})
        elif sys.argv[1] == "--camera":
            from video_source import camera_worker
            camera_worker(int(sys.argv[2]), sys.argv[3])
        else:
            main(sys.argv[1])
    except Exception as exc:
        emit({"type": "fatal", "message": str(exc), "trace": traceback.format_exc()[-1000:]})
        raise
