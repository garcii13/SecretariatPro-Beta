from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .json_store import JSONStore

OFFLINE_GRACE_DAYS = 4
RETENTION_YEARS = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluate_subscription(
    subscription: dict[str, Any] | None,
    *,
    validated_at: datetime | None = None,
    now: datetime | None = None,
    online: bool = True,
    grace_days: int = OFFLINE_GRACE_DAYS,
) -> dict[str, Any]:
    """Normalize one subscription into the access contract used by both apps.

    Online checks are authoritative. Offline checks can reuse a previously
    validated active subscription for at most four days. Expired workspaces
    remain readable in Manager during the two-year retention window, but the
    production app is blocked.
    """
    current = (now or utc_now()).astimezone(timezone.utc)
    row = dict(subscription or {})
    starts_at = parse_datetime(row.get("starts_at"))
    ends_at = parse_datetime(row.get("ends_at"))
    retention_until = parse_datetime(row.get("retention_until"))
    status = str(row.get("status") or "missing").lower()
    grace = int(row.get("offline_grace_days") or grace_days or OFFLINE_GRACE_DAYS)

    active_status = status in {"active", "trial"}
    within_dates = (starts_at is None or current >= starts_at) and (ends_at is None or current <= ends_at)
    online_allowed = bool(online and active_status and within_dates)

    offline_until: datetime | None = None
    if validated_at is not None:
        validated = validated_at.astimezone(timezone.utc)
        offline_until = validated + timedelta(days=max(0, grace))

    offline_allowed = (
        not online
        and active_status
        and validated_at is not None
        and offline_until is not None
        and current <= offline_until
    )

    allowed = bool(online_allowed or offline_allowed)
    if allowed:
        mode = "active" if online else "offline_grace"
        message = "Membresía activa" if online else f"Modo sin conexión · válido hasta {offline_until.isoformat()}"
    elif retention_until and current <= retention_until:
        mode = "read_only"
        message = "Membresía no activa · historial disponible en modo consulta"
    else:
        mode = "blocked"
        message = "No hay una membresía activa"

    plan = row.get("plan") or {}
    if isinstance(plan, list):
        plan = plan[0] if plan else {}
    entitlements = row.get("entitlements") or (plan.get("entitlements") if isinstance(plan, dict) else {}) or {}

    return {
        "allowed": allowed,
        "production_allowed": allowed,
        "manager_read_only": mode == "read_only",
        "mode": mode,
        "status": status,
        "message": message,
        "subscription_id": str(row.get("id") or ""),
        "plan_id": str(row.get("plan_id") or (plan.get("id") if isinstance(plan, dict) else "") or ""),
        "plan_name": str((plan.get("name") if isinstance(plan, dict) else "") or row.get("plan_name") or ""),
        "starts_at": starts_at.isoformat() if starts_at else "",
        "ends_at": ends_at.isoformat() if ends_at else "",
        "retention_until": retention_until.isoformat() if retention_until else "",
        "offline_grace_days": grace,
        "offline_until": offline_until.isoformat() if offline_until else "",
        "validated_at": validated_at.isoformat() if validated_at else "",
        "online_validation": online,
        "entitlements": entitlements if isinstance(entitlements, dict) else {},
    }


class SubscriptionAccessStore:
    """Local cache for the last successful online entitlement validation."""

    def __init__(self, path: str | Path) -> None:
        self.store = JSONStore(path)

    def load(self) -> dict[str, Any]:
        value = self.store.read({})
        return value if isinstance(value, dict) else {}

    def save(self, *, user_id: str, workspace: dict[str, Any], subscription: dict[str, Any], access: dict[str, Any]) -> None:
        self.store.write({
            "user_id": str(user_id or ""),
            "workspace": dict(workspace or {}),
            "subscription": dict(subscription or {}),
            "access": dict(access or {}),
            "validated_at": utc_now().isoformat(),
        })

    def clear(self) -> None:
        self.store.write({})

    def offline_access(self, *, user_id: str, now: datetime | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        cached = self.load()
        if not cached or str(cached.get("user_id") or "") != str(user_id or ""):
            return {}, evaluate_subscription(None, now=now, online=False)
        validated_at = parse_datetime(cached.get("validated_at"))
        subscription = cached.get("subscription") if isinstance(cached.get("subscription"), dict) else {}
        access = evaluate_subscription(subscription, validated_at=validated_at, now=now, online=False)
        return dict(cached.get("workspace") or {}), access
