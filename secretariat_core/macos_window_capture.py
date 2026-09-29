"""Capture one native window; never substitute pixels from a display."""
from __future__ import annotations

import threading
import time


class WindowCaptureError(RuntimeError):
    pass


class MacWindowCapture:
    def __init__(self, timeout=5.0):
        self.timeout = timeout
        self._lock = threading.Lock()
        self._windows = {}
        self._bounds = {}
        self._expires = 0.0
        self._pending = None

    def _wait(self, start):
        # A timed-out native request may still be running. Do not accumulate
        # more capture requests until its completion handler has returned.
        if self._pending is not None and not self._pending.is_set():
            raise WindowCaptureError("La captura de ventana sigue esperando a macOS. Comprueba el permiso de Grabación de pantalla.")
        done = threading.Event()
        result = []
        self._pending = done

        def completed(value, error):
            result.extend((value, error))
            done.set()

        try:
            start(completed)
        except Exception:
            done.set()
            raise
        if not done.wait(self.timeout):
            raise WindowCaptureError("macOS no respondió a la captura de ventana. Comprueba el permiso de Grabación de pantalla.")
        value, error = result
        if error is not None or value is None:
            detail = str(error.localizedDescription()) if error is not None else "sin imagen"
            if any(word in detail.lower() for word in ("tcc", "denied", "declined", "permission")):
                raise WindowCaptureError("macOS ha denegado la captura de ventanas a esta copia de Live. "
                    "Si el permiso de Grabación de pantalla aparece activado, cierra Live y vuelve a añadir "
                    "la copia de Aplicaciones en esa lista; el permiso puede pertenecer a una compilación anterior. "
                    f"Detalle: {detail}")
            raise WindowCaptureError(f"No se pudo capturar la ventana: {detail}. Comprueba el permiso de Grabación de pantalla de SecretariatPro.")
        return value

    def capture_image(self, window_id, *, bounds=None):
        try:
            import objc
            import ScreenCaptureKit as capture
        except ImportError as exc:
            raise WindowCaptureError("Falta ScreenCaptureKit en esta instalación de SecretariatPro. Reinstala la versión corregida.") from exc

        with self._lock, objc.autorelease_pool():
            try:
                if (time.monotonic() >= self._expires or window_id not in self._windows
                        or (bounds is not None and self._bounds.get(window_id) != bounds)):
                    content = self._wait(lambda callback: capture.SCShareableContent.
                        getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(True, False, callback))
                    self._windows = {int(window.windowID()): window for window in content.windows()}
                    self._expires = time.monotonic() + 1.0
                    self._bounds.clear()
                    self._bounds[window_id] = bounds
                window = self._windows.get(window_id)
                if window is None:
                    raise WindowCaptureError("La ventana seleccionada ya no está disponible. Selecciónala de nuevo.")
                # desktopIndependentWindow excludes every other window even
                # when the selected one moves or another application covers it.
                content_filter = capture.SCContentFilter.alloc().initWithDesktopIndependentWindow_(window)
                bounds = content_filter.contentRect()
                scale = float(content_filter.pointPixelScale())
                width = int(round(bounds.size.width * scale))
                height = int(round(bounds.size.height * scale))
                if width <= 0 or height <= 0:
                    raise WindowCaptureError("La ventana seleccionada no tiene una imagen disponible.")
                configuration = capture.SCStreamConfiguration.alloc().init()
                configuration.setWidth_(width)
                configuration.setHeight_(height)
                configuration.setShowsCursor_(False)
                configuration.setIgnoreShadowsSingleWindow_(True)
                return self._wait(lambda callback: capture.SCScreenshotManager.
                    captureImageWithFilter_configuration_completionHandler_(content_filter, configuration, callback))
            except Exception:
                self._windows.clear()
                self._bounds.clear()
                self._expires = 0.0
                raise


capture = MacWindowCapture()
