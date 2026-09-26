from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

PP_DURATION_SECONDS = 120
MAX_DIRECT_FORWARD_JUMP = 30
MAX_CONFIRMED_FORWARD_JUMP = 180
PERIOD_RESET_MIN_DROP = 45
PERIOD_RESET_MAX_NEW_CLOCK = 30


def penalty_values(penalty_type: str) -> tuple[int, int, int]:
    if penalty_type == "2+2":
        return 240, 4, 0
    if penalty_type == "2+10":
        return 120, 12, 10
    return 120, 2, 0


def display_number(info: dict[str, Any]) -> str:
    number = (
        info.get("serving_player_number")
        if info.get("penalty_type") == "2+10"
        else info.get("player_number_raw")
    )
    return str(number).strip() if number is not None else ""


def _clear_pending_clock(info: dict[str, Any]) -> None:
    info["pending_ocr_match_seconds"] = None
    info["pending_ocr_count"] = 0


def _set_clock_state(info: dict[str, Any], state: str, detail: str = "") -> bool:
    changed = info.get("clock_sync_state") != state or info.get("clock_sync_detail") != detail
    info["clock_sync_state"] = state
    info["clock_sync_detail"] = detail
    return changed


def _new_penalty(
    *, current_seconds: int, player_id: str, player_number: Any,
    penalty_type: str = "2", serving_player_id: str = "", serving_player_number: Any = "",
) -> dict[str, Any]:
    current = int(current_seconds)
    item = {
        "overlay_id": uuid4().hex,
        "status": True,
        "player_id": player_id,
        "player_number_raw": "" if player_number is None else player_number,
        "serving_player_id": serving_player_id or player_id,
        "serving_player_number": player_number if serving_player_number in (None, "") else serving_player_number,
        "penalty_type": penalty_type,
        "start_match_seconds": current,
        "block_start_match_seconds": current,
        "last_ocr_match_seconds": current,
        "last_valid_ocr_seconds": current,
        "pending_ocr_match_seconds": None,
        "pending_ocr_count": 0,
        "same_ocr_count": 0,
        "ocr_elapsed_seconds": 0,
        "current_block": 1,
        "total_blocks": 2 if penalty_type == "2+2" else 1,
        "remaining_seconds": PP_DURATION_SECONDS,
        "clock_sync_state": "synced",
        "clock_sync_detail": f"Inicio OCR {current // 60}:{current % 60:02d}",
        "start_time": None,
        "duration": PP_DURATION_SECONDS,
    }
    item["player_number"] = display_number(item)
    return item


def _active_items(info: dict[str, Any]) -> list[dict[str, Any]]:
    had_queue = isinstance(info.get("penalties"), list)
    items = info.get("penalties")
    if not had_queue:
        items = []
    # Migrate a legacy single active penalty into the queue exactly once.
    # An explicitly present empty queue means the last penalty has just ended;
    # do not resurrect the mirrored legacy top-level values.
    if not had_queue and info.get("status"):
        legacy = {k: deepcopy(v) for k, v in info.items() if k != "penalties"}
        legacy["status"] = True
        items = [legacy]
    items = [dict(item) for item in items if isinstance(item, dict) and item.get("status")]
    info["penalties"] = items
    return items


def _sync_primary(info: dict[str, Any]) -> None:
    items = _active_items(info)
    if items:
        primary = items[0]
        for key, value in primary.items():
            if key != "penalties":
                info[key] = deepcopy(value)
        info["status"] = True
        info["player_number"] = display_number(primary)
        info["active_count"] = len(items)
    else:
        # Keep the familiar legacy keys so old UI code and tests still receive a
        # stable shape, while the new overlay can consume ``penalties``.
        info.update({
            "status": False, "player_id": "", "player_number": "", "player_number_raw": "",
            "serving_player_id": "", "serving_player_number": "", "penalty_type": "2",
            "start_time": None, "start_match_seconds": None, "block_start_match_seconds": None,
            "last_ocr_match_seconds": None, "last_valid_ocr_seconds": None,
            "pending_ocr_match_seconds": None, "pending_ocr_count": 0, "same_ocr_count": 0,
            "ocr_elapsed_seconds": 0, "current_block": 1, "total_blocks": 1,
            "remaining_seconds": 0, "clock_sync_state": "idle", "clock_sync_detail": "",
            "duration": PP_DURATION_SECONDS, "active_count": 0,
        })
        info["penalties"] = []


def start_powerplay(
    info: dict[str, Any], *, current_seconds: int, player_id: str,
    player_number: Any, penalty_type: str = "2", serving_player_id: str = "",
    serving_player_number: Any = "",
) -> dict[str, Any]:
    """Append a simultaneous penalty and mirror the first active one at top level."""
    items = _active_items(info)
    items.append(_new_penalty(
        current_seconds=current_seconds,
        player_id=player_id,
        player_number=player_number,
        penalty_type=penalty_type,
        serving_player_id=serving_player_id,
        serving_player_number=serving_player_number,
    ))
    info["penalties"] = items
    _sync_primary(info)
    return info


def _consume_elapsed(item: dict[str, Any], elapsed: int) -> bool:
    changed = False
    elapsed = max(0, int(elapsed))
    if elapsed:
        item["ocr_elapsed_seconds"] = int(item.get("ocr_elapsed_seconds") or 0) + elapsed
    while elapsed > 0 and item.get("status"):
        remaining = max(0, int(item.get("remaining_seconds") or PP_DURATION_SECONDS)) or PP_DURATION_SECONDS
        if elapsed < remaining:
            item["remaining_seconds"] = remaining - elapsed
            elapsed = 0
            changed = True
            break
        elapsed -= remaining
        if int(item.get("current_block") or 1) < int(item.get("total_blocks") or 1):
            item["current_block"] = int(item.get("current_block") or 1) + 1
            item["remaining_seconds"] = PP_DURATION_SECONDS
            changed = True
            continue
        item["status"] = False
        item["remaining_seconds"] = 0
        _set_clock_state(item, "finished", "Expulsión finalizada por reloj OCR")
        changed = True
    return changed


def _is_period_reset(last: int, current: int) -> bool:
    return last - current >= PERIOD_RESET_MIN_DROP and current <= PERIOD_RESET_MAX_NEW_CLOCK


def _accept_clock(item: dict[str, Any], current: int, elapsed: int) -> bool:
    item["same_ocr_count"] = 0
    item["last_ocr_match_seconds"] = current
    item["last_valid_ocr_seconds"] = current
    _clear_pending_clock(item)
    changed = _consume_elapsed(item, elapsed)
    if item.get("status"):
        _set_clock_state(item, "synced", f"OCR {current // 60}:{current % 60:02d} · −{elapsed}s")
    item["player_number"] = display_number(item)
    return changed or True


def _advance_single(item: dict[str, Any], current_seconds: int | None, *, strict_ocr: bool = False) -> bool:
    if not item.get("status") or current_seconds is None:
        return False
    current = int(current_seconds)
    if current < 0:
        return False
    last = item.get("last_ocr_match_seconds")
    if last is None:
        item["last_ocr_match_seconds"] = current
        item["last_valid_ocr_seconds"] = current
        _clear_pending_clock(item)
        _set_clock_state(item, "synced", "Reloj OCR enlazado")
        item["player_number"] = display_number(item)
        return True
    last = int(last)
    delta = current - last
    if delta == 0:
        same_count = int(item.get("same_ocr_count") or 0) + 1
        item["same_ocr_count"] = same_count
        if same_count >= 8:
            return _set_clock_state(item, "paused", f"Reloj parado en {current // 60}:{current % 60:02d}")
        return False
    if delta < 0:
        if _is_period_reset(last, current):
            item["last_ocr_match_seconds"] = current
            item["last_valid_ocr_seconds"] = current
            item["same_ocr_count"] = 0
            _clear_pending_clock(item)
            _set_clock_state(item, "period_reset", "Nuevo periodo; conserva el tiempo restante")
            item["player_number"] = display_number(item)
            return True
        _clear_pending_clock(item)
        _set_clock_state(item, "ignored", f"Lectura atrás ignorada: {current // 60}:{current % 60:02d}")
        return True
    if delta <= MAX_DIRECT_FORWARD_JUMP or not strict_ocr:
        return _accept_clock(item, current, delta)
    pending = item.get("pending_ocr_match_seconds")
    pending_count = int(item.get("pending_ocr_count") or 0)
    coherent = pending is not None and current >= int(pending) and current - int(pending) <= MAX_DIRECT_FORWARD_JUMP
    if coherent:
        confirmed_delta = current - last
        if confirmed_delta <= MAX_CONFIRMED_FORWARD_JUMP:
            return _accept_clock(item, current, confirmed_delta)
    item["pending_ocr_match_seconds"] = current
    item["pending_ocr_count"] = pending_count + 1
    _set_clock_state(item, "confirming", f"Confirmando salto OCR a {current // 60}:{current % 60:02d}")
    return True


def advance_powerplay(info: dict[str, Any], current_seconds: int | None, *, strict_ocr: bool = False) -> bool:
    items = _active_items(info)
    if not items:
        _sync_primary(info)
        return False
    changed = False
    for item in items:
        changed = _advance_single(item, current_seconds, strict_ocr=strict_ocr) or changed
    info["penalties"] = [item for item in items if item.get("status")]
    before = int(info.get("active_count") or 0)
    _sync_primary(info)
    return changed or before != len(info.get("penalties") or [])


def _burn_single(item: dict[str, Any], current_seconds: int | None) -> str:
    if not item.get("status"):
        return "inactive"
    if current_seconds is None:
        current_seconds = item.get("last_ocr_match_seconds") or item.get("block_start_match_seconds")
    if int(item.get("current_block") or 1) < int(item.get("total_blocks") or 1):
        item["current_block"] = int(item.get("current_block") or 1) + 1
        item["block_start_match_seconds"] = current_seconds
        item["last_ocr_match_seconds"] = current_seconds
        item["last_valid_ocr_seconds"] = current_seconds
        item["remaining_seconds"] = PP_DURATION_SECONDS
        _clear_pending_clock(item)
        _set_clock_state(item, "synced", "Gol: comienza el segundo bloque del 2+2")
        item["player_number"] = display_number(item)
        return "next_block"
    item["status"] = False
    item["remaining_seconds"] = 0
    item["last_ocr_match_seconds"] = current_seconds
    _clear_pending_clock(item)
    _set_clock_state(item, "finished", "Gol: expulsión cancelada")
    return "ended"


def burn_powerplay_block(info: dict[str, Any], current_seconds: int | None) -> str:
    """Consume only the first active penalty; subsequent simultaneous penalties move up."""
    items = _active_items(info)
    if not items:
        _sync_primary(info)
        return "inactive"
    result = _burn_single(items[0], current_seconds)
    info["penalties"] = [item for item in items if item.get("status")]
    _sync_primary(info)
    return result


def _end_single(item: dict[str, Any]) -> None:
    item["status"] = False
    item["start_time"] = None
    item["start_match_seconds"] = None
    item["block_start_match_seconds"] = None
    item["last_ocr_match_seconds"] = None
    item["last_valid_ocr_seconds"] = None
    item["same_ocr_count"] = 0
    item["remaining_seconds"] = 0
    _clear_pending_clock(item)
    _set_clock_state(item, "idle", "Expulsión cancelada")


def end_powerplay(info: dict[str, Any]) -> dict[str, Any]:
    """Cancel the first active penalty and promote the next one, if any."""
    items = _active_items(info)
    if items:
        _end_single(items[0])
    info["penalties"] = [item for item in items if item.get("status")]
    _sync_primary(info)
    return info
