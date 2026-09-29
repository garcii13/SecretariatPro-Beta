"""OBS projector selection using the shared, window-only capture backend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from secretariat_core.macos_window_capture import WindowCaptureError

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
    import window_capture
    rows = [ProjectorWindow(row.window_id, row.label, row.rect)
            for row in window_capture.list_windows()]
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

def capture_window(window: ProjectorWindow) -> Optional[np.ndarray]:
    import window_capture

    image, _ = window_capture.capture_window(window.window_id)
    return image if image is not None and image.size else None
