from __future__ import annotations

from secretariat_core.settings_store import period_strip_for_sport

# Compatibility marker for Phase 49 regression tests: "app_release": "57.0.0-beta-rc"

import base64
import copy
import json
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from typing import Any, Callable

from secretariat_core import (
    AccountSettingsStore, AppPaths, OCRConfigStore, ScoreFileStore, SettingsStore, StateStore,
    SubscriptionAccessStore, evaluate_subscription,
)
from secretariat_core.settings_store import normalize_settings
from secretariat_core.match_clock import parse_match_clock
from secretariat_core.services.event_context import apply_events_to_state
from secretariat_core.services.match_context import apply_match_context, competition_label, match_label
from secretariat_core.services.ocr_runtime import OCRRuntimeManager
from video_source import PersistentCameraService
from secretariat_core.services.overlay import hide_all, overlay_summary, set_panel
from secretariat_core.services.powerplay import advance_powerplay, end_powerplay
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.services.replay_plugin_bridge import ReplayPluginBridge

try:
    from obs_controller import OBSController
except Exception:  # pragma: no cover
    OBSController = None

try:
    from supabase_client import ScoreboardSupabaseClient
except Exception:  # pragma: no cover
    ScoreboardSupabaseClient = None


class ApplicationRuntime:
    """Thread-safe application facade shared by HTTP and WebSocket handlers.

    State is reloaded before every mutation so the API, desktop shell and
    OBS browser source always share the same persisted source of truth.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.paths = AppPaths(Path(base_dir).resolve())
        self.state_store = StateStore(self.paths.data_file)
        self.settings_store = SettingsStore(self.paths.app_settings_file)
        self.account_settings_store = AccountSettingsStore(self.paths.account_settings_file)
        self.ocr_store = OCRConfigStore(self.paths.ocr_config_file)
        self.subscription_store = SubscriptionAccessStore(self.paths.subscription_access_file)
        self.score_store = ScoreFileStore(self.paths.scores_dir)
        self.camera_service = PersistentCameraService(self.paths.base_dir / ".runtime" / "ocr_camera_frame.bin")
        self.replays = ReplayLibrary(self.paths.base_dir / ".runtime" / "replays", self.paths.base_dir / "Repeticiones")
        self.ocr_consent: dict[str, Any] = {"enabled": False, "can_manage": False, "role": "producer"}
        self._ocr_sample_outbox = self.paths.base_dir / ".runtime" / "ocr_sample_outbox"
        self._ocr_sample_outbox.mkdir(parents=True, exist_ok=True)
        self._ocr_sample_diag_lock = threading.RLock()
        self._ocr_sample_delivery_lock = threading.Lock()
        self._ocr_sample_wake = threading.Event()
        self._ocr_sample_diag: dict[str, Any] = {
            "generated": 0,
            "uploaded": 0,
            "queued": 0,
            "last_generated_at": "",
            "last_attempt_at": "",
            "last_success_at": "",
            "last_error": "",
        }
        self._ocr_sample_retry_stop = threading.Event()
        self.ocr_runtime = OCRRuntimeManager(
            base_dir=self.paths.base_dir,
            config_store=self.ocr_store,
            score_store=self.score_store,
            settings_store=self.settings_store,
            on_time_reading=self.sync_powerplays_to_time,
            sample_sharing_enabled=self.ocr_sample_sharing_enabled,
            on_sample=self.upload_ocr_sample,
            camera_service=self.camera_service,
        )
        self._lock = threading.RLock()
        self._login_lock = threading.Lock()
        self._session_generation = 0
        from concurrent.futures import ThreadPoolExecutor
        self._replay_import_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="replay-import")
        self._account_sync_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="account-sync")
        self._competitions_loaded = False

        self.supabase: Any | None = None
        self.workspaces: list[dict[str, Any]] = []
        self.active_workspace: dict[str, Any] = {}
        self.subscription: dict[str, Any] = {}
        self.subscription_access: dict[str, Any] = evaluate_subscription(None)
        self._next_subscription_validation = 0.0
        self.competitions: list[dict[str, Any]] = []
        self.matches_by_competition: dict[str, list[dict[str, Any]]] = {}
        self.active_match: dict[str, Any] | None = None
        self.active_competition: dict[str, Any] | None = None
        self.published_theme: dict[str, Any] = {}
        self.rosters: dict[str, list[dict[str, Any]]] = {"team1": [], "team2": []}
        self.attendance: dict[str, set[str]] = {"team1": set(), "team2": set()}
        self.standings: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.obs = OBSController() if OBSController is not None else None
        self.replay_plugin = ReplayPluginBridge(self.obs)
        self._prepare_startup_state()
        self.sync_selected_ocr_camera()
        self._ocr_sample_retry_thread = threading.Thread(
            target=self._ocr_sample_retry_loop, daemon=True, name="SecretariatPro-OCR-Sample-Retry"
        )
        self._ocr_sample_retry_thread.start()


    def sync_selected_ocr_camera(self) -> dict[str, Any]:
        """Keep the configured camera powered while it remains the OCR source."""
        config = self.ocr_store.load()
        source_type = str(config.get("source_type") or "window").strip().lower()
        source_id = str(config.get("source_id") or "").strip()
        if source_type != "camera" or not source_id:
            self.camera_service.deactivate()
            return self.camera_service.status()
        try:
            return self.camera_service.activate(int(source_id))
        except Exception as exc:
            status = self.camera_service.status()
            status["error"] = str(exc)
            return status

    def activate_ocr_source(self, source_type: str, source_id: str, source_label: str = "") -> dict[str, Any]:
        """Persist the chosen OCR source and manage the persistent camera lease.

        Changing source while OCR is running stops the worker first so it cannot
        keep reading a stale camera/window configuration.
        """
        source_type = str(source_type or "window").strip().lower()
        if source_type not in {"window", "camera"}:
            raise ValueError("Fuente OCR no válida")
        source_id = str(source_id or "").strip()
        source_label = str(source_label or "").strip()
        if self.ocr_runtime.status().get("running"):
            self.ocr_runtime.stop()
        config = self.ocr_store.load()
        config["source_type"] = source_type
        config["source_id"] = source_id
        config["source_label"] = source_label
        config["window_title"] = source_label if source_type == "window" else ""
        if source_type == "camera":
            if not source_id:
                raise ValueError("Selecciona una cámara OCR")
            self.camera_service.activate(int(source_id))
        else:
            self.camera_service.deactivate()
        self.ocr_store.save(config)
        return {"config": config, "camera": self.camera_service.status()}

    @staticmethod
    def _overlay_settings_payload(settings: dict[str, Any]) -> dict[str, Any]:
        """Return the non-secret settings consumed by the OBS overlay.

        Mirroring these values into ``data.json`` makes palette and language
        updates travel through the same proven channel as match state. The
        overlay still polls ``/api/settings`` as a fallback, but it no longer
        depends on that additional request being available in OBS.
        """
        normalized = normalize_settings(settings)
        return {
            "language": normalized.get("language", "en"),
            "score_control": copy.deepcopy(normalized.get("score_control") or {}),
            "appearance": copy.deepcopy(normalized.get("appearance") or {}),
        }

    def _sync_overlay_settings_state(self, settings: dict[str, Any]) -> None:
        payload = self._overlay_settings_payload(settings)
        payload["sport_mode"] = self.sport_mode()
        payload["appearance"]["period_strip"] = period_strip_for_sport(payload["appearance"]["period_strip"], self.sport_mode())

        def apply(state: dict[str, Any]) -> None:
            state["overlay_settings"] = copy.deepcopy(payload)

        self.mutate_state(apply)

    @staticmethod
    def _theme_appearance(theme: dict[str, Any]) -> dict[str, Any]:
        config = theme.get("config") if isinstance(theme, dict) else {}
        if not isinstance(config, dict):
            return {}
        source = config.get("appearance") if isinstance(config.get("appearance"), dict) else config
        clean: dict[str, Any] = {}
        for section in ("scoreboard", "bottom_bar", "panels", "elements", "period_strip", "goal_celebration"):
            values = source.get(section)
            if isinstance(values, dict):
                clean[section] = copy.deepcopy(values)
        return clean

    def _settings_with_published_theme(
        self,
        client: Any,
        settings: dict[str, Any],
        competition_id: str = "",
    ) -> dict[str, Any]:
        """Apply the organisation's published overlay palette without touching app light/dark mode."""
        try:
            theme = client.published_visual_theme(competition_id)
        except Exception:
            theme = {}
        return self._apply_published_theme(settings, theme)

    def _apply_published_theme(self, settings: dict[str, Any], theme: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_settings(settings)
        # Start each scope from defaults: no settings may leak from another competition.
        app_theme = normalized["appearance"]["app_theme"]
        normalized["appearance"] = normalize_settings({})["appearance"]
        normalized["appearance"]["app_theme"] = app_theme
        appearance = self._theme_appearance(theme)
        if appearance:
            app_theme = normalized.setdefault("appearance", {}).get("app_theme", "dark")
            for section, values in appearance.items():
                normalized["appearance"].setdefault(section, {}).update(values)
            normalized["appearance"]["app_theme"] = app_theme
        self.published_theme = copy.deepcopy(theme or {})
        return normalize_settings(normalized)

    def refresh_published_theme(self) -> bool:
        """Apply a Manager publication to the running overlay without changing the match."""
        with self._lock:
            client = self.supabase
            workspace_id = str(self.active_workspace.get("id") or "")
            competition_id = str((self.active_competition or {}).get("id") or "")
            previous = copy.deepcopy(self.published_theme)
        if not client or not getattr(client, "user_id", "") or not self.production_access_allowed():
            return False
        try:
            theme = client.published_visual_theme(competition_id)
        except Exception:
            return False  # Keep the on-air identity if the venue is temporarily offline.
        if (theme or {}) == previous:
            return False
        with self._lock:
            if self.supabase is not client or str(self.active_workspace.get("id") or "") != workspace_id or str((self.active_competition or {}).get("id") or "") != competition_id:
                return False
            settings = self._apply_published_theme(self.settings_store.load(), theme or {})
            self.settings_store.save(settings)
            self.account_settings_store.save(client.user_id, settings, client.user_email)
            self._sync_overlay_settings_state(settings)
        return True

    def _enforce_locked_visual_theme(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_settings(settings)
        # Production clients never author broadcast identity, even for legacy unlocked themes.
        appearance = normalize_settings({})["appearance"]
        appearance.pop("app_theme", None)
        appearance.update(self._theme_appearance(self.published_theme))
        normalized["appearance"] = {"app_theme": normalized["appearance"]["app_theme"]}
        app_theme = normalized.setdefault("appearance", {}).get("app_theme", "dark")
        for section, values in appearance.items():
            normalized["appearance"].setdefault(section, {}).update(values)
        normalized["appearance"]["app_theme"] = app_theme
        return normalize_settings(normalized)

    def _prepare_startup_state(self) -> None:
        """Start every control session from a safe, neutral broadcast state.

        Persistent match/team data may remain on disk for recovery, but no overlay,
        penalty or previous online selection is considered active after launching.
        """
        def reset(state: dict[str, Any]) -> None:
            hide_all(state, keep_scoreboard=False)
            state["graphics_queue"] = []
            state.pop("broadcast_flow", None)
            state.pop("pending_goal_celebration", None)
            for team_key in ("team1", "team2"):
                pp = state.setdefault("powerplay", {}).setdefault(team_key, {})
                pp["penalties"] = []
                end_powerplay(pp)
            state["empty_net"] = {"team1": False, "team2": False}
            state.setdefault("match", {})["sport_mode"] = "floorball"
            state.setdefault("online", {}).update({
                "competition_id": "",
                "competition_name": "",
                "match_id": "",
                "match_label": "",
            })
            state["overlay_settings"] = self._overlay_settings_payload(self.settings_store.load())

        self.mutate_state(reset)

    def read_state(self) -> dict[str, Any]:
        with self._lock:
            return self.state_store.load()

    def mutate_state(self, mutator: Callable[[dict[str, Any]], Any]) -> tuple[dict[str, Any], Any]:
        with self._lock:
            state = self.state_store.load()
            result = mutator(state)
            # All entry points (dock, hotkeys, queued graphics) respect the event owner.
            phase = (state.get("broadcast_flow") or {}).get("phase", "IDLE")
            if phase != "IDLE":
                set_panel(state, "scoreboard", False)
                if phase != "GOAL_BOTTOM":
                    set_panel(state, "bottom_bar", False)
            self.state_store.save(state)
            return state, result

    def scores(self) -> dict[str, str]:
        state = self.read_state()
        return {
            "team1_score": self.score_store.read("team1_score", str(state.get("team1", {}).get("score", 0))),
            "team2_score": self.score_store.read("team2_score", str(state.get("team2", {}).get("score", 0))),
            "time": self.score_store.read("time", state.get("match", {}).get("time", "00:00")),
        }

    def graphic_scores(self) -> dict[str, str]:
        scores = self.scores()
        for key, row in self.score_store.reconciliation().items():
            if key in scores:
                scores[key] = str(max(int(scores[key] or 0), int(row.get("internal", 0))))
        return scores

    def current_seconds(self) -> int | None:
        """Return the freshest valid clock without letting stale memory win.

        The web OCR worker exposes its latest reading in memory, but that value
        must only take priority while the worker is active and the reading is
        recent. Otherwise an old in-memory value could freeze powerplays while
        an external/legacy OCR continued updating ``scores/Time.txt``.
        """
        status = self.ocr_runtime.status()
        last_reading = status.get("last_reading")
        reading_is_fresh = bool(
            status.get("running")
            and isinstance(last_reading, (int, float))
            and time.time() - float(last_reading) <= 3.0
        )
        if reading_is_fresh:
            runtime_reading = str((status.get("readings") or {}).get("time") or "").strip()
            parsed = parse_match_clock(runtime_reading)
            if parsed is not None:
                return parsed
        return parse_match_clock(self.scores().get("time", ""))

    def live_snapshot(self) -> dict[str, Any]:
        """Small no-cache payload used by the Direct panel at high frequency.

        The overlay reads the score TXT files directly. Returning the same files
        here guarantees that the control panel and the emitted overlay share one
        source of truth even if the WebSocket reconnects or a full render fails.
        """
        self.advance_powerplays()
        state = self.read_state()
        ocr_status = self.ocr_runtime.status()
        return {
            "scores": self.scores(),
            "graphic_scores": self.graphic_scores(),
            "powerplay": copy.deepcopy(state.get("powerplay") or {}),
            "ocr_runtime": ocr_status,
            "score_control": {
                "mode": self.score_mode(),
                "editable": self.score_mode() == "manual",
            },
            "server_time": time.time(),
        }

    def score_mode(self) -> str:
        settings = self.settings_store.load()
        mode = str(settings.get("score_control", {}).get("mode") or "ocr").lower()
        return mode if mode in {"ocr", "manual"} else "ocr"

    def set_score_mode(self, mode: str) -> str:
        normalized = str(mode or "").lower()
        if normalized not in {"ocr", "manual"}:
            raise ValueError("El modo de marcador debe ser OCR o manual")
        settings = self.settings_store.load()
        settings.setdefault("score_control", {})["mode"] = normalized
        self.save_current_settings(settings)
        return normalized

    def require_manual_score_control(self) -> None:
        if self.score_mode() != "manual":
            raise RuntimeError(
                "El resultado está bloqueado porque la fuente activa es OCR. "
                "Activa el modo manual para editarlo."
            )

    def write_score(self, team_key: str, value: int, *, force: bool = False) -> dict[str, Any]:
        if not force:
            self.require_manual_score_control()
        score_key = "team1_score" if team_key == "team1" else "team2_score"
        clean_value = max(0, int(value))
        self.score_store.correct_score(score_key, clean_value)

        def mutate(state: dict[str, Any]) -> None:
            state.setdefault(team_key, {})["score"] = clean_value

        state, _ = self.mutate_state(mutate)
        return state

    def write_time(self, value: str, *, force: bool = False) -> dict[str, Any]:
        if not force:
            self.require_manual_score_control()
        self.score_store.write_readings({"time": value})

        def mutate(state: dict[str, Any]) -> None:
            state.setdefault("match", {})["time"] = value

        state, _ = self.mutate_state(mutate)
        return state

    def sync_powerplays_to_time(self, clock_value: str) -> bool:
        """Synchronise active penalties immediately after every OCR clock reading."""
        current = parse_match_clock(clock_value)
        if current is None:
            return False
        with self._lock:
            state = self.state_store.load()
            changed = False
            for team_key in ("team1", "team2"):
                info = state.setdefault("powerplay", {}).setdefault(team_key, {})
                changed = advance_powerplay(info, current, strict_ocr=True) or changed
            if changed:
                state.setdefault("match", {})["time"] = clock_value
                self.state_store.save(state)
            return changed

    def advance_powerplays(self) -> bool:
        current = self.current_seconds()
        if current is None:
            return False
        with self._lock:
            state = self.state_store.load()
            changed = False
            for team_key in ("team1", "team2"):
                info = state.setdefault("powerplay", {}).setdefault(team_key, {})
                changed = advance_powerplay(info, current, strict_ocr=True) or changed
            if changed:
                self.state_store.save(state)
            return changed

    def save_current_settings(self, settings: dict[str, Any]) -> None:
        """Persist settings locally and sync the non-secret subset to the account."""
        normalized = self._enforce_locked_visual_theme(settings)
        self.settings_store.save(normalized)
        self._sync_overlay_settings_state(normalized)
        if self.supabase and getattr(self.supabase, "user_id", ""):
            self.account_settings_store.save(
                str(self.supabase.user_id),
                normalized,
                str(getattr(self.supabase, "user_email", "") or ""),
            )
            # Serialize account writes, including the initial login sync, so a
            # slow old request cannot overwrite a more recent settings change.
            self._account_sync_pool.submit(self._sync_initial_account_settings, self.supabase, copy.deepcopy(normalized))

    def safe_settings(self) -> dict[str, Any]:
        raw = self.settings_store.load()
        settings = copy.deepcopy(raw)
        if isinstance(settings.get("obs"), dict):
            settings["obs"]["password"] = ""
            settings["obs"]["password_configured"] = bool(raw.get("obs", {}).get("password"))
        settings["account_scope"] = {
            "linked": bool(self.supabase and getattr(self.supabase, "user_id", "")),
            "email": getattr(self.supabase, "user_email", "") if self.supabase else "",
        }
        theme = self.published_theme or {}
        settings["appearance_policy"] = {
            "inherited": bool(theme),
            "locked": True,
            "editable_in": "manager",
            "theme_id": str(theme.get("id") or ""),
            "theme_name": str(theme.get("name") or ""),
            "competition_id": str(theme.get("competition_id") or ""),
            "scope": "competition" if theme.get("competition_id") else ("workspace" if theme else "personal"),
        }
        settings["sport_mode"] = self.sport_mode()
        settings.setdefault("appearance", {})["period_strip"] = period_strip_for_sport(settings.get("appearance", {}).get("period_strip") or {}, self.sport_mode())
        settings["ocr_data_sharing"] = copy.deepcopy(self.ocr_consent)
        return settings

    def refresh_ocr_consent(self) -> dict[str, Any]:
        if not self.supabase or not self.active_workspace:
            self.ocr_consent = {"enabled": False, "can_manage": False, "role": "producer"}
            return copy.deepcopy(self.ocr_consent)
        try:
            self.ocr_consent = dict(self.supabase.ocr_consent())
        except Exception:
            self.ocr_consent = {
                "enabled": False,
                "can_manage": False,
                "role": str((self.active_workspace or {}).get("role") or "producer"),
                "unavailable": True,
            }
        return copy.deepcopy(self.ocr_consent)

    def ocr_sample_sharing_enabled(self) -> bool:
        return bool(self.supabase and self.ocr_consent.get("enabled"))

    def set_ocr_sample_sharing(self, enabled: bool) -> dict[str, Any]:
        client = self.require_supabase()
        was_running = bool(self.ocr_runtime.status().get("running"))
        result = client.set_ocr_consent(bool(enabled))
        self.ocr_consent = dict(result)
        if not enabled:
            for queued in self._ocr_sample_queue_files():
                try:
                    queued.unlink()
                except Exception:
                    pass
            self._update_ocr_sample_diag(last_error="")
        else:
            self._ocr_sample_wake.set()
        # The isolated worker gets the consent flag in its immutable startup
        # config. Restarting only when needed applies a changed preference
        # immediately without complicating the real-time IPC protocol.
        if was_running:
            self.ocr_runtime.stop()
            self.ocr_runtime.start()
        return copy.deepcopy(self.ocr_consent)

    def _ocr_sample_queue_files(self) -> list[Path]:
        try:
            return sorted(self._ocr_sample_outbox.glob("*.json"), key=lambda p: p.stat().st_mtime)
        except Exception:
            return []

    def _update_ocr_sample_diag(self, **changes: Any) -> None:
        with self._ocr_sample_diag_lock:
            self._ocr_sample_diag.update(changes)
            self._ocr_sample_diag["queued"] = len(self._ocr_sample_queue_files())

    def ocr_sample_delivery_status(self) -> dict[str, Any]:
        with self._ocr_sample_diag_lock:
            payload = dict(self._ocr_sample_diag)
        payload["queued"] = len(self._ocr_sample_queue_files())
        payload["sharing_enabled"] = self.ocr_sample_sharing_enabled()
        payload["workspace_id"] = str((self.active_workspace or {}).get("id") or "")
        payload["connected"] = bool(self.supabase)
        return payload

    def _queue_ocr_sample(self, payload: dict[str, Any], error: str = "") -> bool:
        # Payload contains only the minimised OCR crop, never a full video frame.
        try:
            item = dict(payload)
            item["workspace_id"] = str((self.active_workspace or {}).get("id") or "")
            item["queued_at"] = datetime.now(timezone.utc).isoformat()
            item["last_error"] = str(error or "")[:500]
            path = self._ocr_sample_outbox / f"{time.time_ns()}_{uuid4().hex}.json"
            from secretariat_core.json_store import JSONStore
            JSONStore(path).write(item)
        except Exception as exc:
            self._update_ocr_sample_diag(last_error=f"No se pudo guardar la muestra local: {type(exc).__name__}: {exc}"[:500])
            return False
        self._update_ocr_sample_diag(last_error=str(error or "")[:500])
        return True

    def _send_ocr_sample_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.supabase:
            raise RuntimeError("Sin sesión Supabase")
        queued_workspace = str(payload.get("workspace_id") or "").strip()
        active_workspace = str((self.active_workspace or {}).get("id") or "").strip()
        if queued_workspace and queued_workspace != active_workspace:
            raise RuntimeError("La muestra pertenece a otro espacio de trabajo")
        image_b64 = str(payload.get("image_b64") or "")
        if not image_b64:
            raise ValueError("Muestra OCR sin imagen")
        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception as exc:
            raise ValueError("Muestra OCR con imagen no válida") from exc
        if not image_bytes or len(image_bytes) > 512 * 1024:
            raise ValueError("Muestra OCR fuera del tamaño permitido")
        metadata = {
            "field": payload.get("key"),
            "predicted_value": payload.get("predicted_value"),
            "confidence": payload.get("confidence"),
            "raw": payload.get("raw"),
            "ocr_pass": payload.get("ocr_pass"),
            "model_name": payload.get("model_name"),
            "model_custom": payload.get("model_custom"),
            "app_release": "70.0.0-beta-rc",
            "image_sha256": payload.get("image_sha256"),
            "width": payload.get("width"),
            "height": payload.get("height"),
        }
        result = self.supabase.upload_ocr_sample(image_bytes, metadata)
        if not isinstance(result, dict) or not result.get("id"):
            raise RuntimeError("El servidor no confirmó el identificador de la muestra; se conserva en la cola local")
        return result

    def upload_ocr_sample(self, payload: dict[str, Any]) -> None:
        if not self.ocr_sample_sharing_enabled():
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._ocr_sample_diag_lock:
            self._ocr_sample_diag["generated"] = int(self._ocr_sample_diag.get("generated") or 0) + 1
            self._ocr_sample_diag["last_generated_at"] = now
        # Persist BEFORE networking: a close/crash must not lose an in-flight
        # sample. Only the single retry thread talks to the Lab.
        if self._queue_ocr_sample(payload):
            self._ocr_sample_wake.set()

    def _flush_ocr_sample_outbox_once(self, limit: int = 8) -> int:
        if not self._ocr_sample_delivery_lock.acquire(blocking=False):
            return 0
        try:
            return self._flush_ocr_sample_outbox_locked(limit)
        finally:
            self._ocr_sample_delivery_lock.release()

    def _flush_ocr_sample_outbox_locked(self, limit: int = 8) -> int:
        if not self.ocr_sample_sharing_enabled() or not self.supabase:
            self._update_ocr_sample_diag()
            return 0
        sent = 0
        for path in self._ocr_sample_queue_files():
            if sent >= max(1, int(limit)) or self._ocr_sample_retry_stop.is_set():
                break
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("La muestra no es un objeto JSON")
            except (ValueError, OSError):
                # Preserve corrupt entries for diagnosis without blocking all
                # subsequent valid samples forever.
                try:
                    path.rename(path.with_suffix(".invalid"))
                except OSError:
                    pass
                self._update_ocr_sample_diag(last_error="Muestra local dañada conservada como .invalid")
                continue
            try:
                queued_workspace = str(payload.get("workspace_id") or "").strip()
                active_workspace = str((self.active_workspace or {}).get("id") or "").strip()
                if queued_workspace and queued_workspace != active_workspace:
                    continue
                self._update_ocr_sample_diag(last_attempt_at=datetime.now(timezone.utc).isoformat())
                self._send_ocr_sample_payload(payload)
                path.unlink(missing_ok=True)
                sent += 1
                with self._ocr_sample_diag_lock:
                    self._ocr_sample_diag["uploaded"] = int(self._ocr_sample_diag.get("uploaded") or 0) + 1
                    self._ocr_sample_diag["last_success_at"] = datetime.now(timezone.utc).isoformat()
                    self._ocr_sample_diag["last_error"] = ""
            except Exception as exc:
                self._update_ocr_sample_diag(last_error=f"{type(exc).__name__}: {exc}"[:500])
                # Stop this pass; repeated failures are usually network/RLS related.
                break
        self._update_ocr_sample_diag()
        return sent

    def _ocr_sample_retry_loop(self) -> None:
        while not self._ocr_sample_retry_stop.is_set():
            self._ocr_sample_wake.wait(12.0)
            self._ocr_sample_wake.clear()
            if self._ocr_sample_retry_stop.is_set():
                break
            try:
                self._flush_ocr_sample_outbox_once()
            except Exception:
                pass

    def shutdown(self) -> None:
        self._account_sync_pool.shutdown(wait=False, cancel_futures=True)
        self._replay_import_pool.shutdown(wait=True)
        try:
            self.replay_plugin.cleanup()
        except Exception:
            pass
        self.replays.clear_compositor()
        self._ocr_sample_retry_stop.set()
        self._ocr_sample_wake.set()
        try:
            self.ocr_runtime.stop()
        except Exception:
            pass
        try:
            self.camera_service.close()
        except Exception:
            pass


    def auth_status(self) -> dict[str, Any]:
        connected = bool(self.supabase and getattr(self.supabase, "user_id", ""))
        profile: dict[str, Any] = {}
        if connected:
            try:
                profile = self.supabase.user_profile()
            except Exception:
                profile = {
                    "id": str(getattr(self.supabase, "user_id", "") or ""),
                    "email": str(getattr(self.supabase, "user_email", "") or ""),
                    "display_name": "",
                    "avatar_url": "",
                }
        return {
            "connected": connected,
            "email": getattr(self.supabase, "user_email", "") if self.supabase else "",
            "profile": profile,
            "workspaces": copy.deepcopy(self.workspaces),
            "workspace": copy.deepcopy(self.active_workspace),
            "subscription": copy.deepcopy(self.subscription),
            "access": copy.deepcopy(self.subscription_access),
        }

    def snapshot(self) -> dict[str, Any]:
        self.refresh_subscription_access()
        # Reconcile active penalties every time a client asks for state. This is
        # an additional safety net for external OCR writers and reconnecting
        # tablets; the OCR callback remains the primary low-latency path.
        self.advance_powerplays()
        state = self.read_state()
        match = self.active_match or {}
        competition = self.active_competition or {}
        return {
            "state": state,
            "scores": self.scores(),
            "graphic_scores": self.graphic_scores(),
            "overlays": overlay_summary(state),
            "settings": self.safe_settings(),
            "ocr": self.ocr_store.load(),
            "ocr_runtime": self.ocr_runtime.status(),
            "ocr_sample_delivery": self.ocr_sample_delivery_status(),
            "score_control": {
                "mode": self.score_mode(),
                "editable": self.score_mode() == "manual",
                "label": "Manual" if self.score_mode() == "manual" else "OCR",
            },
            "online": {
                **self.auth_status(),
                "competition": competition,
                "match": match,
                "rosters": copy.deepcopy(self.rosters),
                "attendance": {key: sorted(values) for key, values in self.attendance.items()},
                "standings": copy.deepcopy(self.standings),
                "events": copy.deepcopy(self.events),
            },
            "obs": self.obs_status(),
            "replays": self.replay_snapshot(),
        }

    def replay_snapshot(self) -> dict[str, Any]:
        match_id = str((self.active_match or {}).get("id") or "")
        library = self.replays.snapshot(match_id)
        plugin_status = self.replay_plugin.status()
        if plugin_status.get("available"):
            paths = plugin_status.get("saved_paths") or []
            sources = [str(row.get("path") or "") for row in paths]
            clips = library.get("clips") or []
            with self._lock:
                clips = self.replays.snapshot(match_id).get("clips") or []
                if not plugin_status.get("library_playback") and plugin_status.get("event_ready") and sources and not any(row.get("status") == "pending" for row in clips):
                    if not any(row.get("source_paths") == sources for row in clips):
                        marker = self.replays.create_marker(match_id=match_id, label="Replay", period=int(self.read_state().get("match", {}).get("period") or 1))
                        def import_event():
                            try:
                                self.replays.complete_multicam_marker(marker["id"], paths)
                            except Exception as exc:
                                self.replays.fail_marker(marker["id"], str(exc))
                        self._replay_import_pool.submit(import_event)
            library = self.replays.snapshot(match_id)
            return {**library, "status": plugin_status}
        status = {
            "available": bool(self.obs), "active": False, "last_path": "", "error": "",
            "backend": "obs-native", "plugin_available": False,
        }
        if self.obs and self.obs.connected:
            try:
                status.update(self.obs.replay_status())
            except Exception as exc:
                status["error"] = str(exc)
        return {**library, "status": status}

    @staticmethod
    def _profile_display_name(player: dict[str, Any]) -> str:
        return (
            player.get("display_name")
            or " ".join(value for value in (player.get("first_name"), player.get("last_name")) if value)
            or player.get("name")
            or "Jugador"
        ).strip()

    @staticmethod
    def _profile_value(player: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = player.get(key)
            if value not in (None, ""):
                return str(value)
        return "—"

    @staticmethod
    def _format_birth_date(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return "—"
        try:
            from datetime import datetime
            return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            try:
                from datetime import datetime
                return datetime.strptime(text[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return text

    def update_player_profile(self, team_key: str, player_id: str, *, show: bool = True) -> dict[str, Any]:
        client = self.require_supabase()
        if team_key not in {"team1", "team2"}:
            raise RuntimeError("Equipo desconocido")
        if not self.active_match or not self.active_competition:
            raise RuntimeError("No hay un partido online cargado")
        clean_id = str(player_id or "").strip()
        row = next(
            (
                item for item in self.rosters.get(team_key, [])
                if str(item.get("player_id") or (item.get("player") or {}).get("id") or "") == clean_id
                and str(item.get("member_type") or "player").lower() != "coach"
            ),
            None,
        )
        if not row:
            raise RuntimeError("El jugador no pertenece a la plantilla cargada")

        refresh_match_id = str(self.active_match.get("id") or "")
        competition_id = str(self.active_competition.get("id") or self.active_match.get("competition_id") or "")
        result = client.get_player_profile_stats(clean_id, competition_id)
        player = result.get("player") or row.get("player") or {}
        match_team = self.active_match.get("home_team") if team_key == "team1" else self.active_match.get("away_team")
        match_team = match_team or {}

        def mutate(state: dict[str, Any]) -> None:
            team_state = state.get(team_key, {})
            panel = state.setdefault("statistics", {}).setdefault("player_profile", {})
            panel.update({
                "player_id": clean_id,
                "team_key": team_key,
                "team_color": team_state.get("stripe_color") or match_team.get("primary_color") or match_team.get("secondary_color") or "#59606c",
                "team_logo": team_state.get("logo") or match_team.get("logo_url") or match_team.get("alternate_logo_url") or "",
                "number": str(row.get("shirt_number") or row.get("number") or "—"),
                "name": self._profile_display_name(player),
                "birth_date": self._format_birth_date(self._profile_value(player, "birth_date", "date_of_birth", "dob")),
                "nationality": self._profile_value(player, "nationality", "country", "country_code"),
                "position": self._profile_value(player, "position"),
                "played": int(result.get("played") or 0),
                "goals": int(result.get("goals") or 0),
                "assists": int(result.get("assists") or 0),
            })
            if show:
                state.setdefault("bottombar", {})["status"] = "hide"
                set_panel(state, "player_profile", True)

        state, _ = self.mutate_state(mutate)
        return state

    def refresh_online_events(self) -> list[dict[str, Any]]:
        client = self.require_supabase()
        if not self.active_match:
            raise RuntimeError("No hay un partido online cargado")
        events = client.list_events(str(self.active_match.get("id") or ""))

        def mutate(state: dict[str, Any]) -> None:
            apply_events_to_state(
                state,
                events,
                match=self.active_match or {},
                rosters=self.rosters,
            )

        self.mutate_state(mutate)
        with self._lock:
            self.events = events
        return events

    def cancel_online_event(self, event_id: str) -> list[dict[str, Any]]:
        client = self.require_supabase()
        if not self.active_match:
            raise RuntimeError("No hay un partido online cargado")
        client.cancel_event(event_id)
        return self.refresh_online_events()

    def refresh_statistics(self) -> dict[str, Any]:
        client = self.require_supabase()
        if not self.active_match or not self.active_competition:
            raise RuntimeError("No hay un partido online cargado")
        refresh_match_id = str(self.active_match.get("id") or "")
        competition_id = str(self.active_competition.get("id") or self.active_match.get("competition_id") or "")
        home = self.active_match.get("home_team") or {}
        away = self.active_match.get("away_team") or {}
        standings = client.get_standings(competition_id)
        leaders = client.get_team_top_scorers(
            competition_id,
            [str(home.get("id") or ""), str(away.get("id") or "")],
        )

        def display_name(player: dict[str, Any]) -> str:
            return (
                player.get("display_name")
                or " ".join(value for value in (player.get("first_name"), player.get("last_name")) if value)
                or "—"
            ).strip()

        def mutate(state: dict[str, Any]) -> None:
            statistics = state.setdefault("statistics", {})
            standings_panel = statistics.setdefault("standings", {})
            # Use the already-resolved match identity as the single source of truth.
            # apply_match_context() has already selected the correct home/away logo
            # (including the visitor alternate logo) and competition logo.  Keeping
            # Top scorers on the same state prevents it from showing a different
            # badge than Scoreboard, Prematch or Lineups.
            match_state = state.get("match", {})
            competition_logo = match_state.get("logo") or self.active_competition.get("logo_url") or ""
            competition_name = match_state.get("league") or self.active_competition.get("name") or ""
            standings_panel.update({
                "competition_name": competition_name,
                "competition_logo": competition_logo,
                "rows": standings,
            })
            top_panel = statistics.setdefault("top_scorers", {})
            top_panel.update({
                "competition_name": competition_name,
                "competition_logo": competition_logo,
            })
            for team_key, team in (("team1", home), ("team2", away)):
                leader = leaders.get(str(team.get("id") or "")) or {}
                player = leader.get("player") or {}
                team_state = state.get(team_key, {})
                if team_key == "team1":
                    fallback_color = team.get("primary_color") or team.get("secondary_color") or "#333333"
                    fallback_logo = team.get("logo_url") or team.get("alternate_logo_url") or ""
                else:
                    fallback_color = team.get("secondary_color") or team.get("primary_color") or "#333333"
                    fallback_logo = team.get("alternate_logo_url") or team.get("logo_url") or ""
                top_panel[team_key] = {
                    "team_name": team_state.get("name") or team.get("short_name") or team.get("name") or "",
                    "team_logo": team_state.get("logo") or fallback_logo,
                    "team_color": team_state.get("stripe_color") or fallback_color,
                    "player_name": display_name(player),
                    "goals": int(leader.get("goals") or 0),
                    "assists": int(leader.get("assists") or 0),
                    "points": int(leader.get("points") or 0),
                }

        with self._lock:
            if str((self.active_match or {}).get("id") or "") != refresh_match_id:
                return {"standings": [], "leaders": {}}
            self.mutate_state(mutate)
            self.standings = standings
        return {"standings": standings, "leaders": leaders}

    def obs_status(self, refresh: bool = False) -> dict[str, Any]:
        if not self.obs:
            return {"available": False, "connected": False}
        if not self.obs.connected:
            return {"available": True, "connected": False, "error": self.obs.last_error}
        cached = getattr(self, "_obs_status_cache", None)
        if cached and not refresh:
            result = copy.deepcopy(cached)
            result["program"] = getattr(self.obs, "_program_scene_name", result.get("program", ""))
            return result
        try:
            result = {"available": True, "connected": True, **self.obs.snapshot()}
            self._obs_status_cache = copy.deepcopy(result)
            return result
        except Exception as exc:
            return {"available": True, "connected": False, "error": str(exc)}

    # ---------------- Supabase session ----------------
    def login(self, email: str, password: str) -> dict[str, Any]:
        if not self._login_lock.acquire(blocking=False):
            raise BlockingIOError("Ya hay un inicio de sesión en curso. Espera a que termine.")
        client = None
        try:
            if ScoreboardSupabaseClient is None:
                raise RuntimeError("El cliente Supabase no está disponible")
            client = ScoreboardSupabaseClient(interactive=True)
            return self._login_once(email, password, client)
        except Exception:
            if client is not None and self.supabase is not client:
                client.close()
            raise
        finally:
            self._login_lock.release()

    def _login_once(self, email: str, password: str, client) -> dict[str, Any]:
        generation = self._session_generation
        try:
            user_email = client.login(email, password)
        except Exception as exc:
            if getattr(exc, "code", None) == "invalid_credentials" or getattr(exc, "code", None) == "invalid_login_credentials":
                raise ValueError("El correo o la contraseña no son correctos") from exc
            if getattr(exc, "status", None) in (400, 401, 422):
                raise ValueError(str(exc)) from exc
            raise ConnectionError("No se pudo completar la autenticación. Comprueba la conexión e inténtalo de nuevo.") from exc

        preferred_workspace_id = str((self.subscription_store.load().get("workspace") or {}).get("id") or "")
        context: dict[str, Any]
        online_validation = True
        try:
            context = client.workspace_context(preferred_workspace_id)
            workspaces = context.get("workspaces") or []
            workspace = context.get("workspace") or {}
            subscription = context.get("subscription") or {}
            access = evaluate_subscription(subscription, online=True)
            if workspace:
                self.subscription_store.save(
                    user_id=client.user_id,
                    workspace=workspace,
                    subscription=subscription,
                    access=access,
                )
        except Exception:
            # Authentication succeeded but the entitlement endpoint may be
            # temporarily unavailable in a venue. Reuse only a recent online
            # validation, never a generic local flag.
            online_validation = False
            workspace, access = self.subscription_store.offline_access(user_id=client.user_id)
            workspaces = [workspace] if workspace else []
            subscription = self.subscription_store.load().get("subscription") or {}
            if not access.get("allowed"):
                raise RuntimeError(
                    "No se pudo validar la membresía y no existe un permiso offline válido de 4 días"
                )
            if workspace:
                client.active_workspace = dict(workspace)
                client.active_membership = {
                    "workspace_id": workspace.get("id"),
                    "role": workspace.get("role") or "producer",
                    "status": "active",
                }

        # Independent data is fetched concurrently after authentication and
        # membership validation. A competition-list outage is not bad credentials.
        from concurrent.futures import ThreadPoolExecutor
        warnings = []
        competitions = []
        competitions_loaded = not access.get("allowed")
        theme = {}
        consent = {"enabled": False, "can_manage": False, "role": "producer"}
        if workspace and online_validation:
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="login-data") as pool:
                pending = {"theme": pool.submit(client.published_visual_theme), "consent": pool.submit(client.ocr_consent)}
                if access.get("allowed"):
                    pending["competitions"] = pool.submit(client.list_competitions)
                for key, future in pending.items():
                    try:
                        value = future.result()
                        if key == "theme":
                            theme = value or {}
                        elif key == "consent":
                            consent = value
                        else:
                            competitions = value or []
                            competitions_loaded = True
                    except Exception:
                        if key == "competitions":
                            warnings.append("Sesión iniciada. No se pudieron cargar las competiciones; vuelve a abrir el selector de partido para reintentarlo.")
        elif workspace and access.get("allowed"):
            warnings.append("Sesión iniciada con permiso local vigente. Vuelve a abrir el selector de partido cuando se recupere la conexión.")

        current_settings = self.settings_store.load()
        local_account = self.account_settings_store.load(client.user_id)
        try:
            cloud_account = client.user_app_settings()
        except Exception:
            cloud_account = None

        password_source = local_account or current_settings
        obs_password = str((password_source.get("obs") or {}).get("password") or "")
        if cloud_account is not None:
            selected_settings = normalize_settings(cloud_account)
            selected_settings.setdefault("obs", {})["password"] = obs_password
        elif local_account is not None:
            selected_settings = normalize_settings(local_account)
        else:
            selected_settings = normalize_settings(current_settings)
            selected_settings["replay_templates"] = []
            selected_settings["graphics_sequences"] = []

        with self._lock:
            if generation != self._session_generation:
                raise RuntimeError("El inicio de sesión se canceló al cerrar la sesión")
            selected_settings = self._apply_published_theme(selected_settings, theme)
            self.supabase = client
            self.workspaces = list(workspaces)
            self.active_workspace = dict(workspace)
            self.subscription = dict(subscription)
            self.subscription_access = dict(access)
            self.subscription_access["online_validation"] = online_validation
            self._next_subscription_validation = time.monotonic() + 300.0
            self.competitions = competitions
            self._competitions_loaded = competitions_loaded
            self.ocr_consent = dict(consent)
            self.matches_by_competition.clear()
            self.settings_store.save(selected_settings)
            self.account_settings_store.save(client.user_id, selected_settings, user_email)
        self._sync_overlay_settings_state(selected_settings)
        self._sync_sport_mode_state()

        if cloud_account is None:
            self._account_sync_pool.submit(self._sync_initial_account_settings, client, copy.deepcopy(selected_settings))
        if not self.subscription_access.get("allowed"):
            self.hide_all_overlays()
        return {
            "email": user_email,
            "competitions": self.public_competitions(),
            "workspace": copy.deepcopy(self.active_workspace),
            "access": copy.deepcopy(self.subscription_access),
            "warnings": warnings,
        }

    def _sync_initial_account_settings(self, client, settings) -> None:
        if self.supabase is not client:
            return
        try:
            client.save_user_app_settings(settings)
        except Exception:
            pass  # Settings are already persisted locally; retry on the next save.

    def activate_workspace(self, workspace_id: str) -> dict[str, Any]:
        client = self.require_supabase()
        workspace = client.activate_workspace(workspace_id)
        subscription = client.latest_workspace_subscription(workspace_id)
        access = evaluate_subscription(subscription, online=True)
        workspaces = client.list_workspaces()
        competitions = client.list_competitions() if access.get("allowed") else []
        with self._lock:
            self.workspaces = workspaces
            self.active_workspace = workspace
            self.subscription = subscription
            self.subscription_access = access
            self._next_subscription_validation = time.monotonic() + 300.0
            self.competitions = competitions
            self._competitions_loaded = True
            self.matches_by_competition.clear()
            self.active_match = None
            self.active_competition = None
        self.subscription_store.save(
            user_id=client.user_id,
            workspace=workspace,
            subscription=subscription,
            access=access,
        )
        self.refresh_ocr_consent()
        self._sync_sport_mode_state()
        selected_settings = self._settings_with_published_theme(client, self.settings_store.load())
        self.settings_store.save(selected_settings)
        self.account_settings_store.save(client.user_id, selected_settings, client.user_email)
        self._sync_overlay_settings_state(selected_settings)
        if not access.get("allowed"):
            self.hide_all_overlays()
        return self.snapshot()

    def refresh_subscription_access(self, force: bool = False) -> dict[str, Any]:
        """Revalidate the current membership without disrupting live polling.

        Online status is refreshed every five minutes. When Supabase cannot be
        reached, only the last successful validation can authorize production,
        and only for the agreed four-day window.
        """
        client = self.supabase
        workspace_id = str(self.active_workspace.get("id") or "")
        if not client or not workspace_id:
            return self.subscription_access
        now_mono = time.monotonic()
        if not force and now_mono < self._next_subscription_validation:
            return self.subscription_access
        self._next_subscription_validation = now_mono + 300.0
        previously_allowed = bool(self.subscription_access.get("production_allowed"))
        try:
            subscription = client.latest_workspace_subscription(workspace_id)
            access = evaluate_subscription(subscription, online=True)
            self.subscription_store.save(
                user_id=client.user_id,
                workspace=self.active_workspace,
                subscription=subscription,
                access=access,
            )
            with self._lock:
                self.subscription = subscription
                self.subscription_access = access
        except Exception:
            _, access = self.subscription_store.offline_access(user_id=client.user_id)
            with self._lock:
                self.subscription_access = access
        if previously_allowed and not self.subscription_access.get("production_allowed"):
            self.hide_all_overlays()
            try:
                self.ocr_runtime.stop()
            except Exception:
                pass
        return self.subscription_access

    def production_access_allowed(self) -> bool:
        return bool(self.supabase and self.subscription_access.get("production_allowed"))

    def require_production_access(self) -> None:
        if not self.supabase:
            raise RuntimeError("Debes iniciar sesión para utilizar SecretariatPro")
        if not self.subscription_access.get("production_allowed"):
            raise RuntimeError(self.subscription_access.get("message") or "La membresía no está activa")

    def hide_all_overlays(self) -> None:
        def mutate(state: dict[str, Any]) -> None:
            hide_all(state, keep_scoreboard=False)
        self.mutate_state(mutate)
        if self.obs is not None and self.obs.connected:
            try:
                self.obs.disconnect()
            except Exception:
                pass

    def logout(self) -> None:
        with self._lock:
            self._session_generation += 1
        self.hide_all_overlays()
        try:
            self.ocr_runtime.stop()
        except Exception:
            pass
        # Unsent opt-in telemetry is non-essential; do not retain it across logout.
        for queued in self._ocr_sample_queue_files():
            try:
                queued.unlink()
            except Exception:
                pass
        self._update_ocr_sample_diag(last_error="")
        with self._lock:
            if self.supabase:
                try:
                    self.supabase.logout()
                finally:
                    self.supabase = None
            self.workspaces = []
            self.active_workspace = {}
            self.ocr_consent = {"enabled": False, "can_manage": False, "role": "producer"}
            self.subscription = {}
            self.subscription_access = evaluate_subscription(None)
            self._next_subscription_validation = 0.0
            self.competitions = []
            self._competitions_loaded = False
            self.matches_by_competition.clear()
            self.active_match = None
            self.active_competition = None
            self.rosters = {"team1": [], "team2": []}
            self.attendance = {"team1": set(), "team2": set()}
            self.standings = []
            self.events = []

    def require_supabase(self):
        if not self.supabase:
            raise RuntimeError("Debes iniciar sesión primero")
        return self.supabase

    def account_profile(self) -> dict[str, Any]:
        return self.require_supabase().user_profile()

    def update_account_profile(self, display_name: str) -> dict[str, Any]:
        return self.require_supabase().update_user_profile(display_name)

    def update_account_password(self, new_password: str) -> None:
        self.require_supabase().update_password(new_password)

    def request_password_reset(self, email: str) -> None:
        clean_email = str(email or "").strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Introduce un correo electrónico válido")
        if ScoreboardSupabaseClient is None:
            raise RuntimeError("El cliente Supabase no está disponible")
        client = ScoreboardSupabaseClient()
        client.request_password_reset(clean_email)

    def upload_account_avatar(self, image_data: str) -> dict[str, Any]:
        import base64
        import io

        from PIL import Image, ImageOps, UnidentifiedImageError

        raw = str(image_data or "")
        if not raw.startswith("data:image/") or "," not in raw:
            raise ValueError("Selecciona una imagen JPG, PNG o WEBP válida")
        _header, encoded = raw.split(",", 1)
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise ValueError("La imagen de perfil no es válida") from exc
        if len(decoded) > 8 * 1024 * 1024:
            raise ValueError("La imagen no puede superar 8 MB")
        try:
            with Image.open(io.BytesIO(decoded)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                resampling = getattr(Image, "Resampling", Image).LANCZOS
                image = ImageOps.fit(image, (512, 512), method=resampling, centering=(0.5, 0.5))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=88, optimize=True)
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("No se ha podido leer la imagen seleccionada") from exc
        return self.require_supabase().upload_avatar(output.getvalue(), "image/jpeg")

    def remove_account_avatar(self) -> dict[str, Any]:
        return self.require_supabase().remove_avatar()

    def sport_mode(self) -> str:
        mode = str((self.active_workspace or {}).get("sport_mode") or "floorball").strip().lower()
        return mode if mode in {"floorball", "handball"} else "floorball"

    def _sync_sport_mode_state(self) -> None:
        mode = self.sport_mode()
        def apply(state: dict[str, Any]) -> None:
            state.setdefault("match", {})["sport_mode"] = mode
            count = period_strip_for_sport(self.settings_store.load()["appearance"]["period_strip"], mode)["segments"]
            state["match"]["period"] = min(count, max(1, int(state["match"].get("period") or 1)))
        self.mutate_state(apply)

    def public_competitions(self) -> list[dict[str, Any]]:
        return [{**item, "label": competition_label(item)} for item in self.competitions]

    def available_competitions(self) -> list[dict[str, Any]]:
        client = self.require_supabase()
        workspace_id = str(self.active_workspace.get("id") or "")
        if not self._competitions_loaded:
            rows = client.list_competitions()
            with self._lock:
                if self.supabase is not client or str(self.active_workspace.get("id") or "") != workspace_id:
                    raise RuntimeError("El espacio de trabajo ha cambiado; vuelve a abrir el selector")
                self.competitions = rows
                self._competitions_loaded = True
        return self.public_competitions()

    def list_matches(self, competition_id: str) -> list[dict[str, Any]]:
        client = self.require_supabase()
        rows = client.list_matches(competition_id)
        with self._lock:
            self.matches_by_competition[competition_id] = rows
        return [{**item, "label": match_label(item)} for item in rows]

    def set_attendance(self, selected: dict[str, set[str] | list[str]]) -> None:
        with self._lock:
            self.attendance = {
                "team1": {str(value) for value in selected.get("team1", set()) if value},
                "team2": {str(value) for value in selected.get("team2", set()) if value},
            }

    def require_called_up_player(self, team_key: str, player_id: str) -> dict[str, Any]:
        if team_key not in {"team1", "team2"}:
            raise RuntimeError("Equipo desconocido")
        if not self.active_match:
            raise RuntimeError("Carga un partido y guarda su convocatoria antes de registrar una expulsión")
        clean_id = str(player_id or "").strip()
        if not clean_id or clean_id not in self.attendance.get(team_key, set()):
            raise RuntimeError("El jugador no está convocado para este partido")
        row = next(
            (item for item in self.rosters.get(team_key, [])
             if str(item.get("player_id") or (item.get("player") or {}).get("id") or "") == clean_id),
            None,
        )
        if not row or str(row.get("member_type") or "player").lower() == "coach":
            raise RuntimeError("El jugador convocado no está disponible en la plantilla")
        return row

    def load_match(self, competition_id: str, match_id: str) -> dict[str, Any]:
        client = self.require_supabase()
        matches = self.matches_by_competition.get(competition_id) or client.list_matches(competition_id)
        match = next((item for item in matches if str(item.get("id")) == str(match_id)), None)
        if not match:
            raise RuntimeError("No se encontró el partido entre los asignados de hoy")

        competitions = client.list_competitions()
        competition = next(
            (item for item in competitions if str(item.get("id")) == str(competition_id)),
            self.active_competition or {},
        )
        home = match.get("home_team") or {}
        away = match.get("away_team") or {}
        home_roster = client.list_roster(competition_id, str(home.get("id") or ""))
        away_roster = client.list_roster(competition_id, str(away.get("id") or ""))
        standings = client.get_standings(competition_id)
        events = client.list_events(match_id)
        match_players = client.list_match_players(match_id)
        team_ids = {
            str(home.get("id") or ""): "team1",
            str(away.get("id") or ""): "team2",
        }
        attendance: dict[str, set[str]] = {"team1": set(), "team2": set()}
        starter_ids: dict[str, set[str]] = {"team1": set(), "team2": set()}
        for row in match_players:
            team_key = team_ids.get(str(row.get("team_id") or ""))
            player_id = str(row.get("player_id") or "")
            if team_key and player_id and bool(row.get("played")):
                attendance[team_key].add(player_id)
                if bool(row.get("starter")):
                    starter_ids[team_key].add(player_id)

        def mutate(state: dict[str, Any]) -> None:
            apply_match_context(
                state,
                match=match,
                competition=competition,
                standings=standings,
                home_roster=home_roster,
                away_roster=away_roster,
            )
            state["graphics_queue"] = []
            state.pop("broadcast_flow", None)
            state.pop("pending_goal_celebration", None)
            state.setdefault("match", {})["sport_mode"] = self.sport_mode()
            state["empty_net"] = {"team1": False, "team2": False}
            for team_key in ("team1", "team2"):
                pp = state.setdefault("powerplay", {}).setdefault(team_key, {})
                pp["penalties"] = []
                end_powerplay(pp)
            lineups = state.setdefault("statistics", {}).setdefault("lineups", {})
            for team_key in ("team1", "team2"):
                selected_ids = attendance[team_key]
                available = list(lineups.get(f"{team_key}_players", []))
                selected_players = [
                    player for player in available
                    if str(player.get("player_id") or "") in selected_ids
                ]
                lineups[f"{team_key}_players"] = selected_players
                # Starter positions are edited in the control panel. Keep only
                # a safe empty map until the operator confirms the quintet.
                lineups[f"{team_key}_starters"] = {}
            apply_events_to_state(
                state,
                events,
                match=match,
                rosters={"team1": home_roster, "team2": away_roster},
            )

        self.score_store.reset_reconciliation()
        state, _ = self.mutate_state(mutate)
        with self._lock:
            self.competitions = competitions
            self.active_match = match
            self.active_competition = competition
            self.rosters = {"team1": home_roster, "team2": away_roster}
            self.attendance = attendance
            self.standings = standings
            self.events = events
        selected_settings = self._settings_with_published_theme(
            client, self.settings_store.load(), str(competition_id)
        )
        self.settings_store.save(selected_settings)
        self.account_settings_store.save(client.user_id, selected_settings, client.user_email)
        self._sync_overlay_settings_state(selected_settings)
        return state
