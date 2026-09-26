from __future__ import annotations

import argparse
import html
import json
import socket
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

# Windows windowed bundles do not provide console streams. Uvicorn's
# logging formatter calls isatty(), so supply a valid sink before startup.
import os
import sys
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import uvicorn

APP_TITLE = "SecretariatPro Live"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
BASE_DIR = Path(__file__).resolve().parent
ICON_ICO = BASE_DIR / "assets" / "secretariatpro.ico"
ICON_PNG = BASE_DIR / "assets" / "secretariatpro.png"


def local_ip() -> str:
    """Best-effort LAN address used by the tablet remote."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def port_is_free(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host == "0.0.0.0" else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((bind_host, port))
        except OSError:
            return False
    return True


def health_payload(port: int, timeout: float = 0.5) -> dict | None:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None


def wait_for_server(port: int, timeout: float = 35.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = health_payload(port)
        if payload and payload.get("ok") is True:
            return True
        time.sleep(0.15)
    return False


class BackendServer:
    """Owns the local FastAPI process used by the desktop window and tablet."""

    def __init__(self, host: str, port: int, log_level: str = "warning") -> None:
        config = uvicorn.Config(
            "secretariat_api.main:app",
            host=host,
            port=port,
            log_level=log_level,
            reload=False,
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self.server.run,
            name="SecretariatPro-API",
            daemon=True,
        )

    def start(self) -> None:
        self.thread.start()

    def stop(self, timeout: float = 8.0) -> None:
        self.server.should_exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=timeout)


def error_page(title: str, message: str) -> str:
    safe_title = html.escape(title)
    safe_message = html.escape(message).replace("\n", "<br>")
    return f"""
    <!doctype html>
    <html lang="es"><head><meta charset="utf-8">
    <style>
      body{{margin:0;background:#0b0f14;color:#f5f7fa;font-family:Arial,sans-serif;
      display:grid;place-items:center;min-height:100vh}}
      main{{max-width:680px;padding:38px;border:1px solid #2b3440;border-radius:18px;
      background:#151b23;box-shadow:0 28px 80px rgba(0,0,0,.42)}}
      h1{{margin:0 0 14px;font-size:26px}} p{{color:#b7c0ca;line-height:1.55}}
    </style></head><body><main><h1>{safe_title}</h1><p>{safe_message}</p></main></body></html>
    """


def show_error(message: str) -> None:
    import webview

    webview.create_window(
        f"{APP_TITLE} · Error",
        html=error_page("No se pudo iniciar SecretariatPro Live", message),
        width=760,
        height=440,
        min_size=(620, 360),
        background_color="#0b0f14",
    )
    webview.start(debug=False, private_mode=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SecretariatPro Live desktop application")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--windowed", action="store_true", help="Open without initial maximization")
    return parser.parse_args()


def main() -> int:
    import webview

    args = parse_args()
    backend: BackendServer | None = None
    owns_backend = False

    existing = health_payload(args.port)
    if existing and existing.get("ok") is True:
        # A second launcher may attach to the already running SecretariatPro API.
        pass
    else:
        if not port_is_free(args.host, args.port):
            show_error(
                f"El puerto {args.port} ya está siendo utilizado por otra aplicación.\n"
                "Cierra esa aplicación o inicia SecretariatPro con otro puerto."
            )
            return 2
        backend = BackendServer(args.host, args.port, "info" if args.debug else "warning")
        backend.start()
        owns_backend = True
        if not wait_for_server(args.port):
            backend.stop()
            show_error(
                "El motor local no respondió a tiempo. Revisa requirements.txt y ejecuta "
                "la aplicación desde una terminal para ver el error de arranque."
            )
            return 3

    desktop_url = f"http://127.0.0.1:{args.port}/?desktop=1&native=1"
    tablet_url = f"http://{local_ip()}:{args.port}/tablet/"
    print(f"\n{APP_TITLE} · aplicación de escritorio")
    print(f"Aplicación: {desktop_url}")
    print(f"Tablet/iPad: {tablet_url}\n")

    # Native operating-system chrome is intentional. It gives Windows full
    # control of Snap Layouts, split-screen, taskbar-aware maximization,
    # resizing, restoring and multi-monitor movement.
    webview.settings["SHOW_DEFAULT_MENUS"] = False
    window = webview.create_window(
        APP_TITLE,
        desktop_url,
        width=1440,
        height=900,
        min_size=(860, 580),
        resizable=True,
        maximized=not args.windowed,
        frameless=False,
        shadow=True,
        background_color="#0b0f14",
        text_select=False,
        zoomable=False,
        confirm_close=False,
    )

    def shutdown(*_args) -> None:
        if owns_backend and backend is not None:
            backend.stop()

    window.events.closed += shutdown
    icon = str(ICON_ICO if ICON_ICO.exists() else ICON_PNG) if (ICON_ICO.exists() or ICON_PNG.exists()) else None

    try:
        webview.start(
            debug=args.debug,
            private_mode=True,
            icon=icon,
        )
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
