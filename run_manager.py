from __future__ import annotations

import argparse
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

from manager_release import MANAGER_APPLICATION, MANAGER_RELEASE

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 8766
MAX_PORT_SCAN = 40
# Compatibilidad histórica: MANAGER_BUILD = "phase38"
MANAGER_BUILD = MANAGER_RELEASE


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def health_payload(port: int, timeout: float = 0.35) -> dict | None:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None


def wait_for_manager(port: int, timeout: float = 20.0, backend: "ManagerBackend | None" = None) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if backend is not None and not backend.thread.is_alive():
            return False
        payload = health_payload(port)
        if payload and payload.get("application") == MANAGER_APPLICATION and (payload.get("release") or payload.get("build")) == MANAGER_BUILD:
            return True
        time.sleep(0.12)
    return False


def choose_manager_port(requested_port: int) -> int:
    """Always start this build on its own free port.

    Reusing an old Manager process made a newly installed version display stale
    HTML and JavaScript. A second launcher now selects the next free port rather
    than attaching to a previous backend.
    """
    for candidate in range(requested_port, requested_port + MAX_PORT_SCAN):
        if port_free(candidate):
            return candidate
    raise RuntimeError(
        f"No se encontró ningún puerto libre entre {requested_port} y "
        f"{requested_port + MAX_PORT_SCAN - 1}."
    )


class ManagerBackend:
    def __init__(self, port: int, debug: bool = False) -> None:
        config = uvicorn.Config(
            "manager_api.main:app",
            host="127.0.0.1",
            port=port,
            log_level="info" if debug else "warning",
            access_log=debug,
            reload=False,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self.server.run,
            daemon=True,
            name="SecretariatPro-Manager-API",
        )

    def start(self) -> None:
        self.thread.start()

    def stop(self, timeout: float = 6.0) -> None:
        self.server.should_exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=timeout)


def main() -> int:
    import webview

    parser = argparse.ArgumentParser(description="SecretariatPro Manager")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        port = choose_manager_port(args.port)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    backend = ManagerBackend(port, args.debug)
    backend.start()
    if not wait_for_manager(port, backend=backend):
        backend.stop()
        raise SystemExit(
            "SecretariatPro Manager no pudo iniciar su motor local. "
            "Ejecuta INICIAR_MANAGER_DEBUG.bat para ver el error detallado."
        )

    print(f"SecretariatPro Manager: http://127.0.0.1:{port}/")
    if port != args.port:
        print(f"El puerto {args.port} estaba ocupado; esta instancia utiliza el {port}.")

    icon = BASE_DIR / "assets" / "manager_icon.ico"
    window = webview.create_window(
        "SecretariatPro Manager",
        f"http://127.0.0.1:{port}/?build={MANAGER_BUILD}",
        width=1440,
        height=900,
        min_size=(360, 620),
        maximized=True,
        background_color="#090d13",
    )

    def shutdown(*_args) -> None:
        backend.stop()

    window.events.closed += shutdown
    try:
        webview.start(
            debug=args.debug,
            private_mode=False,
            icon=str(icon) if icon.exists() else None,
        )
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
