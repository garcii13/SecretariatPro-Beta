"""Short-lived, one-use tablet pairing and per-device local sessions."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
from typing import Any


COOKIE_NAME = "sp_tablet_session"
INVITE_SECONDS = 300
SESSION_SECONDS = 12 * 60 * 60


def is_loopback(host: str | None) -> bool:
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TabletAccess:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._invites: dict[str, tuple[float, str]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}

    def invite(self, scope: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._invites = {key: value for key, value in self._invites.items() if value[0] > time.monotonic() and value[1] == scope}
            if len(self._invites) >= 32:
                self._invites.pop(next(iter(self._invites)))
            self._invites[_digest(token)] = (time.monotonic() + INVITE_SECONDS, scope)
        return token

    def pair(self, token: str, scope: str) -> tuple[str, str]:
        with self._lock:
            invite = self._invites.get(_digest(token))
            if not invite or time.monotonic() > invite[0] or invite[1] != scope:
                raise PermissionError("El código de emparejamiento ha caducado")
            self._invites.pop(_digest(token), None)
            session_token = secrets.token_urlsafe(32)
            session_id = secrets.token_hex(8)
            self._sessions[session_id] = {
                "hash": _digest(session_token), "scope": scope,
                "expires": time.monotonic() + SESSION_SECONDS,
                "paired_at": time.time(), "last_seen": time.time(),
            }
            return session_id, session_token

    def authenticate(self, token: str | None, scope: str) -> str | None:
        if not token:
            return None
        digest = _digest(token)
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                if time.monotonic() > session["expires"]:
                    self._sessions.pop(session_id, None)
                    continue
                if session["scope"] == scope and hmac.compare_digest(session["hash"], digest):
                    session["last_seen"] = time.time()
                    return session_id
        return None

    def sessions(self, scope: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"id": key, "paired_at": value["paired_at"], "last_seen": value["last_seen"]}
                for key, value in self._sessions.items()
                if value["scope"] == scope and time.monotonic() < value["expires"]
            ]

    def revoke(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def revoke_all(self) -> None:
        with self._lock:
            self._invites.clear()
            self._sessions.clear()
