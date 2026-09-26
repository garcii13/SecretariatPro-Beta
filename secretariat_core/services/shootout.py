from __future__ import annotations

from typing import Any, Literal

Outcome = Literal["goal", "miss"] | None


def normalize_attempts(values: list[Any] | None) -> list[Outcome]:
    normalized = list(values or [])[:5]
    normalized.extend([None] * (5 - len(normalized)))
    return [value if value in {"goal", "miss", None} else None for value in normalized]


def set_attempt(state: dict[str, Any], team_key: str, index: int, outcome: Outcome) -> list[Outcome]:
    if team_key not in {"team1", "team2"}:
        raise ValueError("Equipo desconocido")
    if not 0 <= int(index) < 5:
        raise ValueError("El intento debe estar entre 1 y 5")
    shootout = state.setdefault("penalty_shootout", {})
    attempts = normalize_attempts(shootout.get(team_key))
    attempts[int(index)] = outcome
    shootout[team_key] = attempts
    return attempts


def reset_shootout(state: dict[str, Any]) -> None:
    shootout = state.setdefault("penalty_shootout", {})
    shootout["team1"] = [None, None, None, None, None]
    shootout["team2"] = [None, None, None, None, None]
