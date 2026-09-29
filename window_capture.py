"""Captura híbrida de ventanas para Scoreboard (Windows y macOS).

Windows
-------
Usa Win32 PrintWindow(PW_RENDERFULLCONTENT) para capturar una ventana aunque
esté detrás de otras. Si falla, no sustituye la ventana por el escritorio.

macOS
-----
Usa ScreenCaptureKit desde macOS 14 y Quartz en versiones anteriores.
La selección siempre identifica una ventana; nunca un rectángulo del escritorio.
En macOS se requiere permiso de Grabación de pantalla.
"""
from __future__ import annotations

import platform
from dataclasses import dataclass

import numpy as np
from secretariat_core.macos_window_capture import WindowCaptureError

SYSTEM = platform.system()

if SYSTEM == "Windows":
    import ctypes
    from ctypes import wintypes
    import win32gui
    import win32ui
    _print_window = ctypes.windll.user32.PrintWindow
    _print_window.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    _print_window.restype = wintypes.BOOL
elif SYSTEM == "Darwin":
    import Quartz


@dataclass
class WindowInfo:
    window_id: int
    title: str
    app_name: str
    rect: tuple[int, int, int, int]

    @property
    def label(self) -> str:
        title = (self.title or "").strip()
        app = (self.app_name or "").strip()
        if app and title and app != title:
            return f"{app} — {title}"
        return title or app or f"Window {self.window_id}"


def list_windows() -> list[WindowInfo]:
    windows: list[WindowInfo] = []

    if SYSTEM == "Windows":
        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").strip()
            if not title:
                return True
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width, height = right - left, bottom - top
            if width >= 100 and height >= 80:
                windows.append(WindowInfo(hwnd, title, title, (left, top, width, height)))
            return True

        win32gui.EnumWindows(callback, None)

    elif SYSTEM == "Darwin":
        options = (
            Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements
        )
        items = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
        for item in items or []:
            title = (item.get("kCGWindowName") or "").strip()
            owner = (item.get("kCGWindowOwnerName") or "").strip()
            bounds = item.get("kCGWindowBounds") or {}
            rect = (
                int(bounds.get("X", 0)),
                int(bounds.get("Y", 0)),
                int(bounds.get("Width", 0)),
                int(bounds.get("Height", 0)),
            )
            window_id = item.get("kCGWindowNumber")
            if window_id is not None and (title or owner) and rect[2] >= 100 and rect[3] >= 80:
                windows.append(WindowInfo(int(window_id), title or owner, owner, rect))
    else:
        raise NotImplementedError(f"Window listing not implemented for {SYSTEM}")

    # Titles are not identities: keep separate windows with identical titles.
    dedup = {window.window_id: window for window in windows}
    return list(dedup.values())


def get_window_rect(window_id: int):
    if SYSTEM == "Windows":
        if not win32gui.IsWindow(window_id):
            return None
        left, top, right, bottom = win32gui.GetWindowRect(window_id)
        return left, top, right - left, bottom - top

    if SYSTEM == "Darwin":
        options = Quartz.kCGWindowListOptionIncludingWindow
        items = Quartz.CGWindowListCopyWindowInfo(options, window_id)
        for item in items or []:
            if int(item.get("kCGWindowNumber", -1)) == int(window_id):
                if not item.get("kCGWindowIsOnscreen", True):
                    return None
                bounds = item.get("kCGWindowBounds") or {}
                return (
                    int(bounds.get("X", 0)),
                    int(bounds.get("Y", 0)),
                    int(bounds.get("Width", 0)),
                    int(bounds.get("Height", 0)),
                )
    return None


def find_window(windows, source_id="", label=""):
    """Resolve an explicit identity, or an unambiguous legacy label."""
    identity = str(source_id or "").strip()
    if identity:
        return next((window for window in windows if str(window.window_id) == identity), None)
    label = str(label or "").strip()
    if not label:
        return None
    matches = [window for window in windows if window.label == label]
    if not matches:
        matches = [window for window in windows if label.lower() in window.label.lower()]
    return matches[0] if len(matches) == 1 else None


def _capture_windows_printwindow(hwnd: int):
    if not hwnd or not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd):
        return None

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    if not hwnd_dc:
        return None

    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        # PW_RENDERFULLCONTENT = 2. Funciona mejor con ventanas modernas.
        result = _print_window(hwnd, save_dc.GetSafeHdc(), 2)
        if not result:
            result = _print_window(hwnd, save_dc.GetSafeHdc(), 0)
        if not result:
            return None

        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        frame = np.frombuffer(bits, dtype=np.uint8)
        frame = frame.reshape((info["bmHeight"], info["bmWidth"], 4))[:, :, :3].copy()

        # PrintWindow devuelve BGRX. Recortamos al área cliente para que las ROI
        # no incluyan bordes ni barra de título.
        client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
        client_rect = win32gui.GetClientRect(hwnd)
        client_width = client_rect[2] - client_rect[0]
        client_height = client_rect[3] - client_rect[1]
        x0 = max(0, client_left - left)
        y0 = max(0, client_top - top)
        if client_width > 0 and client_height > 0:
            cropped = frame[y0:y0 + client_height, x0:x0 + client_width]
            if cropped.size:
                frame = cropped
        return frame
    except Exception:
        return None
    finally:
        try:
            win32gui.DeleteObject(bitmap.GetHandle())
        except Exception:
            pass
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def _capture_macos_quartz(window_id: int):
    """Captura una ventana concreta con Quartz y devuelve BGR."""
    try:
        image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            int(window_id),
            Quartz.kCGWindowImageBoundsIgnoreFraming,
        )
        if image is None:
            return None

        return _cgimage_to_bgr(image)
    except Exception:
        return None


def _cgimage_to_bgr(image):
    """Normalize color layout rather than assuming every CGImage is BGRA."""
    width, height = int(Quartz.CGImageGetWidth(image)), int(Quartz.CGImageGetHeight(image))
    if width <= 0 or height <= 0:
        return None
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    context = Quartz.CGBitmapContextCreate(pixels, width, height, 8, width * 4,
        Quartz.CGColorSpaceCreateDeviceRGB(),
        Quartz.kCGImageAlphaPremultipliedFirst | Quartz.kCGBitmapByteOrder32Little)
    if context is None:
        raise WindowCaptureError("No se pudo convertir la imagen de la ventana.")
    Quartz.CGContextDrawImage(context, Quartz.CGRectMake(0, 0, width, height), image)
    return pixels[:, :, :3].copy()


def capture_window(window_id: int):
    """Devuelve (frame_bgr, rect) o (None, None)."""
    try:
        window_id = int(window_id)
    except (TypeError, ValueError):
        return None, None
    if window_id <= 0:
        return None, None
    if SYSTEM == "Windows":
        frame = _capture_windows_printwindow(window_id)
        if frame is None:
            return None, None
        return frame, get_window_rect(window_id)

    if SYSTEM == "Darwin":
        rect = get_window_rect(window_id)
        if rect is None:
            raise WindowCaptureError("La ventana seleccionada ya no está disponible. Selecciónala de nuevo.")
        if int(platform.mac_ver()[0].split('.')[0]) >= 14:
            from secretariat_core.macos_window_capture import capture
            frame = _cgimage_to_bgr(capture.capture_image(window_id, bounds=rect))
        else:
            frame = _capture_macos_quartz(window_id)
        if frame is None:
            raise WindowCaptureError("No se pudo capturar la ventana. Comprueba el permiso de Grabación de pantalla de SecretariatPro.")
        return frame, rect
    raise NotImplementedError(f"Window capture not implemented for {SYSTEM}")
