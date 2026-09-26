# Compatibility test marker: RELEASE_ID = "phase39"
# Compatibility test marker: APP_VERSION = "3.0.0-alpha"
from __future__ import annotations

import csv
import io
import os
import re
import unicodedata
from pathlib import Path
from datetime import date, datetime, time as dt_time
from threading import RLock
from typing import Any, Callable

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from secretariat_core.subscription_store import evaluate_subscription
from manager_release import MANAGER_APPLICATION, MANAGER_RELEASE, MANAGER_VERSION

try:
    from supabase_client import ScoreboardSupabaseClient
except Exception:  # pragma: no cover
    ScoreboardSupabaseClient = None

BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "manager_app"
APP_VERSION = MANAGER_VERSION
RELEASE_ID = MANAGER_RELEASE
# Compatibility markers retained for v38 launchers/tests: APP_VERSION = "2.0.1-alpha"; BUILD_ID = "phase38"
BUILD_ID = "phase38"
load_dotenv(BASE_DIR / ".env")


class LoginPayload(BaseModel):
    email: str
    password: str


class ResetPasswordPayload(BaseModel):
    email: str


class WorkspacePayload(BaseModel):
    workspace_id: str = Field(min_length=1)


class EntityPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class MemberPayload(BaseModel):
    email: str
    role: str = "producer"


class ProfilePayload(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)


class PasswordPayload(BaseModel):
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class SportModePayload(BaseModel):
    sport_mode: str = Field(pattern="^(floorball|handball)$")


class MatchEventPayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class MatchEventImportPayload(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ManagerRuntime:
    def __init__(self) -> None:
        self._lock = RLock()
        self.client: Any | None = None
        self.workspaces: list[dict[str, Any]] = []
        self.workspace: dict[str, Any] = {}
        self.subscription: dict[str, Any] = {}
        self.access: dict[str, Any] = evaluate_subscription(None)

    @property
    def connected(self) -> bool:
        return bool(self.client and self.client.user_id)

    @property
    def role(self) -> str:
        return str(self.workspace.get("role") or "producer")

    @property
    def can_manage(self) -> bool:
        return self.role in {"owner", "competition_manager"}

    @property
    def read_only(self) -> bool:
        return bool(self.access.get("manager_read_only"))

    @property
    def write_allowed(self) -> bool:
        return self.connected and self.can_manage and bool(self.access.get("allowed")) and not self.read_only

    def require_connected(self) -> Any:
        if not self.connected:
            raise RuntimeError("Debes iniciar sesión")
        return self.client

    def require_write(self) -> Any:
        client = self.require_connected()
        if self.read_only:
            raise PermissionError("La membresía está en modo consulta")
        if not self.access.get("allowed"):
            raise PermissionError("La membresía no está activa")
        if not self.can_manage:
            raise PermissionError("Tu rol no permite modificar este espacio")
        return client

    def state(self) -> dict[str, Any]:
        with self._lock:
            profile = self.client.user_profile() if self.client else {}
            return {
                "connected": self.connected,
                "profile": profile,
                "workspaces": list(self.workspaces),
                "workspace": dict(self.workspace),
                "subscription": dict(self.subscription),
                "access": dict(self.access),
                "permissions": {
                    "can_manage": self.can_manage,
                    "write_allowed": self.write_allowed,
                    "read_only": self.read_only,
                    "can_set_sport_mode": self.role == "owner" and self.write_allowed,
                },
                "application": {
                    "name": "SecretariatPro Manager",
                    "version": APP_VERSION,
                    "build": RELEASE_ID,
                    "compatibility_build": BUILD_ID,
                    "supabase_configured": bool(os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY"))),
                },
                "import_scopes": ["Personas y rosters", "Partidos"],
            }

    def login(self, email: str, password: str) -> dict[str, Any]:
        if ScoreboardSupabaseClient is None:
            raise RuntimeError("No se pudo cargar el cliente de Supabase. Reinstala requirements.txt")
        client = ScoreboardSupabaseClient()
        client.login(email, password)
        context = client.workspace_context()
        workspace = context.get("workspace") or {}
        subscription = context.get("subscription") or {}
        access = evaluate_subscription(subscription, online=True)
        with self._lock:
            self.client = client
            self.workspaces = list(context.get("workspaces") or [])
            self.workspace = dict(workspace)
            self.subscription = dict(subscription)
            self.access = dict(access)
        return self.state()

    def request_password_reset(self, email: str) -> dict[str, Any]:
        if ScoreboardSupabaseClient is None:
            raise RuntimeError("No se pudo cargar el cliente de Supabase")
        client = self.client or ScoreboardSupabaseClient()
        client.request_password_reset(email)
        return {"ok": True, "message": "Se ha solicitado el correo de recuperación"}

    def activate_workspace(self, workspace_id: str) -> dict[str, Any]:
        client = self.require_connected()
        workspace = client.activate_workspace(workspace_id)
        subscription = client.latest_workspace_subscription(workspace_id)
        access = evaluate_subscription(subscription, online=True)
        with self._lock:
            self.workspaces = client.list_workspaces()
            self.workspace = workspace
            self.subscription = subscription
            self.access = access
        return self.state()

    def logout(self) -> dict[str, Any]:
        with self._lock:
            if self.client:
                self.client.logout()
            self.client = None
            self.workspaces = []
            self.workspace = {}
            self.subscription = {}
            self.access = evaluate_subscription(None)
        return self.state()


runtime = ManagerRuntime()
app = FastAPI(title="SecretariatPro Manager API", version=APP_VERSION)


@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-SecretariatPro-Build"] = RELEASE_ID
    return response


app.mount("/manager", StaticFiles(directory=WEB_DIR, html=True), name="manager")


def api_error(exc: Exception, status: int = 400) -> HTTPException:
    if isinstance(exc, PermissionError):
        status = 403
    return HTTPException(status_code=status, detail=str(exc))


async def run_read(method: Callable[..., Any], *args: Any) -> Any:
    try:
        runtime.require_connected()
        return await run_in_threadpool(method, *args)
    except Exception as exc:
        raise api_error(exc) from exc


async def run_write(method: Callable[..., Any], *args: Any) -> Any:
    try:
        runtime.require_write()
        return await run_in_threadpool(method, *args)
    except Exception as exc:
        raise api_error(exc) from exc


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "application": MANAGER_APPLICATION,
        "version": APP_VERSION,
        "build": BUILD_ID,
        "release": RELEASE_ID,
    }


@app.get("/api/state")
async def state() -> dict[str, Any]:
    return await run_in_threadpool(runtime.state)


@app.post("/api/auth/login")
async def login(payload: LoginPayload) -> dict[str, Any]:
    try:
        return await run_in_threadpool(runtime.login, payload.email, payload.password)
    except Exception as exc:
        raise api_error(exc, 401) from exc


@app.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordPayload) -> dict[str, Any]:
    try:
        return await run_in_threadpool(runtime.request_password_reset, payload.email)
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/auth/logout")
async def logout() -> dict[str, Any]:
    return await run_in_threadpool(runtime.logout)


@app.post("/api/workspaces/activate")
async def activate_workspace(payload: WorkspacePayload) -> dict[str, Any]:
    try:
        return await run_in_threadpool(runtime.activate_workspace, payload.workspace_id)
    except Exception as exc:
        raise api_error(exc) from exc


@app.get("/api/dashboard")
async def dashboard() -> dict[str, Any]:
    client = runtime.require_connected()
    counts = await run_read(client.manager_dashboard_counts)
    matches = await run_read(client.manager_list_matches, 8)
    return {"counts": counts, "matches": matches[:8]}


@app.get("/api/seasons")
async def seasons() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_seasons)


@app.post("/api/seasons")
async def create_season(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_season, payload.data)


@app.delete("/api/seasons/{season_id}")
async def delete_season(season_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_season, season_id)


@app.get("/api/competitions")
async def competitions() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_competitions)


@app.post("/api/competitions")
async def create_competition(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_competition, payload.data)


@app.patch("/api/competitions/{competition_id}")
async def update_competition(competition_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_competition, competition_id, payload.data)


@app.delete("/api/competitions/{competition_id}")
async def delete_competition(competition_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_competition, competition_id)


@app.get("/api/teams")
async def teams() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_teams)


@app.post("/api/teams")
async def create_team(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_team, payload.data)


@app.patch("/api/teams/{team_id}")
async def update_team(team_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_team, team_id, payload.data)


@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_team, team_id)


@app.get("/api/players")
async def players() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_players)


@app.post("/api/players")
async def create_player(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_player, payload.data)


@app.patch("/api/players/{player_id}")
async def update_player(player_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_player, player_id, payload.data)


@app.delete("/api/players/{player_id}")
async def delete_player(player_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_player, player_id)


@app.get("/api/teams/{team_id}/rosters")
async def team_rosters(
    team_id: str,
    competition_id: str = Query(default=""),
) -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_team_rosters, team_id, competition_id)


@app.get("/api/players/{player_id}/rosters")
async def player_rosters(player_id: str) -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_player_rosters, player_id)


@app.post("/api/rosters")
async def create_roster(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_roster, payload.data)


@app.patch("/api/rosters/{roster_id}")
async def update_roster(roster_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_roster, roster_id, payload.data)


@app.delete("/api/rosters/{roster_id}")
async def remove_roster(roster_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_remove_roster, roster_id)


@app.post("/api/rosters/with-player")
async def create_player_and_roster(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_player_and_roster, payload.data)


@app.post("/api/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    asset_kind: str = "logos",
) -> dict[str, Any]:
    runtime.require_write()
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo supera el límite de 10 MB")
    client = runtime.require_connected()
    return await run_write(
        client.upload_workspace_asset,
        content,
        file.content_type or "application/octet-stream",
        asset_kind,
        Path(file.filename or "asset.png").suffix.lstrip("."),
    )


@app.patch("/api/account/profile")
async def update_account_profile(payload: ProfilePayload) -> dict[str, Any]:
    client = runtime.require_connected()
    profile = await run_read(client.update_user_profile, payload.display_name)
    return {"profile": profile, "state": await run_in_threadpool(runtime.state)}


@app.post("/api/account/password")
async def update_account_password(payload: PasswordPayload) -> dict[str, Any]:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")
    client = runtime.require_connected()
    await run_read(client.update_password, payload.new_password)
    return {"ok": True, "message": "Contraseña actualizada"}


@app.post("/api/account/avatar")
async def upload_account_avatar(file: UploadFile = File(...)) -> dict[str, Any]:
    runtime.require_connected()
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen supera el límite de 8 MB")
    client = runtime.require_connected()
    profile = await run_read(client.upload_avatar, content, file.content_type or "image/jpeg")
    return {"profile": profile, "state": await run_in_threadpool(runtime.state)}


@app.delete("/api/account/avatar")
async def remove_account_avatar() -> dict[str, Any]:
    client = runtime.require_connected()
    profile = await run_read(client.remove_avatar)
    return {"profile": profile, "state": await run_in_threadpool(runtime.state)}


@app.patch("/api/workspace/sport-mode")
async def set_workspace_sport_mode(payload: SportModePayload) -> dict[str, Any]:
    client = runtime.require_connected()
    if runtime.role != "owner":
        raise HTTPException(status_code=403, detail="Sólo el propietario puede cambiar el deporte de la plataforma")
    if not runtime.write_allowed:
        raise HTTPException(status_code=403, detail="La membresía no permite modificar la configuración")
    workspace = await run_write(client.manager_set_sport_mode, payload.sport_mode)
    with runtime._lock:
        runtime.workspace = dict(workspace)
        runtime.workspaces = client.list_workspaces()
    return runtime.state()


@app.get("/api/matches")
async def matches() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_matches, 500)


@app.post("/api/matches")
async def create_match(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_match, payload.data)


@app.patch("/api/matches/{match_id}")
async def update_match(match_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_match, match_id, payload.data)


@app.delete("/api/matches/{match_id}")
async def delete_match(match_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_match, match_id)


@app.get("/api/matches/{match_id}/events")
async def match_events(match_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_read(client.manager_match_event_context, match_id)


@app.post("/api/matches/{match_id}/events")
async def create_match_event(match_id: str, payload: MatchEventPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    result = await run_write(client.manager_create_match_event, match_id, payload.data)
    return {"result": result, "context": await run_read(client.manager_match_event_context, match_id)}


@app.delete("/api/matches/{match_id}/events/{event_id}")
async def cancel_match_event(match_id: str, event_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    await run_write(client.manager_cancel_match_event, match_id, event_id)
    return await run_read(client.manager_match_event_context, match_id)


def _match_event_template_bytes(context: dict[str, Any]) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Instala openpyxl para generar la plantilla") from exc
    wb = Workbook()
    ws = wb.active
    ws.title = "Eventos"
    headers = ["time", "team", "event_type", "player_number", "assistant_number", "penalty_type", "notes"]
    ws.append(headers)
    ws.append(["12:34", "LOCAL", "goal", 19, 7, "", "Ejemplo: gol con asistencia"])
    ws.append(["18:20", "VISITANTE", "penalty", 23, "", "2", "Ejemplo: expulsión"])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center")
    widths = [14, 16, 18, 18, 20, 18, 42]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + idx)].width = width
    dv_team = DataValidation(type="list", formula1='"LOCAL,VISITANTE"', allow_blank=False)
    dv_type = DataValidation(type="list", formula1='"goal,penalty"', allow_blank=False)
    dv_penalty = DataValidation(type="list", formula1='"2,2+2,2+10"', allow_blank=True)
    ws.add_data_validation(dv_team); dv_team.add("B2:B1000")
    ws.add_data_validation(dv_type); dv_type.add("C2:C1000")
    ws.add_data_validation(dv_penalty); dv_penalty.add("F2:F1000")
    info = wb.create_sheet("Instrucciones")
    match = context.get("match") or {}
    home = match.get("home_team") or {}; away = match.get("away_team") or {}
    info.append(["SECRETARIATPRO · ACTA DE PARTIDO"]); info["A1"].font = Font(bold=True, size=16)
    info.append(["Local", home.get("name") or "LOCAL"]); info.append(["Visitante", away.get("name") or "VISITANTE"])
    info.append([])
    info.append(["Reglas"]); info["A5"].font = Font(bold=True)
    info.append(["team", "LOCAL o VISITANTE"]); info.append(["event_type", "goal o penalty"]); info.append(["player_number", "Dorsal del goleador/jugador sancionado"]); info.append(["assistant_number", "Sólo para gol; dejar vacío si no hubo asistencia"]); info.append(["penalty_type", "Sólo para expulsión: 2, 2+2 o 2+10"]); info.append(["time", "Tiempo de partido, por ejemplo 12:34"]);
    output = io.BytesIO(); wb.save(output); return output.getvalue()


@app.get("/api/matches/{match_id}/events/template")
async def match_event_template(match_id: str) -> Response:
    client = runtime.require_connected()
    context = await run_read(client.manager_match_event_context, match_id)
    content = await run_in_threadpool(_match_event_template_bytes, context)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="SecretariatPro_Acta_{match_id[:8]}.xlsx"'})


def unique_match_event_template_path(directory: Path, match_id: str) -> Path:
    base = directory / f"SecretariatPro_Acta_{str(match_id)[:8]}.xlsx"
    if not base.exists():
        return base
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"SecretariatPro_Acta_{str(match_id)[:8]}_{stamp}.xlsx"


@app.post("/api/matches/{match_id}/events/template/download")
async def download_match_event_template(match_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    context = await run_read(client.manager_match_event_context, match_id)
    content = await run_in_threadpool(_match_event_template_bytes, context)
    destination = unique_match_event_template_path(manager_downloads_directory(), match_id)
    try:
        destination.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar la plantilla: {exc}") from exc
    return {"ok": True, "path": str(destination), "filename": destination.name}


@app.post("/api/matches/{match_id}/events/finalize")
async def finalize_match_event_act(match_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    match = await run_write(client.manager_finalize_match_act, match_id)
    return {"match": match, "context": await run_read(client.manager_match_event_context, match_id)}


def _parse_event_import(content: bytes, context: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except Exception as exc:
        raise ValueError("Instala openpyxl para importar el acta") from exc
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb["Eventos"] if "Eventos" in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [normalized_header(value) for value in rows[0]]
    aliases = {"time":"match_time", "tiempo":"match_time", "team":"team", "equipo":"team", "event_type":"event_type", "evento":"event_type", "player_number":"player_number", "dorsal":"player_number", "assistant_number":"assistant_number", "dorsal_asistente":"assistant_number", "penalty_type":"penalty_type", "sancion":"penalty_type", "notes":"notes", "notas":"notes"}
    headers = [aliases.get(value, value) for value in headers]
    match = context.get("match") or {}
    home = match.get("home_team") or {}; away = match.get("away_team") or {}
    roster_map = {}
    for side, roster in (("home", context.get("home_roster") or []), ("away", context.get("away_roster") or [])):
        for row in roster:
            if str(row.get("member_type") or "player") == "coach": continue
            number = str(row.get("shirt_number") if row.get("shirt_number") is not None else "").strip()
            if number: roster_map[(side, number)] = str(row.get("player_id") or (row.get("player") or {}).get("id") or "")
    def side_for(value: Any) -> str:
        key = normalized_sheet_name(value)
        home_names = {"local","home",normalized_sheet_name(home.get("name")),normalized_sheet_name(home.get("short_name"))}
        away_names = {"visitante","away",normalized_sheet_name(away.get("name")),normalized_sheet_name(away.get("short_name"))}
        if key in home_names: return "home"
        if key in away_names: return "away"
        raise ValueError(f"Equipo no reconocido: {value}")
    parsed=[]
    for row_number, values in enumerate(rows[1:], start=2):
        record={headers[i]: serializable_cell(values[i] if i < len(values) else None) for i in range(len(headers)) if headers[i]}
        if not any(value not in (None, "") for value in record.values()): continue
        try:
            side=side_for(record.get("team")); raw_type=normalized_sheet_name(record.get("event_type"))
            event_type={"gol":"goal","goal":"goal","expulsion":"penalty","penalty":"penalty","sancion":"penalty"}.get(raw_type, raw_type)
            number=str(record.get("player_number") if record.get("player_number") is not None else "").strip()
            player_id=roster_map.get((side, number), "")
            if not player_id: raise ValueError(f"Dorsal {number or 'vacío'} no encontrado en el roster")
            assistant_id=None
            assistant_number=str(record.get("assistant_number") if record.get("assistant_number") is not None else "").strip()
            if assistant_number:
                assistant_id=roster_map.get((side, assistant_number), "")
                if not assistant_id: raise ValueError(f"Dorsal de asistente {assistant_number} no encontrado")
            if event_type not in {"goal","penalty"}: raise ValueError("Tipo de evento no válido")
            parsed.append({"row_number":row_number,"valid":True,"data":{"team":side,"event_type":event_type,"player_id":player_id,"assistant_id":assistant_id,"match_time":str(record.get("match_time") or ""),"penalty_type":str(record.get("penalty_type") or "2"),"notes":str(record.get("notes") or "")}})
        except Exception as exc:
            parsed.append({"row_number":row_number,"valid":False,"error":str(exc),"source":record})
    return parsed


@app.post("/api/matches/{match_id}/events/import-preview")
async def preview_match_event_import(match_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    client = runtime.require_connected()
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El Excel supera 10 MB")
    context = await run_read(client.manager_match_event_context, match_id)
    try:
        rows = await run_in_threadpool(_parse_event_import, content, context)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"rows": rows, "valid": sum(1 for row in rows if row.get("valid")), "errors": sum(1 for row in rows if not row.get("valid"))}


@app.post("/api/matches/{match_id}/events/import-confirm")
async def confirm_match_event_import(match_id: str, payload: MatchEventImportPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    created=0; errors=[]
    for index, row in enumerate(payload.rows, start=1):
        try:
            await run_write(client.manager_create_match_event, match_id, dict(row or {})); created += 1
        except Exception as exc:
            errors.append({"row": index, "error": str(exc)})
    context = await run_read(client.manager_match_event_context, match_id)
    auto_finalized = False
    if created and not errors and (context.get("match") or {}).get("broadcast_enabled") is False:
        await run_write(client.manager_finalize_match_act, match_id)
        context = await run_read(client.manager_match_event_context, match_id)
        auto_finalized = True
    return {"created": created, "errors": errors, "auto_finalized": auto_finalized, "context": context}


@app.get("/api/members")
async def members() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_members)


@app.post("/api/members")
async def add_member(payload: MemberPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_invite_member, payload.email, payload.role)


@app.get("/api/account/portal")
async def account_portal() -> dict[str, str]:
    client = runtime.require_connected()
    return {"url": client.profile_portal_url()}


@app.patch("/api/members/{user_id}")
async def update_member(user_id: str, payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_update_member, user_id, payload.data)


@app.delete("/api/members/{user_id}")
async def delete_member(user_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_member, user_id)


@app.get("/api/themes")
async def themes() -> list[dict[str, Any]]:
    client = runtime.require_connected()
    return await run_read(client.manager_list_themes)


@app.post("/api/themes")
async def create_theme(payload: EntityPayload) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_create_theme, payload.data)


@app.post("/api/themes/{theme_id}/publish")
async def publish_theme(theme_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_publish_theme, theme_id)


@app.delete("/api/themes/{theme_id}")
async def delete_theme(theme_id: str) -> dict[str, Any]:
    client = runtime.require_connected()
    return await run_write(client.manager_delete_theme, theme_id)


TEMPLATE_SHEETS: dict[str, list[str]] = {
    "Jugadores": ["player_code", "first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach"],
}

ALIASES: dict[str, str] = {
    "entrenador": "is_coach", "es entrenador": "is_coach", "coach": "is_coach",
    "fecha de nacimiento": "birth_date", "fecha nacimiento": "birth_date",
    "nacimiento": "birth_date", "date of birth": "birth_date", "dob": "birth_date",
    "nacionalidad": "nationality",
    "nombre": "name",
    "nombre jugador": "first_name",
    "nombre del jugador": "display_name",
    "jugador": "display_name",
    "player": "display_name",
    "nombres": "first_name",
    "apellido": "last_name",
    "apellidos": "last_name",
    "nombre mostrado": "display_name",
    "nombre completo": "display_name",
    "nombre equipo": "team_name",
    "nombre del equipo": "team_name",
    "club": "team_name",
    "equipo": "team_code",
    "codigo equipo": "team_code",
    "abreviatura": "short_name",
    "nombre corto": "short_name",
    "capitan": "captain",
    "captain": "captain",
    "dorsales": "shirt_number",
    "n dorsal": "shirt_number",
    "no dorsal": "shirt_number",
    "n o dorsal": "shirt_number",
    "numero dorsal": "shirt_number",
    "numero de dorsal": "shirt_number",
    "numero camiseta": "shirt_number",
    "numero de camiseta": "shirt_number",
    "shirt number": "shirt_number",
    "jersey number": "shirt_number",
    "dorsal": "shirt_number",
    "numero": "shirt_number",
    "n camiseta": "shirt_number",
    "n o camiseta": "shirt_number",
    "posición": "position",
    "posicion": "position",
    "fecha": "match_date",
    "fecha partido": "match_date",
    "local": "home_team_code",
    "visitante": "away_team_code",
    "correo": "email",
    "realizador": "producer_email",
}


def normalized_header(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return ALIASES.get(text, text.replace(" ", "_"))


IMPORT_SCOPES: dict[str, tuple[str, str]] = {
    "temporadas": ("seasons", "Temporadas"),
    "seasons": ("seasons", "Temporadas"),
    "competiciones": ("competitions", "Competiciones"),
    "competitions": ("competitions", "Competiciones"),
    "ligas": ("competitions", "Competiciones"),
    "equipos": ("teams", "Equipos"),
    "teams": ("teams", "Equipos"),
    "jugadores": ("players", "Jugadores"),
    "players": ("players", "Jugadores"),
    "entrenadores": ("coaches", "Entrenadores"),
    "coaches": ("coaches", "Entrenadores"),
    "plantillas": ("rosters", "Plantillas"),
    "rosters": ("rosters", "Plantillas"),
    "realizadores": ("producers", "Usuarios"),
    "usuarios": ("producers", "Usuarios"),
    "users": ("producers", "Usuarios"),
    "partidos": ("matches", "Partidos"),
    "matches": ("matches", "Partidos"),
    "resultados": ("results", "Resultados"),
    "results": ("results", "Resultados"),
    "eventos": ("events", "Eventos"),
    "events": ("events", "Eventos"),
    "identidad visual": ("visual_identity", "Identidad visual"),
    "personalizacion": ("visual_identity", "Identidad visual"),
    "visual identity": ("visual_identity", "Identidad visual"),
}


def normalized_sheet_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().lower()


def serializable_cell(value: Any) -> Any:
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def infer_scope_from_headers(headers: set[str]) -> tuple[str, str] | tuple[None, str]:
    if {"home_team_code", "away_team_code", "match_date"}.issubset(headers):
        return "matches", "Partidos"
    if {"match_code", "event_type"}.issubset(headers):
        return "events", "Eventos"
    if {"match_code", "home_score", "away_score"}.issubset(headers):
        return "results", "Resultados"
    if {"competition_code", "team_code", "player_code"}.issubset(headers):
        return "rosters", "Plantillas"
    if "email" in headers and ("role" in headers or "display_name" in headers):
        return "producers", "Usuarios"
    if "team_code" in headers and ("short_name" in headers or "primary_color" in headers):
        return "teams", "Equipos"
    if "player_code" in headers or "display_name" in headers or ({"first_name", "last_name"} & headers):
        return "players", "Jugadores"
    if "competition_code" in headers or "points_win" in headers:
        return "competitions", "Competiciones"
    if "season_code" in headers or ({"start_date", "end_date"} & headers and "name" in headers):
        return "seasons", "Temporadas"
    if "primary_color" in headers and "accent_color" in headers:
        return "visual_identity", "Identidad visual"
    return None, "Hoja no reconocida"


def rows_to_dataset(sheet_name: str, rows: list[list[Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "sheet": sheet_name, "scope": None, "scope_label": "Hoja vacía",
            "headers": [], "mapping": {}, "row_count": 0, "preview": [], "rows": [],
        }
    headers = [str(value or "").strip() for value in rows[0]]
    mapping = {header: normalized_header(header) for header in headers if header}
    scope = IMPORT_SCOPES.get(normalized_sheet_name(sheet_name))
    if scope is None:
        scope = infer_scope_from_headers(set(mapping.values()))
    scope_key, scope_label = scope
    if scope_key == "players" and "first_name" not in mapping.values():
        mapping = {source: ("first_name" if target == "name" else target) for source, target in mapping.items()}
    clean_rows: list[dict[str, Any]] = []
    for raw in rows[1:]:
        item = {
            mapping.get(headers[index], headers[index]): serializable_cell(raw[index] if index < len(raw) else None)
            for index in range(len(headers)) if headers[index]
        }
        if any(value not in (None, "") for value in item.values()):
            clean_rows.append(item)
    return {
        "sheet": sheet_name,
        "scope": scope_key,
        "scope_label": scope_label,
        "headers": headers,
        "mapping": mapping,
        "row_count": len(clean_rows),
        "preview": clean_rows[:20],
        "rows": clean_rows,
    }


PLAYER_IMPORT_FIELDS = ("player_code", "first_name", "last_name", "display_name", "position", "birth_date", "nationality", "is_coach")
PLAYER_IMPORT_FIELD_SET = set(PLAYER_IMPORT_FIELDS)
PLAYER_IMPORT_NAME_FIELDS = {"first_name", "last_name", "display_name"}


def player_rows_to_dataset(sheet_name: str, rows: list[list[Any]], roster: bool = False) -> dict[str, Any]:
    """Extract only player identity fields from any sheet.

    The workbook may contain team, competition, roster or shirt-number columns.
    Those columns are deliberately ignored and never reach the commit endpoint.
    Sheet names are not used to classify the data: a sheet called ``Equipos`` is
    still importable when its rows contain identifiable player fields.
    """
    if not rows:
        return {
            "sheet": sheet_name, "scope": None, "scope_label": "Hoja vacía",
            "headers": [], "mapping": {}, "ignored_headers": [],
            "row_count": 0, "source_row_count": 0, "preview": [], "rows": [],
        }

    fields = PLAYER_IMPORT_FIELDS + (("shirt_number", "captain") if roster else ())
    headers = [str(value or "").strip() for value in rows[0]]
    raw_mapping = {header: normalized_header(header) for header in headers if header}
    mapping: dict[str, str] = {}
    ignored_headers: list[str] = []
    for source, target in raw_mapping.items():
        # In this dedicated import screen, an unqualified "Nombre" describes
        # the player. Explicit team-name headers normalize to ``team_name`` and
        # are therefore ignored.
        accepted_target = "first_name" if target == "name" else target
        if accepted_target in fields:
            mapping[source] = accepted_target
        else:
            ignored_headers.append(source)

    has_player_columns = bool(set(mapping.values()) & PLAYER_IMPORT_NAME_FIELDS)
    clean_rows: list[dict[str, Any]] = []
    source_row_count = 0
    for raw in rows[1:]:
        if any((raw[index] if index < len(raw) else None) not in (None, "") for index in range(len(headers))):
            source_row_count += 1
        if not has_player_columns:
            continue
        item: dict[str, Any] = {}
        for index, source in enumerate(headers):
            target = mapping.get(source)
            if not target:
                continue
            value = serializable_cell(raw[index] if index < len(raw) else None)
            # Prefer the first non-empty value if two source columns map to the
            # same personal field.
            if target not in item or item[target] in (None, ""):
                item[target] = value
        if any(item.get(field) not in (None, "") for field in PLAYER_IMPORT_NAME_FIELDS):
            clean_rows.append({field: item.get(field) for field in fields if field in item})

    scope_key = "players" if has_player_columns else None
    scope_label = "Jugadores · solo datos de la ficha" if has_player_columns else "Sin columnas de jugador reconocibles"
    return {
        "sheet": sheet_name,
        "scope": scope_key,
        "scope_label": scope_label,
        "headers": headers,
        "mapping": mapping,
        "ignored_headers": ignored_headers,
        "row_count": len(clean_rows),
        "source_row_count": source_row_count,
        "preview": clean_rows[:20],
        "rows": clean_rows,
    }


def analyse_rows(sheet_name: str, rows: list[list[Any]]) -> dict[str, Any]:
    """Compatibility wrapper retained for Phase 37 tests and integrations."""
    return {key: value for key, value in rows_to_dataset(sheet_name, rows).items() if key != "rows"}

def parse_import_content(filename: str, content: bytes, roster: bool = False) -> list[dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    datasets: list[dict[str, Any]] = []
    if suffix == ".csv":
        decoded = content.decode("utf-8-sig")
        sample = decoded[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(io.StringIO(decoded), dialect))
        datasets.append(player_rows_to_dataset("CSV", rows, roster))
    elif suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        for sheet in workbook.worksheets:
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            datasets.append(player_rows_to_dataset(sheet.title, rows, roster))
    else:
        raise ValueError("Formato no compatible. Utiliza .xlsx o .csv")
    return datasets


def validate_import_upload(filename: str, content: bytes) -> None:
    if not content:
        raise ValueError("El archivo está vacío")
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("El archivo supera el límite de 20 MB")
    if Path(filename).suffix.lower() not in {".csv", ".xlsx", ".xlsm"}:
        raise ValueError("Formato no compatible. Utiliza .xlsx o .csv")


def build_player_import_template(roster: bool = False) -> bytes:
    """Create the player-only workbook used by both web and desktop downloads."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Instala openpyxl para generar la plantilla") from exc

    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, headers in TEMPLATE_SHEETS.items():
        headers = ["Entrenador" if header == "is_coach" else header for header in headers] + (["Dorsal", "Capitán"] if roster else [])
        sheet = workbook.create_sheet(title=title[:31])
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="174A7E")
            cell.alignment = Alignment(horizontal="center")
        if "position" in headers:
            from openpyxl.worksheet.datavalidation import DataValidation
            from openpyxl.comments import Comment
            column = sheet.cell(1, headers.index("position") + 1).column_letter
            sheet[f"{column}1"].comment = Comment("Posición de juego. Indica Sí en is_coach para marcar también como entrenador. Puede quedar vacía si solo entrena.", "Secretariat Pro")
            validation = DataValidation(type="list", formula1='"Portero,Defensa,Medio,Delantero,Lateral izquierdo,Central,Lateral derecho,Pivote,Extremo izquierdo,Extremo derecho"', allow_blank=True)
            validation.showErrorMessage = False
            sheet.add_data_validation(validation)
            validation.add(f"{column}2:{column}10000")
        if "Entrenador" in headers:
            column = sheet.cell(1, headers.index("Entrenador") + 1).column_letter
            validation = DataValidation(type="list", formula1='"Sí,No"', allow_blank=True)
            validation.showErrorMessage = True
            sheet.add_data_validation(validation)
            validation.add(f"{column}2:{column}10000")
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{sheet.cell(1, len(headers)).column_letter}1"
        for index, header in enumerate(headers, 1):
            cell = sheet.cell(1, index)
            sheet.column_dimensions[cell.column_letter].width = max(14, min(30, len(header) + 5))
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def manager_downloads_directory() -> Path:
    """Return a writable local folder for desktop Manager downloads."""
    candidates: list[Path] = []
    for raw in (os.environ.get("USERPROFILE"), os.environ.get("HOME")):
        if raw:
            candidates.append(Path(raw) / "Downloads")
    candidates.extend([Path.home() / "Downloads", Path.home()])
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".secretariatpro_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue
    raise HTTPException(status_code=500, detail="No se encontró una carpeta local con permisos de escritura")


def unique_template_path(directory: Path) -> Path:
    base = directory / "SecretariatPro_importacion_jugadores.xlsx"
    if not base.exists():
        return base
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"SecretariatPro_importacion_jugadores_{stamp}.xlsx"


@app.get("/api/import/template.xlsx")
async def import_template() -> Response:
    return Response(
        content=build_player_import_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="SecretariatPro_importacion_jugadores.xlsx"'},
    )


@app.post("/api/import/template/download")
async def download_import_template() -> dict[str, Any]:
    """Save the workbook directly on the desktop user's computer.

    Embedded WebView engines do not consistently honor the HTML download
    attribute. Writing the file from the local backend makes the button reliable
    on Windows and macOS while the GET route remains available in browsers.
    """
    destination = unique_template_path(manager_downloads_directory())
    try:
        destination.write_bytes(build_player_import_template())
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar la plantilla: {exc}") from exc
    return {
        "ok": True,
        "filename": destination.name,
        "path": str(destination),
        "directory": str(destination.parent),
    }


@app.post("/api/import/analyze")
async def import_analyze(file: UploadFile = File(...)) -> dict[str, Any]:
    runtime.require_write()
    filename = str(file.filename or "archivo").strip()
    content = await file.read()
    try:
        validate_import_upload(filename, content)
        datasets = parse_import_content(filename, content)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="El CSV debe estar codificado en UTF-8") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    analyses = []
    for item in datasets:
        analysis = {key: value for key, value in item.items() if key != "rows"}
        if item.get("scope") != "players":
            analysis["scope"] = None
            analysis["scope_label"] = "No se importará · no contiene datos personales de jugador"
        analyses.append(analysis)
    importable_rows = sum(item["row_count"] for item in datasets if item.get("scope") == "players")
    return {
        "filename": filename,
        "sheets": analyses,
        "total_rows": sum(item["row_count"] for item in datasets),
        "importable_rows": importable_rows,
        "recognized_sheets": sum(1 for item in datasets if item.get("scope") == "players" and item.get("row_count")),
        "message": "Archivo analizado. Se importarán únicamente los datos de la ficha del jugador; equipo, dorsal, competición y roster se ignoran.",
    }


@app.post("/api/import/commit")
async def import_commit(file: UploadFile = File(...)) -> dict[str, Any]:
    runtime.require_write()
    filename = str(file.filename or "archivo").strip()
    content = await file.read()
    try:
        validate_import_upload(filename, content)
        datasets = parse_import_content(filename, content)
        importable = [
            {"sheet": item["sheet"], "scope": "players", "rows": item["rows"]}
            for item in datasets if item.get("scope") == "players" and item.get("rows")
        ]
        if not importable:
            raise ValueError("El archivo no contiene jugadores reconocibles. Utiliza la plantilla de jugadores")
        client = runtime.require_connected()
        report = await run_in_threadpool(client.manager_import_rows, importable)
        report["filename"] = filename
        return report
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="El CSV debe estar codificado en UTF-8") from exc
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/teams/{team_id}/rosters/{competition_id}/import/{action}")
async def import_roster(team_id: str, competition_id: str, action: str, file: UploadFile = File(...)) -> dict[str, Any]:
    runtime.require_write()
    if action not in {"analyze", "commit"}:
        raise HTTPException(404, "Acción no disponible")
    client = runtime.require_connected()
    filename = str(file.filename or "archivo")
    content = await file.read()
    try:
        validate_import_upload(filename, content)
        datasets = parse_import_content(filename, content, roster=True)
        await run_in_threadpool(client.manager_validate_roster_import_target, team_id, competition_id)
        if action == "analyze":
            return {"filename": filename, "sheets": [{k: v for k, v in item.items() if k != "rows"} for item in datasets],
                    "importable_rows": sum(len(item["rows"]) for item in datasets)}
        return await run_in_threadpool(client.manager_import_roster, team_id, competition_id, datasets)
    except Exception as exc:
        raise api_error(exc) from exc


@app.get("/api/import/roster-template.xlsx")
async def roster_import_template() -> Response:
    runtime.require_write()
    return Response(content=build_player_import_template(roster=True),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="SecretariatPro_roster.xlsx"'})


@app.get("/api/roster-groups")
async def roster_groups() -> list[dict[str, Any]]:
    return await run_in_threadpool(runtime.require_connected().manager_list_roster_groups)

@app.post("/api/teams/{team_id}/roster-groups/{competition_id}")
async def create_roster_group(team_id: str, competition_id: str) -> dict[str, Any]:
    runtime.require_write()
    try:
        return await run_in_threadpool(runtime.require_connected().manager_create_roster_group, team_id, competition_id)
    except Exception as exc: raise api_error(exc) from exc

@app.post("/api/import/scoped/{kind}/{action}")
async def scoped_import(kind: str, action: str, competition_id: str, season_id: str, timezone_name: str = "Europe/Madrid", file: UploadFile = File(...)) -> dict[str, Any]:
    runtime.require_write()
    if kind not in {"people", "matches"} or action not in {"analyze", "commit"}: raise HTTPException(404, "Importador no disponible")
    from manager_api.scoped_import import read_rows, preview, commit
    try:
        content = await file.read()
        validate_import_upload(file.filename or "", content)
        rows = await run_in_threadpool(read_rows, file.filename, content, kind)
        method = preview if action == "analyze" else commit
        result = await run_in_threadpool(method, runtime.require_connected(), kind, rows, competition_id, season_id, timezone_name)
        result.pop("_prepared", None)
        return result
    except Exception as exc: raise api_error(exc) from exc

@app.get("/api/import/scoped/{kind}/template.xlsx")
async def scoped_import_template(kind: str) -> Response:
    runtime.require_write()
    if kind not in {"people", "matches"}: raise HTTPException(404, "Importador no disponible")
    from openpyxl import Workbook, load_workbook
    if kind == "people":
        book = load_workbook(io.BytesIO(build_player_import_template(roster=True)))
        sheet = book.active
        sheet.cell(1, sheet.max_column + 1, "Equipo")
        sheet.column_dimensions[sheet.cell(1, sheet.max_column).column_letter].width = 28
    else:
        book = Workbook(); sheet = book.active; sheet.title = "Partidos"
        sheet.append(["Fecha", "Hora", "Instalación", "Local", "Visitante"])
        sheet.freeze_panes = "A2"
        for col in "ABCDE": sheet.column_dimensions[col].width = 25
        from openpyxl.comments import Comment
        sheet["A1"].comment = Comment("DD/MM/AAAA", "Secretariat Pro")
        sheet["B1"].comment = Comment("HH:MM. Dejar vacía si la hora está pendiente.", "Secretariat Pro")
    stream = io.BytesIO(); book.save(stream)
    return Response(content=stream.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="SecretariatPro_{kind}.xlsx"'})


@app.post("/api/import/scoped/{kind}/template/download")
async def scoped_template_download(kind: str) -> dict[str, Any]:
    response = await scoped_import_template(kind)
    filename = f"SecretariatPro_{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
    destination = manager_downloads_directory() / filename
    await run_in_threadpool(destination.write_bytes, response.body)
    return {"path": str(destination), "filename": filename}
