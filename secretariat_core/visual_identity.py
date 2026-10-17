"""Validated presentation settings shared by published competition identities."""
import math
from urllib.parse import urlsplit


def normalize_team_identity(raw):
    raw = raw if isinstance(raw, dict) else {}
    flags = raw.get("flags")
    flags = flags if isinstance(flags, dict) else {}
    clean = {}
    for team_id, value in flags.items():
        if not isinstance(value, str):
            continue
        url = value.strip()
        try:
            parsed = urlsplit(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc and len(url) <= 4096:
                clean[str(team_id)[:128]] = url
        except ValueError:
            continue
    return {"international": raw.get("international") is True, "flags": clean}

ELEMENTS = ("scoreboard", "bottom_bar", "player_profile", "prematch", "intermission",
            "lineups_home", "lineups_away", "top_scorers", "standings", "penalties")
FONTS = ("default", "Arial", "Verdana", "Georgia", "Trebuchet MS", "Courier New")


def normalize_elements(raw):
    raw = raw if isinstance(raw, dict) else {}
    result = {}
    for name in ELEMENTS:
        item = raw.get(name)
        item = item if isinstance(item, dict) else {}
        try:
            scale = float(item.get("scale", 1))
        except (TypeError, ValueError):
            scale = 1.0
        if not math.isfinite(scale):
            scale = 1.0
        font = item.get("font", "default")
        result[name] = {"scale": max(0.5, min(1.5, scale)),
                        "font": font if font in FONTS else "default"}
    return result
