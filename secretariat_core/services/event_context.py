from __future__ import annotations

from typing import Any

from .match_context import roster_player, split_player_name


def _roster_index(rosters: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for team_key in ("team1", "team2"):
        for row in rosters.get(team_key, []):
            player = row.get("player") or {}
            player_id = str(row.get("player_id") or player.get("id") or "")
            if not player_id:
                continue
            _, last_name = split_player_name(player)
            index[player_id] = {
                "number": "" if row.get("shirt_number") is None else str(row.get("shirt_number")),
                "last_name": last_name or str(player.get("display_name") or "").strip(),
            }
    return index


def _event_person(event: dict[str, Any] | None, roster_index: dict[str, dict[str, str]]) -> dict[str, str]:
    event = event or {}
    player = event.get("player") or {}
    player_id = str(event.get("player_id") or player.get("id") or "")
    roster = roster_index.get(player_id, {})
    number = str(roster.get("number") or "").strip()
    _, fallback_last = split_player_name(player)
    last_name = str(
        roster.get("last_name") or fallback_last or player.get("display_name") or "—"
    ).strip().upper()
    return {"number": number, "last_name": last_name}


def build_intermission_events(
    rows: list[dict[str, Any]],
    *,
    match: dict[str, Any],
    rosters: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build the chronological overlay event list from Supabase event rows."""
    home_id = str((match.get("home_team") or {}).get("id") or "")
    away_id = str((match.get("away_team") or {}).get("id") or "")
    roster_index = _roster_index(rosters)
    ordered = sorted(rows, key=lambda event: (str(event.get("created_at") or ""), str(event.get("id") or "")))
    assists_by_goal = {
        str(event.get("related_event_id")): event
        for event in ordered
        if event.get("event_type") == "assist" and event.get("related_event_id")
    }
    home_score = 0
    away_score = 0
    presentation: list[dict[str, Any]] = []
    for event in ordered:
        event_type = str(event.get("event_type") or "").lower()
        if event_type == "assist":
            continue
        team = event.get("team") or {}
        team_id = str(event.get("team_id") or team.get("id") or "")
        minute = str(event.get("match_time") or "--:--")
        person = _event_person(event, roster_index)
        side = "home" if team_id == home_id else "away" if team_id == away_id else "unknown"
        if event_type == "goal":
            if team_id == home_id:
                home_score += 1
            elif team_id == away_id:
                away_score += 1
            assist_event = assists_by_goal.get(str(event.get("id") or ""))
            assistant = _event_person(assist_event, roster_index) if assist_event else None
            notes = str(event.get("notes") or "").lower()
            presentation.append(
                {
                    "type": "goal",
                    "score": f"{home_score}–{away_score}",
                    "minute": minute,
                    "number": person["number"],
                    "last_name": person["last_name"],
                    "assistant_number": assistant["number"] if assistant else "",
                    "assistant_last_name": assistant["last_name"] if assistant else "",
                    "powerplay_goal": "powerplay_goal" in notes,
                    "team_id": team_id,
                    "side": side,
                }
            )
        elif event_type == "penalty":
            presentation.append(
                {
                    "type": "penalty",
                    "score": f"{home_score}–{away_score}",
                    "minute": minute,
                    "number": person["number"],
                    "last_name": person["last_name"],
                    "penalty_type": str(event.get("penalty_type") or "2"),
                    "team_id": team_id,
                    "side": side,
                }
            )
    return presentation


def apply_events_to_state(
    state: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    match: dict[str, Any],
    rosters: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    presentation = build_intermission_events(rows, match=match, rosters=rosters)
    state.setdefault("intermission", {})["events"] = presentation
    return presentation



def _event_player_id(event: dict[str, Any]) -> str:
    player = event.get("player") or {}
    return str(event.get("player_id") or player.get("id") or "")


def _roster_row_for_player(
    rosters: dict[str, list[dict[str, Any]]],
    team_key: str,
    player_id: str | None,
) -> dict[str, Any] | None:
    clean_id = str(player_id or "").strip()
    if not clean_id:
        return None
    return next(
        (
            row
            for row in rosters.get(team_key, [])
            if str(row.get("player_id") or (row.get("player") or {}).get("id") or "") == clean_id
        ),
        None,
    )


def build_goal_bottom_bar(
    *,
    team_key: str,
    scorer_id: str,
    assistant_id: str | None,
    match: dict[str, Any],
    rosters: dict[str, list[dict[str, Any]]],
    events: list[dict[str, Any]],
    team_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the rich goal lower-third used by both Direct and Realización.

    This deliberately derives its people from the loaded roster so shirt
    numbers and names match the saved match context rather than free text.
    """
    if team_key not in {"team1", "team2"}:
        raise ValueError("Equipo desconocido")
    scorer_row = _roster_row_for_player(rosters, team_key, scorer_id)
    if not scorer_row:
        raise ValueError("El goleador no está disponible en la convocatoria")
    assistant_row = _roster_row_for_player(rosters, team_key, assistant_id)
    scorer = roster_player(scorer_row)
    assistant = roster_player(assistant_row) if assistant_row else None
    team = match.get("home_team" if team_key == "team1" else "away_team") or {}
    team_state = team_state or {}
    goal_count = sum(
        1
        for event in events
        if str(event.get("event_type") or "").lower() == "goal"
        and _event_player_id(event) == str(scorer_id)
    ) or 1
    scorer_label = " ".join(value for value in (f"#{scorer['number']}" if scorer.get("number") else "", scorer.get("name") or "") if value)
    assistant_label = ""
    if assistant:
        assistant_label = " ".join(value for value in (f"#{assistant['number']}" if assistant.get("number") else "", assistant.get("name") or "") if value)
    text = scorer_label
    if assistant_label:
        text = f"{text} · ASIST. {assistant_label}".strip()
    if team_key == "team1":
        team_color = team_state.get("stripe_color") or team.get("primary_color") or team.get("secondary_color") or "#222222"
        team_logo = team_state.get("logo") or team.get("logo_url") or team.get("alternate_logo_url") or ""
    else:
        # The visitor lower third always uses the visitor identity. The away
        # secondary colour and alternate crest are authoritative, even when a
        # previous state snapshot still contains an older stripe/logo.
        team_color = team.get("secondary_color") or team_state.get("stripe_color") or team.get("primary_color") or "#222222"
        team_logo = team.get("alternate_logo_url") or team_state.get("logo") or team.get("logo_url") or ""
    return {
        "text": text,
        "status": "show",
        "team_key": team_key,
        "team_name": team.get("name") or team.get("short_name") or team_state.get("name") or "",
        "team_logo": team_logo,
        "team_color": team_color,
        "scorer": scorer.get("name") or "",
        "assistant": assistant.get("name") if assistant else "",
        "scorer_number": scorer.get("number") or "",
        "scorer_last_name": (scorer.get("last_name") or scorer.get("name") or "").upper(),
        "scorer_match_goals": int(goal_count),
        "assistant_number": assistant.get("number") if assistant else "",
        "assistant_last_name": ((assistant.get("last_name") or assistant.get("name") or "").upper() if assistant else ""),
    }
