from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from secretariat_core.ocr_store import OCRConfigStore, ScoreFileStore
from secretariat_core.settings_store import SettingsStore

PREFIX = "OCRMSG "


class OCRRuntimeManager:
    """Owns the isolated OCR worker process used by the web application.

    The worker always reads the clock. Score readings are persisted only while
    score control mode is ``ocr``. In ``manual`` mode the raw OCR readings are
    still exposed for supervision, but they cannot overwrite the operator's
    manual result.
    """

    def __init__(
        self,
        *,
        base_dir: str | Path,
        config_store: OCRConfigStore,
        score_store: ScoreFileStore,
        settings_store: SettingsStore,
        on_time_reading=None,
        sample_sharing_enabled=None,
        on_sample=None,
        camera_service=None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.config_store = config_store
        self.score_store = score_store
        self.settings_store = settings_store
        self.on_time_reading = on_time_reading
        self.sample_sharing_enabled = sample_sharing_enabled
        self.on_sample = on_sample
        self.camera_service = camera_service
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._desired_running = False
        self._native_crash_times: list[float] = []
        self._status: dict[str, Any] = {
            "running": False,
            "pid": None,
            "phase": "idle",
            "last_heartbeat": None,
            "last_reading": None,
            "readings": {"team1_score": "", "team2_score": "", "time": ""},
            "confidence": {"team1_score": 0.0, "team2_score": 0.0, "time": 0.0},
            "raw": {"team1_score": "", "team2_score": "", "time": ""},
            "ocr_pass": {"team1_score": "", "team2_score": "", "time": ""},
            "error": "",
            "window_title": "",
            "source_type": "window",
            "source_id": "",
            "source_label": "",
        }

    def score_mode(self) -> str:
        settings = self.settings_store.load()
        mode = str(settings.get("score_control", {}).get("mode") or "ocr").lower()
        return mode if mode in {"ocr", "manual"} else "ocr"

    def status(self) -> dict[str, Any]:
        with self._lock:
            payload = dict(self._status)
            payload["readings"] = dict(self._status.get("readings") or {})
            payload["confidence"] = dict(self._status.get("confidence") or {})
            payload["raw"] = dict(self._status.get("raw") or {})
            payload["ocr_pass"] = dict(self._status.get("ocr_pass") or {})
            payload["score_mode"] = self.score_mode()
            if self.camera_service is not None:
                payload["camera_stream"] = self.camera_service.status()
            process = self._process
            if process is not None and process.poll() is not None and payload.get("running"):
                payload["running"] = False
                payload["phase"] = "stopped"
            return payload

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._desired_running = True
            if self._process is not None and self._process.poll() is None:
                return self.status()

            config = self.config_store.load()
            source_type = str(config.get("source_type") or "window").strip().lower()
            if source_type not in {"window", "camera"}:
                source_type = "window"
            source_id = str(config.get("source_id") or "").strip()
            source_label = str(config.get("source_label") or config.get("window_title") or "").strip()
            active_regions = {
                key: value
                for key, value in (config.get("regions") or {}).items()
                if key in {"team1_score", "team2_score", "time"} and value
            }
            if not active_regions:
                raise RuntimeError("Configura al menos una región OCR")

            window = None
            if source_type == "window":
                import window_capture
                window = window_capture.find_window(window_capture.list_windows(), source_id, source_label)
                if window is None:
                    raise RuntimeError("La ventana OCR configurada ya no está disponible")
                source_id = str(window.window_id)
                source_label = window.label
            else:
                if not source_id:
                    raise RuntimeError("Selecciona una cámara OCR antes de iniciar la lectura")
                try:
                    camera_index = int(source_id)
                except ValueError as exc:
                    raise RuntimeError("El identificador de cámara OCR no es válido") from exc
                if not source_label:
                    source_label = f"Cámara {camera_index + 1}"
                if self.camera_service is None:
                    raise RuntimeError("El servicio persistente de cámara OCR no está disponible")
                self.camera_service.activate(camera_index)

            runtime_dir = self.base_dir / ".runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            worker_config = runtime_dir / "ocr_worker_config.json"
            worker_config.write_text(
                json.dumps(
                    {
                        "source_type": source_type,
                        "source_id": source_id,
                        "source_label": source_label,
                        "camera_frame_path": str(self.camera_service.frame_path) if source_type == "camera" and self.camera_service is not None else "",
                        "window_id": window.window_id if window is not None else "",
                        "window_title": window.label if window is not None else "",
                        "poll_ms": int(config.get("poll_ms") or 700),
                        "regions": active_regions,
                        "perspective": config.get("perspective") or {},
                        "model": config.get("model") or {},
                        "sample_sharing": bool(self.sample_sharing_enabled()) if callable(self.sample_sharing_enabled) else False,
                        "sample_threshold": 0.72,
                        "sample_thresholds": {"time": 0.90},
                        "sample_interval_s": 30.0,
                        "led_phase_recovery": True,
                        "led_phase_frames": 3,
                        "led_phase_gap_ms": 22,
                        "reading_confirmations": 2,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            if getattr(sys, "frozen", False):
                worker = Path(sys.executable).parent / ("SecretariatPro_OCR.exe" if sys.platform == "win32" else "SecretariatPro_OCR")
                command = [str(worker), str(worker_config)]
            else:
                resource_dir = Path(__file__).resolve().parents[2]
                command = [sys.executable, str(resource_dir / "ocr_worker.py"), str(worker_config)]
            process = subprocess.Popen(
                command,
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._process = process
            self._status.update(
                {
                    "running": True,
                    "pid": process.pid,
                    "phase": "starting",
                    "last_heartbeat": time.time(),
                    "last_reading": None,
                    "error": "",
                    "window_title": window.label if window is not None else "",
                    "source_type": source_type,
                    "source_id": source_id,
                    "source_label": source_label,
                }
            )
            thread = threading.Thread(target=self._reader_loop, args=(process,), daemon=True)
            self._reader_thread = thread
            thread.start()
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._desired_running = False
            process = self._process
            self._process = None
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
            self._status.update(
                {
                    "running": False,
                    "pid": None,
                    "phase": "stopped",
                    "last_heartbeat": time.time(),
                }
            )
            return self.status()

    def _reader_loop(self, process: subprocess.Popen[str]) -> None:
        output = process.stdout
        if output is None:
            return
        log_path = self.base_dir / ".runtime" / "ocr-worker.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_path.exists() and log_path.stat().st_size > 2_000_000:
            log_path.replace(log_path.with_suffix(".previous.log"))
        for line in output:
            line = line.strip()
            if not line:
                continue
            if not line.startswith(PREFIX):
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(line + "\n")
                with self._lock:
                    self._status["error"] = line[-400:]
                continue
            try:
                payload = json.loads(line[len(PREFIX):])
            except json.JSONDecodeError:
                continue
            try:
                self.handle_payload(payload)
            except Exception as exc:
                with self._lock:
                    self._status["error"] = f"No se pudo procesar la lectura OCR: {exc}"

        exit_code = process.wait()
        restart_native = False
        with self._lock:
            if self._process is process:
                self._process = None
            self._status.update(
                {
                    "running": False,
                    "pid": None,
                    "phase": "stopped",
                }
            )

            # POSIX reports a process killed by SIGSEGV as -11. Paddle runs in
            # this isolated worker specifically so a native inference crash can
            # never take down Live. One controlled restart is attempted, but a
            # crash loop is deliberately blocked.
            if exit_code == -11 and self._desired_running:
                now = time.time()
                self._native_crash_times = [t for t in self._native_crash_times if now - t < 60.0]
                if len(self._native_crash_times) < 2:
                    self._native_crash_times.append(now)
                    self._status["error"] = "El motor nativo Paddle OCR se cerró inesperadamente (SIGSEGV). Reiniciando OCR…"
                    self._status["phase"] = "recovering"
                    restart_native = True
                else:
                    self._desired_running = False
                    self._status["error"] = (
                        "Paddle OCR se ha cerrado dos veces en menos de un minuto. "
                        "OCR detenido para evitar un bucle de reinicio. En macOS ejecuta PREPARAR_MAC_BETA.command."
                    )
                    self._status["phase"] = "error"
            elif exit_code not in (0, None) and not self._status.get("error"):
                self._status["error"] = f"El proceso OCR terminó con código {exit_code}"

        if restart_native:
            threading.Timer(1.0, self._restart_after_native_crash).start()

    def _restart_after_native_crash(self) -> None:
        with self._lock:
            if not self._desired_running or self._process is not None:
                return
        try:
            self.start()
        except Exception as exc:
            with self._lock:
                self._desired_running = False
                self._status["running"] = False
                self._status["phase"] = "error"
                self._status["error"] = f"No se pudo recuperar el OCR tras el fallo nativo: {exc}"

    def _deliver_sample(self, payload: dict[str, Any]) -> None:
        try:
            if callable(self.on_sample):
                self.on_sample(payload)
        except Exception:
            # Telemetry is strictly best-effort. A failed upload must never
            # affect OCR, the score files or the live production.
            return

    def handle_payload(self, payload: dict[str, Any]) -> None:
        """Apply one worker message. Public to support deterministic tests."""
        message_type = str(payload.get("type") or "")
        now = float(payload.get("ts") or time.time())
        with self._lock:
            if message_type == "heartbeat":
                self._status["last_heartbeat"] = now
                self._status["phase"] = str(payload.get("phase") or "running")
                return
            if message_type in {"error", "fatal"}:
                self._status["error"] = str(payload.get("message") or "Error OCR")
                self._status["phase"] = "error"
                if message_type == "fatal":
                    self._status["running"] = False
                return
            if message_type == "sample":
                callback = self.on_sample
                if callable(callback):
                    # Uploading to Supabase must never block the stdout reader:
                    # the OCR worker has to remain real-time even on slow Wi-Fi.
                    threading.Thread(target=self._deliver_sample, args=(dict(payload),), daemon=True).start()
                return
            if message_type != "reading":
                return

            key = str(payload.get("key") or "")
            value = str(payload.get("value") or "").strip()
            if key not in {"team1_score", "team2_score", "time"} or not value:
                return
            self._status.setdefault("readings", {})[key] = value
            try:
                self._status.setdefault("confidence", {})[key] = float(payload.get("confidence") or 0.0)
            except (TypeError, ValueError):
                self._status.setdefault("confidence", {})[key] = 0.0
            self._status.setdefault("raw", {})[key] = str(payload.get("raw") or "")
            self._status.setdefault("ocr_pass", {})[key] = str(payload.get("ocr_pass") or "")
            self._status["last_reading"] = now
            self._status["phase"] = key
            self._status["error"] = ""

        # Keep the match clock under OCR control in both modes. Result readings
        # are allowed to reach the shared score files only in OCR mode.
        if key == "time" or self.score_mode() == "ocr":
            self.score_store.write_external({key: value})
        if key == "time" and callable(self.on_time_reading):
            try:
                self.on_time_reading(value)
            except Exception:
                # OCR must remain alive even if a downstream state update fails.
                pass
