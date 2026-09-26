from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .json_store import JSONStore

PP_DURATION_SECONDS = 120


def default_state() -> dict[str, Any]:
    return {
        "team1": {"name": "El Valle", "stripe_color": "#004080", "logo": "", "text_color": "white"},
        "team2": {"name": "Leganes", "stripe_color": "#004000", "logo": "", "text_color": "white"},
        "match": {"league": "Liga Oro", "logo": "", "time": "00:00", "sport_mode": "floorball", "period": 1},
        "animation": {"status": "hide"},
        "bottombar": {
            "text": "", "status": "hide", "team_key": "", "team_name": "", "team_logo": "",
            "team_color": "#222222", "scorer": "", "assistant": "",
            "scorer_number": "", "scorer_last_name": "", "scorer_match_goals": 0,
            "assistant_number": "", "assistant_last_name": "",
        },
        "powerplay": {
            "team1": _default_powerplay(),
            "team2": _default_powerplay(),
        },
        "empty_net": {"team1": False, "team2": False},
        "intermission": {"status": False, "team1_goals": "", "team2_goals": "", "extra_info": "", "events": []},
        "prematch": {
            "status": False, "league_name": "", "team1_position": "", "team1_points": "",
            "team1_wins": "", "team1_goals_for": "", "team1_goals_against": "",
            "team2_position": "", "team2_points": "", "team2_wins": "",
            "team2_goals_for": "", "team2_goals_against": "", "venue": "", "kickoff": "",
        },
        "online": {"competition_id": "", "competition_name": "", "match_id": "", "match_label": ""},
        "statistics": {
            "lineups": {
                "status": False, "team1_status": False, "team2_status": False,
                "title": "ALINEACIONES", "team1_name": "", "team2_name": "",
                "team1_players": [], "team2_players": [], "team1_starters": {},
                "team2_starters": {}, "team1_coaches": [], "team2_coaches": [],
            },
            "top_scorers": {
                "status": False, "title": "MÁXIMOS PUNTUADORES", "competition_name": "",
                "competition_logo": "", "team1": {}, "team2": {},
            },
            "standings": {
                "status": False, "title": "CLASIFICACIÓN", "competition_name": "",
                "competition_logo": "", "rows": [],
            },
            "player_profile": {
                "status": False, "player_id": "", "team_key": "team1", "team_color": "#59606c",
                "team_logo": "", "number": "", "name": "", "birth_date": "—",
                "nationality": "—", "position": "—", "played": 0, "goals": 0, "assists": 0,
            },
        },
        "penalty_shootout": {
            "status": False,
            "team1": [None, None, None, None, None],
            "team2": [None, None, None, None, None],
        },
    }


def _default_powerplay() -> dict[str, Any]:
    return {
        "status": False, "player_number": "", "start_time": None,
        "duration": PP_DURATION_SECONDS, "penalty_type": "2", "player_id": "",
        "serving_player_id": "", "serving_player_number": "",
        "start_match_seconds": None, "block_start_match_seconds": None,
        "last_ocr_match_seconds": None, "last_valid_ocr_seconds": None,
        "pending_ocr_match_seconds": None, "pending_ocr_count": 0,
        "same_ocr_count": 0, "ocr_elapsed_seconds": 0,
        "clock_sync_state": "idle", "clock_sync_detail": "",
        "current_block": 1, "total_blocks": 1,
        "remaining_seconds": PP_DURATION_SECONDS,
        "penalties": [], "active_count": 0,
    }


def _merge_defaults(target: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    for key, value in defaults.items():
        if key not in target:
            target[key] = deepcopy(value)
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_defaults(target[key], value)
    return target


def normalize_state(raw: Any) -> dict[str, Any]:
    state = raw if isinstance(raw, dict) else {}
    _merge_defaults(state, default_state())
    shootout = state["penalty_shootout"]
    for team_key in ("team1", "team2"):
        values = list(shootout.get(team_key) or [])[:5]
        values.extend([None] * (5 - len(values)))
        shootout[team_key] = [value if value in ("goal", "miss", None) else None for value in values]
    return state


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self._store = JSONStore(path)

    def load(self) -> dict[str, Any]:
        return normalize_state(self._store.read(default_state()))

    def save(self, state: dict[str, Any]) -> None:
        self._store.write(normalize_state(state))
