from __future__ import annotations

import argparse
import socket
import webbrowser
from threading import Timer

import uvicorn


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def main() -> None:
    parser = argparse.ArgumentParser(description="SecretariatPro web control panel")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    desktop_url = f"http://127.0.0.1:{args.port}"
    tablet_url = f"http://{local_ip()}:{args.port}/tablet/"
    print("\nSecretariatPro Phase 46 · modo navegador")
    print(f"Ordenador: {desktop_url}")
    print(f"Tablet/iPad (misma red): {tablet_url}\n")
    if not args.no_browser:
        Timer(1.0, lambda: webbrowser.open(desktop_url)).start()
    uvicorn.run("secretariat_api.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
