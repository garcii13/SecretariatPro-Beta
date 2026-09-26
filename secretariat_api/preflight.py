"""Actionable pre-broadcast checks using the current desktop state."""
from __future__ import annotations

import time
from typing import Any


def build_preflight(snapshot: dict[str, Any], tablet_count: int = 0, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    online = snapshot.get("online") or {}
    state = snapshot.get("state") or {}
    obs = snapshot.get("obs") or {}
    ocr = snapshot.get("ocr") or {}
    ocr_runtime = snapshot.get("ocr_runtime") or {}
    settings = snapshot.get("settings") or {}
    score_mode = (snapshot.get("score_control") or {}).get("mode", "ocr")
    checks: list[dict[str, Any]] = []

    def add(
        key: str,
        label: str,
        level: str,
        detail: str,
        action: str = "",
        *,
        required: bool = True,
    ) -> None:
        checks.append({
            "key": key,
            "label": label,
            "level": level,
            "detail": detail,
            "action": action,
            "required": required,
        })

    access = online.get("access") or {}
    add("access", "Membresía", "ok" if access.get("production_allowed") else "fail",
        "Cuenta habilitada para emitir." if access.get("production_allowed") else "La emisión está bloqueada.",
        "Inicia sesión o activa un espacio con membresía vigente.")
    match = online.get("match") or {}
    add("match", "Partido", "ok" if match.get("id") else "fail",
        match.get("label") or "No hay partido seleccionado.", "Carga el partido desde la cabecera.")
    teams_ready = all((state.get(key) or {}).get("name") for key in ("team1", "team2"))
    add("teams", "Equipos", "ok" if teams_ready else "fail",
        "Los dos equipos tienen nombre." if teams_ready else "Falta identificar uno de los equipos.",
        "Revisa equipos y partido en Manager.")
    logos_ready = all((state.get(key) or {}).get("logo") for key in ("team1", "team2"))
    add("logos", "Logos", "ok" if logos_ready else "warn",
        "Los dos logos están preparados." if logos_ready else "Falta un logo; algunos gráficos quedarán incompletos.",
        "Completa los logos en Manager y vuelve a cargar el partido.", required=False)
    obs_ready = bool(obs.get("connected") and obs.get("program"))
    add("obs", "OBS", "ok" if obs_ready else "warn",
        f"Escena en programa: {obs.get('program')}." if obs.get("connected") and obs.get("program") else "OBS no está conectado o no hay escena en programa.",
        "Conecta OBS si quieres controlarlo desde SecretariatPro.", required=False)
    add("monitor", "Monitor de programa", "ok" if obs.get("connected") else "warn",
        "La vista usa directamente la escena Program de OBS." if obs.get("connected") else "La vista Program estará disponible al conectar OBS.",
        "Conecta OBS WebSocket para comprobar la señal sin capturar el escritorio.", required=False)
    source_ready = bool(ocr.get("source_id") or ocr.get("window_title"))
    add("source", "Fuente de marcador", "ok" if source_ready else "warn",
        "Fuente OCR configurada." if source_ready else "No hay cámara o ventana de marcador seleccionada.",
        "Selecciona la fuente en OCR.", required=score_mode != "manual")
    last = ocr_runtime.get("last_reading")
    fresh = bool(ocr_runtime.get("running") and isinstance(last, (int, float)) and now - float(last) <= 5)
    if score_mode == "manual":
        add("reading", "Lectura del marcador", "warn", "Control manual activo; el resultado no depende del OCR.",
            "Comprueba resultado y tiempo con el marcador físico.", required=False)
    else:
        add("reading", "Lectura del marcador", "ok" if fresh else "fail",
            "Lectura OCR reciente." if fresh else "El OCR está detenido o la última lectura es antigua.",
            "Inicia OCR y verifica las tres regiones, o activa control manual.")
    policy = settings.get("appearance_policy") or {}
    add("identity", "Identidad gráfica", "ok" if policy.get("inherited") else "warn",
        f"Publicada: {policy.get('theme_name')}." if policy.get("inherited") else "Se muestran los gráficos originales.",
        "Publica una identidad en Manager si esta competición la requiere.", required=False)
    add("tablet", "Tablet", "ok" if tablet_count else "warn",
        f"{tablet_count} dispositivo(s) emparejado(s)." if tablet_count else "No hay tablet emparejada; el ordenador conserva el control.",
        "Escanea el QR de Configuración si usarás tablet.", required=False)
    counts = {level: sum(item["level"] == level for item in checks) for level in ("ok", "warn", "fail")}
    blocking = sum(item["level"] == "fail" and item["required"] for item in checks)
    counts["blocking"] = blocking
    return {"checks": checks, "counts": counts, "ready": blocking == 0}
