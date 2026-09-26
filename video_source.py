from __future__ import annotations

"""Video sources shared by OCR preview and the isolated OCR worker.

Window capture remains the default. Camera sources use OpenCV so USB capture
cards, webcams and Continuity Camera devices exposed by the OS can be selected
without changing the OCR pipeline.

Phase 58: a selected camera is now held open persistently by the main Live
process. Preview and the isolated OCR worker consume the same continuously
updated stream through a tiny memory-mapped frame bridge, so selecting a camera
no longer means open -> capture one preview -> close.
"""

from dataclasses import dataclass
import mmap
import os
from pathlib import Path
import platform
import subprocess
import sys
import struct
import threading
import time
from typing import Any


@dataclass(frozen=True)
class VideoSource:
    source_type: str
    source_id: str
    label: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "label": self.label,
            "detail": self.detail,
            "source_key": f"{self.source_type}:{self.source_id}",
        }


def _camera_backend(cv2: Any) -> int:
    system = platform.system().lower()
    if system == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
        return cv2.CAP_AVFOUNDATION
    if system == "windows" and hasattr(cv2, "CAP_DSHOW"):
        return cv2.CAP_DSHOW
    if system == "linux" and hasattr(cv2, "CAP_V4L2"):
        return cv2.CAP_V4L2
    return getattr(cv2, "CAP_ANY", 0)


def open_camera(index: int):
    import cv2

    camera_index = int(index)
    backend = _camera_backend(cv2)
    cap = cv2.VideoCapture(camera_index, backend) if backend else cv2.VideoCapture(camera_index)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    return cap


def _macos_camera_devices() -> list[VideoSource] | None:
    """Enumerate macOS cameras without opening them.

    OpenCV/AVFoundation emits noisy native errors when asked to open indexes
    outside the real device range. PyObjC lets us query AVFoundation first, so
    the UI can list only devices that macOS actually exposes. Returning None
    means native enumeration is unavailable and the caller should use the
    conservative OpenCV fallback.
    """
    if platform.system().lower() != "darwin":
        return None
    try:
        import AVFoundation  # type: ignore
    except Exception:
        return None

    devices = None
    try:
        devices = AVFoundation.AVCaptureDevice.devicesWithMediaType_(AVFoundation.AVMediaTypeVideo)
    except Exception:
        devices = None

    if devices is None:
        # Fallback for SDKs where devicesWithMediaType_ is no longer exposed.
        try:
            device_types = []
            for name in (
                "AVCaptureDeviceTypeBuiltInWideAngleCamera",
                "AVCaptureDeviceTypeExternalUnknown",
                "AVCaptureDeviceTypeContinuityCamera",
                "AVCaptureDeviceTypeDeskViewCamera",
            ):
                value = getattr(AVFoundation, name, None)
                if value is not None and value not in device_types:
                    device_types.append(value)
            session_cls = getattr(AVFoundation, "AVCaptureDeviceDiscoverySession", None)
            if not device_types or session_cls is None:
                return None
            session = session_cls.discoverySessionWithDeviceTypes_mediaType_position_(
                device_types,
                AVFoundation.AVMediaTypeVideo,
                getattr(AVFoundation, "AVCaptureDevicePositionUnspecified", 0),
            )
            devices = session.devices()
        except Exception:
            return None

    rows: list[VideoSource] = []
    try:
        iterable = list(devices or [])
    except Exception:
        iterable = []
    for index, device in enumerate(iterable):
        try:
            label = str(device.localizedName() or f"Cámara {index + 1}")
        except Exception:
            label = f"Cámara {index + 1}"
        detail_parts = ["AVFoundation"]
        try:
            unique_id = str(device.uniqueID() or "").strip()
            if unique_id:
                # Keep the UI useful without exposing a long hardware identifier.
                detail_parts.append(unique_id[-8:])
        except Exception:
            pass
        rows.append(VideoSource("camera", str(index), label, " · ".join(detail_parts)))
    return rows


def _probe_cameras(
    max_devices: int,
    *,
    active_index: int | None = None,
    active_detail: str = "",
    stop_after_gap: bool = False,
) -> list[VideoSource]:
    """Conservative OpenCV fallback used outside native macOS enumeration."""
    rows: list[VideoSource] = []
    found_any = False
    for index in range(max(1, int(max_devices))):
        if active_index is not None and index == int(active_index):
            rows.append(VideoSource("camera", str(index), f"Cámara {index + 1}", active_detail or "Activa"))
            found_any = True
            continue
        cap = None
        try:
            cap = open_camera(index)
            if not cap or not cap.isOpened():
                if stop_after_gap and (found_any or index == 0):
                    break
                continue
            ok, frame = cap.read()
            if not ok or frame is None or getattr(frame, "size", 0) <= 0:
                if stop_after_gap and found_any:
                    break
                continue
            found_any = True
            width = int(cap.get(3) or frame.shape[1])
            height = int(cap.get(4) or frame.shape[0])
            rows.append(VideoSource("camera", str(index), f"Cámara {index + 1}", f"{width}×{height}"))
        except Exception:
            if stop_after_gap and (found_any or index == 0):
                break
            continue
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    return rows


def list_cameras(
    max_devices: int = 8,
    *,
    active_index: int | None = None,
    active_detail: str = "",
) -> list[VideoSource]:
    """Return cameras exposed by the operating system.

    On macOS we enumerate AVFoundation natively instead of trying indexes 0..7.
    This prevents repeated ``out device of bound`` warnings and avoids briefly
    opening every camera whenever the source list is refreshed.
    """
    native_rows = _macos_camera_devices()
    if native_rows is not None:
        rows = native_rows
        if active_index is not None:
            wanted = int(active_index)
            replaced = False
            updated: list[VideoSource] = []
            for row in rows:
                if int(row.source_id) == wanted:
                    detail = active_detail or row.detail or "Activa"
                    updated.append(VideoSource("camera", row.source_id, row.label, detail))
                    replaced = True
                else:
                    updated.append(row)
            if not replaced:
                updated.append(VideoSource("camera", str(wanted), f"Cámara {wanted + 1}", active_detail or "Activa"))
            rows = updated
        return rows

    # PyObjC AVFoundation should be available in supported macOS installs. If it
    # is not, stop at the first missing index because AVFoundation indexes are
    # contiguous; this limits native warning spam to at most one failed probe.
    return _probe_cameras(
        max_devices,
        active_index=active_index,
        active_detail=active_detail,
        stop_after_gap=platform.system().lower() == "darwin",
    )


def capture_camera(index: int):
    """Legacy one-shot capture retained for compatibility tests/tools."""
    cap = open_camera(int(index))
    try:
        if not cap or not cap.isOpened():
            raise RuntimeError("La cámara seleccionada no está disponible")
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("No se pudo obtener imagen de la cámara")
        return frame
    finally:
        try:
            cap.release()
        except Exception:
            pass


class CameraStream:
    """Low-latency OpenCV capture handle."""

    def __init__(self, index: int) -> None:
        self.index = int(index)
        self.cap = open_camera(self.index)
        if not self.cap or not self.cap.isOpened():
            self.close()
            raise RuntimeError("La cámara OCR configurada ya no está disponible")

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self) -> None:
        cap = getattr(self, "cap", None)
        self.cap = None
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


_FRAME_MAGIC = b"SPCF"
_FRAME_VERSION = 1
_FRAME_HEADER = struct.Struct("<4sIQIIIId")
_FRAME_HEADER_SIZE = 64


class SharedFramePublisher:
    """Publish raw BGR frames to a memory-mapped file for the OCR subprocess."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._map: mmap.mmap | None = None
        self._capacity = 0
        self._seq = 0
        self._shape: tuple[int, int, int] | None = None

    def _open(self, frame_bytes: int, shape: tuple[int, int, int]) -> None:
        self.close(remove=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        total = _FRAME_HEADER_SIZE + int(frame_bytes)
        handle = open(self.path, "w+b")
        handle.truncate(total)
        mm = mmap.mmap(handle.fileno(), total, access=mmap.ACCESS_WRITE)
        self._file = handle
        self._map = mm
        self._capacity = int(frame_bytes)
        self._shape = shape

    def publish(self, frame) -> None:
        import numpy as np

        array = np.ascontiguousarray(frame, dtype=np.uint8)
        if array.ndim == 2:
            array = array[:, :, None]
        height, width, channels = map(int, array.shape[:3])
        frame_bytes = int(array.nbytes)
        shape = (height, width, channels)
        if self._map is None or frame_bytes > self._capacity or self._shape != shape:
            self._open(frame_bytes, shape)
        mm = self._map
        if mm is None:
            return
        self._seq += 1
        if self._seq % 2 == 0:
            self._seq += 1
        odd = self._seq
        header = _FRAME_HEADER.pack(_FRAME_MAGIC, _FRAME_VERSION, odd, width, height, channels, frame_bytes, time.time())
        mm.seek(0)
        mm.write(header)
        if _FRAME_HEADER_SIZE > len(header):
            mm.write(b"\0" * (_FRAME_HEADER_SIZE - len(header)))
        mm.seek(_FRAME_HEADER_SIZE)
        mm.write(array.tobytes(order="C"))
        self._seq += 1
        even = self._seq
        header = _FRAME_HEADER.pack(_FRAME_MAGIC, _FRAME_VERSION, even, width, height, channels, frame_bytes, time.time())
        mm.seek(0)
        mm.write(header)

    def close(self, *, remove: bool = False) -> None:
        mm, handle = self._map, self._file
        self._map = None
        self._file = None
        self._capacity = 0
        self._shape = None
        if mm is not None:
            try:
                mm.close()
            except Exception:
                pass
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
        if remove:
            try:
                self.path.unlink(missing_ok=True)
            except Exception:
                pass


class SharedFrameReader:
    """Read stable snapshots from the persistent camera bridge."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read(self):
        import numpy as np

        try:
            size = self.path.stat().st_size
            if size <= _FRAME_HEADER_SIZE:
                return None
            with open(self.path, "rb") as handle:
                mm = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    for _ in range(3):
                        raw1 = mm[:_FRAME_HEADER.size]
                        magic, version, seq1, width, height, channels, frame_bytes, _ts = _FRAME_HEADER.unpack(raw1)
                        if magic != _FRAME_MAGIC or version != _FRAME_VERSION or seq1 % 2:
                            time.sleep(0.002)
                            continue
                        end = _FRAME_HEADER_SIZE + int(frame_bytes)
                        if end > len(mm) or width <= 0 or height <= 0 or channels <= 0:
                            return None
                        payload = bytes(mm[_FRAME_HEADER_SIZE:end])
                        raw2 = mm[:_FRAME_HEADER.size]
                        _m2, _v2, seq2, *_rest = _FRAME_HEADER.unpack(raw2)
                        if seq1 != seq2 or seq2 % 2:
                            time.sleep(0.002)
                            continue
                        frame = np.frombuffer(payload, dtype=np.uint8)
                        expected = int(width) * int(height) * int(channels)
                        if frame.size != expected:
                            return None
                        shaped = frame.reshape((int(height), int(width), int(channels)))
                        if int(channels) == 1:
                            shaped = shaped[:, :, 0]
                        return shaped.copy()
                    return None
                finally:
                    mm.close()
        except (FileNotFoundError, OSError, ValueError, struct.error):
            return None

    def close(self) -> None:
        return None


class IsolatedCameraStream:
    """AVFoundation/OpenCV failures stay in a child process, never the UI."""
    def __init__(self, index: int, frame_path: Path):
        self.path = frame_path.with_name("camera_capture.bin")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        if getattr(sys, "frozen", False):
            worker = Path(sys.executable).parent / ("SecretariatPro_OCR.exe" if sys.platform == "win32" else "SecretariatPro_OCR")
            command = [str(worker), "--camera", str(index), str(self.path)]
        else:
            command = [sys.executable, str(Path(__file__).with_name("ocr_worker.py")), "--camera", str(index), str(self.path)]
        with self.path.with_suffix(".log").open("w", encoding="utf-8") as log:
            self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        self.reader = SharedFrameReader(self.path)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline and self.process.poll() is None:
            if self.reader.read() is not None:
                return
            time.sleep(.05)
        code = self.process.poll()
        self.close()
        raise RuntimeError(f"La cámara no se pudo iniciar (salida {code}). Revisa permisos y conexión; diagnóstico: {self.path.with_suffix('.log')}")

    def read(self):
        if self.process.poll() is not None:
            return None
        return self.reader.read()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.reader.close()
        self.path.unlink(missing_ok=True)


def camera_worker(index: int, frame_path: str):
    stream = CameraStream(index)
    publisher = SharedFramePublisher(Path(frame_path))
    try:
        while True:
            frame = stream.read()
            if frame is not None:
                publisher.publish(PersistentCameraService._bridge_frame(frame))
            time.sleep(.01)
    finally:
        stream.close()
        publisher.close(remove=True)


class PersistentCameraService:
    """Own one selected camera for the lifetime of that OCR source selection.

    The camera stays open even when OCR itself is stopped. A background thread
    continuously refreshes both an in-memory preview frame and the mmap bridge
    consumed by the isolated OCR worker.
    """

    def __init__(self, frame_path: str | Path) -> None:
        self.frame_path = Path(frame_path)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream: CameraStream | None = None
        self._publisher = SharedFramePublisher(self.frame_path)
        self._index: int | None = None
        self._frame = None
        self._width = 0
        self._height = 0
        self._last_frame_at = 0.0
        self._error = ""

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = self._stream is not None and self._thread is not None and self._thread.is_alive()
            detail = (f"{self._width}×{self._height}" if self._width and self._height else "Activa") if active else ""
            return {
                "active": bool(active),
                "index": self._index,
                "detail": detail,
                "width": self._width,
                "height": self._height,
                "last_frame_at": self._last_frame_at,
                "error": self._error,
                "frame_path": str(self.frame_path),
            }

    @staticmethod
    def _bridge_frame(frame):
        """Cap the cross-process frame size without changing normalized ROIs."""
        try:
            import cv2
            height, width = frame.shape[:2]
            if int(width) > 1920:
                scale = 1920.0 / float(width)
                return cv2.resize(frame, (1920, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
        except Exception:
            pass
        return frame

    def activate(self, index: int) -> dict[str, Any]:
        wanted = int(index)
        with self._lock:
            if self._index == wanted and self._stream is not None and self._thread is not None and self._thread.is_alive():
                return self.status()
        self.deactivate()
        stream = IsolatedCameraStream(wanted, self.frame_path)
        first = stream.read()
        if first is None:
            stream.close()
            raise RuntimeError("La cámara seleccionada está abierta pero no entrega imagen")
        with self._lock:
            self._index = wanted
            self._stream = stream
            self._frame = first.copy()
            self._height, self._width = map(int, first.shape[:2])
            self._last_frame_at = time.time()
            self._error = ""
            self._publisher.publish(self._bridge_frame(first))
            self._stop = threading.Event()
            thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"SecretariatPro-Camera-{wanted}")
            self._thread = thread
            thread.start()
        return self.status()

    def _capture_loop(self) -> None:
        failures = 0
        last_published = 0.0
        while not self._stop.is_set():
            with self._lock:
                stream = self._stream
            if stream is None:
                break
            frame = stream.read()
            if frame is None:
                process = getattr(stream, "process", None)
                if process is not None and process.poll() is not None:
                    with self._lock:
                        self._frame = None
                        self._publisher.close(remove=True)
                        self._error = "El proceso de cámara se ha cerrado. Reactiva la cámara; Live sigue disponible."
                    break
                failures += 1
                with self._lock:
                    self._error = "La cámara no está entregando imagen"
                time.sleep(min(0.25, 0.02 * failures))
                continue
            failures = 0
            now = time.time()
            should_publish = now - last_published >= 0.10
            bridge_frame = self._bridge_frame(frame) if should_publish else None
            with self._lock:
                self._frame = frame.copy()
                self._height, self._width = map(int, frame.shape[:2])
                self._last_frame_at = now
                self._error = ""
                if bridge_frame is not None:
                    self._publisher.publish(bridge_frame)
                    last_published = now
            # Keep draining the device so its internal buffer never accumulates.
            time.sleep(0.005)

    def read(self, index: int | None = None, *, timeout: float = 1.0):
        if index is not None:
            status = self.status()
            if not status.get("active") or status.get("index") != int(index):
                self.activate(int(index))
        deadline = time.monotonic() + max(0.0, float(timeout))
        while True:
            with self._lock:
                if self._frame is not None:
                    return self._frame.copy()
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)

    def deactivate(self) -> None:
        with self._lock:
            stop = self._stop
            thread = self._thread
            stream = self._stream
            self._thread = None
            self._stream = None
            self._index = None
            self._frame = None
            self._width = 0
            self._height = 0
            self._last_frame_at = 0.0
            self._error = ""
            stop.set()
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        if stream is not None:
            stream.close()
        self._publisher.close(remove=True)

    def close(self) -> None:
        self.deactivate()
