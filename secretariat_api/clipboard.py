from __future__ import annotations

import ctypes
from ctypes import wintypes
import subprocess
import sys


class ClipboardUnavailable(RuntimeError):
    pass


def _copy_windows(text: str) -> None:
    """Write Unicode text using the native Win32 clipboard API."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    encoded = (text + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(0x0002, len(encoded))  # GMEM_MOVEABLE
    if not handle:
        raise OSError("No se pudo reservar memoria para el portapapeles")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        raise OSError("No se pudo bloquear la memoria del portapapeles")
    try:
        ctypes.memmove(pointer, encoded, len(encoded))
    finally:
        kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise OSError("No se pudo abrir el portapapeles")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
            kernel32.GlobalFree(handle)
            raise OSError("No se pudo copiar el texto")
        handle = None  # ownership is transferred to the operating system
    finally:
        user32.CloseClipboard()


def copy_text(text: str) -> None:
    """Copy text through the host OS, independent of WebView permissions."""
    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["/usr/bin/pbcopy"],
                input=text.encode("utf-8"),
                check=True,
                timeout=3,
            )
            return
        if sys.platform == "win32":
            _copy_windows(text)
            return

        # Browser clipboard APIs remain the primary path on Linux. This fallback
        # supports local desktop sessions where Tk has access to the display.
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
        finally:
            root.destroy()
    except Exception as exc:
        raise ClipboardUnavailable("No se pudo acceder al portapapeles") from exc
