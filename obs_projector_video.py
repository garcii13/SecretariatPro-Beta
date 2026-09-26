"""High-frequency capture of an OBS Program Projector window.

Windows uses PrintWindow so the projector can be captured even when another
window overlaps it. macOS/Linux fall back to visible-window screen capture.
"""
from __future__ import annotations

import platform
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

SYSTEM = platform.system()

try:
    import pygetwindow as gw
except Exception:
    gw = None

try:
    import mss
except Exception:
    mss = None

if SYSTEM == "Windows":
    import ctypes
    from ctypes import wintypes


@dataclass
class ProjectorWindow:
    window_id: int
    title: str
    rect: tuple[int, int, int, int]

    @property
    def label(self) -> str:
        return self.title or f"Window {self.window_id}"


def _looks_like_projector(title: str) -> bool:
    text = (title or "").lower()
    projector_words = ("projector", "proyector")
    output_words = ("program", "programa", "emisión", "emision", "preview", "previsualización", "previsualizacion")
    return any(w in text for w in projector_words) and any(w in text for w in output_words)


def _looks_like_program_projector(title: str) -> bool:
    text = (title or "").lower()
    return _looks_like_projector(title) and any(w in text for w in ("program", "programa", "emisión", "emision"))


def _looks_like_preview_projector(title: str) -> bool:
    text = (title or "").lower()
    return _looks_like_projector(title) and any(w in text for w in ("preview", "previsualización", "previsualizacion"))


def _looks_like_fullscreen_projector(title: str) -> bool:
    text = (title or "").lower()
    fullscreen_words = ("fullscreen", "full screen", "pantalla completa")
    return _looks_like_projector(title) and any(word in text for word in fullscreen_words)


def _projector_priority(title: str) -> tuple[int, str]:
    if _looks_like_fullscreen_projector(title) and _looks_like_program_projector(title):
        return (0, title.lower())
    if _looks_like_fullscreen_projector(title) and _looks_like_preview_projector(title):
        return (1, title.lower())
    if _looks_like_program_projector(title):
        return (2, title.lower())
    if _looks_like_preview_projector(title):
        return (3, title.lower())
    return (4, title.lower())

def list_windows(projectors_first: bool = True) -> list[ProjectorWindow]:
    rows: list[ProjectorWindow] = []
    if SYSTEM == "Windows" and gw is not None:
        for w in gw.getAllWindows():
            title = (w.title or "").strip()
            if not title or w.width < 120 or w.height < 90:
                continue
            if getattr(w, "isMinimized", False):
                continue
            rows.append(ProjectorWindow(int(w._hWnd), title, (int(w.left), int(w.top), int(w.width), int(w.height))))
    elif SYSTEM == "Darwin":
        try:
            import Quartz
            opts = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            for item in Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID):
                title = ((item.get("kCGWindowOwnerName") or "") + " — " + (item.get("kCGWindowName") or "")).strip(" —")
                b = item.get("kCGWindowBounds") or {}
                rect = (int(b.get("X", 0)), int(b.get("Y", 0)), int(b.get("Width", 0)), int(b.get("Height", 0)))
                if title and rect[2] >= 120 and rect[3] >= 90:
                    rows.append(ProjectorWindow(int(item.get("kCGWindowNumber")), title, rect))
        except Exception:
            pass
    if projectors_first:
        rows.sort(key=lambda r: _projector_priority(r.title))
    return rows


def best_projector_window(windows: list[ProjectorWindow]) -> Optional[ProjectorWindow]:
    # Fullscreen Program has no title bar in the captured pixels and normally
    # exposes the highest available resolution. Fall back to a windowed Program
    # projector when no fullscreen output is open.
    ordered = sorted((w for w in windows if _looks_like_projector(w.title)), key=lambda w: _projector_priority(w.title))
    return ordered[0] if ordered else None




def select_projector_window(windows: list[ProjectorWindow], wanted: str = "") -> Optional[ProjectorWindow]:
    configured = (wanted or "").strip()
    configured_lower = configured.lower()

    # Phase 68 stores the native window id instead of the visible title. Titles
    # are not unique and may change with the active OBS scene; the OS id is the
    # only reliable way to keep capturing exactly what the operator selected.
    if configured_lower.startswith("window:"):
        try:
            wanted_id = int(configured.split(":", 1)[1])
        except (TypeError, ValueError):
            return None
        return next((window for window in windows if int(window.window_id) == wanted_id), None)

    # Upgrade legacy windowed settings automatically while respecting whether
    # the operator asked for Program or Preview.
    if "windowed projector" in configured_lower or "proyector en ventana" in configured_lower:
        prefer_preview = "preview" in configured_lower or "previsual" in configured_lower
        fullscreen = next((w for w in windows if (
            _looks_like_fullscreen_projector(w.title)
            and (_looks_like_preview_projector(w.title) if prefer_preview else _looks_like_program_projector(w.title))
        )), None)
        if fullscreen is not None:
            return fullscreen

    exact = next((w for w in windows if w.label == configured or w.title == configured), None)
    return exact or best_projector_window(windows)

def _capture_windows_printwindow(hwnd: int) -> Optional[np.ndarray]:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    if not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return None
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = user32.GetWindowDC(wintypes.HWND(hwnd))
    if not hwnd_dc:
        return None
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    old_obj = gdi32.SelectObject(mem_dc, bitmap)
    try:
        # PW_RENDERFULLCONTENT works best for modern GPU-backed windows.
        ok = user32.PrintWindow(wintypes.HWND(hwnd), mem_dc, 0x00000002)
        if not ok:
            ok = user32.PrintWindow(wintypes.HWND(hwnd), mem_dc, 0)
        if not ok:
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        buf = ctypes.create_string_buffer(width * height * 4)
        lines = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)
        if lines != height:
            return None
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
        return arr[:, :, :3].copy()  # BGR
    finally:
        gdi32.SelectObject(mem_dc, old_obj)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(wintypes.HWND(hwnd), hwnd_dc)


def _current_rect(window_id: int) -> Optional[tuple[int, int, int, int]]:
    if SYSTEM == "Windows" and gw is not None:
        for w in gw.getAllWindows():
            if int(w._hWnd) == int(window_id):
                return int(w.left), int(w.top), int(w.width), int(w.height)
    return None


_thread_local = threading.local()


def _screen_capture(rect: tuple[int, int, int, int]) -> Optional[np.ndarray]:
    if mss is None:
        return None
    if not hasattr(_thread_local, "sct"):
        _thread_local.sct = mss.mss()
    left, top, width, height = rect
    if width <= 0 or height <= 0:
        return None
    shot = _thread_local.sct.grab({"left": left, "top": top, "width": width, "height": height})
    return np.asarray(shot)[:, :, :3].copy()


def capture_window(window: ProjectorWindow) -> Optional[np.ndarray]:
    if SYSTEM == "Windows":
        image = _capture_windows_printwindow(window.window_id)
        if image is not None and image.size:
            # Some GPU windows return a fully black PrintWindow frame. Fall back
            # to visible screen capture in that case.
            if float(image.mean()) > 1.0:
                return image
        rect = _current_rect(window.window_id) or window.rect
        return _screen_capture(rect)
    if SYSTEM == "Darwin":
        # A rectangle grab records whichever application happens to cover the
        # projector (often SecretariatPro itself). Quartz can capture the exact
        # OBS window by id even when it is behind another window.
        try:
            import window_capture

            image, _ = window_capture.capture_window(window.window_id)
            if image is not None and getattr(image, "size", 0):
                return image
        except Exception:
            pass
    return _screen_capture(window.rect)
