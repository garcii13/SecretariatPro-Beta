"""Captura híbrida de ventanas para Scoreboard (Windows y macOS).

Windows
-------
Usa Win32 PrintWindow(PW_RENDERFULLCONTENT) para capturar una ventana aunque
esté detrás de otras. Si PrintWindow falla, intenta BitBlt.

macOS
-----
Primero intenta capturar directamente la ventana mediante Quartz
CGWindowListCreateImage. Si el sistema o la aplicación no lo permiten, usa
como respaldo Quartz para localizar la ventana y mss para capturar su rectángulo.
En macOS se requiere permiso de Grabación de pantalla.
"""
from __future__ import annotations

import platform
from dataclasses import dataclass

import numpy as np

SYSTEM = platform.system()

if SYSTEM == "Windows":
    import ctypes
    import win32con
    import win32gui
    import win32ui
elif SYSTEM == "Darwin":
    import mss
    import Quartz
else:
    import mss


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
        for item in items:
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

    # Evita entradas repetidas conservando la ventana más grande.
    dedup: dict[tuple[str, str], WindowInfo] = {}
    for window in windows:
        key = (window.app_name, window.title)
        if key not in dedup or window.rect[2] * window.rect[3] > dedup[key].rect[2] * dedup[key].rect[3]:
            dedup[key] = window
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
        for item in items:
            if int(item.get("kCGWindowNumber", -1)) == int(window_id):
                bounds = item.get("kCGWindowBounds") or {}
                return (
                    int(bounds.get("X", 0)),
                    int(bounds.get("Y", 0)),
                    int(bounds.get("Width", 0)),
                    int(bounds.get("Height", 0)),
                )
    return None


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
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
        if not result:
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

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

        width = int(Quartz.CGImageGetWidth(image))
        height = int(Quartz.CGImageGetHeight(image))
        bytes_per_row = int(Quartz.CGImageGetBytesPerRow(image))
        if width <= 0 or height <= 0:
            return None

        provider = Quartz.CGImageGetDataProvider(image)
        data = Quartz.CGDataProviderCopyData(provider)
        raw = np.frombuffer(data, dtype=np.uint8)
        expected = height * bytes_per_row
        if raw.size < expected:
            return None
        raw = raw[:expected].reshape((height, bytes_per_row))
        pixels = raw[:, : width * 4].reshape((height, width, 4))

        # Quartz suele entregar BGRA premultiplicado en macOS. Se descarta alfa.
        return pixels[:, :, :3].copy()
    except Exception:
        return None


_sct = None


def _screen():
    global _sct
    if _sct is None:
        _sct = mss.mss()
    return _sct


def capture_rect(rect):
    left, top, width, height = rect
    if width <= 0 or height <= 0:
        return None
    shot = _screen().grab({
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height),
    })
    return np.array(shot)[:, :, :3].copy()


def capture_window(window_id: int):
    """Devuelve (frame_bgr, rect) o (None, None)."""
    if SYSTEM == "Windows":
        frame = _capture_windows_printwindow(window_id)
        if frame is None:
            return None, None
        return frame, get_window_rect(window_id)

    if SYSTEM == "Darwin":
        rect = get_window_rect(window_id)
        frame = _capture_macos_quartz(window_id)
        if frame is not None:
            return frame, rect
        # Respaldo para versiones/ventanas que no permitan CGWindowListCreateImage.
        if rect is None:
            return None, None
        return capture_rect(rect), rect

    rect = get_window_rect(window_id)
    if rect is None:
        return None, None
    return capture_rect(rect), rect
