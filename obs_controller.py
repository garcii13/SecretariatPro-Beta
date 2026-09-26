from __future__ import annotations

import base64
import ipaddress
import re
import threading
from typing import Any
from urllib.parse import urlsplit

try:
    import obsws_python as obs
    OBSWS_AVAILABLE = True
    OBSWS_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover
    obs = None
    OBSWS_AVAILABLE = False
    OBSWS_IMPORT_ERROR = str(exc)


def normalize_obs_endpoint(host_value: str, port_value: int | str = 4455) -> tuple[str, int]:
    """Normalize localhost, IPv4, host:port, ws:// URLs and IPv6 for obsws-python.

    obsws-python ultimately builds a WebSocket URL. Raw IPv6 addresses must be
    enclosed in square brackets or urllib can mistake part of the address for
    the port (for example: ``Port could not be cast ...``).
    """
    raw = str(host_value or "").strip()
    try:
        port = int(str(port_value or 4455).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("El puerto OBS debe ser un número entre 1 y 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("El puerto OBS debe estar entre 1 y 65535")

    if not raw:
        return "127.0.0.1", port

    # Accept full WebSocket URLs and HTTP-like URLs pasted by the user.
    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.hostname:
            raw = parsed.hostname
        if parsed.port is not None:
            port = parsed.port
    else:
        # Bracketed IPv6, optionally followed by :port.
        bracketed = re.fullmatch(r"\[([^\]]+)\](?::(\d+))?", raw)
        if bracketed:
            raw = bracketed.group(1)
            if bracketed.group(2):
                port = int(bracketed.group(2))
        # Plain hostname/IPv4 followed by :port. Do not use this branch for raw IPv6.
        elif raw.count(":") == 1:
            possible_host, possible_port = raw.rsplit(":", 1)
            if possible_port.isdigit():
                raw = possible_host.strip()
                port = int(possible_port)

    raw = raw.strip().strip("[]")
    if not raw:
        raise ValueError("La dirección de OBS está vacía")
    if not 1 <= port <= 65535:
        raise ValueError("El puerto OBS debe estar entre 1 y 65535")

    # Bracket valid IPv6 addresses so urllib/websocket-client parses them correctly.
    # Zone identifiers such as fe80::1%12 are supported by validating the address
    # part before the percent sign.
    address_part = raw.split("%", 1)[0]
    try:
        if isinstance(ipaddress.ip_address(address_part), ipaddress.IPv6Address):
            raw = f"[{raw}]"
    except ValueError:
        # Hostnames remain unchanged. A string with several colons is almost
        # certainly malformed IPv6, so fail early with a useful message.
        if raw.count(":") > 1:
            raise ValueError(
                "La dirección IPv6 de OBS no es válida. Usa, por ejemplo, "
                "[2001:db8::1] y deja 4455 en el campo Puerto."
            )

    return raw, port


class OBSController:
    """Small thread-safe wrapper around obs-websocket v5."""

    def __init__(self) -> None:
        self._client = None
        self._preview = None
        self._preview_lock = threading.RLock()
        self._password = ""
        self._lock = threading.RLock()
        self.connected = False
        self.last_error = ""
        self.host = "127.0.0.1"
        self.port = 4455
        self._program_scene_name = ""

    def connect(self, host: str, port: int, password: str, timeout: float = 3.0) -> dict[str, Any]:
        if not OBSWS_AVAILABLE:
            raise RuntimeError(f"obsws-python no está instalado: {OBSWS_IMPORT_ERROR or ''}")
        with self._lock:
            self.disconnect()
            self.host, self.port = normalize_obs_endpoint(host, port)
            try:
                self._client = obs.ReqClient(
                    host=self.host,
                    port=self.port,
                    password=password or "",
                    timeout=timeout,
                )
                version = self._client.get_version()
            except Exception as exc:
                self._client = None
                self.connected = False
                text = str(exc)
                self.last_error = text
                lowered = text.lower()
                if "identify client" in lowered or "authentication" in lowered or "authentication failed" in lowered:
                    raise RuntimeError(
                        "OBS rechazó la identificación. Comprueba que el servidor WebSocket está activado, "
                        "que la contraseña coincide exactamente y que el puerto es el configurado en OBS."
                    ) from exc
                if "port could not be cast" in lowered:
                    raise RuntimeError(
                        "La dirección de OBS tiene un formato incorrecto. Para IPv6 usa corchetes, "
                        "por ejemplo [2001:db8::1], y escribe 4455 en el campo Puerto."
                    ) from exc
                raise RuntimeError(f"No se pudo conectar con OBS: {text}") from exc

            self._password = password or ""
            self.connected = True
            self.last_error = ""
            self._program_scene_name = ""
            return {
                "obs_version": getattr(version, "obs_version", ""),
                "websocket_version": getattr(version, "obs_web_socket_version", ""),
                "host": self.host,
                "port": self.port,
            }

    def disconnect(self) -> None:
        with self._lock:
            with self._preview_lock:
                if self._preview is not None:
                    self._preview.disconnect()
                    self._preview = None
            self._password = ""
            client = self._client
            self._client = None
            self.connected = False
            self.last_error = ""
            self._program_scene_name = ""
            if client is not None:
                try:
                    client.disconnect()
                except Exception:
                    pass

    def _mark_connection_lost(self, client, exc: Exception) -> None:
        """Atomically invalidate a socket that OBS has already closed."""
        self._client = None
        self.connected = False
        self.last_error = str(exc) or type(exc).__name__
        try:
            client.disconnect()
        except Exception:
            pass

    def _require(self):
        if not self.connected or self._client is None:
            raise RuntimeError("OBS no está conectado")
        return self._client

    def _studio_mode_enabled(self, client) -> bool:
        """Return OBS Studio Mode state without failing on older server/client builds."""
        try:
            response = client.get_studio_mode_enabled()
            return bool(getattr(response, "studio_mode_enabled", False))
        except Exception:
            # If the request itself is unavailable, behave conservatively and
            # avoid calling preview-only requests that can return code 506.
            return False

    def snapshot(self) -> dict[str, Any]:
        """Return only the OBS Program bus: the scene currently being emitted."""
        with self._lock:
            client = self._require()
            try:
                scenes_resp = client.get_scene_list()
                scenes = []
                for item in getattr(scenes_resp, "scenes", []) or []:
                    if isinstance(item, dict):
                        name = item.get("sceneName") or item.get("scene_name")
                    else:
                        name = getattr(item, "scene_name", None)
                    if name:
                        scenes.append(str(name))
                current_program = getattr(scenes_resp, "current_program_scene_name", "")
                self._program_scene_name = str(current_program or "")
                stream = client.get_stream_status()
                record = client.get_record_status()
                return {
                    "scenes": scenes,
                    "program": current_program,
                    "streaming": bool(getattr(stream, "output_active", False)),
                    "recording": bool(getattr(record, "output_active", False)),
                }
            except Exception as exc:
                self._mark_connection_lost(client, exc)
                raise RuntimeError(f"Se perdió la conexión WebSocket con OBS: {exc}") from exc

    def set_program_scene(self, scene_name: str) -> None:
        with self._lock:
            self._require().set_current_program_scene(scene_name)
            self._program_scene_name = str(scene_name)

    def set_preview_scene(self, scene_name: str) -> None:
        with self._lock:
            client = self._require()
            if not self._studio_mode_enabled(client):
                # Without Studio Mode there is no independent preview bus.
                # Treat the action as a normal scene change instead of raising 506.
                client.set_current_program_scene(scene_name)
                return
            try:
                client.set_current_preview_scene(scene_name)
            except Exception as exc:
                if "506" in str(exc):
                    client.set_current_program_scene(scene_name)
                    return
                raise

    def toggle_stream(self) -> bool:
        with self._lock:
            client = self._require()
            active = bool(getattr(client.get_stream_status(), "output_active", False))
            (client.stop_stream if active else client.start_stream)()
            return not active

    def toggle_record(self) -> bool:
        with self._lock:
            client = self._require()
            active = bool(getattr(client.get_record_status(), "output_active", False))
            (client.stop_record if active else client.start_record)()
            return not active

    def toggle_input_mute(self, input_name: str) -> bool:
        with self._lock:
            response = self._require().toggle_input_mute(input_name)
            return bool(getattr(response, "input_muted", False))

    def input_names(self) -> list[str]:
        with self._lock:
            response = self._require().get_input_list()
            names = []
            for item in getattr(response, "inputs", []) or []:
                if isinstance(item, dict):
                    name = item.get("inputName") or item.get("input_name")
                else:
                    name = getattr(item, "input_name", None)
                if name:
                    names.append(str(name))
            return names

    def refresh_browser_source(self, input_name: str) -> None:
        with self._lock:
            client = self._require()
            client.press_input_properties_button(input_name, "refreshnocache")

    @staticmethod
    def _response_value(response: Any, *names: str) -> Any:
        if isinstance(response, dict):
            candidate = response
            nested = candidate.get("responseData") or candidate.get("response_data")
            if isinstance(nested, dict):
                candidate = nested
            for name in names:
                if name in candidate:
                    return candidate[name]
            return None
        for name in names:
            value = getattr(response, name, None)
            if value is not None:
                return value
        return None

    def screenshot(self, source_name: str, width: int = 640, image_format: str = "png") -> bytes:
        """Capture the current OBS Program scene without relying on generated method signatures.

        Different obsws-python releases expose ``get_source_screenshot`` with
        incompatible Python signatures.  The generic ``send`` API is stable and
        sends the official obs-websocket v5 request payload directly.
        """
        with self._lock:
            client = self._require()
            target_width = max(160, int(width))
            payload = {
                "sourceName": str(source_name),
                "imageFormat": str(image_format or "png"),
                "imageWidth": target_width,
            }

            try:
                response = client.send("GetSourceScreenshot", payload, raw=True)
            except TypeError:
                # Some older releases do not expose the ``raw`` keyword but do
                # support the same generic request method.
                response = client.send("GetSourceScreenshot", payload)
            except Exception as exc:
                raise RuntimeError(f"OBS no pudo capturar la escena en programa: {exc}") from exc

            # Depending on the SDK release, send() may return responseData
            # directly, a full protocol envelope, or a response object.
            data_url = ""
            if isinstance(response, dict):
                candidate = response
                nested = candidate.get("responseData") or candidate.get("response_data")
                if isinstance(nested, dict):
                    candidate = nested
                data_url = (
                    candidate.get("imageData")
                    or candidate.get("image_data")
                    or ""
                )
            else:
                data_url = (
                    getattr(response, "image_data", "")
                    or getattr(response, "imageData", "")
                    or ""
                )

            if not data_url:
                raise RuntimeError(
                    "OBS devolvió una captura vacía. Comprueba que la escena en programa "
                    "contiene una fuente visible."
                )
            if "," in data_url:
                data_url = data_url.split(",", 1)[1]
            try:
                return base64.b64decode(data_url)
            except Exception as exc:
                raise RuntimeError("OBS devolvió una captura con formato no válido") from exc

    def current_program_scene(self) -> str:
        with self._lock:
            response = self._require().send("GetCurrentProgramScene", raw=True)
            scene_name = self._response_value(
                response, "currentProgramSceneName", "current_program_scene_name"
            )
            if not scene_name:
                raise RuntimeError("OBS no ha devuelto una escena de programa")
            self._program_scene_name = str(scene_name)
            return self._program_scene_name

    def program_screenshot(self, width: int = 960, image_format: str = "jpg", refresh_scene: bool = False) -> bytes:
        """Capture only OBS Program, independently of desktop occlusion or monitors."""
        # Screenshots can take hundreds of milliseconds. They must never hold
        # the command socket/lock used by a goal mark or scene change.
        with self._preview_lock:
            if not self.connected:
                raise RuntimeError("OBS no está conectado")
            if self._preview is None or not self._preview.connected:
                preview = OBSController()
                preview.connect(self.host, self.port, self._password, timeout=1.0)
                self._preview = preview
            preview = self._preview
            scene_name = preview.current_program_scene() if refresh_scene or not self._program_scene_name else self._program_scene_name
            try:
                return preview.screenshot(str(scene_name), width=width, image_format=image_format)
            except Exception:
                preview.disconnect()
                self._preview = None
                raise

    def replay_status(self) -> dict[str, Any]:
        """Return replay-buffer state through the stable obs-websocket v5 API."""
        with self._lock:
            client = self._require()
            response = client.get_replay_buffer_status()
            active = bool(self._response_value(response, "output_active", "outputActive"))
            last_path = ""
            try:
                last = client.get_last_replay_buffer_replay()
                last_path = str(self._response_value(last, "saved_replay_path", "savedReplayPath") or "")
            except Exception:
                pass
            return {"available": True, "active": active, "last_path": last_path}

    def trigger_hotkey_by_name(self, hotkey_name: str) -> None:
        """Trigger a registered OBS frontend hotkey without requiring a key binding."""
        with self._lock:
            client = self._require()
            payload = {"hotkeyName": str(hotkey_name or "").strip()}
            if not payload["hotkeyName"]:
                raise ValueError("El nombre del atajo de OBS está vacío")
            try:
                client.send("TriggerHotkeyByName", payload, raw=True)
            except TypeError:
                client.send("TriggerHotkeyByName", payload)

    def start_replay_buffer(self) -> dict[str, Any]:
        with self._lock:
            client = self._require()
            status = client.get_replay_buffer_status()
            if not bool(self._response_value(status, "output_active", "outputActive")):
                client.start_replay_buffer()
        return self.replay_status()

    def stop_replay_buffer(self) -> dict[str, Any]:
        with self._lock:
            client = self._require()
            status = client.get_replay_buffer_status()
            if bool(self._response_value(status, "output_active", "outputActive")):
                client.stop_replay_buffer()
        return {"available": True, "active": False, "last_path": ""}

    def save_replay_buffer(self, timeout: float = 12.0) -> str:
        """Save the replay buffer and wait until OBS reports the new clip path."""
        import time

        with self._lock:
            client = self._require()
            status = client.get_replay_buffer_status()
            if not bool(self._response_value(status, "output_active", "outputActive")):
                raise RuntimeError("Activa el búfer de repetición de OBS antes de guardar clips")
            previous = ""
            try:
                last = client.get_last_replay_buffer_replay()
                previous = str(self._response_value(last, "saved_replay_path", "savedReplayPath") or "")
            except Exception:
                pass
            client.save_replay_buffer()

        deadline = time.monotonic() + max(1.0, float(timeout))
        latest = ""
        while time.monotonic() < deadline:
            time.sleep(0.2)
            with self._lock:
                response = self._require().get_last_replay_buffer_replay()
                latest = str(self._response_value(response, "saved_replay_path", "savedReplayPath") or "")
            if latest and latest != previous:
                return latest
        if latest:
            return latest
        raise RuntimeError("OBS no devolvió la ruta del clip guardado")
