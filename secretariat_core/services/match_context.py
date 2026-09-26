from __future__ import annotations

from typing import Any

POSITION_ORDER = {
    "goalkeeper": 0, "por": 0,
    "defender": 1, "def": 1,
    "centre": 2, "center": 2, "midfielder": 2, "med": 2,
    "forward": 3, "del": 3,
    "unknown": 9,
}
POSITION_LABELS = {
    "goalkeeper": "POR", "por": "POR",
    "defender": "DEF", "def": "DEF",
    "centre": "MED", "center": "MED", "midfielder": "MED", "med": "MED",
    "forward": "DEL", "del": "DEL",
    "player_coach": "J/E",
    "unknown": "",
}


def split_player_name(player: dict[str, Any]) -> tuple[str, str]:
    first_name = str(player.get("first_name") or "").strip()
    last_name = str(player.get("last_name") or "").strip()
    display_name = str(player.get("display_name") or "").strip()
    if not first_name and display_name:
        parts = display_name.split()
        first_name = parts[0] if parts else ""
        if not last_name and len(parts) > 1:
            last_name = " ".join(parts[1:])
    if not first_name and not last_name:
        first_name = "Jugador"
    return first_name, last_name


def roster_player(row: dict[str, Any]) -> dict[str, Any]:
    player = row.get("player") or {}
    first_name, last_name = split_player_name(player)
    position_key = str(player.get("position") or "unknown").strip().lower()
    base_position = position_key.removesuffix("_coach") if position_key.endswith("_coach") else position_key
    number = row.get("shirt_number")
    return {
        "player_id": str(row.get("player_id") or player.get("id") or ""),
        "number": "" if number is None else str(number),
        "first_name": first_name,
        "last_name": last_name,
        "name": " ".join(value for value in (first_name, last_name) if value),
        "position": POSITION_LABELS.get(base_position, base_position.upper()[:3]),
        "position_key": position_key,
        "is_coach": bool(player.get("is_coach")) or position_key == "coach" or position_key.endswith("_coach"),
        "captain": bool(row.get("captain") or row.get("is_captain")),
        "member_type": str(row.get("member_type") or "player").lower(),
    }


def competition_label(item: dict[str, Any]) -> str:
    season = item.get("seasons") or {}
    parts = [item.get("category") or "", season.get("name") if isinstance(season, dict) else ""]
    suffix = " · ".join(value for value in parts if value)
    return f"{item.get('name', 'Sin nombre')}{' — ' + suffix if suffix else ''}"


def match_label(item: dict[str, Any]) -> str:
    home, away = item.get("home_team") or {}, item.get("away_team") or {}
    date = (item.get("match_date") or "").replace("T", " ")[:16]
    home_name = home.get("short_name") or home.get("name") or "Local"
    away_name = away.get("short_name") or away.get("name") or "Visitante"
    return f"{date + ' · ' if date else ''}{home_name} - {away_name} [{item.get('status') or ''}]"


def _standing_for(standings: list[dict[str, Any]], team_id: str | None) -> dict[str, Any]:
    return next((row for row in standings if str(row.get("team_id") or "") == str(team_id or "")), {})


def _apply_team(state: dict[str, Any], team_key: str, team: dict[str, Any]) -> None:
    is_home = team_key == "team1"
    if is_home:
        color = team.get("primary_color") or team.get("secondary_color") or "#000000"
        logo = team.get("logo_url") or team.get("alternate_logo_url") or state[team_key].get("logo", "")
        alternate = team.get("secondary_color") or team.get("primary_color") or "#FFFFFF"
    else:
        color = team.get("secondary_color") or team.get("primary_color") or "#000000"
        logo = team.get("alternate_logo_url") or team.get("logo_url") or state[team_key].get("logo", "")
        alternate = team.get("primary_color") or team.get("secondary_color") or "#FFFFFF"

    state[team_key].update({
        "name": team.get("short_name") or team.get("name") or "",
        "stripe_color": color,
        "alternate_text_color": alternate,
        "logo": logo,
        "text_color": "white",
    })


def _lineup_payload(
    rows: list[dict[str, Any]],
    team: dict[str, Any],
    *,
    is_home: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    players: list[dict[str, Any]] = []
    coaches: list[dict[str, Any]] = []
    for row in rows:
        normalized = roster_player(row)
        if normalized["member_type"] == "coach" or normalized["is_coach"]:
            coaches.append({
                "first_name": normalized["first_name"],
                "last_name": normalized["last_name"],
                "name": normalized["name"],
            })
        if normalized["position_key"].endswith("_coach") or (normalized["member_type"] != "coach" and normalized["position_key"] != "coach"):
            players.append(normalized)
    players.sort(key=lambda player: (
        POSITION_ORDER.get(player.get("position_key", "unknown").removesuffix("_coach"), 9),
        int(player["number"]) if str(player.get("number", "")).isdigit() else 999,
        player.get("name", ""),
    ))
    return players, coaches


def apply_match_context(
    state: dict[str, Any],
    *,
    match: dict[str, Any],
    competition: dict[str, Any],
    standings: list[dict[str, Any]],
    home_roster: list[dict[str, Any]],
    away_roster: list[dict[str, Any]],
) -> dict[str, Any]:
    home = match.get("home_team") or {}
    away = match.get("away_team") or {}
    _apply_team(state, "team1", home)
    _apply_team(state, "team2", away)

    state.setdefault("online", {}).update({
        "competition_id": str(match.get("competition_id") or competition.get("id") or ""),
        "competition_name": competition.get("name") or "",
        "match_id": str(match.get("id") or ""),
        "match_label": match_label(match),
    })

    competition_logo = competition.get("logo_url") or state.setdefault("match", {}).get("logo", "")
    state.setdefault("match", {}).update({
        "league": competition.get("name") or state.get("match", {}).get("league", ""),
        "logo": competition_logo,
    })

    prematch = state.setdefault("prematch", {})
    prematch.update({
        "league_name": competition.get("name") or "",
        "venue": match.get("venue") or "",
        "kickoff": (match.get("scheduled_date") or "") if match.get("time_confirmed") is False else (match.get("match_date") or "").replace("T", " ")[:16],
    })
    for prefix, team in (("team1", home), ("team2", away)):
        stats = _standing_for(standings, team.get("id"))
        prematch[f"{prefix}_position"] = str(stats.get("position") or "-")
        prematch[f"{prefix}_points"] = str(stats.get("points") or 0)
        prematch[f"{prefix}_wins"] = f"{stats.get('wins', 0)}-{stats.get('draws', 0)}-{stats.get('losses', 0)}"
        prematch[f"{prefix}_goals_for"] = str(stats.get("goals_for") or 0)
        prematch[f"{prefix}_goals_against"] = str(stats.get("goals_against") or 0)

    lineups = state.setdefault("statistics", {}).setdefault("lineups", {})
    for team_key, team, rows, is_home in (
        ("team1", home, home_roster, True),
        ("team2", away, away_roster, False),
    ):
        players, coaches = _lineup_payload(rows, team, is_home=is_home)
        lineups[f"{team_key}_players"] = players
        lineups[f"{team_key}_coaches"] = coaches
        lineups[f"{team_key}_name"] = team.get("name") or ("Local" if is_home else "Visitante")
        lineups[f"{team_key}_logo"] = (
            team.get("logo_url") if is_home else (team.get("alternate_logo_url") or team.get("logo_url"))
        ) or ""
        lineups[f"{team_key}_color"] = (
            team.get("primary_color") if is_home else (team.get("secondary_color") or team.get("primary_color"))
        ) or "#333333"
        lineups[f"{team_key}_secondary_color"] = team.get("secondary_color") or "#FFFFFF"
        lineups[f"{team_key}_number_color"] = (
            team.get("secondary_color") or team.get("primary_color") or "#FFFFFF"
            if is_home
            else team.get("primary_color") or team.get("secondary_color") or "#FFFFFF"
        )

    lineups["competition_logo"] = competition_logo
    lineups["competition_name"] = competition.get("name") or ""
    return state
