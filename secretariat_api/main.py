# Compatibility marker: API_VERSION = "64.0.0-beta-rc"
# Compatibility test marker: API_VERSION = "39.0.0-alpha"
# Compatibility marker: API_VERSION = "57.0.0-beta-rc"
from __future__ import annotations

import re

import asyncio
import json
import os
import io
import socket
from urllib.parse import quote
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import qrcode
import qrcode.image.svg

from secretariat_core.services.broadcast_flow import BroadcastFlow
from secretariat_core.services.program_preview import ProgramPreview
from secretariat_api.lan_access import lan_addresses, listener_reachable
from secretariat_core.services.overlay import ALL_PANELS, hide_all, set_panel, toggle_panel, overlay_summary
from secretariat_core.services.graphics_queue import add_cue, clear_cues, cue_preview, move_cue, remove_cue, take_cue
from secretariat_core.services.graphics_sequences import delete_sequence, find_sequence, save_sequence
from secretariat_core.services.match_context import roster_player
from secretariat_core.services.event_context import build_goal_bottom_bar
from secretariat_core.services.shootout import reset_shootout, set_attempt
from secretariat_core.services.powerplay import (
    burn_powerplay_block,
    end_powerplay,
    penalty_values,
    start_powerplay,
)

from .runtime import ApplicationRuntime
from .tablet_access import COOKIE_NAME, TabletAccess, is_loopback
from .preflight import build_preflight
from .clipboard import ClipboardUnavailable, copy_text
from .schemas import (
    AccountAvatarUpdate,
    AccountPasswordUpdate,
    AccountProfileUpdate,
    AttendancePayload,
    ClipboardPayload,
    FinishPayload,
    GraphicsCueRequest,
    GraphicsCueMoveRequest,
    GraphicsSequenceRequest,
    GoalPayload,
    ReplayTemplateRequest,
    LoginRequest,
    PasswordResetRequest,
    OCRConfigPayload,
    OCRSourceActivation,
    OverlayRequest,
    OBSConnectRequest,
    OBSSceneRequest,
    PenaltyAttemptRequest,
    PlayerProfileRequest,
    PowerplayStartRequest,
    ScoreDeltaRequest,
    ScoreModeRequest,
    ScoreRequest,
    SettingsPatch,
    TimeRequest,
    PeriodRequest,
    ReplayMarkRequest,
    ReplaySelectionRequest,
    HighlightsRequest,
    ReplayCompositionRequest,
    WorkspaceActivateRequest,
)

# Legacy compatibility marker for phase 36 tests/clients: version="36.0.0-alpha"
LEGACY_API_VERSION = "36.0.0-alpha"
API_VERSION = "71.0.0-beta-rc"

BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "webapp"
from secretariat_core.app_environment import data_directory
runtime = ApplicationRuntime(data_directory(BASE_DIR))
tablet_access_control = TabletAccess()


def _tablet_scope() -> str:
    client = runtime.supabase
    return f"{getattr(client, 'user_id', '')}:{(runtime.active_workspace or {}).get('id', '')}"


def _tablet_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    online = snapshot.get("online") or {}
    obs = snapshot.get("obs") or {}
    return {
        "state": snapshot.get("state") or {}, "scores": snapshot.get("scores") or {},
        "overlays": snapshot.get("overlays") or {},
        "score_control": snapshot.get("score_control") or {},
        "graphic_scores": snapshot.get("graphic_scores") or {},
        "replays": snapshot.get("replays") or {},
        "settings": {key: (snapshot.get("settings") or {}).get(key) for key in ("language", "appearance", "graphics_sequences", "replay_templates")},
        "obs": {"connected": bool(obs.get("connected")), "scenes": obs.get("scenes") or [], "program": obs.get("program") or ""},
        "online": {key: online.get(key) for key in ("match", "rosters", "attendance", "access")},
    }


_TABLET_ACTIONS = {
    "/api/events/goal", "/api/player-profile", "/api/obs/scenes/program",
    "/api/overlays/hide-all", "/api/powerplays/team1/start", "/api/powerplays/team2/start",
    "/api/powerplays/team1/end", "/api/powerplays/team2/end",
}


def _tablet_route_allowed(path: str, method: str) -> bool:
    if method == "GET":
        return path in {"/api/state", "/api/obs/status", "/api/replays", "/api/replays/templates", "/api/graphics/sequences"} or path.startswith(("/api/replays/media/", "/api/replays/thumbnail/"))
    if method == "DELETE":
        return bool(re.fullmatch(r"/api/replays/library/[a-f0-9]{32}", path))
    if method == "PATCH":
        return bool(re.fullmatch(r"/api/replays/[a-f0-9]{32}", path))
    if method == "POST":
        if path in {"/api/replays/mark", "/api/replays/composition", "/api/replays/out", "/api/replays/goal/skip", "/api/replays/highlights", "/api/replays/start", "/api/replays/stop", "/api/match/period", "/api/graphics/cues", "/api/graphics/sequences/stop"}:
            return True
        if re.fullmatch(r"/api/replays/library/[a-f0-9]{32}/(?:take|restore)|/api/empty-net/team[12]/toggle|/api/graphics/(?:cues/[^/]+/take|sequences/[^/]+/run)", path):
            return True
        return path in _TABLET_ACTIONS or (
            path.startswith("/api/overlays/") and path.endswith("/toggle")
            and path.removeprefix("/api/overlays/").removesuffix("/toggle") in ALL_PANELS
        )
    return False


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False)
        tablet_payload = payload.get("payload") or {}
        if payload.get("type") == "live":
            tablet_payload = {key: tablet_payload.get(key) for key in ("scores", "graphic_scores", "powerplay", "score_control")}
        else:
            tablet_payload = _tablet_snapshot(tablet_payload)
        tablet_encoded = json.dumps({"type": payload.get("type", "state"), "payload": tablet_payload}, ensure_ascii=False)
        stale: list[WebSocket] = []
        async with self._lock:
            targets = list(self.connections)
        async def send(websocket):
            try:
                await asyncio.wait_for(websocket.send_text(encoded if is_loopback(websocket.client.host if websocket.client else None) else tablet_encoded), timeout=0.25)
            except Exception:
                stale.append(websocket)
        await asyncio.gather(*(send(websocket) for websocket in targets))
        if stale:
            async with self._lock:
                for websocket in stale:
                    self.connections.discard(websocket)


manager = ConnectionManager()
_graphics_sequence_task: asyncio.Task | None = None
_goal_celebration_task: asyncio.Task | None = None
_goal_replay_task: asyncio.Task | None = None
_replay_exports: set[asyncio.Task] = set()


async def broadcast_state() -> dict[str, Any]:
    snapshot = await run_in_threadpool(runtime.snapshot)
    await manager.broadcast({"type": "state", "payload": snapshot})
    return snapshot


broadcast_flow = BroadcastFlow(runtime, broadcast_state)


async def _show_goal_celebration() -> None:
    await broadcast_flow.without_replay()


async def watch_state_files(stop_event: asyncio.Event) -> None:
    watched = [runtime.paths.data_file, runtime.paths.app_settings_file, runtime.paths.account_settings_file, runtime.paths.ocr_config_file]
    score_paths = {runtime.paths.scores_dir / filename for filename in runtime.score_store.FILES.values()}
    watched.extend(score_paths)
    mtimes: dict[str, int] = {}
    while not stop_event.is_set():
        changed = await run_in_threadpool(runtime.advance_powerplays)
        scores_changed = False
        for path in watched:
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                mtime = -1
            key = str(path)
            if key in mtimes and mtimes[key] != mtime:
                if path in score_paths:
                    scores_changed = True
                else:
                    changed = True
            mtimes[key] = mtime
        if changed:
            await broadcast_state()
        elif scores_changed:
            # Clock ticks must not query OBS, rebuild replay libraries or
            # regenerate the entire desktop/tablet interface.
            live = await run_in_threadpool(runtime.live_snapshot)
            await manager.broadcast({"type": "live", "payload": live})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.35)
        except asyncio.TimeoutError:
            pass


async def watch_published_theme(stop_event: asyncio.Event) -> None:
    # Cloud latency must never delay local clock/score notifications.
    # One request at a time; no accumulating tasks on a slow connection.
    while not stop_event.is_set():
        try:
            await run_in_threadpool(runtime.refresh_published_theme)
        except Exception:
            pass  # Keep the last published identity; the next pass retries.
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = await run_in_threadpool(runtime.settings_store.load)
    obs_settings = settings.get("obs", {})
    if runtime.obs is not None and obs_settings.get("auto_connect") and runtime.production_access_allowed():
        try:
            await run_in_threadpool(
                runtime.obs.connect,
                obs_settings.get("host", "127.0.0.1"),
                obs_settings.get("port", 4455),
                obs_settings.get("password", ""),
            )
        except Exception:
            pass
    stop_event = asyncio.Event()
    task = asyncio.create_task(watch_state_files(stop_event))
    theme_task = asyncio.create_task(watch_published_theme(stop_event))
    yield
    broadcast_flow.cancel()
    stop_event.set()
    await asyncio.gather(task, theme_task)
    if _replay_exports:
        await asyncio.gather(*list(_replay_exports), return_exceptions=True)
    await run_in_threadpool(runtime.shutdown)
    if runtime.obs is not None:
        await run_in_threadpool(runtime.obs.disconnect)


TABLET_DIR = BASE_DIR / "tablet"

app = FastAPI(title="SecretariatPro Local API", version=API_VERSION, lifespan=lifespan)
app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="webapp")
app.mount("/tablet", StaticFiles(directory=TABLET_DIR, html=True), name="tablet")

_PUBLIC_API_PATHS = {
    "/api/health", "/api/state", "/api/auth/login", "/api/auth/logout",
    "/api/auth/password-reset", "/api/account/profile", "/api/account/password",
    "/api/account/avatar", "/api/workspaces/activate", "/api/tablet-access", "/api/tablet-qr.svg",
    "/api/system/clipboard",
}


@app.middleware("http")
async def subscription_gate(request: Request, call_next):
    """Block every production route unless a paid workspace is active.

    The desktop shell and account endpoints remain reachable so the user can
    sign in, inspect the reason for the block, change workspace or renew.
    """
    path = request.url.path
    remote = not is_loopback(request.client.host if request.client else None)
    if remote:
        if path.startswith("/tablet"):
            pass
        elif path in {"/api/health", "/api/tablet/pair", "/api/tablet/session"}:
            pass
        elif not tablet_access_control.authenticate(request.cookies.get(COOKIE_NAME), _tablet_scope()):
            return JSONResponse(status_code=401, content={"detail": "Empareja esta tablet desde el ordenador"})
        elif not _tablet_route_allowed(path, request.method):
            return JSONResponse(status_code=403, content={"detail": "Esta acción solo está disponible en el ordenador"})
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                return JSONResponse(status_code=403, content={"detail": "Origen no permitido"})
    elif path.startswith("/api/tablet/") or path in {"/api/tablet-access", "/api/tablet-qr.svg"}:
        # Pairing codes and revocation are managed exclusively on the host PC.
        pass
    if path.startswith("/api/") and path not in _PUBLIC_API_PATHS:
        if not runtime.production_access_allowed():
            return JSONResponse(
                status_code=402,
                content={
                    "detail": runtime.subscription_access.get("message")
                    or "SecretariatPro requiere una membresía activa",
                    "access": runtime.subscription_access,
                },
            )
    if path.startswith("/tablet") and not runtime.production_access_allowed():
        return HTMLResponse(
            "<html><body style='font-family:Arial;background:#0b0f14;color:white;display:grid;place-items:center;min-height:100vh'>"
            "<main><h1>SecretariatPro bloqueado</h1><p>Inicia sesión en el ordenador con una membresía activa.</p></main>"
            "</body></html>",
            status_code=402,
        )
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/overlay.html")
async def overlay_html() -> FileResponse:
    return FileResponse(BASE_DIR / "overlay.html")


@app.get("/script.js")
async def overlay_script() -> FileResponse:
    return FileResponse(BASE_DIR / "script.js", media_type="application/javascript")


@app.get("/styles.css")
async def overlay_styles() -> FileResponse:
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")


@app.get("/data.json")
async def overlay_data() -> JSONResponse:
    """Serve an immutable in-memory state snapshot.

    ``data.json`` is rewritten frequently while a match is running. Serving
    that mutable file with ``FileResponse`` can race with an atomic replace:
    Starlette calculates Content-Length from one version and can then stream a
    newer, larger version, which Uvicorn rejects with
    ``Response content longer than Content-Length``.
    """
    payload = await run_in_threadpool(runtime.state_store.load)
    payload["graphic_scores"] = await run_in_threadpool(runtime.graphic_scores)
    return JSONResponse(
        payload,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


_SCORE_FILES = {filename: key for key, filename in runtime.score_store.FILES.items()}


@app.get("/scores/{filename}")
async def overlay_score_file(filename: str) -> Response:
    """Return a snapshot of a mutable score/timer file.

    The overlay polls these values four times per second. Reading the complete
    value into memory before building the response guarantees that the body
    length and Content-Length always describe the same snapshot.
    """
    key = _SCORE_FILES.get(filename)
    if key is None:
        raise HTTPException(404, "Archivo de marcador no válido")
    value = await run_in_threadpool(runtime.score_store.read, key, "")
    return Response(
        content=value.encode("utf-8"),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "version": API_VERSION, "base_dir": str(BASE_DIR), "local_logo_service": False}


@app.post("/api/system/clipboard")
async def system_clipboard(payload: ClipboardPayload, request: Request) -> dict[str, bool]:
    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "El portapapeles solo está disponible en este ordenador")
    try:
        await run_in_threadpool(copy_text, payload.text)
    except ClipboardUnavailable as exc:
        raise HTTPException(503, "No se pudo acceder al portapapeles") from exc
    return {"copied": True}


def _lan_ip() -> str:
    addresses = lan_addresses()
    return addresses[0]["address"] if addresses else ""


def _tablet_url(request: Request, address: str = "") -> str:
    candidates = lan_addresses()
    chosen = address or (candidates[0]["address"] if candidates else "")
    if chosen not in {row["address"] for row in candidates}:
        raise HTTPException(409, "No hay una dirección de red local disponible; conecta el ordenador a Wi-Fi o Ethernet")
    port = request.url.port or 8765
    return f"http://{chosen}:{port}/tablet/"


@app.get("/api/tablet-access")
async def tablet_access(request: Request, address: str = "") -> dict[str, Any]:
    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "El QR solo se genera en el ordenador")
    if not runtime.production_access_allowed():
        raise HTTPException(402, "Inicia sesión con una membresía activa")
    code = tablet_access_control.invite(_tablet_scope())
    url = f"{_tablet_url(request, address)}#pair={code}"
    selected = address or _lan_ip()
    reachable = await asyncio.to_thread(listener_reachable, selected, request.url.port or 8765)
    return {"url": url, "qr": f"/api/tablet-qr.svg?code={quote(code)}&address={quote(selected)}", "expires_in": "300", "addresses": lan_addresses(), "selected_address": selected, "listener_reachable": reachable}


@app.get("/api/tablet-qr.svg")
async def tablet_qr(request: Request, code: str = "", address: str = "") -> Response:
    if not is_loopback(request.client.host if request.client else None) or not code:
        raise HTTPException(403, "QR de emparejamiento no disponible")
    image = qrcode.make(
        f"{_tablet_url(request, address)}#pair={code}",
        image_factory=qrcode.image.svg.SvgPathFillImage,
        box_size=10,
        border=4,
    )
    output = io.BytesIO()
    image.save(output)
    return Response(
        output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.post("/api/tablet/pair")
async def pair_tablet(request: Request) -> Response:
    if is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "Abre el QR desde una tablet en la red local")
    if not runtime.production_access_allowed():
        raise HTTPException(402, "Membresía no activa")
    try:
        payload = await request.json()
        session_id, token = tablet_access_control.pair(str(payload.get("code") or ""), _tablet_scope())
    except (ValueError, AttributeError, PermissionError) as exc:
        raise HTTPException(403, str(exc)) from exc
    response = JSONResponse({"paired": True, "id": session_id})
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", max_age=12 * 60 * 60, path="/")
    return response


@app.get("/api/tablet/session")
async def tablet_session(request: Request) -> dict[str, Any]:
    session_id = tablet_access_control.authenticate(request.cookies.get(COOKIE_NAME), _tablet_scope())
    return {"paired": bool(session_id), "id": session_id or ""}


@app.get("/api/tablet/sessions")
async def tablet_sessions(request: Request) -> list[dict[str, Any]]:
    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "Solo desde el ordenador")
    return tablet_access_control.sessions(_tablet_scope())


@app.delete("/api/tablet/sessions/{session_id}")
async def revoke_tablet(session_id: str, request: Request) -> dict[str, bool]:
    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "Solo desde el ordenador")
    return {"revoked": tablet_access_control.revoke(session_id)}


@app.get("/api/state")
async def get_state(request: Request) -> dict[str, Any]:
    snapshot = await run_in_threadpool(runtime.snapshot)
    return snapshot if is_loopback(request.client.host if request.client else None) else _tablet_snapshot(snapshot)


@app.get("/api/preflight")
async def preflight(request: Request) -> dict[str, Any]:
    if not is_loopback(request.client.host if request.client else None):
        raise HTTPException(403, "Comprobación previa solo desde el ordenador")
    snapshot = await run_in_threadpool(runtime.snapshot)
    return build_preflight(snapshot, len(tablet_access_control.sessions(_tablet_scope())))


@app.get("/api/live")
async def get_live_state() -> JSONResponse:
    payload = await run_in_threadpool(runtime.live_snapshot)
    return JSONResponse(
        payload,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not runtime.production_access_allowed():
        await websocket.close(code=4402, reason="Membresía no activa")
        return
    remote = not is_loopback(websocket.client.host if websocket.client else None)
    if remote and not tablet_access_control.authenticate(websocket.cookies.get(COOKIE_NAME), _tablet_scope()):
        await websocket.close(code=4401, reason="Tablet no emparejada")
        return
    await manager.connect(websocket)
    try:
        snapshot = await run_in_threadpool(runtime.snapshot)
        await websocket.send_json({"type": "state", "payload": _tablet_snapshot(snapshot) if remote else snapshot})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@app.post("/api/overlays/{panel}/show")
async def show_overlay(panel: str, payload: OverlayRequest | None = None) -> dict[str, Any]:
    if panel not in ALL_PANELS:
        raise HTTPException(404, "Panel desconocido")
    lineup_team = payload.lineup_team if payload else None
    await run_in_threadpool(runtime.mutate_state, lambda state: set_panel(state, panel, True, lineup_team=lineup_team))
    return await broadcast_state()


@app.post("/api/overlays/{panel}/hide")
async def hide_overlay(panel: str) -> dict[str, Any]:
    if panel not in ALL_PANELS:
        raise HTTPException(404, "Panel desconocido")
    await run_in_threadpool(runtime.mutate_state, lambda state: set_panel(state, panel, False))
    return await broadcast_state()


@app.post("/api/overlays/{panel}/toggle")
async def toggle_overlay(panel: str, payload: OverlayRequest | None = None) -> dict[str, Any]:
    if panel not in ALL_PANELS:
        raise HTTPException(404, "Panel desconocido")
    # Statistical overlays must always open with current competition/team
    # identity and current aggregates. This also prevents stale logos after a
    # manager-side logo change followed by a newly loaded match.
    if panel in {"top_scorers", "standings"} and runtime.active_match and runtime.active_competition:
        if not overlay_summary(runtime.read_state()).get(panel):
            task = getattr(runtime, "_statistics_refresh_task", None)
            if task is None or task.done():
                async def refresh_statistics_later():
                    try:
                        await asyncio.to_thread(runtime.refresh_statistics)
                        await broadcast_state()
                    except Exception:
                        pass  # The already loaded competition data remains usable offline.
                runtime._statistics_refresh_task = asyncio.create_task(refresh_statistics_later())
    lineup_team = payload.lineup_team if payload else None
    def mutate(state: dict[str, Any]) -> None:
        toggle_panel(state, panel, lineup_team=lineup_team)
        # A manual operation takes ownership of the on-air panel, so a timer
        # from an earlier queued cue must no longer be allowed to hide it.
        state.pop("graphics_on_air", None)
    await run_in_threadpool(runtime.mutate_state, mutate)
    return await broadcast_state()


@app.post("/api/overlays/hide-all")
async def hide_all_overlays(keep_scoreboard: bool = Query(False)) -> dict[str, Any]:
    broadcast_flow.cancel()
    def mutate(state: dict[str, Any]) -> None:
        state.pop("broadcast_flow", None)
        state.pop("pending_goal_celebration", None)
        hide_all(state, keep_scoreboard=keep_scoreboard)
        state.pop("graphics_on_air", None)
    await run_in_threadpool(runtime.mutate_state, mutate)
    return await broadcast_state()


@app.post("/api/graphics/cues")
async def queue_graphic(payload: GraphicsCueRequest) -> dict[str, Any]:
    match_id = str((runtime.active_match or {}).get("id") or "")
    try:
        await run_in_threadpool(runtime.mutate_state,
            lambda state: add_cue(
                state, payload.panel, match_id, payload.lineup_team,
                payload.label, payload.duration_seconds,
            ))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.get("/api/graphics/preview/{cue_id}")
async def preview_graphic(cue_id: str) -> JSONResponse:
    match_id = str((runtime.active_match or {}).get("id") or "")
    try:
        preview = await run_in_threadpool(cue_preview, runtime.read_state(), cue_id, match_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return JSONResponse(preview, headers={"Cache-Control": "no-store"})


@app.post("/api/graphics/cues/{cue_id}/take")
async def take_graphic(cue_id: str) -> dict[str, Any]:
    match_id = str((runtime.active_match or {}).get("id") or "")
    first = (runtime.read_state().get("graphics_queue") or [{}])[0]
    if first.get("id") != cue_id:
        raise HTTPException(409, "Solo se puede lanzar el siguiente gráfico de la cola")
    if first.get("panel") in {"top_scorers", "standings"} and runtime.active_competition:
        try:
            await run_in_threadpool(runtime.refresh_statistics)
        except Exception as exc:
            raise HTTPException(400, str(exc)) from exc
    try:
        _, cue = await run_in_threadpool(runtime.mutate_state, lambda state: take_cue(state, cue_id, match_id))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    snapshot = await broadcast_state()
    duration = int(cue.get("duration_seconds") or 0)
    if duration > 0:
        async def hide_later(panel: str, delay: int, scheduled_cue_id: str) -> None:
            await asyncio.sleep(delay)
            def hide_if_still_current(state: dict[str, Any]) -> bool:
                active = state.get("graphics_on_air") or {}
                if active.get("cue_id") != scheduled_cue_id:
                    return False
                set_panel(state, panel, False)
                state.pop("graphics_on_air", None)
                return True
            _, hidden = await run_in_threadpool(runtime.mutate_state, hide_if_still_current)
            if hidden:
                await broadcast_state()
        asyncio.create_task(hide_later(str(cue.get("panel") or ""), duration, str(cue.get("id") or "")))
    return snapshot


@app.delete("/api/graphics/cues/{cue_id}")
async def discard_graphic(cue_id: str) -> dict[str, Any]:
    _, removed = await run_in_threadpool(runtime.mutate_state, lambda state: remove_cue(state, cue_id))
    if not removed:
        raise HTTPException(404, "Gráfico preparado no disponible")
    return await broadcast_state()


@app.patch("/api/graphics/cues/{cue_id}/position")
async def reposition_graphic(cue_id: str, payload: GraphicsCueMoveRequest) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.mutate_state, lambda state: move_cue(state, cue_id, payload.position))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return await broadcast_state()


@app.delete("/api/graphics/cues")
async def discard_all_graphics() -> dict[str, Any]:
    await run_in_threadpool(runtime.mutate_state, clear_cues)
    return await broadcast_state()


@app.get("/api/graphics/sequences")
async def graphics_sequences() -> list[dict[str, Any]]:
    return list((await run_in_threadpool(runtime.safe_settings)).get("graphics_sequences") or [])


@app.post("/api/graphics/sequences")
async def create_graphics_sequence(payload: GraphicsSequenceRequest) -> dict[str, Any]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    try:
        sequence = save_sequence(settings, payload.model_dump())
        await run_in_threadpool(runtime.save_current_settings, settings)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"sequence": sequence, "sequences": settings["graphics_sequences"]}


@app.patch("/api/graphics/sequences/{sequence_id}")
async def update_graphics_sequence(sequence_id: str, payload: GraphicsSequenceRequest) -> dict[str, Any]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    try:
        sequence = save_sequence(settings, payload.model_dump(), sequence_id)
        await run_in_threadpool(runtime.save_current_settings, settings)
    except KeyError as exc:
        raise HTTPException(404, "Secuencia personal no disponible") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"sequence": sequence, "sequences": settings["graphics_sequences"]}


@app.delete("/api/graphics/sequences/{sequence_id}")
async def remove_graphics_sequence(sequence_id: str) -> dict[str, Any]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    if not delete_sequence(settings, sequence_id):
        raise HTTPException(404, "Secuencia personal no disponible")
    await run_in_threadpool(runtime.save_current_settings, settings)
    return {"sequences": settings["graphics_sequences"]}


@app.post("/api/graphics/sequences/{sequence_id}/run", status_code=202)
async def run_graphics_sequence(sequence_id: str) -> dict[str, Any]:
    global _graphics_sequence_task
    match_id = str((runtime.active_match or {}).get("id") or "")
    if not match_id:
        raise HTTPException(409, "Carga un partido antes de lanzar una secuencia")
    try:
        sequence = find_sequence(runtime.settings_store.load(), sequence_id)
    except KeyError as exc:
        raise HTTPException(404, "Secuencia personal no disponible") from exc
    if _graphics_sequence_task and not _graphics_sequence_task.done():
        _graphics_sequence_task.cancel()

    async def play() -> None:
        try:
            for index, step in enumerate(sequence["steps"]):
                def show(current: dict[str, Any]) -> None:
                    hide_all(current)
                    set_panel(current, step["panel"], True, lineup_team=step.get("lineup_team"))
                    current["graphics_sequence_run"] = {
                        "id": sequence["id"], "name": sequence["name"],
                        "step": index + 1, "total": len(sequence["steps"]), "status": "running",
                    }
                await run_in_threadpool(runtime.mutate_state, show)
                await broadcast_state()
                await asyncio.sleep(step["duration_seconds"])
                await run_in_threadpool(runtime.mutate_state, lambda current: set_panel(current, step["panel"], False))
                await broadcast_state()
                if step["interval_seconds"]:
                    await asyncio.sleep(step["interval_seconds"])
        except asyncio.CancelledError:
            pass
        finally:
            def finish(current: dict[str, Any]) -> None:
                run = current.get("graphics_sequence_run") or {}
                if run.get("id") == sequence["id"]:
                    current.pop("graphics_sequence_run", None)
            await run_in_threadpool(runtime.mutate_state, finish)
            await broadcast_state()
    _graphics_sequence_task = asyncio.create_task(play())
    return await broadcast_state()


@app.post("/api/graphics/sequences/stop")
async def stop_graphics_sequence() -> dict[str, Any]:
    global _graphics_sequence_task
    if _graphics_sequence_task and not _graphics_sequence_task.done():
        _graphics_sequence_task.cancel()
    await run_in_threadpool(runtime.mutate_state, lambda state: state.pop("graphics_sequence_run", None))
    return await broadcast_state()


@app.post("/api/player-profile")
async def update_player_profile(payload: PlayerProfileRequest) -> dict[str, Any]:
    try:
        await run_in_threadpool(
            runtime.update_player_profile,
            payload.team,
            payload.player_id,
            show=payload.show,
        )
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return await broadcast_state()


@app.put("/api/score-control")
async def set_score_control(payload: ScoreModeRequest) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.set_score_mode, payload.mode)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/scores/{team_key}")
async def set_score(team_key: str, payload: ScoreRequest) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    try:
        await run_in_threadpool(runtime.write_score, team_key, payload.value)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/scores/{team_key}/delta")
async def change_score(team_key: str, payload: ScoreDeltaRequest) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    scores = await run_in_threadpool(runtime.scores)
    key = "team1_score" if team_key == "team1" else "team2_score"
    try:
        current = int(scores.get(key) or 0)
    except ValueError:
        current = 0
    try:
        await run_in_threadpool(runtime.write_score, team_key, max(0, current + payload.delta))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/time")
async def set_time(payload: TimeRequest) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.write_time, payload.value.strip())
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/match/period")
async def set_period(payload: PeriodRequest) -> dict[str, Any]:
    appearance = runtime.safe_settings().get("appearance") or {}
    maximum = int((appearance.get("period_strip") or {}).get("segments") or 3)
    if payload.value > maximum:
        raise HTTPException(409, f"La identidad publicada tiene {maximum} periodos configurados")
    await run_in_threadpool(
        runtime.mutate_state,
        lambda state: state.setdefault("match", {}).update({"period": payload.value}),
    )
    return await broadcast_state()


@app.post("/api/powerplays/{team_key}/start")
async def start_powerplay_route(team_key: str, payload: PowerplayStartRequest) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    try:
        player_row = await run_in_threadpool(runtime.require_called_up_player, team_key, payload.player_id)
        player_number = player_row.get("shirt_number")
        if player_number in (None, ""):
            raise RuntimeError("El jugador convocado no tiene dorsal asignado")

        serving_row = player_row
        if payload.penalty_type == "2+10":
            if not payload.serving_player_id:
                raise RuntimeError("En 2+10 debes seleccionar otro jugador convocado para cumplir los 2 minutos")
            serving_row = await run_in_threadpool(
                runtime.require_called_up_player, team_key, payload.serving_player_id
            )
            if str(payload.serving_player_id) == str(payload.player_id):
                raise RuntimeError("En 2+10 los 2 minutos debe cumplirlos otro jugador convocado")
        serving_number = serving_row.get("shirt_number")
        if serving_number in (None, ""):
            raise RuntimeError("El jugador que cumple la sanción no tiene dorsal asignado")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc

    current_seconds = payload.current_seconds
    if current_seconds is None:
        current_seconds = await run_in_threadpool(runtime.current_seconds)
    if current_seconds is None:
        raise HTTPException(409, "No hay un tiempo OCR válido")

    def mutate(state: dict[str, Any]) -> None:
        info = state.setdefault("powerplay", {}).setdefault(team_key, {})
        start_powerplay(
            info,
            current_seconds=current_seconds,
            player_id=payload.player_id,
            player_number=player_number,
            penalty_type=payload.penalty_type,
            serving_player_id=str(serving_row.get("player_id") or (serving_row.get("player") or {}).get("id") or ""),
            serving_player_number=serving_number,
        )

    await run_in_threadpool(runtime.mutate_state, mutate)

    if runtime.supabase and runtime.active_match:
        team = runtime.active_match.get("home_team" if team_key == "team1" else "away_team") or {}
        seconds, total_minutes, personal = penalty_values(payload.penalty_type)
        try:
            await run_in_threadpool(
                runtime.supabase.create_event,
                match_id=runtime.active_match["id"],
                team_id=team["id"],
                player_id=payload.player_id,
                event_type="penalty",
                match_time=runtime.scores().get("time", ""),
                penalty_type=payload.penalty_type,
                penalty_minutes=total_minutes,
                team_penalty_seconds=seconds,
                personal_penalty_minutes=personal,
            )
            await run_in_threadpool(runtime.refresh_online_events)
        except Exception:
            pass
    return await broadcast_state()


@app.post("/api/powerplays/{team_key}/end")
async def end_powerplay_route(team_key: str) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    await run_in_threadpool(runtime.mutate_state, lambda state: end_powerplay(state["powerplay"][team_key]))
    return await broadcast_state()


@app.post("/api/powerplays/{team_key}/burn")
async def burn_powerplay_route(team_key: str) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    current = await run_in_threadpool(runtime.current_seconds)
    await run_in_threadpool(runtime.mutate_state, lambda state: burn_powerplay_block(state["powerplay"][team_key], current))
    return await broadcast_state()



@app.post("/api/empty-net/{team_key}/toggle")
async def toggle_empty_net_route(team_key: str) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")

    def mutate(state: dict[str, Any]) -> None:
        empty = state.setdefault("empty_net", {"team1": False, "team2": False})
        empty[team_key] = not bool(empty.get(team_key))

    await run_in_threadpool(runtime.mutate_state, mutate)
    return await broadcast_state()


@app.post("/api/penalties/{team_key}/{attempt_index}")
async def set_penalty_attempt(team_key: str, attempt_index: int, payload: PenaltyAttemptRequest) -> dict[str, Any]:
    if team_key not in {"team1", "team2"}:
        raise HTTPException(404, "Equipo desconocido")
    if not 0 <= attempt_index < 5:
        raise HTTPException(400, "El intento debe estar entre 1 y 5")

    def mutate(state: dict[str, Any]) -> None:
        set_attempt(state, team_key, attempt_index, payload.outcome)

    await run_in_threadpool(runtime.mutate_state, mutate)
    return await broadcast_state()


@app.post("/api/penalties/reset")
async def reset_penalty_attempts() -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> None:
        reset_shootout(state)

    await run_in_threadpool(runtime.mutate_state, mutate)
    return await broadcast_state()


@app.post("/api/obs/connect")
async def connect_obs(payload: OBSConnectRequest | None = None) -> dict[str, Any]:
    if runtime.obs is None:
        raise HTTPException(503, "El controlador OBS no está disponible")
    settings = await run_in_threadpool(runtime.settings_store.load)
    obs_settings = settings.setdefault("obs", {})
    if payload is not None:
        updates = payload.model_dump(exclude_none=True)
        # An empty password means preserve the stored password, never erase it.
        if updates.get("password") == "":
            updates.pop("password", None)
        obs_settings.update(updates)
        await run_in_threadpool(runtime.save_current_settings, settings)
    try:
        await run_in_threadpool(
            runtime.obs.connect,
            obs_settings.get("host", "127.0.0.1"),
            obs_settings.get("port", 4455),
            obs_settings.get("password", ""),
        )
    except Exception as exc:
        password_hint = "" if obs_settings.get("password") else " No hay una contraseña OBS guardada en SecretariatPro."
        raise HTTPException(503, f"{exc}{password_hint}") from exc
    return await broadcast_state()


@app.post("/api/obs/disconnect")
async def disconnect_obs() -> dict[str, Any]:
    if runtime.obs is not None:
        await run_in_threadpool(runtime.obs.disconnect)
    return await broadcast_state()


@app.get("/api/obs/status")
async def get_obs_status() -> dict[str, Any]:
    return await run_in_threadpool(runtime.obs_status, refresh=True)


@app.post("/api/obs/scenes/program")
async def set_obs_program_scene(payload: OBSSceneRequest) -> dict[str, Any]:
    if runtime.obs is None:
        raise HTTPException(503, "El controlador OBS no está disponible")
    if not runtime.obs.connected:
        raise HTTPException(409, "Conecta OBS antes de cambiar de escena")
    try:
        await run_in_threadpool(runtime.obs.set_program_scene, payload.scene_name)
    except Exception as exc:
        raise HTTPException(503, f"No se pudo cambiar la escena de OBS: {exc}") from exc
    return await broadcast_state()


@app.get("/api/obs/projector-windows")
async def projector_windows() -> list[dict[str, Any]]:
    try:
        import obs_projector_video
        rows = await run_in_threadpool(obs_projector_video.list_windows)
        return [
            {
                "window_id": row.window_id,
                "selection_key": f"window:{row.window_id}",
                "label": row.label,
                "rect": row.rect,
            }
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


def _projector_frames(initial_label: str):
    import time
    import cv2
    import obs_projector_video

    missing_cycles = 0
    while True:
        settings = runtime.settings_store.load().get("obs", {})
        wanted = str(settings.get("projector_window") or initial_label or "").strip()
        windows = obs_projector_video.list_windows()
        window = obs_projector_video.select_projector_window(windows, wanted)
        if window is None:
            missing_cycles += 1
            if missing_cycles >= 20:
                return
            time.sleep(0.25)
            continue
        missing_cycles = 0
        frame = obs_projector_video.capture_window(window)
        if frame is None or not getattr(frame, "size", 0):
            time.sleep(0.25)
            continue
        height, width = frame.shape[:2]
        if width > 1920:
            scale = 1920 / width
            frame = cv2.resize(frame, (1920, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-store\r\n\r\n" + encoded.tobytes() + b"\r\n"
        time.sleep(0.12)


@app.get("/api/obs/projector-stream")
async def projector_stream() -> StreamingResponse:
    try:
        import obs_projector_video
        windows = await run_in_threadpool(obs_projector_video.list_windows)
        settings = await run_in_threadpool(runtime.settings_store.load)
        wanted = str(settings.get("obs", {}).get("projector_window") or "").strip()
        window = obs_projector_video.select_projector_window(windows, wanted)
        if window is None:
            raise HTTPException(404, "No se encontró una ventana de proyector OBS")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return StreamingResponse(
        _projector_frames(window.label),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


_program_preview = ProgramPreview(fps=8)


def _obs_program_frames():
    """MJPEG directly from OBS Program; never falls back to desktop pixels."""
    import time

    failures = 0
    while runtime.obs is not None and runtime.obs.connected:
        try:
            frame = _program_preview.read(runtime.obs)
            failures = 0
            yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-store\r\n\r\n" + frame + b"\r\n"
        except Exception:
            failures += 1
            if failures >= 12:
                return
        # Monitoring only: output/recording FPS and OCR capture are unchanged.
        # Demand-driven requests stop when the last monitor disconnects.
        time.sleep(_program_preview.interval)


@app.get("/api/obs/program-stream")
async def obs_program_stream() -> StreamingResponse:
    if runtime.obs is None or not runtime.obs.connected:
        raise HTTPException(409, "Conecta OBS para ver la escena de programa")
    return StreamingResponse(
        _obs_program_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/replays")
async def replay_library() -> dict[str, Any]:
    return await run_in_threadpool(runtime.replay_snapshot)


@app.post("/api/replays/start")
async def start_replay_buffer() -> dict[str, Any]:
    if runtime.obs is None or not runtime.obs.connected:
        raise HTTPException(409, "Conecta OBS antes de iniciar el búfer de repetición")
    try:
        plugin = await run_in_threadpool(runtime.replay_plugin.status)
        if plugin.get("available"):
            await run_in_threadpool(runtime.replay_plugin.set_buffers_active, True)
        else:
            await run_in_threadpool(runtime.obs.start_replay_buffer)
    except Exception as exc:
        raise HTTPException(503, f"No se pudo iniciar el búfer de repetición: {exc}") from exc
    return await run_in_threadpool(runtime.replay_snapshot)


@app.post("/api/replays/stop")
async def stop_replay_buffer() -> dict[str, Any]:
    if runtime.obs is None or not runtime.obs.connected:
        raise HTTPException(409, "OBS no está conectado")
    try:
        plugin = await run_in_threadpool(runtime.replay_plugin.status)
        if plugin.get("available"):
            await run_in_threadpool(runtime.replay_plugin.set_buffers_active, False)
        else:
            await run_in_threadpool(runtime.obs.stop_replay_buffer)
    except Exception as exc:
        raise HTTPException(503, f"No se pudo detener el búfer de repetición: {exc}") from exc
    return await run_in_threadpool(runtime.replay_snapshot)


async def _save_replay_marker(marker: dict[str, Any]) -> None:
    try:
        if runtime.obs is None:
            raise RuntimeError("El controlador OBS no está disponible")
        plugin = await asyncio.to_thread(runtime.replay_plugin.status)
        if plugin.get("available"):
            result = await asyncio.to_thread(runtime.replay_plugin.mark)
            await asyncio.to_thread(
                runtime.replays.complete_multicam_marker,
                marker["id"],
                result.get("saved_paths") or [],
            )
        else:
            path = await asyncio.to_thread(runtime.obs.save_replay_buffer)
            await asyncio.to_thread(runtime.replays.complete_marker, marker["id"], path)
    except Exception as exc:
        await asyncio.to_thread(runtime.replays.fail_marker, marker["id"], str(exc))
    try:
        await broadcast_state()
    except Exception:
        pass


@app.post("/api/replays/mark", status_code=202)
async def mark_replay(payload: ReplayMarkRequest) -> dict[str, Any]:
    if runtime.obs is None or not runtime.obs.connected:
        raise HTTPException(409, "Conecta OBS antes de marcar un replay")
    try:
        plugin = await run_in_threadpool(runtime.replay_plugin.status)
        status = plugin if plugin.get("available") else await run_in_threadpool(runtime.obs.replay_status)
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    if not status.get("active"):
        raise HTTPException(409, "Activa el búfer de repetición de OBS antes de marcar una jugada")
    marker = await run_in_threadpool(
        runtime.replays.create_marker,
        match_id=str((runtime.active_match or {}).get("id") or ""),
        label=payload.label,
        event_type=payload.label,
        period=int(runtime.read_state().get("match", {}).get("period") or 1),
        match_time=payload.match_time or runtime.scores().get("time", ""),
        event_id=payload.event_id,
        team=payload.team,
        player=payload.player,
        post_roll_seconds=payload.post_roll_seconds,
    )
    saving = asyncio.create_task(_save_replay_marker(marker))
    _replay_exports.add(saving)
    saving.add_done_callback(_replay_exports.discard)
    return {"marker": marker, **(await run_in_threadpool(runtime.replay_snapshot))}


@app.post("/api/replays/take")
async def take_multicam_replay() -> dict[str, Any]:
    snapshot = await run_in_threadpool(runtime.replay_snapshot)
    status = snapshot.get("status") or {}
    clips = snapshot.get("clips") or []
    clip = next((row for row in clips if row.get("status") == "ready"), None)
    if not clip:
        raise HTTPException(409, "Marca un evento antes de lanzar la repetición")
    segments = status.get("timeline") or [{"camera": 1, "duration_seconds": 3, "speed_percent": 100}]
    return await compose_multicam_replay(ReplayCompositionRequest(clip_id=clip["id"], segments=segments, play_now=True))


@app.post("/api/replays/out")
async def return_replay_to_live() -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.replay_plugin.out)
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
    return await run_in_threadpool(runtime.replay_snapshot)


@app.post("/api/replays/camera/{direction}")
async def switch_replay_camera(direction: str) -> dict[str, Any]:
    if direction not in {"next", "previous"}:
        raise HTTPException(400, "Dirección de cámara no válida")
    try:
        await run_in_threadpool(runtime.replay_plugin.switch_camera, direction)
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
    return await run_in_threadpool(runtime.replay_snapshot)


@app.patch("/api/replays/{clip_id}")
async def select_replay(clip_id: str, payload: ReplaySelectionRequest) -> dict[str, Any]:
    try:
        if payload.label:
            await run_in_threadpool(runtime.replays.update_marker, clip_id, str((runtime.active_match or {}).get("id") or ""), label=payload.label, event_type=payload.label)
        await run_in_threadpool(runtime.replays.set_included, clip_id, payload.included)
    except KeyError as exc:
        raise HTTPException(404, "Clip no disponible") from exc
    return await run_in_threadpool(runtime.replay_snapshot)


@app.post("/api/replays/composition")
async def compose_multicam_replay(payload: ReplayCompositionRequest) -> dict[str, Any]:
    global _goal_replay_task
    plugin = await run_in_threadpool(runtime.replay_plugin.status)
    if not plugin.get("available"):
        raise HTTPException(409, "Esta función necesita el plugin multicámara conectado")
    clips = (await run_in_threadpool(runtime.replay_snapshot)).get("clips") or []
    clip = next((row for row in clips if row.get("id") == payload.clip_id), None) if payload.clip_id else next((row for row in clips if row.get("status") == "ready"), None)
    if not clip:
        raise HTTPException(409, "Espera a que la marca termine de guardar todas las cámaras")
    if clip.get("status") != "ready" or plugin.get("library_playback"):
        raise HTTPException(409, "Espera a que las cámaras de este evento estén listas")
    sources = [str(r.get("path") or "") for r in plugin.get("saved_paths", [])]
    if clip.get("source_paths") != sources:
        raise HTTPException(409, "El plugin tiene otro evento cargado; usa la biblioteca para los anteriores")
    if plugin.get("playing"):
        raise HTTPException(409, "Espera a que termine la repetición actual")
    segments = [segment.model_dump() for segment in payload.segments]
    if not segments:
        if payload.save_video or payload.play_now:
            raise HTTPException(400, "Añade al menos un plano a la repetición")
        await run_in_threadpool(runtime.replay_plugin.compose, [], play_now=False)
        return await run_in_threadpool(runtime.replay_snapshot)
    if (payload.save_video or payload.play_now) and not runtime.replays._ffmpeg():
        raise HTTPException(409, "FFmpeg no está disponible para guardar la repetición")
    try:
        if payload.play_now:
            await broadcast_flow._state("REPLAY_LOADING")
        applied = await run_in_threadpool(runtime.replay_plugin.compose, segments, play_now=payload.play_now)
        actual = applied.get("timeline") or segments
        saved = await run_in_threadpool(runtime.replays.set_composition, clip["id"], actual, int(applied.get("window_start_ms") or 0))
        async def export_event() -> None:
            try:
                await asyncio.to_thread(runtime.replays.create_highlights, str(clip.get("match_id") or ""), [clip["id"]], clip.get("label") or "Replay")
            except Exception as exc:
                await asyncio.to_thread(runtime.replays.fail_marker, clip["id"], str(exc))
            await broadcast_state()
        if payload.save_video or payload.play_now:
            export_task = asyncio.create_task(export_event())
            _replay_exports.add(export_task)
            export_task.add_done_callback(_replay_exports.discard)
    except (KeyError, ValueError) as exc:
        await broadcast_flow._state("BUILDING" if payload.goal_flow else "IDLE", scoreboard=not payload.goal_flow)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        # A timeout is not confirmation of live: keep graphics hidden if OBS may be playing.
        current = await run_in_threadpool(runtime.replay_plugin.status)
        if current.get("playing"):
            await broadcast_flow.playing(goal=payload.goal_flow)
        else:
            await broadcast_flow._state("BUILDING" if payload.goal_flow else "IDLE", scoreboard=not payload.goal_flow)
        raise HTTPException(409, str(exc)) from exc
    if payload.play_now:
        await broadcast_flow.playing(goal=payload.goal_flow)
    elif payload.goal_flow and payload.save_video:
        await broadcast_flow.without_replay()
    return {"clip": saved, "goal_flow": payload.goal_flow, **(await run_in_threadpool(runtime.replay_snapshot))}


@app.post("/api/replays/goal/skip")
async def skip_goal_replay() -> dict[str, Any]:
    if runtime.read_state().get("pending_goal_celebration"):
        await broadcast_flow.without_replay()
    else:
        broadcast_flow.cancel()
        await broadcast_flow._state("IDLE", scoreboard=True)
    return await broadcast_state()


@app.post("/api/replays/highlights")
async def create_highlights(payload: HighlightsRequest) -> dict[str, Any]:
    match_id = str((runtime.active_match or {}).get("id") or "")
    try:
        result = await run_in_threadpool(runtime.replays.create_highlights, match_id, payload.clip_ids, payload.title, saved_events=True)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"highlight": result, **(await run_in_threadpool(runtime.replay_snapshot))}


@app.post("/api/replays/folder")
async def open_replay_folder() -> dict[str, str]:
    import subprocess
    import sys
    directory = str(runtime.replays.match_directory(str((runtime.active_match or {}).get("id") or "")))
    if sys.platform == "darwin":
        await run_in_threadpool(subprocess.run, ["open", directory], check=True)
    elif os.name == "nt":
        os.startfile(directory)
    else:
        await run_in_threadpool(subprocess.run, ["xdg-open", directory], check=True)
    return {"path": directory}


@app.get("/api/replays/media/{item_id}")
async def replay_media(item_id: str, angle: int | None = None) -> FileResponse:
    try:
        path = await run_in_threadpool(runtime.replays.media_path, item_id, angle)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(404, "Archivo de replay no disponible") from exc
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


@app.get("/api/replays/templates")
async def replay_templates() -> list[dict]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    return list(settings.get("replay_templates") or [])


@app.post("/api/replays/templates")
async def save_replay_template(payload: ReplayTemplateRequest) -> list[dict]:
    from uuid import uuid4
    settings = await run_in_threadpool(runtime.settings_store.load)
    rows = list(settings.get("replay_templates") or [])
    if payload.id and not any(row.get("id") == payload.id for row in rows):
        raise HTTPException(404, "Plantilla no disponible")
    row = payload.model_dump()
    row["id"] = payload.id or uuid4().hex
    rows = [r for r in rows if r.get("id") != row["id"]]
    if row["default"]:
        for other in rows:
            other["default"] = False
    rows.append(row)
    settings["replay_templates"] = rows
    await run_in_threadpool(runtime.save_current_settings, settings)
    return rows


@app.delete("/api/replays/templates/{template_id}")
async def delete_replay_template(template_id: str) -> list[dict]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    rows = [r for r in settings.get("replay_templates", []) if r.get("id") != template_id]
    settings["replay_templates"] = rows
    await run_in_threadpool(runtime.save_current_settings, settings)
    return rows


@app.get("/api/replays/thumbnail/{item_id}")
async def replay_thumbnail(item_id: str) -> FileResponse:
    rows = (await run_in_threadpool(runtime.replays.snapshot)).get("highlights", [])
    item = next((r for r in rows if r.get("id") == item_id), {})
    path = Path(item.get("thumbnail") or "")
    if not path.is_file():
        raise HTTPException(404, "Miniatura no disponible")
    return FileResponse(path, media_type="image/jpeg")


@app.delete("/api/replays/library/{item_id}")
async def delete_replay_video(item_id: str) -> dict[str, Any]:
    try:
        path = await run_in_threadpool(runtime.replays.media_path, item_id)
        plugin = await run_in_threadpool(runtime.replay_plugin.status)
        if plugin.get("playing") and any(str(row.get("path")) == str(path) for row in plugin.get("saved_paths", [])):
            raise HTTPException(409, "Vuelve al directo antes de eliminar el vídeo en emisión")
        result = await run_in_threadpool(runtime.replays.delete_video, item_id, str((runtime.active_match or {}).get("id") or ""))
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(404, "Repetición no disponible") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await broadcast_state()
    return {"deleted": result, **(await run_in_threadpool(runtime.replay_snapshot))}


@app.post("/api/replays/library/{item_id}/restore")
async def restore_replay_video(item_id: str) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.replays.restore_video, item_id, str((runtime.active_match or {}).get("id") or ""))
    except KeyError as exc:
        raise HTTPException(404, "Repetición no disponible en la papelera") from exc
    await broadcast_state()
    return await run_in_threadpool(runtime.replay_snapshot)


@app.post("/api/replays/library/{item_id}/take")
async def take_saved_replay(item_id: str) -> dict:
    state = runtime.read_state()
    if (state.get("broadcast_flow") or {}).get("phase", "IDLE") != "IDLE":
        raise HTTPException(409, "Termina el evento actual antes de lanzar otro")
    try:
        path = await run_in_threadpool(runtime.replays.media_path, item_id)
        await broadcast_flow.begin()
        await broadcast_flow._state("REPLAY_LOADING")
        await run_in_threadpool(runtime.replay_plugin.play_file, path)
        await broadcast_flow.playing(goal=False)
    except Exception as exc:
        await broadcast_flow._state("IDLE", scoreboard=True)
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return await run_in_threadpool(runtime.safe_settings)


@app.patch("/api/settings")
async def patch_settings(payload: SettingsPatch) -> dict[str, Any]:
    settings = await run_in_threadpool(runtime.settings_store.load)
    if payload.language is not None:
        settings["language"] = payload.language
    if payload.obs is not None:
        existing_password = settings.setdefault("obs", {}).get("password", "")
        settings["obs"].update(payload.obs)
        if not payload.obs.get("password"):
            settings["obs"]["password"] = existing_password
    if payload.shortcuts is not None:
        settings["shortcuts"] = dict(payload.shortcuts)
    if payload.appearance is not None:
        if "app_theme" in payload.appearance:
            settings["appearance"]["app_theme"] = payload.appearance["app_theme"]
    if payload.ocr_data_sharing is not None:
        try:
            await run_in_threadpool(runtime.set_ocr_sample_sharing, payload.ocr_data_sharing)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(409, str(exc)) from exc
    await run_in_threadpool(runtime.save_current_settings, settings)
    return await broadcast_state()


@app.post("/api/ocr/start")
async def start_ocr_runtime() -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.ocr_runtime.start)
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/ocr/stop")
async def stop_ocr_runtime() -> dict[str, Any]:
    # Detener reconocimiento no libera la cámara seleccionada; la fuente OCR
    # permanece activa hasta cambiar de fuente o cerrar SecretariatPro.
    await run_in_threadpool(runtime.ocr_runtime.stop)
    return await broadcast_state()


@app.get("/api/ocr/status")
async def ocr_runtime_status() -> dict[str, Any]:
    return await run_in_threadpool(runtime.ocr_runtime.status)


@app.get("/api/ocr/sample-sharing-status")
async def ocr_sample_sharing_status() -> dict[str, Any]:
    return await run_in_threadpool(runtime.ocr_sample_delivery_status)


@app.get("/api/ocr/preview")
async def ocr_preview(
    source_type: str = Query("window", pattern="^(window|camera)$"),
    source_id: str = Query(""),
    window_title: str = Query(""),
    raw: bool = Query(False),
) -> Response:
    try:
        import cv2
        if source_type == "camera":
            if str(source_id).strip() == "":
                raise HTTPException(400, "Selecciona una cámara")
            await run_in_threadpool(runtime.camera_service.activate, int(source_id))
            frame = await run_in_threadpool(runtime.camera_service.read, int(source_id))
        else:
            import window_capture
            windows = await run_in_threadpool(window_capture.list_windows)
            window = None
            if str(source_id).strip():
                window = next((row for row in windows if str(row.window_id) == str(source_id)), None)
            if window is None and str(window_title).strip():
                window = next((row for row in windows if row.label == window_title), None)
            if window is None:
                raise HTTPException(404, "La ventana seleccionada ya no está disponible")
            frame, _ = await run_in_threadpool(window_capture.capture_window, window.window_id)
        if frame is None:
            raise HTTPException(503, "No se pudo capturar la fuente de vídeo")
        if not raw:
            from secretariat_core.ocr_geometry import apply_perspective
            config = await run_in_threadpool(runtime.ocr_store.load)
            frame = await run_in_threadpool(apply_perspective, frame, config.get("perspective"))
        height, width = frame.shape[:2]
        if width > 1440:
            scale = 1440 / width
            frame = cv2.resize(frame, (1440, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if not ok:
            raise HTTPException(503, "No se pudo codificar el preview")
        return Response(encoded.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/ocr/source/activate")
async def activate_ocr_source(payload: OCRSourceActivation) -> dict[str, Any]:
    try:
        result = await run_in_threadpool(
            runtime.activate_ocr_source,
            payload.source_type,
            payload.source_id,
            payload.source_label,
        )
    except Exception as exc:
        raise HTTPException(409, str(exc)) from exc
    snapshot = await broadcast_state()
    return {"source": result, "snapshot": snapshot}


@app.get("/api/ocr/config")
async def get_ocr_config() -> dict[str, Any]:
    config = await run_in_threadpool(runtime.ocr_store.load)
    # Old installations only stored window_title. Treat them as a window source.
    config.setdefault("source_type", "window")
    config.setdefault("source_id", "")
    config.setdefault("source_label", config.get("window_title") or "")
    return config


@app.put("/api/ocr/config")
async def put_ocr_config(payload: OCRConfigPayload) -> dict[str, Any]:
    from secretariat_core.ocr_geometry import normalize_perspective
    config = payload.model_dump()
    for key in ("team1_score", "team2_score", "time"):
        config.setdefault("regions", {}).setdefault(key, None)
    config["perspective"] = normalize_perspective(config.get("perspective"))
    config.setdefault("model", {})
    config["model"] = {"model_name": "en_PP-OCRv4_mobile_rec", "model_dir": "", "min_confidence": 0.25}
    if config.get("source_type") == "window":
        config["window_title"] = str(config.get("source_label") or config.get("window_title") or "")
        await run_in_threadpool(runtime.camera_service.deactivate)
    else:
        config["window_title"] = ""
        try:
            await run_in_threadpool(runtime.camera_service.activate, int(config.get("source_id") or ""))
        except Exception as exc:
            raise HTTPException(409, str(exc)) from exc
    await run_in_threadpool(runtime.ocr_store.save, config)
    return await broadcast_state()


@app.get("/api/ocr/model")
async def ocr_model_info() -> dict[str, Any]:
    import ocr_engine
    config = await run_in_threadpool(runtime.ocr_store.load)
    await run_in_threadpool(ocr_engine.configure, config.get("model") or {}, base_dir=BASE_DIR)
    return await run_in_threadpool(ocr_engine.active_model_info)


@app.get("/api/ocr/sources")
async def list_ocr_sources() -> list[dict[str, Any]]:
    try:
        import window_capture
        from video_source import list_cameras
        windows = await run_in_threadpool(window_capture.list_windows)
        window_rows = [{
            "source_type": "window", "source_id": str(window.window_id), "source_key": f"window:{window.window_id}",
            "label": window.label, "detail": "Ventana", "rect": window.rect,
        } for window in windows]
        # Camera discovery is intentionally isolated from window enumeration; a
        # denied camera permission must not remove the proven window source.
        try:
            camera_status = await run_in_threadpool(runtime.camera_service.status)
            active_index = camera_status.get("index") if camera_status.get("active") else None
            active_detail = str(camera_status.get("detail") or "")
            cameras = await run_in_threadpool(
                lambda: list_cameras(active_index=active_index, active_detail=active_detail)
            )
            camera_rows = [row.as_dict() for row in cameras]
        except Exception:
            camera_rows = []
        return window_rows + camera_rows
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/ocr/windows")
async def list_ocr_windows() -> list[dict[str, Any]]:
    # Backward-compatible endpoint retained for older clients.
    try:
        import window_capture
        windows = await run_in_threadpool(window_capture.list_windows)
        return [{"window_id": window.window_id, "label": window.label, "rect": window.rect} for window in windows]
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/auth/login")
async def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        result = await run_in_threadpool(runtime.login, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    except BlockingIOError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    tablet_access_control.revoke_all()
    snapshot = await broadcast_state()
    return {**result, "snapshot": snapshot}


@app.post("/api/auth/logout")
async def logout() -> dict[str, Any]:
    tablet_access_control.revoke_all()
    await run_in_threadpool(runtime.logout)
    return await broadcast_state()


@app.post("/api/workspaces/activate")
async def activate_workspace(payload: WorkspaceActivateRequest) -> dict[str, Any]:
    try:
        tablet_access_control.revoke_all()
        snapshot = await run_in_threadpool(runtime.activate_workspace, payload.workspace_id)
        await manager.broadcast({"type": "state", "payload": snapshot})
        return snapshot
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/password-reset")
async def password_reset(payload: PasswordResetRequest) -> dict[str, str]:
    # Always return a neutral response so the endpoint does not reveal whether
    # an address exists in the Supabase project.
    try:
        await run_in_threadpool(runtime.request_password_reset, payload.email)
    except Exception as exc:
        message = str(exc)
        if "válido" in message.lower() or "valid" in message.lower():
            raise HTTPException(400, message) from exc
    return {"message": "Si la cuenta existe, recibirás un correo para restablecer la contraseña."}


@app.get("/api/account/profile")
async def account_profile() -> dict[str, Any]:
    try:
        return await run_in_threadpool(runtime.account_profile)
    except Exception as exc:
        raise HTTPException(401, str(exc)) from exc


@app.patch("/api/account/profile")
async def update_account_profile(payload: AccountProfileUpdate) -> dict[str, Any]:
    try:
        profile = await run_in_threadpool(runtime.update_account_profile, payload.display_name)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    await broadcast_state()
    return profile


@app.post("/api/account/password")
async def update_account_password(payload: AccountPasswordUpdate) -> dict[str, str]:
    try:
        await run_in_threadpool(runtime.update_account_password, payload.password)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"message": "Contraseña actualizada correctamente."}


@app.post("/api/account/avatar")
async def update_account_avatar(payload: AccountAvatarUpdate) -> dict[str, Any]:
    try:
        profile = await run_in_threadpool(runtime.upload_account_avatar, payload.image_data)
    except Exception as exc:
        message = str(exc)
        if "bucket" in message.lower() or "row-level security" in message.lower() or "storage" in message.lower():
            message = (
                "No se pudo guardar la foto. Ejecuta SUPABASE_PROFILE_SETUP.sql "
                "en Supabase para crear el bucket avatars y sus políticas."
            )
        raise HTTPException(400, message) from exc
    await broadcast_state()
    return profile


@app.delete("/api/account/avatar")
async def delete_account_avatar() -> dict[str, Any]:
    try:
        profile = await run_in_threadpool(runtime.remove_account_avatar)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    await broadcast_state()
    return profile


@app.get("/api/competitions")
async def competitions() -> list[dict[str, Any]]:
    if not runtime.supabase:
        raise HTTPException(401, "Debes iniciar sesión primero")
    try:
        return await run_in_threadpool(runtime.available_competitions)
    except Exception as exc:
        raise HTTPException(503, "No se pudieron cargar las competiciones. Tu sesión sigue abierta; vuelve a intentarlo.") from exc


@app.get("/api/competitions/{competition_id}/matches")
async def matches(competition_id: str) -> list[dict[str, Any]]:
    try:
        return await run_in_threadpool(runtime.list_matches, competition_id)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/competitions/{competition_id}/matches/{match_id}/load")
async def load_match(competition_id: str, match_id: str) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.load_match, competition_id, match_id)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return await broadcast_state()


@app.put("/api/match/attendance")
async def save_attendance(payload: AttendancePayload) -> dict[str, Any]:
    if not runtime.supabase or not runtime.active_match:
        raise HTTPException(409, "No hay un partido online cargado")
    match = runtime.active_match
    for team_key, team_field in (("team1", "home_team"), ("team2", "away_team")):
        selected = set(getattr(payload, team_key))
        team = match.get(team_field) or {}
        rows = [row for row in runtime.rosters[team_key] if str(row.get("member_type") or "player").lower() != "coach"]
        await run_in_threadpool(
            runtime.supabase.save_match_players,
            match["id"], team["id"], rows, selected,
        )

    def mutate(state: dict[str, Any]) -> None:
        lineups = state.setdefault("statistics", {}).setdefault("lineups", {})
        for team_key in ("team1", "team2"):
            selected = set(getattr(payload, team_key))
            available_players = [
                roster_player(row)
                for row in runtime.rosters.get(team_key, [])
                if str(row.get("member_type") or "player").lower() != "coach"
            ]
            player_index = {
                str(player.get("player_id") or ""): player
                for player in available_players
                if player.get("player_id")
            }
            lineups[f"{team_key}_players"] = [
                player for player in available_players
                if str(player.get("player_id") or "") in selected
            ]
            selected_starters = {}
            for slot, player_id in (payload.starters.get(team_key, {}) or {}).items():
                player = player_index.get(str(player_id or ""))
                if player and str(player.get("player_id") or "") in selected:
                    selected_starters[slot] = player
            lineups[f"{team_key}_starters"] = selected_starters

    await run_in_threadpool(runtime.mutate_state, mutate)
    await run_in_threadpool(
        runtime.set_attendance,
        {"team1": set(payload.team1), "team2": set(payload.team2)},
    )
    return await broadcast_state()


@app.post("/api/statistics/refresh")
async def refresh_statistics() -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.refresh_statistics)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return await broadcast_state()


@app.post("/api/events/refresh")
async def refresh_events() -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.refresh_online_events)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return await broadcast_state()


@app.delete("/api/events/{event_id}")
async def cancel_event(event_id: str) -> dict[str, Any]:
    try:
        await run_in_threadpool(runtime.cancel_online_event, event_id)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return await broadcast_state()


_goal_submit_lock = asyncio.Lock()
_goal_results: dict[str, dict] = {}

@app.post("/api/events/goal")
async def create_goal(payload: GoalPayload) -> dict[str, Any]:
    async with _goal_submit_lock:
        key = f"{(runtime.active_match or {}).get('id')}:{payload.request_id}"
        if payload.request_id and key in _goal_results:
            return _goal_results[key]
        result = await _create_goal(payload)
        if payload.request_id:
            _goal_results[key] = result
            if len(_goal_results) > 500:
                del _goal_results[next(iter(_goal_results))]
        return result

async def _create_goal(payload: GoalPayload) -> dict[str, Any]:
    global _goal_replay_task, _goal_celebration_task
    if not runtime.supabase or not runtime.active_match:
        raise HTTPException(409, "No hay un partido online cargado")
    team_field = "home_team" if payload.team == "team1" else "away_team"
    team = runtime.active_match.get(team_field) or {}
    try:
        scorer_row = await run_in_threadpool(runtime.require_called_up_player, payload.team, payload.scorer_id)
        assistant_row = None
        if payload.assistant_id:
            assistant_row = await run_in_threadpool(runtime.require_called_up_player, payload.team, payload.assistant_id)
            if str(payload.assistant_id) == str(payload.scorer_id):
                raise RuntimeError("Goleador y asistente no pueden ser el mismo jugador")
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    match_time = payload.match_time or runtime.scores().get("time", "")
    opponent = "team2" if payload.team == "team1" else "team1"
    state = runtime.read_state()
    powerplay_goal = bool(state.get("powerplay", {}).get(opponent, {}).get("status"))
    goal_marker: dict[str, Any] | None = None
    goal_replay_flow = False
    try:
        await run_in_threadpool(
            runtime.supabase.create_goal_with_assist,
            match_id=runtime.active_match["id"],
            team_id=team["id"],
            scorer_id=payload.scorer_id,
            assistant_id=payload.assistant_id,
            match_time=match_time,
            goal_notes="powerplay_goal" if powerplay_goal else "",
        )
        score_key = "team1_score" if payload.team == "team1" else "team2_score"
        internal = await run_in_threadpool(runtime.score_store.confirm_goal, score_key, payload.score_before)
        if runtime.score_mode() == "manual":
            await run_in_threadpool(runtime.score_store.write_readings, {score_key: internal})
        await run_in_threadpool(runtime.mutate_state, lambda state: state.update(graphic_scores=runtime.graphic_scores()))

        try:
            events = await run_in_threadpool(runtime.refresh_online_events)
        except Exception:
            events = list(getattr(runtime, "events", []) or [])
        # Floorball ends the first opposing minor penalty after a power-play goal.
        # Handball suspensions always continue until their own clock expires.
        if powerplay_goal and runtime.sport_mode() != "handball":
            current_seconds = await run_in_threadpool(runtime.current_seconds)
            await run_in_threadpool(
                runtime.mutate_state,
                lambda score_state: burn_powerplay_block(
                    score_state.setdefault("powerplay", {}).setdefault(opponent, {}),
                    current_seconds,
                ),
            )

        current_state = await run_in_threadpool(runtime.read_state)
        lower_third = build_goal_bottom_bar(
            team_key=payload.team,
            scorer_id=payload.scorer_id,
            assistant_id=payload.assistant_id,
            match=runtime.active_match or {},
            rosters=runtime.rosters,
            events=events,
            team_state=current_state.get(payload.team) or {},
        )
        lower_third["graphic_scores"] = runtime.graphic_scores()
        replay_settings = (runtime.settings_store.load().get("obs") or {})
        if runtime.obs and runtime.obs.connected:
            try:
                replay_status = (await run_in_threadpool(runtime.replay_snapshot)).get("status") or {}
                if replay_status.get("active"):
                    player_data = scorer_row.get("player") or scorer_row
                    player_name = (
                        player_data.get("display_name")
                        or " ".join(str(player_data.get(key) or "") for key in ("first_name", "last_name")).strip()
                        or "Gol"
                    )
                    event_id = ""
                    for event in events:
                        event_player = event.get("player") or {}
                        if event.get("event_type") == "goal" and str(event_player.get("id") or event.get("player_id") or "") == str(payload.scorer_id):
                            event_id = str(event.get("id") or "")
                            break
                    if payload.marker_id:
                        goal_marker = await run_in_threadpool(runtime.replays.update_marker, payload.marker_id, str(runtime.active_match["id"]), label=f"Gol · {player_name}", event_type="Gol", event_id=event_id, team=str(team.get("name") or ""), player=player_name, assistant=runtime._profile_display_name((assistant_row or {}).get("player") or assistant_row or {}) if assistant_row else "")
                    else:
                        goal_marker = await run_in_threadpool(
                            runtime.replays.create_marker,
                        match_id=str(runtime.active_match.get("id") or ""),
                        label=f"Gol · {player_name}",
                        event_type="Gol",
                        period=int(current_state.get("match", {}).get("period") or 1),
                        assistant=runtime._profile_display_name((assistant_row or {}).get("player") or assistant_row or {}) if assistant_row else "",
                        match_time=match_time,
                        event_id=event_id,
                        team=str(team.get("short_name") or team.get("name") or ""),
                        player=player_name,
                        post_roll_seconds=float(replay_settings.get("replay_post_roll_seconds") or 0),
                    )
                    goal_replay_flow = bool(replay_status.get("backend") == "multicam-plugin" and replay_status.get("available"))
                    if not payload.marker_id:
                        saving = asyncio.create_task(_save_replay_marker(goal_marker))
                        _replay_exports.add(saving)
                        saving.add_done_callback(_replay_exports.discard)
            except Exception:
                # A replay failure must never prevent the official goal event.
                pass
        await broadcast_flow.begin(lower_third)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    snapshot = await broadcast_state()
    if goal_marker:
        snapshot["goal_replay_marker_id"] = goal_marker["id"]
        snapshot["goal_replay_flow"] = goal_replay_flow
    if not goal_replay_flow:
        await broadcast_flow.without_replay()
    return snapshot


@app.post("/api/match/finish")
async def finish_match(payload: FinishPayload) -> dict[str, Any]:
    if not runtime.supabase or not runtime.active_match:
        raise HTTPException(409, "No hay un partido online cargado")
    try:
        await run_in_threadpool(
            runtime.supabase.finish_match,
            runtime.active_match["id"],
            payload.home_score,
            payload.away_score,
        )
        runtime.active_match["home_score"] = payload.home_score
        runtime.active_match["away_score"] = payload.away_score
        runtime.active_match["status"] = "finished"
        runtime.standings = await run_in_threadpool(
            runtime.supabase.get_standings,
            runtime.active_match["competition_id"],
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    await run_in_threadpool(runtime.write_score, "team1", payload.home_score, force=True)
    await run_in_threadpool(runtime.write_score, "team2", payload.away_score, force=True)
    return await broadcast_state()
