from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import tempfile
import threading
import time
from copy import deepcopy

from .json_store import JSONStore, LiveJSONStore, storage_exhausted
from .ocr_geometry import default_perspective, normalize_perspective


def default_ocr_config() -> dict[str, Any]:
    return {
        "source_type": "window",
        "source_id": "",
        "source_label": "",
        "window_title": "",
        "poll_ms": 700,
        "regions": {"team1_score": None, "team2_score": None, "time": None},
        "perspective": default_perspective(),
        "model": {
            "model_name": "en_PP-OCRv4_mobile_rec",
            "model_dir": "",
            "min_confidence": 0.25,
        },
    }


class OCRConfigStore:
    def __init__(self, path: str | Path) -> None:
        self._store = JSONStore(path)

    def load(self) -> dict[str, Any]:
        config = self._store.read(default_ocr_config())
        if not isinstance(config, dict):
            config = default_ocr_config()
        config.setdefault("source_type", "window")
        if config.get("source_type") not in {"window", "camera"}:
            config["source_type"] = "window"
        config.setdefault("source_id", "")
        config.setdefault("window_title", "")
        config.setdefault("source_label", config.get("window_title") or "")
        config.setdefault("poll_ms", 700)
        config.setdefault("regions", {})
        for key in ("team1_score", "team2_score", "time"):
            config["regions"].setdefault(key, None)
        config["perspective"] = normalize_perspective(config.get("perspective"))
        config.setdefault("model", {})
        config["model"] = {"model_name": "en_PP-OCRv4_mobile_rec", "model_dir": "", "min_confidence": 0.25}
        return config

    def save(self, config: dict[str, Any]) -> None:
        config = dict(config or {})
        config["model"] = {"model_name": "en_PP-OCRv4_mobile_rec", "model_dir": "", "min_confidence": 0.25}
        self._store.write(config)


class ScoreFileStore:
    FILES = {
        "team1_score": "Home Score.txt",
        "team2_score": "Away Score.txt",
        "time": "Time.txt",
    }

    def __init__(self, scores_dir: str | Path) -> None:
        self.scores_dir = Path(scores_dir)
        self._lock = threading.RLock()
        self._reconciliation = LiveJSONStore(self.scores_dir / "reconciliation.json")
        self._pending_readings: dict[str, str] = {}
        self.revision = 0
        self._pending_retry_at = 0.0

    @staticmethod
    def _atomic_write(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            try:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            except OSError:
                pass

    def write_readings(self, readings: dict[str, Any]) -> None:
        with self._lock:
            for key, filename in self.FILES.items():
                value = readings.get(key)
                if value in (None, ""):
                    continue
                text = str(value)
                changed = self.read(key, default="") != text
                if key in self._pending_readings or changed:
                    try:
                        self._atomic_write(self.scores_dir / filename, text)
                    except OSError as exc:
                        if not storage_exhausted(exc):
                            raise
                        self._pending_readings[key] = text
                        self._pending_retry_at = time.monotonic() + 5
                    else:
                        self._pending_readings.pop(key, None)
                    if changed:
                        self.revision += 1

    def read(self, key: str, default: str = "") -> str:
        filename = self.FILES.get(key, key)
        with self._lock:
            if key in self._pending_readings:
                value = self._pending_readings[key]
                if time.monotonic() >= self._pending_retry_at:
                    self._pending_retry_at = time.monotonic() + 5
                    # Recover all pending score files, including manual values
                    # that may not receive another write after space is freed.
                    for pending_key, pending_value in list(self._pending_readings.items()):
                        try:
                            self._atomic_write(self.scores_dir / self.FILES[pending_key], pending_value)
                        except OSError:
                            continue
                        self._pending_readings.pop(pending_key, None)
                return value
            try:
                return (self.scores_dir / filename).read_text(encoding="utf-8").strip()
            except OSError:
                return default

    def confirm_goal(self, key: str, before: int | None = None, event_id: str = "") -> int:
        """Advance graphic score only. The scoreboard TXT files remain raw OCR."""
        with self._lock:
            data = self._reconciliation.read({})
            confirmed = list(data.get("confirmed_events") or [])
            if event_id and (event_id in confirmed or (data.get("event_goals_initialized") and event_id in data.get("event_goals", {}))):
                return int(data.get(key, {}).get("internal", self.read(key, "0")) or 0)
            current = max(int(self.read(key, "0") or 0), int(data.get(key, {}).get("internal", 0)))
            target = max(current, int(before) + 1) if before is not None else current + 1
            previous = data.get(key, {})
            floor = max(target, int(previous.get("floor", 0)))
            data[key] = {"internal": target, "ocr": previous.get("ocr", current), "floor": floor, "pending": True}
            if event_id:
                data["confirmed_events"] = [*confirmed, event_id]
                data.setdefault("event_goals", {})[event_id] = key
            self._reconciliation.write(data)
            return target

    def reconcile_event_goals(self, goals: dict[str, str], *, manual: bool = False, seed: bool = False) -> None:
        """Apply each act correction once, preserving any manual/OCR score offset."""
        with self._lock:
            data = self._reconciliation.read({})
            old = data.get("event_goals", {})
            initialized = data.get("event_goals_initialized", False)
            outputs = {}
            if initialized and not seed:
                for key in ("team1_score", "team2_score"):
                    delta = list(goals.values()).count(key) - list(old.values()).count(key)
                    if delta:
                        row = data.get(key, {})
                        current = int(row.get("internal", self.read(key, "0")) or 0)
                        value = max(0, current + delta)
                        data[key] = {"internal": value, "floor": value, "ocr": row.get("ocr", self.read(key, "0")), "pending": False}
                        if manual:
                            outputs[key] = value
            data["event_goals"] = dict(goals)
            data["event_goals_initialized"] = True
            self._reconciliation.write(data)
            if outputs:
                self.write_readings(outputs)

    def write_external(self, readings: dict[str, Any]) -> None:
        with self._lock:
            data = self._reconciliation.read({})
            previous = deepcopy(data)
            output = dict(readings)
            for key in ("team1_score", "team2_score"):
                if key not in readings:
                    continue
                try:
                    external = int(readings[key])
                except (ValueError, TypeError):
                    output.pop(key, None)
                    continue
                row = data.setdefault(key, {})
                floor = int(row.get("floor", 0))
                # Keep the confirmed score floor even after acknowledgement:
                # one stale OCR frame must not roll the score back.
                value = max(external, floor)
                row.update(ocr=external, internal=value, pending=external < floor)
                # Publish the external reading unchanged to the scoreboard.
                output[key] = str(external)
            if data != previous:
                self._reconciliation.write(data)
            self.write_readings(output)

    def correct_score(self, key: str, value: int) -> None:
        with self._lock:
            data = self._reconciliation.read({})
            data[key] = {"internal": value, "floor": value, "pending": False}
            self._reconciliation.write(data)
            self.write_readings({key: value})

    def reset_reconciliation(self) -> None:
        with self._lock:
            self._reconciliation.write({})

    def reconciliation(self) -> dict[str, Any]:
        with self._lock:
            return self._reconciliation.read({})
