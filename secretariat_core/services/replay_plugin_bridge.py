"""Local bridge between SecretariatPro and the native OBS multicamera replay plugin."""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import threading
from pathlib import Path
from typing import Any, Callable


class ReplayPluginBridge:
    """Control plugin hotkeys and read the atomic state file written by OBS."""

    HOTKEYS = {
        "toggle": "secretariatpro_replay_toggle_buffer",
        "mark": "secretariatpro_replay_mark",
        "take": "secretariatpro_replay_take",
        "out": "secretariatpro_replay_out",
        "next_camera": "secretariatpro_replay_next_camera",
        "previous_camera": "secretariatpro_replay_previous_camera",
    }

    def __init__(self, obs_controller: Any, status_path: str | Path | None = None) -> None:
        self._command_lock = threading.RLock()
        self.obs = obs_controller
        self._explicit_path = Path(status_path).expanduser() if status_path else None

    @staticmethod
    def candidate_paths() -> list[Path]:
        override = os.getenv("SECRETARIATPRO_REPLAY_BRIDGE", "").strip()
        candidates: list[Path] = []
        if override:
            candidates.append(Path(override).expanduser())
        home = Path.home()
        plugin_dir = Path("obs-studio") / "plugin_config" / "secretariatpro-multicam-replay"
        if sys.platform == "darwin":
            candidates.append(home / "Library" / "Application Support" / plugin_dir)
        elif os.name == "nt":
            appdata = os.getenv("APPDATA", "").strip()
            if appdata:
                candidates.append(Path(appdata) / plugin_dir)
        else:
            config_home = Path(os.getenv("XDG_CONFIG_HOME", home / ".config"))
            candidates.append(config_home / plugin_dir)
        return [path / "secretariatpro-bridge.json" for path in candidates]

    @property
    def status_path(self) -> Path:
        if self._explicit_path is not None:
            return self._explicit_path
        candidates = self.candidate_paths()
        existing = next((path for path in candidates if path.is_file()), None)
        return existing or candidates[0]

    def status(self) -> dict[str, Any]:
        path = self.status_path
        base: dict[str, Any] = {
            "available": False,
            "backend": "multicam-plugin",
            "active": False,
            "buffers_active": False,
            "saving": False,
            "event_ready": False,
            "playing": False,
            "camera_count": 0,
            "active_camera": 0,
            "event_serial": 0,
            "saved_paths": [],
            "timeline": [],
            "last_command_id": "",
            "status": "",
            "error": "",
            "bridge_path": str(path),
        }
        if not path.is_file():
            return base
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("estado no válido")
        except Exception as exc:
            base["error"] = f"No se pudo leer el estado del plugin: {exc}"
            return base
        base.update(data)
        base["available"] = bool(data.get("loaded", False)) and bool(self.obs and self.obs.connected)
        if int(data.get("schema") or 1) >= 2:
            base["available"] = base["available"] and time.time() * 1000 - float(data.get("updated_at_unix_ms") or 0) < 5000
        base["active"] = bool(data.get("buffers_active", False))
        base["bridge_path"] = str(path)
        paths = data.get("saved_paths")
        base["saved_paths"] = paths if isinstance(paths, list) else []
        return base

    def _trigger(self, action: str) -> None:
        if action not in self.HOTKEYS:
            raise ValueError(f"Acción de replay desconocida: {action}")
        if self.obs is None or not self.obs.connected:
            raise RuntimeError("Conecta OBS antes de controlar el plugin de replay")
        self.obs.trigger_hotkey_by_name(self.HOTKEYS[action])

    def _wait_for(self, predicate: Callable[[dict[str, Any]], bool], timeout: float, *, ignore_previous_error: bool = False) -> dict[str, Any]:
        deadline = time.monotonic() + max(0.5, float(timeout))
        latest = self.status()
        while time.monotonic() < deadline:
            if predicate(latest):
                return latest
            if latest.get("error") and not ignore_previous_error:
                raise RuntimeError(str(latest["error"]))
            time.sleep(0.15)
            latest = self.status()
        if predicate(latest):
            return latest
        raise RuntimeError("El plugin de replay no confirmó la operación a tiempo")

    def set_buffers_active(self, active: bool, timeout: float = 5.0) -> dict[str, Any]:
        current = self.status()
        if not current.get("available"):
            raise RuntimeError("El plugin SecretariatPro Multicam Replay no está cargado en OBS")
        if bool(current.get("buffers_active")) == bool(active):
            return current
        self._trigger("toggle")
        return self._wait_for(lambda state: bool(state.get("buffers_active")) == bool(active), timeout)

    def mark(self, timeout: float = 30.0) -> dict[str, Any]:
        current = self.status()
        if not current.get("available"):
            raise RuntimeError("El plugin SecretariatPro Multicam Replay no está cargado en OBS")
        if not current.get("buffers_active"):
            raise RuntimeError("Activa primero el búfer multicámara")
        if current.get("saving") or current.get("playing") or current.get("returning_live"):
            raise RuntimeError("El plugin aún está guardando o emitiendo el evento anterior")
        previous_serial = int(current.get("event_serial") or 0)
        self._trigger("mark")

        def ready(state: dict[str, Any]) -> bool:
            return (
                int(state.get("event_serial") or 0) > previous_serial
                and bool(state.get("event_ready"))
                and bool(state.get("saved_paths"))
            )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            latest = self.status()
            if ready(latest):
                return latest
            if int(latest.get("event_serial") or 0) > previous_serial and latest.get("error"):
                raise RuntimeError(str(latest["error"]))
            time.sleep(.1)
        raise RuntimeError("La captura no terminó; revisa las cámaras y el estado del búfer")

    def take(self) -> dict[str, Any]:
        self._trigger("take")
        return self._wait_for(lambda state: bool(state.get("playing")), 5.0)

    def out(self) -> dict[str, Any]:
        self._trigger("out")
        return self._wait_for(lambda state: not bool(state.get("playing")), 5.0)

    def switch_camera(self, direction: str) -> dict[str, Any]:
        action = "previous_camera" if direction == "previous" else "next_camera"
        before = int(self.status().get("active_camera") or 0)
        self._trigger(action)
        return self._wait_for(
            lambda state: int(state.get("active_camera") or 0) != before,
            3.0,
        )

    def _compose(self, segments: list[dict[str, Any]], *, play_now: bool = False, timeout: float = 6.0) -> dict[str, Any]:
        """Send an atomic multicamera timeline to plugin 0.5+ through its local bridge."""
        status = self.status()
        if not status.get("available"):
            raise RuntimeError("El plugin SecretariatPro Multicam Replay no está cargado en OBS")
        if not status.get("event_ready"):
            raise RuntimeError("Espera a que el plugin termine de guardar todas las cámaras")
        command_id = uuid.uuid4().hex
        command_path = self.status_path.with_name("secretariatpro-command.json")
        command_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "command_id": command_id,
            "action": "compose" if segments else "clear_timeline",
            "segments": segments,
            "play_now": bool(play_now),
        }
        temporary = command_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(command_path)
        result = self._wait_for(lambda state: str(state.get("last_command_id") or "") == command_id, timeout, ignore_previous_error=True)
        if result.get("error"):
            raise RuntimeError(str(result["error"]))
        return result

    def _play_file(self, media_path: Path) -> dict[str, Any]:
        status = self.status()
        if not status.get("available") or int(status.get("schema") or 1) < 2:
            raise RuntimeError("Actualiza el plugin para lanzar vídeos de la biblioteca")
        command_id = uuid.uuid4().hex
        path = self.status_path.with_name("secretariatpro-command.json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"command_id": command_id, "action": "play_file", "path": str(media_path.resolve())}), encoding="utf-8")
        temporary.replace(path)
        result = self._wait_for(lambda s: s.get("last_command_id") == command_id, 8, ignore_previous_error=True)
        if result.get("error") or not result.get("playing"):
            raise RuntimeError(result.get("error") or "El plugin no confirmó la reproducción")
        return result

    def _cleanup(self) -> None:
        """Ask the owning plugin to release media before deleting its buffer files."""
        if not self.status().get("available"):
            return
        command_id = uuid.uuid4().hex
        path = self.status_path.with_name("secretariatpro-command.json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"command_id": command_id, "action": "cleanup"}), encoding="utf-8")
        temporary.replace(path)
        result = self._wait_for(lambda state: state.get("last_command_id") == command_id, 6, ignore_previous_error=True)
        if result.get("error"):
            raise RuntimeError(result["error"])

    def compose(self, *args, **kwargs):
        with self._command_lock:
            return self._compose(*args, **kwargs)

    def play_file(self, *args, **kwargs):
        with self._command_lock:
            return self._play_file(*args, **kwargs)

    def cleanup(self):
        with self._command_lock:
            return self._cleanup()
