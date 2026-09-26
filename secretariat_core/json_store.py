from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable


class JSONStore:
    """Thread-safe JSON persistence with Windows-safe atomic replacement.

    ``os.replace`` is normally the safest way to publish a complete JSON file,
    but Windows may temporarily reject the rename when another process has the
    destination open without delete-sharing (antivirus, indexer, preview,
    second app instance, etc.). We retry the atomic path first and then fall
    back to an in-place write so a brief external lock does not take down the
    FastAPI request.
    """

    _RETRY_DELAYS = (0.01, 0.02, 0.04, 0.06, 0.08, 0.12, 0.18)

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def read(self, default: Any) -> Any:
        with self._lock:
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                return deepcopy(default)

    @staticmethod
    def _is_windows_lock(error: OSError) -> bool:
        return isinstance(error, PermissionError) or getattr(error, "winerror", None) in {5, 32, 33}

    def _make_writable(self) -> None:
        try:
            if self.path.exists():
                current = self.path.stat().st_mode
                self.path.chmod(current | stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass

    def _replace_with_retries(self, temp_name: str) -> bool:
        last_error: OSError | None = None
        for attempt, delay in enumerate((0.0, *self._RETRY_DELAYS)):
            if delay:
                time.sleep(delay)
            try:
                os.replace(temp_name, self.path)
                return True
            except OSError as error:
                last_error = error
                if not self._is_windows_lock(error):
                    raise
                if attempt == 0:
                    self._make_writable()
        if last_error is not None and not self._is_windows_lock(last_error):
            raise last_error
        return False

    def _direct_write_with_retries(self, serialized: str) -> None:
        """Fallback for destinations that Windows allows writing but not replacing."""
        self._make_writable()
        last_error: OSError | None = None
        for delay in (0.0, *self._RETRY_DELAYS):
            if delay:
                time.sleep(delay)
            try:
                with self.path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(serialized)
                    handle.flush()
                    os.fsync(handle.fileno())
                return
            except OSError as error:
                last_error = error
                if not self._is_windows_lock(error):
                    raise
        raise PermissionError(
            f"No se pudo guardar {self.path.name}: Windows mantiene el archivo bloqueado. "
            "Cierra una segunda instancia de SecretariatPro o cualquier editor que tenga el archivo abierto."
        ) from last_error

    def write(self, value: Any) -> None:
        serialized = json.dumps(value, indent=2, ensure_ascii=False)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(serialized)
                    handle.flush()
                    os.fsync(handle.fileno())
                if not self._replace_with_retries(temp_name):
                    self._direct_write_with_retries(serialized)
            finally:
                try:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
                except OSError:
                    pass

    def update(self, default: Any, mutator: Callable[[Any], None]) -> Any:
        with self._lock:
            value = self.read(default)
            mutator(value)
            self.write(value)
            return value
