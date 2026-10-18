"""Origin and Host boundary shared by the desktop APIs (including WebSocket).

No untrusted hostname is resolved. Native clients without Origin remain usable;
browser requests must come from this exact local service, including its port.
"""
from __future__ import annotations

from functools import lru_cache
import ipaddress
import hmac
from http.cookies import SimpleCookie
import secrets
import socket
import time
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


@lru_cache(maxsize=2)
def _interface_hosts(time_bucket: int) -> frozenset[str]:
    hosts = {"localhost", "127.0.0.1", "::1"}
    name = socket.gethostname().lower().rstrip(".")
    for name in (name, name.split(".", 1)[0], name if "." in name else f"{name}.local"):
        if name:
            hosts.add(name.lower().rstrip("."))
    try:
        import psutil
        for addresses in psutil.net_if_addrs().values():
            for address in addresses:
                if address.family in (socket.AF_INET, socket.AF_INET6):
                    hosts.add(address.address.split("%", 1)[0].lower())
    except (ImportError, OSError):
        pass
    return frozenset(hosts)


def _authority(value: str, scheme: str) -> tuple[str, int] | None:
    try:
        url = urlsplit(f"{scheme}://{value}")
        if url.username or url.password or url.path or url.query or url.fragment or not url.hostname:
            return None
        return url.hostname.lower().rstrip("."), url.port or (443 if scheme == "https" else 80)
    except ValueError:
        return None


def trusted_request(scope: dict) -> bool:
    headers = {key.lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
    # Duplicate security headers are ambiguous across proxies/frameworks.
    for key in (b"host", b"origin"):
        if sum(name.lower() == key for name, _ in scope.get("headers", [])) > 1:
            return False
    scheme = "https" if scope.get("scheme") in ("https", "wss") else "http"
    authority = _authority(headers.get(b"host", ""), scheme)
    if authority is None:
        return False
    host, port = authority
    allowed = set(_interface_hosts(int(time.monotonic() // 10)))
    server = scope.get("server") or ("", port)
    try:
        address = ipaddress.ip_address(server[0].split("%", 1)[0])
        if not address.is_unspecified:
            allowed.add(str(address))
    except ValueError:
        # ASGI's in-memory test server; not a wildcard for real listeners.
        if server[0] == "testserver":
            allowed.add("testserver")
    if host not in allowed or port != server[1]:
        return False
    origin = headers.get(b"origin")
    if origin is None:
        return headers.get(b"sec-fetch-site", "").lower() != "cross-site"
    try:
        url = urlsplit(origin)
        if url.scheme != scheme or url.path or url.query or url.fragment:
            return False
        return _authority(url.netloc, scheme) == authority
    except ValueError:
        return False


class LocalAccessMiddleware:
    def __init__(self, app, cookie_name="sp_live_session"):
        self.app = app
        self.cookie_name = cookie_name
        self.token = secrets.token_urlsafe(32)

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = {key.lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        try:
            local = ipaddress.ip_address((scope.get("client") or ("",))[0]).is_loopback
        except ValueError:
            local = False
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get(b"cookie", ""))
            value = cookie[self.cookie_name].value if self.cookie_name in cookie else ""
        except Exception:
            value = ""
        sensitive = scope["type"] == "websocket" or scope.get("path", "").startswith("/api/")
        # Browsers bootstrap on the local HTML response. Native clients without
        # Origin retain their existing desktop/CLI API contract.
        session_missing = local and sensitive and b"origin" in headers and not hmac.compare_digest(value, self.token)
        if not trusted_request(scope) or session_missing:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4403, "reason": "Origen no permitido"})
            else:
                await JSONResponse({"detail": "Origen o servidor no permitido"}, status_code=403)(scope, receive, send)
            return
        async def send_with_session(message):
            starting = scope["type"] == "http" and message["type"] == "http.response.start"
            html = starting and any(key.lower() == b"content-type" and value.startswith(b"text/html")
                                    for key, value in message.get("headers", []))
            cache = next((value for key, value in message.get("headers", [])
                          if key.lower() == b"cache-control"), b"")
            if html and b"no-cache" not in cache and b"no-store" not in cache:
                # A cached desktop document must not retain a previous process's cookie.
                message = {**message, "headers": [(k,v) for k,v in message.get("headers", [])
                           if k.lower() != b"cache-control"] + [(b"cache-control",b"no-store")]}
            if local and starting and scope.get("method") == "GET" and (html or scope.get("path") == "/api/health"):
                cookie = SimpleCookie()
                cookie[self.cookie_name] = self.token
                cookie[self.cookie_name]["path"] = "/"
                cookie[self.cookie_name]["httponly"] = True
                cookie[self.cookie_name]["samesite"] = "Strict"
                if scope.get("scheme") == "https":
                    cookie[self.cookie_name]["secure"] = True
                message = {**message, "headers": [*message.get("headers", []),
                    (b"set-cookie", cookie.output(header="").strip().encode("latin1"))]}
            await send(message)
        await self.app(scope, receive, send_with_session)
