from __future__ import annotations

from typing import Any

FULLSCREEN_PANELS = {
    "prematch",
    "intermission",
    "lineups",
    "top_scorers",
    "standings",
    "player_profile",
    "penalties",
}

ALL_PANELS = {
    "scoreboard",
    "bottom_bar",
    *FULLSCREEN_PANELS,
}


def _show_value(visible: bool) -> str:
    return "show" if visible else "hide"


def hide_fullscreen_panels(state: dict[str, Any], except_panel: str | None = None) -> None:
    if except_panel != "prematch":
        state.setdefault("prematch", {})["status"] = False
    if except_panel != "intermission":
        state.setdefault("intermission", {})["status"] = False

    statistics = state.setdefault("statistics", {})
    lineups = statistics.setdefault("lineups", {})
    if except_panel != "lineups":
        lineups["status"] = False
        lineups["team1_status"] = False
        lineups["team2_status"] = False
    if except_panel != "top_scorers":
        statistics.setdefault("top_scorers", {})["status"] = False
    if except_panel != "standings":
        statistics.setdefault("standings", {})["status"] = False
    if except_panel != "player_profile":
        statistics.setdefault("player_profile", {})["status"] = False
    if except_panel != "penalties":
        state.setdefault("penalty_shootout", {})["status"] = False


def panel_visible(state: dict[str, Any], panel: str) -> bool:
    if panel == "scoreboard":
        return state.get("animation", {}).get("status") == "show"
    if panel == "bottom_bar":
        return state.get("bottombar", {}).get("status") == "show"
    if panel == "prematch":
        return bool(state.get("prematch", {}).get("status"))
    if panel == "intermission":
        return bool(state.get("intermission", {}).get("status"))
    if panel == "lineups":
        return bool(state.get("statistics", {}).get("lineups", {}).get("status"))
    if panel in {"top_scorers", "standings", "player_profile"}:
        return bool(state.get("statistics", {}).get(panel, {}).get("status"))
    if panel == "penalties":
        return bool(state.get("penalty_shootout", {}).get("status"))
    raise KeyError(f"Panel desconocido: {panel}")


def set_panel(
    state: dict[str, Any],
    panel: str,
    visible: bool,
    *,
    lineup_team: str | None = None,
) -> None:
    if panel not in ALL_PANELS:
        raise KeyError(f"Panel desconocido: {panel}")

    if visible and panel in FULLSCREEN_PANELS:
        hide_fullscreen_panels(state, panel)

    if panel == "scoreboard":
        state.setdefault("animation", {})["status"] = _show_value(visible)
        state.setdefault("scoreboard", {})["status"] = _show_value(visible)
    elif panel == "bottom_bar":
        state.setdefault("bottombar", {})["status"] = _show_value(visible)
    elif panel == "prematch":
        state.setdefault("prematch", {})["status"] = visible
    elif panel == "intermission":
        state.setdefault("intermission", {})["status"] = visible
    elif panel == "lineups":
        lineups = state.setdefault("statistics", {}).setdefault("lineups", {})
        lineups["status"] = visible
        if not visible:
            lineups["team1_status"] = False
            lineups["team2_status"] = False
        else:
            team = lineup_team if lineup_team in {"team1", "team2"} else "team1"
            lineups["team1_status"] = team == "team1"
            lineups["team2_status"] = team == "team2"
    elif panel in {"top_scorers", "standings", "player_profile"}:
        state.setdefault("statistics", {}).setdefault(panel, {})["status"] = visible
    elif panel == "penalties":
        state.setdefault("penalty_shootout", {})["status"] = visible


def toggle_panel(
    state: dict[str, Any],
    panel: str,
    *,
    lineup_team: str | None = None,
) -> bool:
    visible = not panel_visible(state, panel)
    set_panel(state, panel, visible, lineup_team=lineup_team)
    return visible


def hide_all(state: dict[str, Any], *, keep_scoreboard: bool = False) -> None:
    hide_fullscreen_panels(state)
    set_panel(state, "bottom_bar", False)
    if not keep_scoreboard:
        set_panel(state, "scoreboard", False)


def overlay_summary(state: dict[str, Any]) -> dict[str, bool]:
    return {panel: panel_visible(state, panel) for panel in sorted(ALL_PANELS)}
