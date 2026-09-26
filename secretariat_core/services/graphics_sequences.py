"""Personal, reusable graphic sequences for a Live producer."""
from __future__ import annotations

import uuid
from typing import Any

from .graphics_queue import QUEUE_PANELS

MAX_SEQUENCES = 24
MAX_STEPS = 16


def normalize_step(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Cada paso debe ser un gráfico válido")
    panel = str(raw.get("panel") or "").strip()
    if panel not in QUEUE_PANELS:
        raise ValueError("La secuencia contiene un gráfico no disponible")
    team = str(raw.get("lineup_team") or "team1")
    if team not in {"team1", "team2"}:
        team = "team1"
    return {
        "panel": panel,
        "lineup_team": team,
        "duration_seconds": max(1, min(120, int(raw.get("duration_seconds") or 5))),
        "interval_seconds": max(0, min(60, int(raw.get("interval_seconds") or 0))),
    }


def normalize_sequence(raw: Any, *, sequence_id: str = "") -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Secuencia no válida")
    name = str(raw.get("name") or "").strip()[:80]
    if not name:
        raise ValueError("Pon un nombre a la secuencia")
    steps = [normalize_step(step) for step in list(raw.get("steps") or [])[:MAX_STEPS]]
    if not steps:
        raise ValueError("Añade al menos un gráfico a la secuencia")
    return {"id": sequence_id or uuid.uuid4().hex, "name": name, "steps": steps}


def save_sequence(settings: dict[str, Any], raw: Any, sequence_id: str = "") -> dict[str, Any]:
    sequences = list(settings.get("graphics_sequences") or [])
    if sequence_id:
        index = next((i for i, row in enumerate(sequences) if row.get("id") == sequence_id), None)
        if index is None:
            raise KeyError(sequence_id)
        sequence = normalize_sequence(raw, sequence_id=sequence_id)
        sequences[index] = sequence
    else:
        if len(sequences) >= MAX_SEQUENCES:
            raise ValueError("Has alcanzado el máximo de secuencias personales")
        sequence = normalize_sequence(raw)
        sequences.append(sequence)
    settings["graphics_sequences"] = sequences
    return sequence


def delete_sequence(settings: dict[str, Any], sequence_id: str) -> bool:
    sequences = list(settings.get("graphics_sequences") or [])
    settings["graphics_sequences"] = [row for row in sequences if row.get("id") != sequence_id]
    return len(settings["graphics_sequences"]) != len(sequences)


def find_sequence(settings: dict[str, Any], sequence_id: str) -> dict[str, Any]:
    sequence = next((row for row in settings.get("graphics_sequences") or [] if row.get("id") == sequence_id), None)
    if not sequence:
        raise KeyError(sequence_id)
    return normalize_sequence(sequence, sequence_id=sequence_id)
