"""Cliente Supabase completo para Scoreboard.

Mantiene todas las funciones de la versión de estadísticas (rosters,
convocatorias, eventos, goles, asistencias y expulsiones) y añade
clasificación automática y finalización de partidos.
"""
from __future__ import annotations

import os
import re
import hashlib
import time
import unicodedata
from copy import deepcopy
from threading import RLock

_ROSTER_IMPORT_LOCK = RLock()
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import Client, create_client
from secretariat_core.services.powerplay import penalty_values

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

APP_SETTINGS_METADATA_KEY = "secretariatpro_settings"
AVATAR_BUCKET = "avatars"
WORKSPACE_ASSETS_BUCKET = "workspace-assets"
DEFAULT_PROFILE_PORTAL_URL = "https://secretariatproapp.com/cuenta"



class SupabaseConfigurationError(RuntimeError):
    pass


class ScoreboardSupabaseClient:
    def __init__(self, env_path: Path | str | None = None, *, interactive: bool = False) -> None:
        self.env_path = Path(env_path) if env_path else ENV_PATH
        import json
        public_path = BASE_DIR / "public_config.json"
        if public_path.exists():
            public = json.loads(public_path.read_text(encoding="utf-8"))
            for name in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_PROFILE_PORTAL_URL"):
                if public.get(name):
                    os.environ.setdefault(name, str(public[name]))
        load_dotenv(self.env_path)
        self.url = (os.getenv("SUPABASE_URL") or "").strip()
        self.key = (
            os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or ""
        ).strip()
        if not self.url or not self.key:
            raise SupabaseConfigurationError(
                f"Faltan SUPABASE_URL y/o SUPABASE_PUBLISHABLE_KEY en {self.env_path}"
            )
        self._http_transport = None
        if interactive:
            from supabase import ClientOptions
            import httpx
            # Bound stalled Live requests including Auth. Leave the Manager's
            # bulk import/export timeouts unchanged. These are per-I/O limits.
            self._http_transport = httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0, pool=5.0), follow_redirects=True)
            try:
                self.client = create_client(self.url, self.key, options=ClientOptions(httpx_client=self._http_transport))
            except Exception:
                self._http_transport.close()
                raise
        else:
            self.client: Client = create_client(self.url, self.key)
        self.user: Any | None = None
        self.active_workspace: dict[str, Any] = {}
        self.active_membership: dict[str, Any] = {}

    def close(self) -> None:
        """Release an abandoned Live login without signing out other sessions."""
        transport = getattr(self, "_http_transport", None)
        if transport is not None:
            transport.close()

    @property
    def user_email(self) -> str:
        return getattr(self.user, "email", "") or ""

    @property
    def user_id(self) -> str:
        return str(getattr(self.user, "id", "") or "")

    def _user_metadata(self) -> dict[str, Any]:
        metadata = getattr(self.user, "user_metadata", None) or {}
        if isinstance(metadata, dict):
            return deepcopy(metadata)
        try:
            return deepcopy(dict(metadata))
        except Exception:
            return {}

    @staticmethod
    def _date_value(value: Any) -> str:
        if value in (None, ""):
            return ""
        return str(value)

    def user_profile(self) -> dict[str, Any]:
        """Return the safe account details shown in the desktop profile panel."""
        if self.user is None:
            return {}
        metadata = self._user_metadata()
        display_name = str(
            metadata.get("display_name")
            or metadata.get("full_name")
            or metadata.get("name")
            or self.user_email.split("@", 1)[0]
            or "Operador"
        ).strip()
        return {
            "id": self.user_id,
            "email": self.user_email,
            "display_name": display_name,
            "avatar_url": str(metadata.get("avatar_url") or ""),
            "created_at": self._date_value(getattr(self.user, "created_at", "")),
            "last_sign_in_at": self._date_value(getattr(self.user, "last_sign_in_at", "")),
        }

    def update_user_profile(self, display_name: str) -> dict[str, Any]:
        if self.user is None:
            raise RuntimeError("Debes iniciar sesión primero")
        clean_name = " ".join(str(display_name or "").split()).strip()
        if len(clean_name) < 2:
            raise ValueError("Introduce un nombre de al menos 2 caracteres")
        if len(clean_name) > 80:
            raise ValueError("El nombre no puede superar 80 caracteres")

        metadata = self._user_metadata()
        metadata["display_name"] = clean_name
        metadata["full_name"] = clean_name
        response = self.client.auth.update_user({"data": metadata})
        updated_user = getattr(response, "user", None)
        if updated_user is not None:
            self.user = updated_user

        # Keep the operational directory readable when the public table exists.
        # The Auth profile remains authoritative, so a missing table/column must
        # never prevent the user from updating their account.
        try:
            (
                self.client.table("scoreboard_operators")
                .update({"display_name": clean_name, "email": self.user_email})
                .eq("id", self.user_id)
                .execute()
            )
        except Exception:
            pass
        return self.user_profile()

    def update_password(self, new_password: str) -> None:
        if self.user is None:
            raise RuntimeError("Debes iniciar sesión primero")
        clean_password = str(new_password or "")
        if len(clean_password) < 8:
            raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")
        response = self.client.auth.update_user({"password": clean_password})
        updated_user = getattr(response, "user", None)
        if updated_user is not None:
            self.user = updated_user

    def request_password_reset(self, email: str) -> None:
        clean_email = str(email or "").strip()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Introduce un correo electrónico válido")
        self.client.auth.reset_password_for_email(clean_email)

    @staticmethod
    def _public_url_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get("publicUrl") or value.get("public_url") or value.get("url") or "")
        return str(getattr(value, "public_url", "") or getattr(value, "publicUrl", "") or "")

    def upload_avatar(self, image_bytes: bytes, content_type: str = "image/jpeg") -> dict[str, Any]:
        """Upload one public profile image and store its URL in Auth metadata."""
        if self.user is None:
            raise RuntimeError("Debes iniciar sesión primero")
        if not image_bytes:
            raise ValueError("No se ha recibido ninguna imagen")
        object_path = f"{self.user_id}/profile.jpg"
        bucket = self.client.storage.from_(AVATAR_BUCKET)
        # storage-py accepts the raw byte payload. Passing io.BytesIO here
        # is incompatible with versions that treat every non-bytes value as
        # a filesystem path, producing: expected str, bytes or os.PathLike.
        bucket.upload(
            file=image_bytes,
            path=object_path,
            file_options={
                "cache-control": "3600",
                "content-type": content_type,
                "upsert": "true",
            },
        )
        public_url = self._public_url_value(bucket.get_public_url(object_path))
        if not public_url:
            raise RuntimeError("Supabase no devolvió la URL pública del avatar")
        separator = "&" if "?" in public_url else "?"
        public_url = f"{public_url}{separator}v={int(time.time())}"
        metadata = self._user_metadata()
        metadata["avatar_url"] = public_url
        response = self.client.auth.update_user({"data": metadata})
        updated_user = getattr(response, "user", None)
        if updated_user is not None:
            self.user = updated_user
        return self.user_profile()

    def remove_avatar(self) -> dict[str, Any]:
        if self.user is None:
            raise RuntimeError("Debes iniciar sesión primero")
        object_path = f"{self.user_id}/profile.jpg"
        try:
            self.client.storage.from_(AVATAR_BUCKET).remove([object_path])
        except Exception:
            # Metadata still needs to be cleaned if the object was already gone.
            pass
        metadata = self._user_metadata()
        metadata.pop("avatar_url", None)
        response = self.client.auth.update_user({"data": metadata})
        updated_user = getattr(response, "user", None)
        if updated_user is not None:
            self.user = updated_user
        return self.user_profile()

    def login(self, email: str, password: str) -> str:
        email = (email or "").strip()
        if not email or not password:
            raise SupabaseConfigurationError("Introduce email y contraseña")
        response = self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        self.user = response.user
        if self.user is None:
            raise RuntimeError("Supabase no devolvió un usuario autenticado")
        return self.user_email

    def logout(self) -> None:
        try:
            self.client.auth.sign_out()
        finally:
            self.user = None
            self.active_workspace = {}
            self.active_membership = {}

    def user_app_settings(self) -> dict[str, Any] | None:
        """Return non-secret SecretariatPro settings stored in Supabase user metadata."""
        if self.user is None:
            return None
        metadata = getattr(self.user, "user_metadata", None) or {}
        if not isinstance(metadata, dict):
            try:
                metadata = dict(metadata)
            except Exception:
                return None
        settings = metadata.get(APP_SETTINGS_METADATA_KEY)
        return deepcopy(settings) if isinstance(settings, dict) else None

    def save_user_app_settings(self, settings: dict[str, Any]) -> None:
        """Sync non-secret operator settings to the authenticated account.

        OBS connection parameters follow the operator, but the OBS password is
        deliberately excluded and remains encrypted by the operating context /
        local account profile instead of being written to public user metadata.
        """
        if self.user is None:
            return
        clean = deepcopy(settings) if isinstance(settings, dict) else {}
        obs = clean.get("obs")
        if isinstance(obs, dict):
            obs.pop("password", None)
            obs.pop("password_configured", None)
        clean.pop("account_scope", None)
        metadata = getattr(self.user, "user_metadata", None) or {}
        if not isinstance(metadata, dict):
            try:
                metadata = dict(metadata)
            except Exception:
                metadata = {}
        metadata = deepcopy(metadata)
        metadata[APP_SETTINGS_METADATA_KEY] = clean
        response = self.client.auth.update_user({"data": metadata})
        updated_user = getattr(response, "user", None)
        if updated_user is not None:
            self.user = updated_user

    def list_workspaces(self) -> list[dict[str, Any]]:
        """Return every active workspace the authenticated user belongs to."""
        if not self.user_id:
            return []
        memberships = (
            self.client.table("sp_workspace_members")
            .select("workspace_id,role,status,joined_at")
            .eq("user_id", self.user_id)
            .eq("status", "active")
            .execute()
        ).data or []
        workspace_ids = [str(row.get("workspace_id") or "") for row in memberships if row.get("workspace_id")]
        if not workspace_ids:
            self.active_workspace = {}
            self.active_membership = {}
            return []
        rows = (
            self.client.table("sp_workspaces")
            .select("id,name,slug,workspace_type,assignment_mode,visual_identity_mode,sport_mode,owner_user_id,created_at")
            .in_("id", workspace_ids)
            .is_("deleted_at", "null")
            .order("name")
            .execute()
        ).data or []
        membership_by_workspace = {str(row.get("workspace_id") or ""): row for row in memberships}
        result = []
        for row in rows:
            item = dict(row)
            membership = membership_by_workspace.get(str(item.get("id") or ""), {})
            item["role"] = str(membership.get("role") or "producer")
            item["membership_status"] = str(membership.get("status") or "active")
            result.append(item)
        return result

    def activate_workspace(self, workspace_id: str) -> dict[str, Any]:
        clean_id = str(workspace_id or "").strip()
        workspace = next((row for row in self.list_workspaces() if str(row.get("id")) == clean_id), None)
        if not workspace:
            raise RuntimeError("No tienes acceso a ese espacio de trabajo")
        self.active_workspace = dict(workspace)
        self.active_membership = {
            "workspace_id": clean_id,
            "role": workspace.get("role") or "producer",
            "status": workspace.get("membership_status") or "active",
        }
        return dict(self.active_workspace)

    def latest_workspace_subscription(self, workspace_id: str) -> dict[str, Any]:
        rows = (
            self.client.table("sp_subscriptions")
            .select(
                "id,workspace_id,plan_id,status,starts_at,ends_at,retention_until,"
                "offline_grace_days,payment_provider,provider_customer_id,provider_subscription_id,"
                "plan:sp_plans(id,name,audience,entitlements)"
            )
            .eq("workspace_id", str(workspace_id))
            .order("ends_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        return dict(rows[0]) if rows else {}

    def workspace_context(self, preferred_workspace_id: str = "") -> dict[str, Any]:
        workspaces = self.list_workspaces()
        if not workspaces:
            self.active_workspace = {}
            self.active_membership = {}
            return {"workspaces": [], "workspace": {}, "subscription": {}}
        selected = next(
            (row for row in workspaces if str(row.get("id") or "") == str(preferred_workspace_id or "")),
            None,
        ) or workspaces[0]
        # The membership list was validated immediately above. Re-fetching it
        # via activate_workspace used to add two serial round trips per login.
        self.active_workspace = dict(selected)
        self.active_membership = {
            "workspace_id": str(selected.get("id") or ""),
            "role": selected.get("role") or "producer",
            "status": selected.get("membership_status") or "active",
        }
        workspace = dict(self.active_workspace)
        subscription = self.latest_workspace_subscription(str(workspace.get("id") or ""))
        return {"workspaces": workspaces, "workspace": workspace, "subscription": subscription}


    # ------------------------------------------------------------------
    # OCR improvement programme (opt-in, workspace scoped)
    # ------------------------------------------------------------------

    def ocr_consent(self) -> dict[str, Any]:
        """Return the active workspace consent without exposing any sample data."""
        workspace_id = self._active_workspace_id()
        role = self._active_role()
        enabled = False
        updated_at = ""
        try:
            rows = (
                self.client.table("sp_ocr_consent")
                .select("workspace_id,enabled,updated_at")
                .eq("workspace_id", workspace_id)
                .limit(1)
                .execute()
            ).data or []
            if rows:
                enabled = bool(rows[0].get("enabled"))
                updated_at = str(rows[0].get("updated_at") or "")
        except Exception:
            # Migration not installed / offline: privacy-safe default is off.
            enabled = False
        return {
            "workspace_id": workspace_id,
            "enabled": enabled,
            "can_manage": role in {"owner", "competition_manager"},
            "role": role,
            "updated_at": updated_at,
        }

    def set_ocr_consent(self, enabled: bool) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        payload = {
            "workspace_id": workspace_id,
            "enabled": bool(enabled),
            "updated_by": self.user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            (
                self.client.table("sp_ocr_consent")
                .upsert(payload, on_conflict="workspace_id")
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                "No se pudo guardar la preferencia OCR. Ejecuta la migración SUPABASE_PHASE47_OCR_LAB.sql."
            ) from exc
        return self.ocr_consent()

    def upload_ocr_sample(self, image_bytes: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
        """Upload one privacy-minimised ROI to the private OCR training bucket.

        This method intentionally accepts no match/team/player identifiers.
        OCR Lab reviewers receive only the cropped display region and technical
        recognition metadata required to label and evaluate it.
        """
        if not image_bytes:
            raise ValueError("Muestra OCR vacía")
        # Do not query consent for every sample. The running app already keeps
        # the current workspace decision cached, while RLS on both the bucket
        # and metadata table is the authoritative server-side guard.
        workspace_id = self._active_workspace_id()
        clean_field = str(metadata.get("field") or "")
        if clean_field not in {"team1_score", "team2_score", "time"}:
            clean_field = "unknown"
        model_name = str(metadata.get("model_name") or "")[:128]
        supplied_hash = str(metadata.get("image_sha256") or "").strip().lower()
        image_sha256 = supplied_hash if re.fullmatch(r"[0-9a-f]{64}", supplied_hash) else hashlib.sha256(image_bytes).hexdigest()

        # Ask the server before uploading. The sample table is deliberately
        # private, so this narrow RPC is the only duplicate lookup exposed to
        # the commercial client. Skipping an existing sample prevents an
        # unreferenced Storage object for every repeated OCR frame.
        existing_response = self.client.rpc("sp_find_ocr_sample", {
            "p_workspace_id": workspace_id,
            "p_field": clean_field,
            "p_image_sha256": image_sha256,
            "p_model_name": model_name,
        }).execute()
        existing_value = getattr(existing_response, "data", None)
        if isinstance(existing_value, list):
            existing_value = existing_value[0] if existing_value else None
        if existing_value:
            return {"uploaded": False, "duplicate": True, "id": existing_value}

        model_key = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:12]
        object_path = f"{workspace_id}/dedupe/{clean_field}/{model_key}/{image_sha256}.jpg"
        bucket = self.client.storage.from_("ocr-training-samples")
        try:
            # The private bucket grants INSERT only. Upsert additionally needs
            # SELECT/UPDATE and therefore fails RLS even for permitted samples.
            bucket.upload(
                file=image_bytes,
                path=object_path,
                file_options={"cache-control": "0", "content-type": "image/jpeg", "upsert": "false"},
            )
        except Exception as exc:
            details = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else {}
            code = str(details.get("statusCode") or details.get("status") or getattr(exc, "status", ""))
            message = str(exc).lower()
            if code != "409" and not ("duplicate" in message and "already exists" in message):
                raise
            # A previous upload may have succeeded before metadata submission
            # failed. Reuse its deterministic object; never request read access.

        payload = {
            "workspace_id": workspace_id,
            "uploaded_by": self.user_id,
            "field": clean_field,
            "predicted_value": str(metadata.get("predicted_value") or "")[:32],
            "confidence": max(0.0, min(1.0, float(metadata.get("confidence") or 0.0))),
            "raw_text": str(metadata.get("raw") or "")[:128],
            "ocr_pass": str(metadata.get("ocr_pass") or "")[:32],
            "model_name": model_name,
            "model_custom": bool(metadata.get("model_custom")),
            "app_release": str(metadata.get("app_release") or "")[:64],
            "storage_path": object_path,
            "image_sha256": image_sha256,
            "image_width": int(metadata.get("width") or 0),
            "image_height": int(metadata.get("height") or 0),
            "status": "pending",
        }
        # Metadata is submitted through a SECURITY DEFINER RPC instead of a
        # direct table INSERT. This deliberately keeps authenticated users
        # without SELECT access to the private training table. PostgREST's
        # normal INSERT response may request RETURNING representation and thus
        # require SELECT even when the client only needs to write.
        rpc_payload = {
            "p_workspace_id": payload["workspace_id"],
            "p_field": payload["field"],
            "p_predicted_value": payload["predicted_value"],
            "p_confidence": payload["confidence"],
            "p_raw_text": payload["raw_text"],
            "p_ocr_pass": payload["ocr_pass"],
            "p_model_name": payload["model_name"],
            "p_model_custom": payload["model_custom"],
            "p_app_release": payload["app_release"],
            "p_storage_path": payload["storage_path"],
            "p_image_sha256": payload["image_sha256"],
            "p_image_width": payload["image_width"],
            "p_image_height": payload["image_height"],
        }
        try:
            response = self.client.rpc("sp_submit_ocr_sample", rpc_payload).execute()
        except Exception:
            # The server may have committed metadata before a timeout. Keep
            # the deterministic object for retry; deleting it can break a
            # successfully created sample (or another client's duplicate).
            raise
        value = getattr(response, "data", None)
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            sample_id = value.get("id") or value.get("sample_id")
        else:
            sample_id = value
        if not sample_id:
            raise RuntimeError("OCR Lab no confirmó el guardado de los metadatos")
        return {"uploaded": True, "duplicate": False, "id": sample_id, "path": object_path}

    # ------------------------------------------------------------------
    # SecretariatPro Manager
    # ------------------------------------------------------------------

    def _active_workspace_id(self) -> str:
        workspace_id = str((self.active_workspace or {}).get("id") or "").strip()
        if not workspace_id:
            raise RuntimeError("Selecciona un espacio de trabajo")
        return workspace_id

    def _active_role(self) -> str:
        return str((self.active_membership or {}).get("role") or "producer")

    def _require_competition_manager(self) -> None:
        if self._active_role() not in {"owner", "competition_manager"}:
            raise PermissionError("Tu rol no permite modificar este espacio")

    @staticmethod
    def _clean_payload(payload: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in dict(payload or {}).items():
            if key not in allowed:
                continue
            if isinstance(value, str):
                value = value.strip()
            if value == "":
                value = None
            clean[key] = value
        return clean

    def _manager_count_rows(self, table: str, **filters: Any) -> int:
        query = self.client.table(table).select("*", count="exact", head=True)
        for key, value in filters.items():
            query = query.eq(key, value)
        response = query.execute()
        return int(getattr(response, "count", 0) or 0)

    def _manager_delete_by_id(self, table: str, entity_id: str) -> dict[str, Any]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table(table)
            .delete()
            .eq("id", str(entity_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return {"ok": True, "deleted": bool(response.data), "id": str(entity_id)}

    def manager_dashboard_counts(self) -> dict[str, int]:
        workspace_id = self._active_workspace_id()
        result: dict[str, int] = {}
        for table, key in (
            ("competitions", "competitions"),
            ("teams", "teams"),
            ("players", "players"),
            ("matches", "matches"),
            ("sp_workspace_members", "members"),
        ):
            query = self.client.table(table).select("*", count="exact", head=True)
            if table == "sp_workspace_members":
                query = query.eq("workspace_id", workspace_id).eq("status", "active")
            else:
                query = query.eq("workspace_id", workspace_id)
            response = query.execute()
            result[key] = int(getattr(response, "count", 0) or 0)
        return result

    def manager_list_seasons(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("seasons")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("name", desc=True)
            .execute()
        )
        return response.data or []

    def manager_create_season(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(payload, {"name"})
        if not clean.get("name"):
            raise ValueError("El nombre de la temporada es obligatorio")
        clean["workspace_id"] = workspace_id
        response = self.client.table("seasons").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_delete_season(self, season_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        dependencies = self._manager_count_rows("competitions", workspace_id=workspace_id, season_id=str(season_id))
        if dependencies:
            raise ValueError(f"No se puede eliminar la temporada porque contiene {dependencies} competiciones. Elimina o reasigna esas competiciones primero")
        return self._manager_delete_by_id("seasons", season_id)

    def manager_list_competitions(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("competitions")
            .select("id,workspace_id,name,category,season_id,active,logo_url,points_win,points_draw,points_loss,seasons(name)")
            .eq("workspace_id", workspace_id)
            .order("name")
            .execute()
        )
        return response.data or []

    def manager_create_competition(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"name", "category", "season_id", "active", "logo_url", "points_win", "points_draw", "points_loss"},
        )
        if not clean.get("name"):
            raise ValueError("El nombre de la competición es obligatorio")
        clean.setdefault("active", True)
        clean.setdefault("points_win", 2)
        clean.setdefault("points_draw", 1)
        clean.setdefault("points_loss", 0)
        clean["workspace_id"] = workspace_id
        response = self.client.table("competitions").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_update_competition(self, competition_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"name", "category", "season_id", "active", "logo_url", "points_win", "points_draw", "points_loss"},
        )
        response = (
            self.client.table("competitions")
            .update(clean)
            .eq("id", str(competition_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return dict((response.data or [{}])[0])

    def manager_delete_competition(self, competition_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        matches = self._manager_count_rows("matches", workspace_id=workspace_id, competition_id=str(competition_id))
        if matches:
            raise ValueError(f"No se puede eliminar la competición porque tiene {matches} partidos. Elimina primero esos partidos")
        self.client.table("rosters").delete().eq("workspace_id", workspace_id).eq("competition_id", str(competition_id)).execute()
        self.client.table("sp_visual_themes").delete().eq("workspace_id", workspace_id).eq("competition_id", str(competition_id)).execute()
        return self._manager_delete_by_id("competitions", competition_id)

    def manager_list_teams(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("teams")
            .select("id,workspace_id,name,short_name,logo_url,alternate_logo_url,primary_color,secondary_color")
            .eq("workspace_id", workspace_id)
            .order("name")
            .execute()
        )
        return response.data or []

    def manager_create_team(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"name", "short_name", "logo_url", "alternate_logo_url", "primary_color", "secondary_color"},
        )
        if not clean.get("name"):
            raise ValueError("El nombre del equipo es obligatorio")
        if not clean.get("short_name"):
            clean["short_name"] = str(clean["name"])[:12].upper()
        clean.setdefault("primary_color", "#1f2937")
        clean.setdefault("secondary_color", "#ffffff")
        clean["workspace_id"] = workspace_id
        response = self.client.table("teams").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_update_team(self, team_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"name", "short_name", "logo_url", "alternate_logo_url", "primary_color", "secondary_color"},
        )
        response = (
            self.client.table("teams")
            .update(clean)
            .eq("id", str(team_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return dict((response.data or [{}])[0])

    def manager_delete_team(self, team_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        home_matches = self._manager_count_rows("matches", workspace_id=workspace_id, home_team_id=str(team_id))
        away_matches = self._manager_count_rows("matches", workspace_id=workspace_id, away_team_id=str(team_id))
        matches = home_matches + away_matches
        if matches:
            raise ValueError(f"No se puede eliminar el equipo porque aparece en {matches} partidos. Elimina primero esos partidos para conservar la integridad del histórico")
        self.client.table("rosters").delete().eq("workspace_id", workspace_id).eq("team_id", str(team_id)).execute()
        return self._manager_delete_by_id("teams", team_id)

    def manager_list_players(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("players")
            .select("id,workspace_id,first_name,last_name,display_name,position,birth_date,nationality,is_coach")
            .eq("workspace_id", workspace_id)
            .order("last_name")
            .order("first_name")
            .execute()
        )
        return [self._person_role(row) for row in (response.data or [])]

    def manager_create_player(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(payload, {"first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"})
        clean.update(self._import_person_details(clean))
        clean = self._person_role(clean)
        if not clean.get("first_name") and not clean.get("display_name"):
            raise ValueError("Introduce al menos el nombre del jugador")
        if not clean.get("display_name"):
            clean["display_name"] = " ".join(x for x in [clean.get("first_name"), clean.get("last_name")] if x)
        clean["workspace_id"] = workspace_id
        response = self.client.table("players").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_update_player(self, player_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(payload, {"first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"})
        clean.update(self._import_person_details(clean))
        clean = self._person_role(clean)
        response = (
            self.client.table("players")
            .update(clean)
            .eq("id", str(player_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        person = dict((response.data or [{}])[0])
        if person and ("position" in clean or "is_coach" in clean):
            coach_only = self._coach_only(person)
            assignment = {"member_type": "coach" if coach_only else "player"}
            if coach_only: assignment.update(shirt_number=None, captain=False)
            self.client.table("rosters").update(assignment).eq("workspace_id", workspace_id).eq("player_id", str(player_id)).execute()
        return person

    def manager_delete_player(self, player_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        called_up = self._manager_count_rows("match_players", workspace_id=workspace_id, player_id=str(player_id))
        events = self._manager_count_rows("match_events", workspace_id=workspace_id, player_id=str(player_id))
        if called_up or events:
            raise ValueError(f"No se puede eliminar el jugador porque tiene histórico deportivo ({called_up} convocatorias y {events} eventos). Puedes retirarlo de los rosters sin borrar ese histórico")
        self.client.table("rosters").delete().eq("workspace_id", workspace_id).eq("player_id", str(player_id)).execute()
        return self._manager_delete_by_id("players", player_id)

    def manager_list_matches(self, limit: int = 250) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("matches")
            .select(
                "id,workspace_id,competition_id,match_date,time_confirmed,scheduled_date,venue,status,home_score,away_score,assigned_to,broadcast_enabled,"
                "home_team_id,away_team_id,competition:competitions(name),"
                "home_team:teams!matches_home_team_id_fkey(id,name,short_name),"
                "away_team:teams!matches_away_team_id_fkey(id,name,short_name),"
                "assigned_operator:scoreboard_operators!matches_assigned_to_fkey(id,email,display_name)"
            )
            .eq("workspace_id", workspace_id)
            .order("match_date", desc=True)
            .limit(max(1, min(int(limit), 1000)))
            .execute()
        )
        return response.data or []

    def manager_create_match(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"competition_id", "match_date", "time_confirmed", "scheduled_date", "venue", "status", "home_score", "away_score", "assigned_to", "home_team_id", "away_team_id", "broadcast_enabled"},
        )
        required = ["competition_id", "match_date", "home_team_id", "away_team_id"]
        if any(not clean.get(key) for key in required):
            raise ValueError("Competición, fecha, equipo local y visitante son obligatorios")
        if clean.get("home_team_id") == clean.get("away_team_id"):
            raise ValueError("El equipo local y el visitante deben ser distintos")
        clean.setdefault("status", "scheduled")
        clean.setdefault("home_score", 0)
        clean.setdefault("away_score", 0)
        clean.setdefault("broadcast_enabled", True)
        clean["workspace_id"] = workspace_id
        response = self.client.table("matches").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_update_match(self, match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"competition_id", "match_date", "time_confirmed", "scheduled_date", "venue", "status", "home_score", "away_score", "assigned_to", "home_team_id", "away_team_id", "broadcast_enabled"},
        )
        response = (
            self.client.table("matches")
            .update(clean)
            .eq("id", str(match_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return dict((response.data or [{}])[0])

    def manager_delete_match(self, match_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        self.client.table("match_events").delete().eq("workspace_id", workspace_id).eq("match_id", str(match_id)).execute()
        self.client.table("match_players").delete().eq("workspace_id", workspace_id).eq("match_id", str(match_id)).execute()
        return self._manager_delete_by_id("matches", match_id)

    def manager_set_sport_mode(self, sport_mode: str) -> dict[str, Any]:
        """Owner-only platform ruleset. Competition managers and producers cannot change it."""
        if self._active_role() != "owner":
            raise PermissionError("Sólo el propietario de la cuenta puede cambiar el deporte de la plataforma")
        mode = str(sport_mode or "floorball").strip().lower()
        if mode not in {"floorball", "handball"}:
            raise ValueError("Modo de deporte no válido")
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("sp_workspaces")
            .update({"sport_mode": mode})
            .eq("id", workspace_id)
            .execute()
        )
        if not (response.data or []):
            raise ValueError("No se pudo actualizar el modo de deporte")
        self.active_workspace.update(dict(response.data[0]))
        return dict(self.active_workspace)

    def _manager_match_row(self, match_id: str) -> dict[str, Any]:
        workspace_id = self._active_workspace_id()
        rows = (
            self.client.table("matches")
            .select("id,workspace_id,competition_id,home_team_id,away_team_id,status,home_score,away_score,broadcast_enabled,home_team:teams!matches_home_team_id_fkey(id,name,short_name),away_team:teams!matches_away_team_id_fkey(id,name,short_name)")
            .eq("id", str(match_id)).eq("workspace_id", workspace_id).limit(1).execute()
        ).data or []
        if not rows:
            raise ValueError("Partido no encontrado")
        return dict(rows[0])

    def manager_match_event_context(self, match_id: str) -> dict[str, Any]:
        match = self._manager_match_row(match_id)
        competition_id = str(match.get("competition_id") or "")
        home_id = str(match.get("home_team_id") or "")
        away_id = str(match.get("away_team_id") or "")
        return {
            "match": match,
            "home_roster": self.manager_list_team_rosters(home_id, competition_id),
            "away_roster": self.manager_list_team_rosters(away_id, competition_id),
            "events": self.list_events(str(match_id)),
        }

    def _manager_recalculate_match_score(self, match_id: str) -> dict[str, Any]:
        match = self._manager_match_row(match_id)
        events = self.list_events(str(match_id))
        home_id = str(match.get("home_team_id") or "")
        away_id = str(match.get("away_team_id") or "")
        home_score = sum(1 for row in events if row.get("event_type") == "goal" and str(row.get("team_id") or "") == home_id)
        away_score = sum(1 for row in events if row.get("event_type") == "goal" and str(row.get("team_id") or "") == away_id)
        return self.manager_update_match(str(match_id), {"home_score": home_score, "away_score": away_score})

    def manager_create_match_event(self, match_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        context = self.manager_match_event_context(match_id)
        match = context["match"]
        side = str(payload.get("team") or "").lower()
        if side not in {"home", "away"}:
            raise ValueError("Selecciona equipo local o visitante")
        team_id = str(match.get("home_team_id") if side == "home" else match.get("away_team_id"))
        event_type = str(payload.get("event_type") or "").lower()
        player_id = str(payload.get("player_id") or "").strip() or None
        match_time = str(payload.get("match_time") or "").strip()
        notes = str(payload.get("notes") or "").strip()
        if event_type == "goal":
            if not player_id:
                raise ValueError("Selecciona el goleador")
            assistant_id = str(payload.get("assistant_id") or "").strip() or None
            if assistant_id == player_id:
                raise ValueError("Goleador y asistente no pueden ser el mismo jugador")
            goal, assist = self.create_goal_with_assist(
                match_id=str(match_id), team_id=team_id, scorer_id=player_id, assistant_id=assistant_id, match_time=match_time, goal_notes=notes
            )
            self._manager_recalculate_match_score(match_id)
            return {"event": goal, "assist": assist}
        if event_type == "penalty":
            if not player_id:
                raise ValueError("Selecciona el jugador sancionado")
            penalty_type = str(payload.get("penalty_type") or "2")
            seconds, total_minutes, personal = penalty_values(penalty_type)
            event = self.create_event(
                match_id=str(match_id), team_id=team_id, player_id=player_id, event_type="penalty", match_time=match_time,
                penalty_type=penalty_type, penalty_minutes=total_minutes, team_penalty_seconds=seconds, personal_penalty_minutes=personal, notes=notes
            )
            return {"event": event}
        raise ValueError("El acta admite goles/asistencias y expulsiones")

    def manager_finalize_match_act(self, match_id: str) -> dict[str, Any]:
        """Recalculate the event-derived score and mark an administrative act as finished."""
        self._require_competition_manager()
        result = self._manager_recalculate_match_score(match_id)
        return self.manager_update_match(str(match_id), {
            "status": "finished",
            "home_score": int(result.get("home_score") or 0),
            "away_score": int(result.get("away_score") or 0),
        })

    def manager_cancel_match_event(self, match_id: str, event_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        self._manager_match_row(match_id)
        events = self.list_events(str(match_id))
        target = next((row for row in events if str(row.get("id") or "") == str(event_id)), None)
        if not target:
            raise ValueError("Evento no encontrado")
        self.cancel_event(str(event_id))
        if target.get("event_type") == "goal":
            for row in events:
                if row.get("event_type") == "assist" and str(row.get("related_event_id") or "") == str(event_id):
                    self.cancel_event(str(row.get("id")))
            self._manager_recalculate_match_score(match_id)
        return {"ok": True}

    def manager_list_members(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        memberships = (
            self.client.table("sp_workspace_members")
            .select("workspace_id,user_id,role,status,joined_at")
            .eq("workspace_id", workspace_id)
            .order("joined_at")
            .execute()
        ).data or []
        user_ids = [str(row.get("user_id") or "") for row in memberships if row.get("user_id")]
        directory: dict[str, dict[str, Any]] = {}
        if user_ids:
            try:
                rows = (
                    self.client.table("scoreboard_operators")
                    .select("id,email,display_name")
                    .in_("id", user_ids)
                    .execute()
                ).data or []
                directory = {str(row.get("id") or ""): dict(row) for row in rows}
            except Exception:
                directory = {}
        result = []
        for membership in memberships:
            item = dict(membership)
            item["profile"] = directory.get(str(item.get("user_id") or ""), {})
            result.append(item)
        return result

    def manager_invite_member(self, email: str, role: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean_email = str(email or "").strip().lower()
        clean_role = str(role or "producer").strip()
        if "@" not in clean_email:
            raise ValueError("Introduce un correo válido")
        if clean_role not in {"competition_manager", "producer"}:
            raise ValueError("Rol no válido")
        options = {
            "body": {"workspace_id": workspace_id, "email": clean_email, "role": clean_role},
            "responseType": "json",
        }
        recovered_from_timeout = False
        for attempt in range(2):
            try:
                value = self.client.functions.invoke("invite-member", options)
                break
            except Exception as exc:
                message = str(exc).lower()
                timeout = "timed out" in message or "timeout" in type(exc).__name__.lower()
                if attempt == 0 and timeout:
                    recovered_from_timeout = True
                    time.sleep(0.35)
                    continue
                raise
        else:  # pragma: no cover - the loop either returns or raises
            raise RuntimeError("No se pudo completar la invitación")
        if not isinstance(value, dict):
            raise RuntimeError("Supabase no devolvió una respuesta válida al invitar")
        if not value.get("ok"):
            raise RuntimeError(str(value.get("error") or "No se pudo enviar la invitación"))
        result = dict(value)
        if recovered_from_timeout:
            result["recovered_from_timeout"] = True
        return result

    def manager_add_existing_member(self, email: str, role: str) -> dict[str, Any]:
        """Compatibility alias for older Manager builds."""
        return self.manager_invite_member(email, role)

    def profile_portal_url(self) -> str:
        configured = str(os.getenv("SUPABASE_PROFILE_PORTAL_URL") or "").strip()
        return configured or DEFAULT_PROFILE_PORTAL_URL

    def manager_update_member(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        if str(user_id) == str((self.active_workspace or {}).get("owner_user_id") or ""):
            raise ValueError("No se puede modificar al propietario desde esta pantalla")
        clean = self._clean_payload(payload, {"role", "status"})
        if clean.get("role") and clean["role"] not in {"competition_manager", "producer"}:
            raise ValueError("Rol no válido")
        if clean.get("status") and clean["status"] not in {"active", "suspended"}:
            raise ValueError("Estado no válido")
        response = (
            self.client.table("sp_workspace_members")
            .update(clean)
            .eq("workspace_id", workspace_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        return dict((response.data or [{}])[0])

    def manager_delete_member(self, user_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        owner_id = str((self.active_workspace or {}).get("owner_user_id") or "")
        if str(user_id) == owner_id:
            raise ValueError("No se puede eliminar al propietario del espacio")
        if str(user_id) == str(self.user_id or ""):
            raise ValueError("No puedes eliminar tu propio acceso mientras estás utilizando este espacio")
        self.client.table("matches").update({"assigned_to": None}).eq("workspace_id", workspace_id).eq("assigned_to", str(user_id)).execute()
        response = (
            self.client.table("sp_workspace_members")
            .delete()
            .eq("workspace_id", workspace_id)
            .eq("user_id", str(user_id))
            .execute()
        )
        return {"ok": True, "deleted": bool(response.data), "user_id": str(user_id)}

    def manager_list_themes(self) -> list[dict[str, Any]]:
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("sp_visual_themes")
            .select("id,workspace_id,competition_id,name,config,version,published,locked,created_at,updated_at")
            .eq("workspace_id", workspace_id)
            .order("competition_id")
            .order("version", desc=True)
            .execute()
        )
        return response.data or []

    def _validate_theme_scope(self, competition_id):
        if not competition_id:
            return
        if (self.active_workspace or {}).get("visual_identity_mode") != "competition":
            raise PermissionError("La cuenta no permite identidades por competición")
        rows = (self.client.table("competitions").select("id")
                .eq("workspace_id", self._active_workspace_id()).eq("id", str(competition_id))
                .limit(1).execute()).data or []
        if not rows:
            raise PermissionError("La competición no pertenece al espacio activo")

    def manager_create_theme(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(payload, {"competition_id", "name", "config", "published", "locked"})
        clean.setdefault("name", "Identidad principal")
        clean.setdefault("config", {})
        clean.setdefault("published", False)
        clean["locked"] = True
        self._validate_theme_scope(clean.get("competition_id"))
        from secretariat_core.settings_store import normalize_settings
        config = clean.get("config")
        if not isinstance(config, dict):
            raise ValueError("La identidad visual debe ser un objeto")
        appearance = config.get("appearance", config)
        if not isinstance(appearance, dict):
            raise ValueError("La apariencia debe ser un objeto")
        clean["config"] = {"appearance": normalize_settings({"appearance": appearance})["appearance"]}
        response = self.client.rpc("sp_create_visual_theme", {
            "p_workspace": workspace_id,
            "p_competition": clean.get("competition_id") or None,
            "p_name": clean["name"],
            "p_config": clean["config"],
            "p_publish": bool(clean.get("published")),
        }).execute()
        return dict(response.data or {})

    def manager_publish_theme(self, theme_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        response = self.client.rpc("sp_publish_visual_theme", {
            "p_workspace": self._active_workspace_id(), "p_theme": str(theme_id),
        }).execute()
        return dict(response.data or {})

    def manager_delete_theme(self, theme_id: str) -> dict[str, Any]:
        self._require_competition_manager()
        return self._manager_delete_by_id("sp_visual_themes", theme_id)

    # ---------------- Phase 39: rosters and shared visual assets ----------------
    def manager_list_team_rosters(
        self, team_id: str, competition_id: str = ""
    ) -> list[dict[str, Any]]:
        """List the active roster rows for one team, optionally scoped to a competition."""
        workspace_id = self._active_workspace_id()
        query = (
            self.client.table("rosters")
            .select(
                "id,workspace_id,competition_id,team_id,player_id,shirt_number,captain,active,member_type,"
                "player:players(id,first_name,last_name,display_name,position,birth_date,nationality,is_coach),"
                "competition:competitions(id,name,season_id,seasons(id,name))"
            )
            .eq("workspace_id", workspace_id)
            .eq("team_id", str(team_id))
            .eq("active", True)
            .order("competition_id")
            .order("shirt_number")
        )
        if str(competition_id or "").strip():
            query = query.eq("competition_id", str(competition_id))
        return query.execute().data or []

    def manager_list_player_rosters(self, player_id: str) -> list[dict[str, Any]]:
        """List every active roster membership for a player in the current workspace."""
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("rosters")
            .select(
                "id,workspace_id,competition_id,team_id,player_id,shirt_number,captain,active,member_type,"
                "team:teams(id,name,short_name,logo_url,primary_color,secondary_color),"
                "competition:competitions(id,name,season_id,seasons(id,name))"
            )
            .eq("workspace_id", workspace_id)
            .eq("player_id", str(player_id))
            .eq("active", True)
            .order("competition_id")
            .execute()
        )
        return response.data or []

    @staticmethod
    def _normalise_shirt_number(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("El dorsal debe ser un número entero") from exc
        if number < 0 or number > 999:
            raise ValueError("El dorsal debe estar entre 0 y 999")
        return number

    def _validate_roster_assignment(
        self, payload: dict[str, Any], exclude_id: str = ""
    ) -> dict[str, Any]:
        workspace_id = self._active_workspace_id()
        clean = self._clean_payload(
            payload,
            {"competition_id", "team_id", "player_id", "shirt_number", "captain", "active", "member_type"},
        )
        required = ("competition_id", "team_id", "player_id")
        if any(not clean.get(key) for key in required):
            raise ValueError("Competición, equipo y jugador son obligatorios")
        people = self.client.table("players").select("id,position,is_coach").eq("workspace_id", workspace_id).eq("id", clean["player_id"]).limit(1).execute().data or []
        if not people: raise ValueError("Persona no disponible en este espacio de trabajo")
        clean["member_type"] = "coach" if self._coach_only(people[0]) else "player"
        clean["shirt_number"] = None if clean.get("member_type") == "coach" else self._normalise_shirt_number(clean.get("shirt_number"))
        if clean.get("member_type") == "coach": clean["captain"] = False
        clean.setdefault("captain", False)
        clean.setdefault("active", True)
        clean.setdefault("member_type", "player")
        clean["workspace_id"] = workspace_id

        # Give a useful message before PostgreSQL's unique index rejects the row.
        duplicate_player = (
            self.client.table("rosters")
            .select("id")
            .eq("workspace_id", workspace_id)
            .eq("competition_id", clean["competition_id"])
            .eq("team_id", clean["team_id"])
            .eq("player_id", clean["player_id"])
            .eq("active", True)
        )
        if exclude_id:
            duplicate_player = duplicate_player.neq("id", str(exclude_id))
        if duplicate_player.limit(1).execute().data:
            raise ValueError("Este jugador ya pertenece a ese roster")

        if clean.get("shirt_number") is not None and clean.get("member_type") == "player":
            duplicate_number = (
                self.client.table("rosters")
                .select("id,player_id")
                .eq("workspace_id", workspace_id)
                .eq("competition_id", clean["competition_id"])
                .eq("team_id", clean["team_id"])
                .eq("shirt_number", clean["shirt_number"])
                .eq("active", True)
            )
            if exclude_id:
                duplicate_number = duplicate_number.neq("id", str(exclude_id))
            if duplicate_number.limit(1).execute().data:
                raise ValueError(f"El dorsal {clean['shirt_number']} ya está asignado en este roster")
        return clean

    def manager_create_roster(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        clean = self._validate_roster_assignment(payload)
        response = self.client.table("rosters").insert(clean).execute()
        return dict((response.data or [{}])[0])

    def manager_update_roster(self, roster_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        current_rows = (
            self.client.table("rosters")
            .select("competition_id,team_id,player_id,shirt_number,captain,active,member_type")
            .eq("id", str(roster_id))
            .eq("workspace_id", workspace_id)
            .limit(1)
            .execute()
        ).data or []
        if not current_rows:
            raise ValueError("Registro de roster no encontrado")
        merged = {**current_rows[0], **dict(payload or {})}
        clean = self._validate_roster_assignment(merged, str(roster_id))
        clean.pop("workspace_id", None)
        response = (
            self.client.table("rosters")
            .update(clean)
            .eq("id", str(roster_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return dict((response.data or [{}])[0])

    def manager_remove_roster(self, roster_id: str) -> dict[str, Any]:
        """Soft-delete a membership so it remains available for historical reports."""
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        response = (
            self.client.table("rosters")
            .update({"active": False})
            .eq("id", str(roster_id))
            .eq("workspace_id", workspace_id)
            .execute()
        )
        if not (response.data or []):
            raise ValueError("Registro de roster no encontrado")
        return dict(response.data[0])

    def manager_create_player_and_roster(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        player_payload = dict(payload.get("player") or {})
        roster_payload = dict(payload.get("roster") or {})
        player = self.manager_create_player(player_payload)
        try:
            roster_payload["player_id"] = player.get("id")
            roster_payload["member_type"] = "coach" if self._coach_only(player) else "player"
            roster = self.manager_create_roster(roster_payload)
        except Exception:
            # Avoid leaving an accidental orphan when validation fails after creating the player.
            try:
                self.client.table("players").delete().eq("id", player.get("id")).eq(
                    "workspace_id", self._active_workspace_id()
                ).execute()
            except Exception:
                pass
            raise
        return {"player": player, "roster": roster}

    # ---------------- Phase 42: confirmed bulk import ----------------
    @staticmethod
    def _import_key(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    @staticmethod
    def _import_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "y", "x", "activo", "active", "publicado", "published"}

    @staticmethod
    def _import_int(value: Any, default: int = 0) -> int:
        if value in (None, ""):
            return default
        try:
            return int(float(str(value).replace(",", ".")))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{value}' no es un número válido") from exc

    @staticmethod
    def _import_role(value: Any) -> str:
        key = ScoreboardSupabaseClient._import_key(value)
        if key in {"competition manager", "competition_manager", "gestor", "gestor de competiciones", "manager", "administrador"}:
            return "competition_manager"
        return "producer"

    @staticmethod
    def _import_status(value: Any, category: str = "match") -> str:
        key = ScoreboardSupabaseClient._import_key(value)
        if category == "member":
            return "suspended" if key in {"suspended", "suspendido", "inactivo", "inactive"} else "active"
        mapping = {
            "programado": "scheduled", "scheduled": "scheduled",
            "en directo": "live", "directo": "live", "live": "live",
            "finalizado": "finished", "finished": "finished", "terminado": "finished",
            "aplazado": "postponed", "postponed": "postponed",
            "cancelado": "cancelled", "cancelled": "cancelled", "canceled": "cancelled",
        }
        return mapping.get(key, "scheduled" if not key else key)

    @staticmethod
    def _import_datetime_key(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.replace(microsecond=0).isoformat()
        except ValueError:
            return text

    @staticmethod
    def _import_position(value: Any, coach: bool = False) -> str | None:
        if coach:
            return "coach"
        key = ScoreboardSupabaseClient._import_key(value)
        if key.endswith("_coach") and key != "player_coach":
            return key
        if "+" in key:
            base, suffix = (part.strip() for part in key.rsplit("+", 1))
            if suffix in {"entrenador", "entrenadora", "coach", "trainer", "tranare", "trener", "valmentaja"}:
                position = ScoreboardSupabaseClient._import_position(base)
                if position in {"goalkeeper", "defender", "midfielder", "forward", "left_back", "center_back", "right_back", "pivot", "left_wing", "right_wing"}:
                    return position + "_coach"
                raise ValueError("Posición con entrenador no reconocida")
        mapping = {
            "portero": "goalkeeper", "goalkeeper": "goalkeeper", "gk": "goalkeeper",
            "defensa": "defender", "defender": "defender", "df": "defender",
            "medio": "midfielder", "centrocampista": "midfielder", "midfielder": "midfielder", "mf": "midfielder",
            "delantero": "forward", "forward": "forward", "fw": "forward",
            "lateral izquierdo": "left_back", "left back": "left_back", "left_back": "left_back",
            "central": "center_back", "center back": "center_back", "centre back": "center_back", "center_back": "center_back",
            "lateral derecho": "right_back", "right back": "right_back", "right_back": "right_back",
            "pivote": "pivot", "pivot": "pivot",
            "extremo izquierdo": "left_wing", "left wing": "left_wing", "left_wing": "left_wing",
            "extremo derecho": "right_wing", "right wing": "right_wing", "right_wing": "right_wing",
            "entrenador": "coach", "entrenadora": "coach", "coach": "coach",
            "jugador-entrenador": "player_coach", "jugador entrenador": "player_coach",
            "jugador y entrenador": "player_coach", "jugadora-entrenadora": "player_coach",
            "player_coach": "player_coach", "player-coach": "player_coach", "player coach": "player_coach",
            "spelande tranare": "player_coach", "hrajici trener": "player_coach",
            "pelaajavalmentaja": "player_coach", "spielertrainer": "player_coach",
        }
        return mapping.get(key, str(value).strip() if value not in (None, "") else None)

    @staticmethod
    def _person_role(payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        position = str(result.get("position") or "").strip()
        if position == "coach":
            result.update(position=None, is_coach=True)
        elif position.endswith("_coach"):
            base = position.removesuffix("_coach")
            result.update(position=None if base == "player" else base, is_coach=True)
        return result

    @staticmethod
    def _coach_only(person: dict[str, Any]) -> bool:
        return person.get("position") == "coach" or (bool(person.get("is_coach")) and not person.get("position"))

    @staticmethod
    def _import_person_details(row: dict[str, Any]) -> dict[str, Any]:
        result = {}
        if "is_coach" in row and row["is_coach"] not in (None, ""):
            value = row["is_coach"]
            text = str(value).strip().lower()
            if text not in {"true", "false", "1", "0", "si", "sí", "yes", "no", "ja", "nej", "ano", "ne", "kyllä", "ei", "nein"}:
                raise ValueError("Entrenador debe ser Sí o No")
            result["is_coach"] = text in {"true", "1", "si", "sí", "yes", "ja", "ano", "kyllä"}
        if "nationality" in row:
            result["nationality"] = str(row.get("nationality") or "").strip() or None
        if "birth_date" in row:
            value = row.get("birth_date")
            if value in (None, ""):
                result["birth_date"] = None
            else:
                text = str(value).strip()
                parsed = None
                if isinstance(value, datetime): parsed = value.date()
                elif isinstance(value, date): parsed = value
                else:
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
                        try:
                            parsed = datetime.strptime(text, fmt).date()
                            break
                        except ValueError:
                            continue
                if parsed is None or parsed > date.today():
                    raise ValueError("Fecha de nacimiento inválida: utiliza DD/MM/AAAA o AAAA-MM-DD, sin fechas futuras")
                result["birth_date"] = parsed.isoformat()
        return result

    def manager_list_roster_groups(self) -> list[dict[str, Any]]:
        return self.client.table("sp_roster_groups").select("id,team_id,competition_id").eq("workspace_id", self._active_workspace_id()).execute().data or []

    def manager_create_roster_group(self, team_id: str, competition_id: str) -> dict[str, Any]:
        self.manager_validate_roster_import_target(team_id, competition_id)
        payload = {"workspace_id": self._active_workspace_id(), "team_id": team_id, "competition_id": competition_id}
        response = self.client.table("sp_roster_groups").upsert(payload, on_conflict="workspace_id,competition_id,team_id").execute()
        return dict((response.data or [{}])[0])

    def manager_import_fixture(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_competition_manager()
        query = self.client.table("matches").select("id,venue,time_confirmed").eq("workspace_id", self._active_workspace_id())
        for field in ("competition_id", "home_team_id", "away_team_id", "match_date"):
            query = query.eq(field, payload[field])
        rows = query.limit(2).execute().data or []
        if rows:
            if any((row.get("venue") or "") != (payload.get("venue") or "") or bool(row.get("time_confirmed", True)) != payload["time_confirmed"] for row in rows):
                raise ValueError("Ya existe este partido con otros datos. Edítalo en Partidos")
            return {"created": False, "id": rows[0]["id"]}
        return {"created": True, **self.manager_create_match(payload)}

    def manager_validate_roster_import_target(self, team_id: str, competition_id: str) -> None:
        self._require_competition_manager()
        if not any(str(row.get("id")) == team_id for row in self.manager_list_teams()):
            raise ValueError("Equipo no disponible en este espacio de trabajo")
        if not any(str(row.get("id")) == competition_id for row in self.manager_list_competitions()):
            raise ValueError("Competición no disponible en este espacio de trabajo")

    def manager_import_roster(self, team_id: str, competition_id: str, datasets: list[dict[str, Any]]) -> dict[str, Any]:
        """Reuse exact personal profiles and add missing memberships, tolerating row errors."""
        with _ROSTER_IMPORT_LOCK:
            return self._manager_import_roster(team_id, competition_id, datasets)

    def _manager_import_roster(self, team_id: str, competition_id: str, datasets: list[dict[str, Any]]) -> dict[str, Any]:
        self.manager_validate_roster_import_target(team_id, competition_id)
        fields = ("first_name", "last_name", "display_name", "position", "birth_date", "nationality")
        def key(row):
            return tuple(str(row.get(field) or "").strip() for field in fields)
        profiles = {key(row): row for row in self.manager_list_players()}
        members = self.manager_list_team_rosters(team_id, competition_id)
        assigned = {str(row["player_id"]) for row in members}
        numbers = {row["shirt_number"] for row in members if row.get("shirt_number") is not None}
        report = {"totals": {"created": 0, "updated": 0, "skipped": 0, "failed": 0}, "profiles_created": 0, "profiles_reused": 0, "errors": []}
        for dataset in datasets:
            for index, row in enumerate(dataset.get("rows", []), 2):
                try:
                    first = str(row.get("first_name") or "").strip()
                    last = str(row.get("last_name") or "").strip()
                    display = str(row.get("display_name") or " ".join(filter(None, [first, last]))).strip()
                    if not first and not display:
                        raise ValueError("Falta el nombre")
                    payload = {"first_name": first, "last_name": last or None, "display_name": display,
                               "position": self._import_position(row.get("position"))}
                    payload.update(self._import_person_details(row))
                    payload = self._person_role(payload)
                    person = profiles.get(key(payload))
                    role_changed = bool(person and "is_coach" in payload and bool(person.get("is_coach")) != bool(payload["is_coach"]))
                    if role_changed:
                        updated = self.manager_update_player(str(person["id"]), {"is_coach": payload["is_coach"]})
                        person.update(updated)
                        person["is_coach"] = payload["is_coach"]
                    if person and str(person["id"]) in assigned:
                        report["totals"]["updated" if role_changed else "skipped"] += 1
                        continue
                    if person and "is_coach" not in payload: payload["is_coach"] = bool(person.get("is_coach"))
                    number = None if self._coach_only(payload) else self._normalise_shirt_number(row.get("shirt_number"))
                    if number is not None and number in numbers:
                        raise ValueError(f"El dorsal {number} ya está asignado en este roster")
                    if person is None:
                        person = self.manager_create_player(payload)
                        profiles[key(payload)] = person
                        report["profiles_created"] += 1
                    else:
                        report["profiles_reused"] += 1
                    self.manager_create_roster({"team_id": team_id, "competition_id": competition_id,
                        "player_id": person["id"], "shirt_number": number, "captain": False if self._coach_only(payload) else self._import_bool(row.get("captain"), False),
                        "active": True, "member_type": "coach" if self._coach_only(payload) else "player"})
                    assigned.add(str(person["id"]))
                    if number is not None: numbers.add(number)
                    report["totals"]["created"] += 1
                except Exception as exc:
                    report["totals"]["failed"] += 1
                    report["errors"].append(f"{dataset.get('sheet', '')}, fila {index}: {exc}")
        return report

    def manager_import_rows(self, datasets: list[dict[str, Any]]) -> dict[str, Any]:
        """Import already-confirmed normalized rows into the active workspace.

        The operation is deliberately row-tolerant: valid rows are committed and every
        rejected row is returned in the final report. Re-importing the same workbook
        updates or skips matching records instead of duplicating them where a stable
        natural key exists.
        """
        self._require_competition_manager()
        workspace_id = self._active_workspace_id()
        labels = {
            "seasons": "Temporadas", "competitions": "Competiciones", "teams": "Equipos",
            "players": "Jugadores", "coaches": "Entrenadores", "rosters": "Plantillas",
            "producers": "Usuarios", "matches": "Partidos", "results": "Resultados",
            "events": "Eventos", "visual_identity": "Identidad visual",
        }
        report: dict[str, Any] = {
            "ok": True,
            "totals": {"created": 0, "updated": 0, "skipped": 0, "failed": 0},
            "sections": {},
            "errors": [],
        }

        grouped: dict[str, list[tuple[str, int, dict[str, Any]]]] = {}
        allowed_player_fields = {"player_code", "first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"}
        for dataset in datasets or []:
            # Phase 44 is intentionally player-only. Even if this method is
            # called directly with team/roster data, those scopes and fields
            # are discarded before any write can occur.
            scope = str(dataset.get("scope") or "")
            if scope != "players":
                continue
            sheet = str(dataset.get("sheet") or labels.get(scope) or scope)
            for index, row in enumerate(dataset.get("rows") or [], start=2):
                clean_row = {key: value for key, value in dict(row or {}).items() if key in allowed_player_fields}
                grouped.setdefault("players", []).append((sheet, index, clean_row))

        def section(scope: str) -> dict[str, Any]:
            return report["sections"].setdefault(scope, {
                "label": labels.get(scope, scope), "created": 0, "updated": 0, "skipped": 0, "failed": 0,
            })

        def mark(scope: str, action: str) -> None:
            section(scope)[action] += 1
            report["totals"][action] += 1

        def fail(scope: str, sheet: str, row_number: int, exc: Exception) -> None:
            mark(scope, "failed")
            report["errors"].append(f"{sheet}, fila {row_number}: {exc}")

        def changed(existing: dict[str, Any], payload: dict[str, Any]) -> bool:
            for key, value in payload.items():
                if value is None and existing.get(key) in (None, ""):
                    continue
                if str(existing.get(key) if existing.get(key) is not None else "") != str(value if value is not None else ""):
                    return True
            return False

        season_rows = self.manager_list_seasons()
        seasons_by_name = {self._import_key(item.get("name")): item for item in season_rows}
        season_refs: dict[str, str] = {}
        for sheet, row_number, row in grouped.get("seasons", []):
            try:
                name = str(row.get("name") or row.get("season_code") or "").strip()
                if not name:
                    raise ValueError("Falta el nombre de la temporada")
                key = self._import_key(name)
                item = seasons_by_name.get(key)
                if item:
                    mark("seasons", "skipped")
                else:
                    item = self.manager_create_season({"name": name})
                    seasons_by_name[key] = item
                    mark("seasons", "created")
                item_id = str(item.get("id") or "")
                for ref in (row.get("season_code"), name):
                    if ref not in (None, ""):
                        season_refs[self._import_key(ref)] = item_id
            except Exception as exc:
                fail("seasons", sheet, row_number, exc)
        for item in season_rows:
            season_refs.setdefault(self._import_key(item.get("name")), str(item.get("id") or ""))

        competition_rows = self.manager_list_competitions()
        competition_refs: dict[str, str] = {}
        for item in competition_rows:
            competition_refs[self._import_key(item.get("name"))] = str(item.get("id") or "")
        for sheet, row_number, row in grouped.get("competitions", []):
            try:
                name = str(row.get("name") or row.get("competition_code") or "").strip()
                if not name:
                    raise ValueError("Falta el nombre de la competición")
                season_id = season_refs.get(self._import_key(row.get("season_code"))) if row.get("season_code") else None
                payload = {
                    "name": name,
                    "category": row.get("category"),
                    "season_id": season_id,
                    "active": self._import_bool(row.get("active"), True),
                    "logo_url": row.get("logo_url"),
                    "points_win": self._import_int(row.get("points_win"), 2),
                    "points_draw": self._import_int(row.get("points_draw"), 1),
                    "points_loss": self._import_int(row.get("points_loss"), 0),
                }
                candidate = next((item for item in competition_rows if self._import_key(item.get("name")) == self._import_key(name)
                                  and (not season_id or str(item.get("season_id") or "") == str(season_id))), None)
                if candidate:
                    if changed(candidate, payload):
                        item = self.manager_update_competition(str(candidate.get("id")), payload)
                        candidate.update(item)
                        mark("competitions", "updated")
                    else:
                        item = candidate
                        mark("competitions", "skipped")
                else:
                    item = self.manager_create_competition(payload)
                    competition_rows.append(item)
                    mark("competitions", "created")
                item_id = str(item.get("id") or "")
                for ref in (row.get("competition_code"), name):
                    if ref not in (None, ""):
                        competition_refs[self._import_key(ref)] = item_id
            except Exception as exc:
                fail("competitions", sheet, row_number, exc)

        team_rows = self.manager_list_teams()
        team_refs: dict[str, str] = {}
        for item in team_rows:
            for ref in (item.get("name"), item.get("short_name")):
                if ref:
                    team_refs[self._import_key(ref)] = str(item.get("id") or "")
        for sheet, row_number, row in grouped.get("teams", []):
            try:
                name = str(row.get("name") or row.get("team_code") or "").strip()
                if not name:
                    raise ValueError("Falta el nombre del equipo")
                short_name = str(row.get("short_name") or row.get("team_code") or name[:12]).strip()
                payload = {
                    "name": name, "short_name": short_name,
                    "primary_color": row.get("primary_color") or "#1f2937",
                    "secondary_color": row.get("secondary_color") or "#ffffff",
                    "logo_url": row.get("logo_url"), "alternate_logo_url": row.get("alternate_logo_url"),
                }
                candidate = next((item for item in team_rows if self._import_key(item.get("short_name")) == self._import_key(short_name)
                                  or self._import_key(item.get("name")) == self._import_key(name)), None)
                if candidate:
                    if changed(candidate, payload):
                        item = self.manager_update_team(str(candidate.get("id")), payload)
                        candidate.update(item)
                        mark("teams", "updated")
                    else:
                        item = candidate
                        mark("teams", "skipped")
                else:
                    item = self.manager_create_team(payload)
                    team_rows.append(item)
                    mark("teams", "created")
                item_id = str(item.get("id") or "")
                for ref in (row.get("team_code"), name, short_name):
                    if ref not in (None, ""):
                        team_refs[self._import_key(ref)] = item_id
            except Exception as exc:
                fail("teams", sheet, row_number, exc)

        player_rows = self.manager_list_players()
        player_refs: dict[str, str] = {}
        for item in player_rows:
            for ref in (item.get("display_name"), " ".join(x for x in [item.get("first_name"), item.get("last_name")] if x)):
                if ref:
                    player_refs[self._import_key(ref)] = str(item.get("id") or "")

        def import_people(scope: str, code_field: str, coach: bool = False) -> None:
            for sheet, row_number, row in grouped.get(scope, []):
                try:
                    first_name = str(row.get("first_name") or "").strip()
                    last_name = str(row.get("last_name") or "").strip()
                    display_name = str(row.get("display_name") or " ".join(x for x in [first_name, last_name] if x) or row.get(code_field) or "").strip()
                    if not display_name:
                        raise ValueError("Falta el nombre")
                    payload = {
                        "first_name": first_name or display_name,
                        "last_name": last_name or None,
                        "display_name": display_name,
                        "position": self._import_position(row.get("position"), coach),
                    }
                    payload.update(self._import_person_details(row))
                    payload = self._person_role(payload)
                    candidate = next((item for item in player_rows if all(
                        str(item.get(field) or "").strip() == str(payload.get(field) or "").strip()
                        for field in ("first_name", "last_name", "display_name", "position", "birth_date", "nationality")
                    )), None)
                    if candidate:
                        if changed(candidate, payload):
                            item = self.manager_update_player(str(candidate.get("id")), payload)
                            candidate.update(item)
                            mark(scope, "updated")
                        else:
                            item = candidate
                            mark(scope, "skipped")
                    else:
                        item = self.manager_create_player(payload)
                        player_rows.append(item)
                        mark(scope, "created")
                    item_id = str(item.get("id") or "")
                    for ref in (row.get(code_field), display_name):
                        if ref not in (None, ""):
                            player_refs[self._import_key(ref)] = item_id
                except Exception as exc:
                    fail(scope, sheet, row_number, exc)

        import_people("players", "player_code", False)
        import_people("coaches", "coach_code", True)

        member_rows = self.manager_list_members()
        members_by_email: dict[str, dict[str, Any]] = {}
        for item in member_rows:
            email = str((item.get("profile") or {}).get("email") or "").strip().lower()
            if email:
                members_by_email[email] = item
        for sheet, row_number, row in grouped.get("producers", []):
            try:
                email = str(row.get("email") or "").strip().lower()
                if "@" not in email:
                    raise ValueError("Falta un correo válido")
                role = self._import_role(row.get("role"))
                status = self._import_status(row.get("status"), "member")
                current = members_by_email.get(email)
                if current:
                    desired = {"role": role, "status": status}
                    if changed(current, desired) and str(current.get("role")) != "owner":
                        item = self.manager_update_member(str(current.get("user_id")), desired)
                        current.update(item)
                        mark("producers", "updated")
                    else:
                        mark("producers", "skipped")
                else:
                    self.manager_add_existing_member(email, role)
                    refreshed = self.manager_list_members()
                    current = next((item for item in refreshed if str((item.get("profile") or {}).get("email") or "").lower() == email), None)
                    if current is None:
                        raise ValueError("El usuario se añadió, pero no se pudo recuperar su ficha")
                    if status != "active":
                        updated = self.manager_update_member(str(current.get("user_id")), {"status": status})
                        current.update(updated)
                    members_by_email[email] = current
                    mark("producers", "created")
            except Exception as exc:
                fail("producers", sheet, row_number, exc)

        match_rows = self.manager_list_matches(1000)
        match_refs: dict[str, str] = {}
        for sheet, row_number, row in grouped.get("matches", []):
            try:
                competition_id = competition_refs.get(self._import_key(row.get("competition_code")))
                home_team_id = team_refs.get(self._import_key(row.get("home_team_code")))
                away_team_id = team_refs.get(self._import_key(row.get("away_team_code")))
                match_date = str(row.get("match_date") or "").strip()
                if not competition_id:
                    raise ValueError(f"No se reconoce la competición '{row.get('competition_code') or ''}'")
                if not home_team_id or not away_team_id:
                    raise ValueError("No se reconoce el equipo local o visitante")
                if not match_date:
                    raise ValueError("Falta la fecha del partido")
                producer_email = str(row.get("producer_email") or "").strip().lower()
                assigned_to = str((members_by_email.get(producer_email) or {}).get("user_id") or "") or None
                payload = {
                    "competition_id": competition_id, "match_date": match_date,
                    "venue": row.get("venue"), "home_team_id": home_team_id, "away_team_id": away_team_id,
                    "assigned_to": assigned_to, "status": self._import_status(row.get("status"), "match"),
                }
                candidate = next((item for item in match_rows if str(item.get("competition_id") or "") == competition_id
                                  and str(item.get("home_team_id") or "") == home_team_id
                                  and str(item.get("away_team_id") or "") == away_team_id
                                  and self._import_datetime_key(item.get("match_date")) == self._import_datetime_key(match_date)), None)
                if candidate:
                    if changed(candidate, payload):
                        item = self.manager_update_match(str(candidate.get("id")), payload)
                        candidate.update(item)
                        mark("matches", "updated")
                    else:
                        item = candidate
                        mark("matches", "skipped")
                else:
                    item = self.manager_create_match(payload)
                    match_rows.append(item)
                    mark("matches", "created")
                if row.get("match_code") not in (None, ""):
                    match_refs[self._import_key(row.get("match_code"))] = str(item.get("id") or "")
            except Exception as exc:
                fail("matches", sheet, row_number, exc)

        roster_rows = (
            self.client.table("rosters").select("id,competition_id,team_id,player_id,shirt_number,captain,active,member_type")
            .eq("workspace_id", workspace_id).eq("active", True).execute().data or []
        )
        roster_index = {(str(item.get("competition_id")), str(item.get("team_id")), str(item.get("player_id"))): item for item in roster_rows}
        for sheet, row_number, row in grouped.get("rosters", []):
            try:
                competition_id = competition_refs.get(self._import_key(row.get("competition_code")))
                team_id = team_refs.get(self._import_key(row.get("team_code")))
                player_ref = row.get("player_code") or row.get("coach_code")
                player_id = player_refs.get(self._import_key(player_ref))
                if not competition_id or not team_id or not player_id:
                    raise ValueError("No se reconoce la competición, el equipo o el jugador")
                member_type = "coach" if self._import_key(row.get("member_type")) in {"coach", "entrenador"} else "player"
                payload = {
                    "competition_id": competition_id, "team_id": team_id, "player_id": player_id,
                    "shirt_number": None if member_type == "coach" or row.get("shirt_number") in (None, "") else self._import_int(row.get("shirt_number")),
                    "captain": self._import_bool(row.get("captain"), False),
                    "member_type": member_type, "active": self._import_bool(row.get("active"), True),
                }
                key = (competition_id, team_id, player_id)
                candidate = roster_index.get(key)
                if candidate:
                    if changed(candidate, payload):
                        item = self.manager_update_roster(str(candidate.get("id")), payload)
                        candidate.update(item)
                        mark("rosters", "updated")
                    else:
                        mark("rosters", "skipped")
                else:
                    item = self.manager_create_roster(payload)
                    roster_index[key] = item
                    mark("rosters", "created")
            except Exception as exc:
                fail("rosters", sheet, row_number, exc)

        for sheet, row_number, row in grouped.get("results", []):
            try:
                match_id = match_refs.get(self._import_key(row.get("match_code")))
                if not match_id:
                    raise ValueError(f"No se reconoce el partido '{row.get('match_code') or ''}'")
                payload = {
                    "home_score": self._import_int(row.get("home_score"), 0),
                    "away_score": self._import_int(row.get("away_score"), 0),
                    "status": self._import_status(row.get("status") or "finished", "match"),
                }
                self.manager_update_match(match_id, payload)
                mark("results", "updated")
            except Exception as exc:
                fail("results", sheet, row_number, exc)

        theme_rows = self.manager_list_themes()
        for sheet, row_number, row in grouped.get("visual_identity", []):
            try:
                competition_id = competition_refs.get(self._import_key(row.get("competition_code"))) if row.get("competition_code") else None
                name = str(row.get("name") or "Identidad importada").strip()
                config = {
                    "scoreboard": {
                        "background": row.get("primary_color") or "#2a2d34",
                        "name_box": row.get("secondary_color") or "#3b3f47",
                        "text": "#ffffff",
                    },
                    "bottom_bar": {
                        "body": row.get("primary_color") or "#24272e",
                        "middle": row.get("secondary_color") or "#30333b",
                        "text": "#ffffff", "secondary_text": "#c6cad2",
                    },
                    "panels": {
                        "background": row.get("primary_color") or "#171c25",
                        "surface": row.get("secondary_color") or "#232a35",
                        "accent": row.get("accent_color") or "#59606c",
                        "text": "#ffffff",
                    },
                }
                published = self._import_bool(row.get("published"), False)
                locked = self._import_bool(row.get("locked"), True)
                candidate = next((item for item in theme_rows if self._import_key(item.get("name")) == self._import_key(name)
                                  and str(item.get("competition_id") or "") == str(competition_id or "")), None)
                if candidate and candidate.get("config") == config and bool(candidate.get("published")) == published and bool(candidate.get("locked")) == locked:
                    mark("visual_identity", "skipped")
                else:
                    item = self.manager_create_theme({"competition_id": competition_id, "name": name, "config": config, "published": published, "locked": locked})
                    theme_rows.append(item)
                    mark("visual_identity", "created")
            except Exception as exc:
                fail("visual_identity", sheet, row_number, exc)

        event_type_map = {
            "gol": "goal", "goal": "goal", "asistencia": "assist", "assist": "assist",
            "penalizacion": "penalty", "penalty": "penalty", "expulsion": "penalty",
        }
        for sheet, row_number, row in grouped.get("events", []):
            try:
                match_id = match_refs.get(self._import_key(row.get("match_code")))
                team_id = team_refs.get(self._import_key(row.get("team_code")))
                player_id = player_refs.get(self._import_key(row.get("player_code"))) if row.get("player_code") else None
                if not match_id or not team_id:
                    raise ValueError("No se reconoce el partido o el equipo")
                event_key = self._import_key(row.get("event_type"))
                event_type = event_type_map.get(event_key, event_key or "event")
                minute = self._import_int(row.get("minute"), 0)
                second = self._import_int(row.get("second"), 0)
                match_time = f"{minute:02d}:{second:02d}"
                duplicate = (
                    self.client.table("match_events").select("id").eq("match_id", match_id).eq("team_id", team_id)
                    .eq("event_type", event_type).eq("match_time", match_time)
                )
                duplicate = duplicate.eq("player_id", player_id) if player_id else duplicate.is_("player_id", "null")
                if duplicate.limit(1).execute().data:
                    mark("events", "skipped")
                    continue
                assist_id = player_refs.get(self._import_key(row.get("assist_player_code"))) if row.get("assist_player_code") else None
                if event_type == "goal" and player_id:
                    self.create_goal_with_assist(match_id=match_id, team_id=team_id, scorer_id=player_id, assistant_id=assist_id, match_time=match_time)
                else:
                    penalty_type = str(row.get("penalty_type") or "").strip() or None
                    self.create_event(
                        match_id=match_id, team_id=team_id, player_id=player_id, event_type=event_type,
                        match_time=match_time, penalty_type=penalty_type,
                        penalty_minutes=self._import_int(penalty_type.split("+")[0], 0) if penalty_type and penalty_type.split("+")[0].isdigit() else None,
                    )
                mark("events", "created")
            except Exception as exc:
                fail("events", sheet, row_number, exc)

        report["ok"] = report["totals"]["failed"] == 0
        report["message"] = "Importación completada" if report["ok"] else "Importación completada con filas pendientes de revisión"
        return report

    def upload_workspace_asset(
        self,
        image_bytes: bytes,
        content_type: str,
        asset_kind: str = "logos",
        extension: str = "png",
    ) -> dict[str, Any]:
        self._require_competition_manager()
        if not image_bytes:
            raise ValueError("No se ha recibido ningún archivo")
        if len(image_bytes) > 10 * 1024 * 1024:
            raise ValueError("El archivo supera el límite de 10 MB")
        allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}
        mime = str(content_type or "").split(";", 1)[0].strip().lower()
        if mime not in allowed:
            raise ValueError("Formato no compatible. Utiliza PNG, JPG, WEBP o SVG")
        clean_kind = "".join(ch for ch in str(asset_kind or "assets").lower() if ch.isalnum() or ch in {"-", "_"}) or "assets"
        ext = allowed[mime]
        object_path = f"{self._active_workspace_id()}/{clean_kind}/{uuid4().hex}.{ext}"
        bucket = self.client.storage.from_(WORKSPACE_ASSETS_BUCKET)
        bucket.upload(
            file=image_bytes,
            path=object_path,
            file_options={"cache-control": "31536000", "content-type": mime, "upsert": "false"},
        )
        public_url = self._public_url_value(bucket.get_public_url(object_path))
        if not public_url:
            raise RuntimeError("Supabase no devolvió la URL pública del recurso")
        return {"url": public_url, "path": object_path, "content_type": mime}

    def published_visual_theme(self, competition_id: str = "") -> dict[str, Any]:
        """Return the published competition theme, falling back to the workspace theme."""
        workspace_id = self._active_workspace_id()
        clean_competition = str(competition_id or "").strip()
        if clean_competition:
            rows = (
                self.client.table("sp_visual_themes")
                .select("id,workspace_id,competition_id,name,config,version,published,locked,updated_at")
                .eq("workspace_id", workspace_id)
                .eq("competition_id", clean_competition)
                .eq("published", True)
                .order("version", desc=True)
                .limit(1)
                .execute()
            ).data or []
            if rows:
                return dict(rows[0])
        rows = (
            self.client.table("sp_visual_themes")
            .select("id,workspace_id,competition_id,name,config,version,published,locked,updated_at")
            .eq("workspace_id", workspace_id)
            .is_("competition_id", "null")
            .eq("published", True)
            .order("version", desc=True)
            .limit(1)
            .execute()
        ).data or []
        return dict(rows[0]) if rows else {}

    def list_competitions(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("competitions")
            .select(
                "id,workspace_id,name,category,season_id,active,logo_url,points_win,points_draw,points_loss,"
                "seasons(name)"
            )
        )
        workspace_id = str((self.active_workspace or {}).get("id") or "")
        if workspace_id:
            response = response.eq("workspace_id", workspace_id)
        response = (
            response.eq("active", True)
            .order("name")
            .execute()
        )
        return response.data or []

    def list_matches(
        self,
        competition_id: str,
        local_day: date | None = None,
        timezone_name: str = "Europe/Madrid",
    ) -> list[dict[str, Any]]:
        """Return only today's matches assigned to the logged-in operator.

        ``match_date`` is a timestamptz in Supabase. The day boundaries are
        calculated in Europe/Madrid and converted to UTC before filtering, so
        late matches are not lost when daylight-saving time changes.
        """
        if not self.user_id:
            raise RuntimeError("Debes iniciar sesión antes de consultar partidos")

        tz = ZoneInfo(timezone_name)
        selected_day = local_day or datetime.now(tz).date()
        start_local = datetime.combine(selected_day, dt_time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(timezone.utc).isoformat()
        end_utc = end_local.astimezone(timezone.utc).isoformat()

        response = (
            self.client.table("matches")
            .select(
                "id,workspace_id,competition_id,match_date,time_confirmed,scheduled_date,venue,status,home_score,away_score,assigned_to,broadcast_enabled,"
                "assigned_operator:scoreboard_operators!matches_assigned_to_fkey("
                "id,email,display_name),"
                "home_team:teams!matches_home_team_id_fkey("
                "id,name,short_name,logo_url,alternate_logo_url,primary_color,secondary_color),"
                "away_team:teams!matches_away_team_id_fkey("
                "id,name,short_name,logo_url,alternate_logo_url,primary_color,secondary_color)"
            )
            .eq("competition_id", competition_id)
        )
        role = str((self.active_membership or {}).get("role") or "producer")
        assignment_mode = str((self.active_workspace or {}).get("assignment_mode") or "assigned")
        if role == "producer" and assignment_mode == "assigned":
            response = response.eq("assigned_to", self.user_id)
        response = response.eq("broadcast_enabled", True)
        response = (
            response.gte("match_date", start_utc)
            .lt("match_date", end_utc)
            .order("match_date")
            .execute()
        )
        return response.data or []

    def list_roster(self, competition_id: str, team_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("rosters")
            .select(
                "id,team_id,player_id,shirt_number,captain,active,member_type,"
                "player:players!rosters_player_id_fkey("
                "id,first_name,last_name,display_name,position,birth_date,nationality,is_coach)"
            )
            .eq("competition_id", competition_id)
            .eq("team_id", team_id)
            .eq("active", True)
            .order("shirt_number")
            .execute()
        )
        rows = response.data or []
        for row in rows:
            position = (row.get("player") or {}).get("position")
            if str(position or "").endswith("_coach"): row["member_type"] = "player"
            elif self._coach_only(row.get("player") or {}): row["member_type"] = "coach"
            else: row["member_type"] = "player"
        return rows

    def list_team_coaches(self, team_id: str) -> list[dict[str, Any]]:
        """Return active coaches for a team, regardless of competition.

        This is a fallback for teams whose coach was created in a different
        competition roster than the currently loaded match.
        """
        response = (
            self.client.table("rosters")
            .select(
                "id,team_id,competition_id,player_id,shirt_number,captain,active,member_type,"
                "player:players!rosters_player_id_fkey("
                "id,first_name,last_name,display_name,position,birth_date,nationality,is_coach)"
            )
            .eq("team_id", team_id)
            .eq("active", True)
            .execute()
        )
        rows = response.data or []
        return [row for row in rows if bool((row.get("player") or {}).get("is_coach")) or row.get("member_type") == "coach"
                or (row.get("player") or {}).get("position") == "coach"
                or str((row.get("player") or {}).get("position") or "").endswith("_coach")]

    def list_match_players(self, match_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("match_players")
            .select(
                "id,match_id,team_id,player_id,shirt_number,starter,played,"
                "player:players!match_players_player_id_fkey("
                "id,first_name,last_name,display_name,position,birth_date,nationality,is_coach)"
            )
            .eq("match_id", match_id)
            .order("shirt_number")
            .execute()
        )
        return response.data or []

    def save_match_players(
        self,
        match_id: str,
        team_id: str,
        roster_rows: list[dict[str, Any]],
        selected_player_ids: set[str],
    ) -> None:
        payload = []
        for row in roster_rows:
            player_id = str(row.get("player_id") or "")
            if not player_id:
                continue
            payload.append(
                {
                    "workspace_id": str((self.active_workspace or {}).get("id") or "") or None,
                    "match_id": match_id,
                    "team_id": team_id,
                    "player_id": player_id,
                    "shirt_number": row.get("shirt_number"),
                    "played": player_id in selected_player_ids,
                    "starter": False,
                }
            )
        if payload:
            self.client.table("match_players").upsert(
                payload, on_conflict="match_id,player_id"
            ).execute()

    def create_event(
        self,
        *,
        match_id: str,
        team_id: str,
        player_id: str | None,
        event_type: str,
        match_time: str = "",
        related_event_id: str | None = None,
        penalty_type: str | None = None,
        penalty_minutes: int | None = None,
        team_penalty_seconds: int | None = None,
        personal_penalty_minutes: int | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "workspace_id": str((self.active_workspace or {}).get("id") or "") or None,
            "match_id": match_id,
            "team_id": team_id,
            "player_id": player_id or None,
            "event_type": event_type,
            "match_time": match_time or None,
            "related_event_id": related_event_id,
            "penalty_type": penalty_type,
            "penalty_minutes": penalty_minutes,
            "team_penalty_seconds": team_penalty_seconds,
            "personal_penalty_minutes": personal_penalty_minutes,
            "notes": notes or None,
            "created_by": self.user_id or None,
        }
        response = self.client.table("match_events").insert(payload).execute()
        if not response.data:
            raise RuntimeError("Supabase no devolvió el evento creado")
        return response.data[0]

    def create_goal_with_assist(
        self,
        *,
        match_id: str,
        team_id: str,
        scorer_id: str,
        assistant_id: str | None,
        match_time: str = "",
        goal_notes: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        goal = self.create_event(
            match_id=match_id,
            team_id=team_id,
            player_id=scorer_id,
            event_type="goal",
            match_time=match_time,
            notes=goal_notes,
        )
        assist = None
        if assistant_id:
            assist = self.create_event(
                match_id=match_id,
                team_id=team_id,
                player_id=assistant_id,
                event_type="assist",
                match_time=match_time,
                related_event_id=goal["id"],
            )
        return goal, assist

    def list_events(self, match_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("match_events")
            .select(
                "id,team_id,player_id,event_type,match_time,penalty_type,penalty_minutes,created_at,"
                "cancelled_at,related_event_id,notes,"
                "team:teams!match_events_team_id_fkey(id,name,short_name),"
                "player:players!match_events_player_id_fkey("
                "id,first_name,last_name,display_name)"
            )
            .eq("match_id", match_id)
            .is_("cancelled_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def cancel_event(self, event_id: str) -> None:
        self.client.table("match_events").update(
            {
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "cancelled_by": self.user_id or None,
            }
        ).eq("id", event_id).execute()

    def get_standings(self, competition_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("competition_standings")
            .select("*")
            .eq("competition_id", competition_id)
            .order("position")
            .execute()
        )
        return response.data or []


    def get_team_top_scorers(self, competition_id: str, team_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Return the leading point scorer for each requested team.

        Points are goals + assists from non-cancelled match_events in the
        selected competition. No duplicated aggregate table is required.
        """
        result: dict[str, dict[str, Any]] = {str(tid): {} for tid in team_ids if tid}
        match_rows = (
            self.client.table("matches")
            .select("id")
            .eq("competition_id", competition_id)
            .execute()
        ).data or []
        match_ids = [str(row.get("id")) for row in match_rows if row.get("id")]
        if not match_ids or not result:
            return result

        events = (
            self.client.table("match_events")
            .select(
                "team_id,player_id,event_type,cancelled_at,"
                "player:players!match_events_player_id_fkey("
                "id,first_name,last_name,display_name,position,birth_date,nationality,is_coach)"
            )
            .in_("match_id", match_ids)
            .in_("team_id", list(result.keys()))
            .in_("event_type", ["goal", "assist"])
            .is_("cancelled_at", "null")
            .execute()
        ).data or []

        totals: dict[tuple[str, str], dict[str, Any]] = {}
        for event in events:
            team_id = str(event.get("team_id") or "")
            player_id = str(event.get("player_id") or "")
            if not team_id or not player_id:
                continue
            key = (team_id, player_id)
            row = totals.setdefault(key, {
                "team_id": team_id, "player_id": player_id,
                "goals": 0, "assists": 0, "points": 0,
                "player": event.get("player") or {},
            })
            if event.get("event_type") == "goal":
                row["goals"] += 1
            elif event.get("event_type") == "assist":
                row["assists"] += 1
            row["points"] = row["goals"] + row["assists"]

        for team_id in result:
            candidates = [v for (tid, _), v in totals.items() if tid == team_id]
            if candidates:
                result[team_id] = max(
                    candidates,
                    key=lambda x: (x["points"], x["goals"], x["assists"]),
                )
        return result


    def get_player_profile_stats(self, player_id: str, competition_id: str) -> dict[str, Any]:
        """Return player profile and competition totals without relying on an aggregate table."""
        player_rows = (
            self.client.table("players")
            .select("*")
            .eq("id", player_id)
            .limit(1)
            .execute()
        ).data or []
        player = player_rows[0] if player_rows else {}

        match_rows = (
            self.client.table("matches")
            .select("id")
            .eq("competition_id", competition_id)
            .execute()
        ).data or []
        match_ids = [str(row.get("id")) for row in match_rows if row.get("id")]

        played = 0
        goals = 0
        assists = 0
        if match_ids:
            played_rows = (
                self.client.table("match_players")
                .select("match_id,played")
                .eq("player_id", player_id)
                .in_("match_id", match_ids)
                .eq("played", True)
                .execute()
            ).data or []
            played = len({str(row.get("match_id")) for row in played_rows if row.get("match_id")})

            events = (
                self.client.table("match_events")
                .select("event_type")
                .eq("player_id", player_id)
                .in_("match_id", match_ids)
                .in_("event_type", ["goal", "assist"])
                .is_("cancelled_at", "null")
                .execute()
            ).data or []
            goals = sum(1 for row in events if row.get("event_type") == "goal")
            assists = sum(1 for row in events if row.get("event_type") == "assist")

        return {"player": player, "played": played, "goals": goals, "assists": assists}

    def finish_match(
        self,
        match_id: str,
        home_score: int,
        away_score: int,
    ) -> dict[str, Any]:
        if home_score < 0 or away_score < 0:
            raise ValueError("El resultado no puede contener valores negativos")
        response = (
            self.client.table("matches")
            .update(
                {
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "status": "finished",
                }
            )
            .eq("id", match_id)
            .execute()
        )
        if not response.data:
            raise RuntimeError("No se pudo finalizar el partido")
        return response.data[0]
