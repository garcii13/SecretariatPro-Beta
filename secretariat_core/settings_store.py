from __future__ import annotations

import locale
import re
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .json_store import JSONStore
from .visual_identity import normalize_elements


DEFAULT_APPEARANCE = {
    "app_theme": "system",
    "elements": normalize_elements({}),
    "scoreboard": {
        "background": "#2a2d34",
        "name_box": "#3b3f47",
        "text": "#ffffff",
    },
    "bottom_bar": {
        "body": "#24272e",
        "middle": "#30333b",
        "text": "#ffffff",
        "secondary_text": "#c6cad2",
    },
    "panels": {
        "background": "#171c25",
        "surface": "#232a35",
        "accent": "#59606c",
        "text": "#ffffff",
    },
    "period_strip": {
        "enabled": False,
        "segments": 3,
        "labels": ["1", "2", "3"],
        "active_color": "#8cff00",
        "text_color": "#102000",
    },
    "goal_celebration": {
        "delay_seconds": 4,
        "duration_seconds": 6,
    },
}

SUPPORTED_LANGUAGES = frozenset({"es", "en", "sv", "cs", "fi", "de"})


def system_language() -> str:
    """Return the operating-system language when SecretariatPro supports it."""
    candidates: list[str] = []
    try:
        language, _encoding = locale.getlocale()
        if language:
            candidates.append(language)
    except (ValueError, TypeError):
        pass
    candidates.extend(os.getenv(name, "") for name in ("LC_ALL", "LC_MESSAGES", "LANG"))
    for candidate in candidates:
        base = str(candidate or "").split(".", 1)[0].split("@", 1)[0].replace("_", "-").split("-", 1)[0].lower()
        if base in SUPPORTED_LANGUAGES:
            return base
    return "en"


def default_settings() -> dict[str, Any]:
    return {
        "language": system_language(),
        "score_control": {"mode": "ocr"},
        "obs": {
            "host": "127.0.0.1", "port": 4455, "password": "",
            "auto_connect": False, "overlay_source": "", "audio_input": "",
            "projector_window": "Fullscreen Projector (Program)",
            "replay_auto_mark_goals": True, "replay_post_roll_seconds": 4,
        },
        "shortcuts": {
            "scoreboard": "Alt+F1", "prematch": "Alt+F2", "intermission": "Alt+F3",
            "lineups_home": "Alt+F4", "lineups_away": "Alt+F5",
            "top_scorers": "Alt+F6", "standings": "Alt+F7",
            "bottom_bar": "Alt+F8", "penalties": "Alt+F9", "hide_all": "Alt+F10",
        },
        # Personal to the authenticated producer. AccountSettingsStore keeps
        # this list isolated per account and the cloud profile follows it to
        # the producer's other Live installations.
        "graphics_sequences": [],
        "replay_templates": [],
        "appearance": deepcopy(DEFAULT_APPEARANCE),
    }


def _deep_merge(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def normalize_settings(raw: Any) -> dict[str, Any]:
    result = default_settings()
    if not isinstance(raw, dict):
        return result
    _deep_merge(result, raw)
    defaults = default_settings()
    for section in ("appearance", "score_control", "obs", "shortcuts"):
        if not isinstance(result.get(section), dict):
            result[section] = defaults[section]
    for section in ("scoreboard", "bottom_bar", "panels"):
        if not isinstance(result["appearance"].get(section), dict):
            result["appearance"][section] = defaults["appearance"][section]
    period_strip = result["appearance"].get("period_strip")
    period_strip = period_strip if isinstance(period_strip, dict) else {}
    try:
        segments = max(1, min(12, int(period_strip.get("segments", 3))))
    except (TypeError, ValueError):
        segments = 3
    labels = [str(value).strip()[:8] for value in (period_strip.get("labels") or [])]
    labels = [(labels[index] if index < len(labels) and labels[index] else str(index + 1)) for index in range(segments)]
    result["appearance"]["period_strip"] = {
        "enabled": bool(period_strip.get("enabled", False)),
        "show_number": bool(period_strip.get("show_number", False)),
        "segments": segments,
        "labels": labels,
        **{key: str(period_strip.get(key)) if re.fullmatch(r"#[0-9a-fA-F]{6}", str(period_strip.get(key, ""))) else default for key, default in (("active_color", "#8cff00"), ("text_color", "#102000"))},
    }
    goal_celebration = result["appearance"].get("goal_celebration")
    goal_celebration = goal_celebration if isinstance(goal_celebration, dict) else {}
    try:
        goal_delay = max(0, min(30, int(goal_celebration.get("delay_seconds", 4))))
    except (TypeError, ValueError):
        goal_delay = 4
    try:
        goal_duration = max(1, min(30, int(goal_celebration.get("duration_seconds", 6))))
    except (TypeError, ValueError):
        goal_duration = 6
    result["appearance"]["goal_celebration"] = {
        "delay_seconds": goal_delay,
        "duration_seconds": goal_duration,
    }
    sequences = result.get("graphics_sequences")
    result["graphics_sequences"] = sequences if isinstance(sequences, list) else []
    mode = str(result["score_control"].get("mode") or "ocr").lower()
    result["score_control"]["mode"] = mode if mode in {"ocr", "manual"} else "ocr"
    language = str(result.get("language") or system_language()).lower()
    result["language"] = language if language in SUPPORTED_LANGUAGES else system_language()
    theme = str(result.get("appearance", {}).get("app_theme") or "dark").lower()
    result["appearance"].pop("overlay", None)  # removed legacy/dead palette block
    result["appearance"].pop("app", None)      # app colours are fixed by the selected theme
    result["appearance"].pop("deck", None)     # Realización is part of the app, not the overlay palette
    result["appearance"]["app_theme"] = theme if theme in {"dark", "light", "system"} else "system"
    result["appearance"]["elements"] = normalize_elements(result["appearance"].get("elements"))
    return result


class SettingsStore:
    def __init__(self, path: str | Path) -> None:
        self._store = JSONStore(path)

    def load(self) -> dict[str, Any]:
        return normalize_settings(self._store.read(default_settings()))

    def save(self, settings: dict[str, Any]) -> None:
        self._store.write(normalize_settings(settings))


class AccountSettingsStore:
    """Local settings profiles keyed by authenticated Supabase user id.

    This keeps OBS credentials and appearance isolated per operator without
    exposing passwords through the web API. Profiles follow the authenticated
    account on this workstation and are activated automatically at login.
    """

    def __init__(self, path: str | Path) -> None:
        self._store = JSONStore(path)

    def _all(self) -> dict[str, Any]:
        raw = self._store.read({"profiles": {}})
        if not isinstance(raw, dict):
            raw = {"profiles": {}}
        profiles = raw.get("profiles")
        if not isinstance(profiles, dict):
            raw["profiles"] = {}
        return raw

    def load(self, user_id: str) -> dict[str, Any] | None:
        key = str(user_id or "").strip()
        if not key:
            return None
        profile = self._all()["profiles"].get(key)
        if not isinstance(profile, dict):
            return None
        clean = {name: value for name, value in profile.items() if not str(name).startswith("_")}
        return normalize_settings(clean)

    def save(self, user_id: str, settings: dict[str, Any], email: str = "") -> None:
        key = str(user_id or "").strip()
        if not key:
            return
        payload = self._all()
        payload["profiles"][key] = {
            **normalize_settings(settings),
            "_account_email": str(email or ""),
        }
        self._store.write(payload)


def period_strip_for_sport(config: dict[str, Any], sport_mode: str) -> dict[str, Any]:
    result = deepcopy(config)
    count = 2 if sport_mode == "handball" else max(1, min(12, int(result.get("segments") or 3)))
    labels = list(result.get("labels") or [])
    result["segments"] = count
    result["labels"] = [str(labels[i]) if i < len(labels) else str(i + 1) for i in range(count)]
    return result
