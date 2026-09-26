"""Match-bound graphic cues. Preparing a cue never changes the on-air overlay."""
from __future__ import annotations

import copy
import uuid
from typing import Any

from .overlay import ALL_PANELS, hide_all, set_panel


QUEUE_PANELS = ALL_PANELS - {"player_profile"}
MAX_CUES = 16


def add_cue(
    state: dict[str, Any], panel: str, match_id: str, lineup_team: str = "team1",
    label: str = "", duration_seconds: int = 0,
) -> dict[str, Any]:
    if panel not in QUEUE_PANELS:
        raise ValueError("Este gráfico no se puede preparar en la cola")
    if not match_id:
        raise ValueError("Carga un partido antes de preparar gráficos")
    if lineup_team not in {"team1", "team2"}:
        raise ValueError("Equipo de alineación no válido")
    queue = state.setdefault("graphics_queue", [])
    if len(queue) >= MAX_CUES:
        raise ValueError("La cola está llena")
    duration = max(0, min(120, int(duration_seconds or 0)))
    cue = {
        "id": uuid.uuid4().hex,
        "panel": panel,
        "lineup_team": lineup_team,
        "match_id": match_id,
        "label": str(label or "").strip()[:80],
        "duration_seconds": duration,
    }
    queue.append(cue)
    return cue


def remove_cue(state: dict[str, Any], cue_id: str) -> bool:
    queue = state.setdefault("graphics_queue", [])
    before = len(queue)
    state["graphics_queue"] = [cue for cue in queue if cue.get("id") != cue_id]
    return len(state["graphics_queue"]) != before


def move_cue(state: dict[str, Any], cue_id: str, position: int) -> dict[str, Any]:
    queue = state.setdefault("graphics_queue", [])
    current = next((index for index, cue in enumerate(queue) if cue.get("id") == cue_id), None)
    if current is None:
        raise ValueError("Gráfico preparado no disponible")
    cue = queue.pop(current)
    target = max(0, min(len(queue), int(position)))
    queue.insert(target, cue)
    return cue


def clear_cues(state: dict[str, Any]) -> int:
    queue = state.setdefault("graphics_queue", [])
    count = len(queue)
    state["graphics_queue"] = []
    return count


def take_cue(state: dict[str, Any], cue_id: str, match_id: str) -> dict[str, Any]:
    queue = state.setdefault("graphics_queue", [])
    if not queue or queue[0].get("id") != cue_id:
        raise ValueError("Solo se puede lanzar el siguiente gráfico de la cola")
    cue = queue[0]
    if cue.get("match_id") != match_id:
        raise ValueError("El gráfico pertenece a otro partido")
    set_panel(state, cue["panel"], True, lineup_team=cue.get("lineup_team"))
    state["graphics_on_air"] = {"cue_id": cue["id"], "panel": cue["panel"]}
    queue.pop(0)
    return cue


def cue_preview(state: dict[str, Any], cue_id: str, match_id: str) -> dict[str, Any]:
    cue = next((item for item in state.get("graphics_queue", []) if item.get("id") == cue_id), None)
    if not cue or cue.get("match_id") != match_id:
        raise ValueError("Gráfico preparado no disponible")
    preview = copy.deepcopy(state)
    preview.pop("graphics_queue", None)
    hide_all(preview)
    set_panel(preview, cue["panel"], True, lineup_team=cue.get("lineup_team"))
    return preview
