"""Validated presentation settings shared by published competition identities."""
import math

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
