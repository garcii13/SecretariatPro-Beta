const app = {
  snapshot: null,
  players: { team1: [], team2: [] },
  socket: null,
  reconnectTimer: null,
  pollTimer: null,
  language: "es",
  flow: { kind: "", team: "", step: "", penaltyType: "", scorerId: "", offenderId: "" },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const I18N = {
  es: { noMatch:"Sin partido cargado", pc:"PC", obs:"OBS", ready:"LISTO", onAir:"ON AIR", scene:"ESCENA OBS", program:"EN PROGRAMA", scoreboard:"Marcador", lineupHome:"Alineación local", lineupAway:"Alineación visitante", scorers:"Puntuadores", standings:"Clasificación", playerHome:"Jugador local", playerAway:"Jugador visitante", shootout:"Penaltis", goalHome:"Gol local", goalAway:"Gol visitante", penaltyHome:"Expulsión local", penaltyAway:"Expulsión visitante", clear:"Limpiar todo", event:"EVENTO", choose:"Selecciona", cancel:"Cancelar", back:"Volver", noRoster:"No hay convocatoria disponible", scorer:"¿Quién ha marcado?", assistant:"Selecciona asistencia", noAssist:"Sin asistencia", penaltyType:"Selecciona la sanción", offender:"Selecciona al sancionado", serving:"¿Quién cumple los 2 minutos?", profile:"Selecciona jugador", players:"jugadores", goalSaved:"Gol registrado", penaltyStarted:"Expulsión iniciada", cleared:"Emisión limpia", obsDisconnected:"OBS está desconectado en el ordenador", pcDisconnected:"Sin conexión con el ordenador", ppCancel:"Cancelar PP", penalty2:"2 minutos", penalty22:"Dos bloques consecutivos", penalty210:"Expulsado + jugador que cumple", local:"LOCAL", away:"VISITANTE" },
  en: { noMatch:"No match loaded", pc:"PC", obs:"OBS", ready:"READY", onAir:"ON AIR", scene:"OBS SCENE", program:"PROGRAM", scoreboard:"Scoreboard", lineupHome:"Home lineup", lineupAway:"Away lineup", scorers:"Top scorers", standings:"Standings", playerHome:"Home player", playerAway:"Away player", shootout:"Shootout", goalHome:"Home goal", goalAway:"Away goal", penaltyHome:"Home penalty", penaltyAway:"Away penalty", clear:"Clear all", event:"EVENT", choose:"Choose", cancel:"Cancel", back:"Back", noRoster:"No selected roster available", scorer:"Who scored?", assistant:"Choose assist", noAssist:"No assist", penaltyType:"Choose penalty", offender:"Choose penalised player", serving:"Who serves the 2 minutes?", profile:"Choose player", players:"players", goalSaved:"Goal registered", penaltyStarted:"Penalty started", cleared:"Output cleared", obsDisconnected:"OBS is disconnected on the computer", pcDisconnected:"No connection to the computer", ppCancel:"Cancel PP", penalty2:"2 minutes", penalty22:"Two consecutive blocks", penalty210:"Ejected + serving player", local:"HOME", away:"AWAY" },
  sv: { noMatch:"Ingen match laddad", pc:"PC", obs:"OBS", ready:"KLAR", onAir:"I SÄNDNING", scene:"OBS-SCEN", program:"PROGRAM", scoreboard:"Resultattavla", lineupHome:"Hemmalagets uppställning", lineupAway:"Bortalagets uppställning", scorers:"Poängliga", standings:"Tabell", playerHome:"Hemmaspelare", playerAway:"Bortaspelare", shootout:"Straffar", goalHome:"Mål hemma", goalAway:"Mål borta", penaltyHome:"Utvisning hemma", penaltyAway:"Utvisning borta", clear:"Rensa allt", event:"HÄNDELSE", choose:"Välj", cancel:"Avbryt", back:"Tillbaka", noRoster:"Ingen uttagning tillgänglig", scorer:"Vem gjorde målet?", assistant:"Välj assist", noAssist:"Ingen assist", penaltyType:"Välj utvisning", offender:"Välj utvisad spelare", serving:"Vem avtjänar 2 minuter?", profile:"Välj spelare", players:"spelare", goalSaved:"Mål registrerat", penaltyStarted:"Utvisning startad", cleared:"Sändningen rensad", obsDisconnected:"OBS är frånkopplat på datorn", pcDisconnected:"Ingen anslutning till datorn", ppCancel:"Avbryt PP", penalty2:"2 minuter", penalty22:"Två block i följd", penalty210:"Utvisad + avtjänande spelare", local:"HEMMA", away:"BORTA" },
  cs: { noMatch:"Není načten zápas", pc:"PC", obs:"OBS", ready:"PŘIPRAVENO", onAir:"VE VYSÍLÁNÍ", scene:"SCÉNA OBS", program:"PROGRAM", scoreboard:"Skóre", lineupHome:"Domácí sestava", lineupAway:"Hostující sestava", scorers:"Bodování", standings:"Tabulka", playerHome:"Domácí hráč", playerAway:"Hostující hráč", shootout:"Nájezdy", goalHome:"Gól domácích", goalAway:"Gól hostů", penaltyHome:"Trest domácích", penaltyAway:"Trest hostů", clear:"Vyčistit vše", event:"UDÁLOST", choose:"Vyberte", cancel:"Zrušit", back:"Zpět", noRoster:"Nominace není dostupná", scorer:"Kdo skóroval?", assistant:"Vyberte asistenci", noAssist:"Bez asistence", penaltyType:"Vyberte trest", offender:"Vyberte potrestaného hráče", serving:"Kdo odpyká 2 minuty?", profile:"Vyberte hráče", players:"hráčů", goalSaved:"Gól zapsán", penaltyStarted:"Trest spuštěn", cleared:"Výstup vyčištěn", obsDisconnected:"OBS není na počítači připojeno", pcDisconnected:"Bez spojení s počítačem", ppCancel:"Zrušit PP", penalty2:"2 minuty", penalty22:"Dva po sobě jdoucí bloky", penalty210:"Vyloučený + odpykávající hráč", local:"DOMÁCÍ", away:"HOSTÉ" },
  fi: { noMatch:"Ottelua ei ole ladattu", pc:"PC", obs:"OBS", ready:"VALMIS", onAir:"LÄHETYKSESSÄ", scene:"OBS-KOHTAUS", program:"OHJELMA", scoreboard:"Tulostaulu", lineupHome:"Kotijoukkueen kokoonpano", lineupAway:"Vierasjoukkueen kokoonpano", scorers:"Pistepörssi", standings:"Sarjataulukko", playerHome:"Kotipelaaja", playerAway:"Vieraspelaaja", shootout:"Rangaistuslaukaukset", goalHome:"Kotimaali", goalAway:"Vierasmaalı", penaltyHome:"Kotijäähy", penaltyAway:"Vierasjäähy", clear:"Tyhjennä kaikki", event:"TAPAHTUMA", choose:"Valitse", cancel:"Peruuta", back:"Takaisin", noRoster:"Kokoonpanoa ei ole saatavilla", scorer:"Kuka teki maalin?", assistant:"Valitse syöttäjä", noAssist:"Ei syöttäjää", penaltyType:"Valitse rangaistus", offender:"Valitse rangaistu pelaaja", serving:"Kuka kärsii 2 minuuttia?", profile:"Valitse pelaaja", players:"pelaajaa", goalSaved:"Maali kirjattu", penaltyStarted:"Jäähy käynnistetty", cleared:"Lähetys tyhjennetty", obsDisconnected:"OBS ei ole yhdistetty tietokoneella", pcDisconnected:"Ei yhteyttä tietokoneeseen", ppCancel:"Peru PP", penalty2:"2 minuuttia", penalty22:"Kaksi peräkkäistä jaksoa", penalty210:"Poistettu + kärsivä pelaaja", local:"KOTI", away:"VIERAS" },
  de: { noMatch:"Kein Spiel geladen", pc:"PC", obs:"OBS", ready:"BEREIT", onAir:"ON AIR", scene:"OBS-SZENE", program:"PROGRAMM", scoreboard:"Anzeigetafel", lineupHome:"Heimaufstellung", lineupAway:"Gastaufstellung", scorers:"Topscorer", standings:"Tabelle", playerHome:"Heimspieler", playerAway:"Gastspieler", shootout:"Penaltyschießen", goalHome:"Heimtor", goalAway:"Gasttor", penaltyHome:"Heimstrafe", penaltyAway:"Gaststrafe", clear:"Alles ausblenden", event:"EREIGNIS", choose:"Auswählen", cancel:"Abbrechen", back:"Zurück", noRoster:"Kein Kader verfügbar", scorer:"Wer hat getroffen?", assistant:"Assist auswählen", noAssist:"Ohne Assist", penaltyType:"Strafe auswählen", offender:"Bestrafter Spieler", serving:"Wer verbüßt 2 Minuten?", profile:"Spieler auswählen", players:"Spieler", goalSaved:"Tor registriert", penaltyStarted:"Strafe gestartet", cleared:"Ausgabe geleert", obsDisconnected:"OBS ist am Computer nicht verbunden", pcDisconnected:"Keine Verbindung zum Computer", ppCancel:"PP beenden", penalty2:"2 Minuten", penalty22:"Zwei aufeinanderfolgende Blöcke", penalty210:"Ausgeschlossen + absitzender Spieler", local:"HEIM", away:"GAST" }
};

function t(key) { return (I18N[app.language] || I18N.es)[key] || I18N.es[key] || key; }

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload?.detail || payload?.message || payload || `Error ${response.status}`);
  return payload;
}

function toast(message, error = false) {
  const node = document.createElement("div");
  node.className = `toast${error ? " error" : ""}`;
  node.textContent = message;
  $("#toast-region").appendChild(node);
  setTimeout(() => node.remove(), 3000);
}

function escapeHTML(value) { return String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]); }

function normalizedPlayer(row) {
  const player = row?.player || row || {};
  const first = player.first_name || "";
  const last = player.last_name || "";
  return {
    player_id: String(row?.player_id || player.id || ""),
    number: String(row?.shirt_number ?? row?.number ?? player.shirt_number ?? ""),
    name: player.display_name || [first,last].filter(Boolean).join(" ") || player.name || "Jugador",
    position: String(player.position || row?.position || "").toUpperCase(),
    member_type: String(row?.member_type || player.member_type || "player").toLowerCase(),
  };
}

function roster(team) {
  const online = app.snapshot?.online?.rosters?.[team] || [];
  const fallback = app.snapshot?.state?.statistics?.lineups?.[`${team}_players`] || [];
  return (online.length ? online : fallback).map(normalizedPlayer).filter((p) => p.player_id);
}

function selectedIds(team) { return new Set((app.snapshot?.online?.attendance?.[team] || []).map(String)); }
function calledUp(team) { const selected = selectedIds(team); return app.players[team].filter((p) => selected.has(p.player_id) && p.member_type !== "coach"); }
function profilePlayers(team) { return app.players[team].filter((p) => p.member_type !== "coach"); }
function playerById(team, id) { return app.players[team].find((p) => p.player_id === String(id)); }
function teamName(team) { const state = app.snapshot?.state || {}; return state?.[team]?.name || (team === "team1" ? t("local") : t("away")); }

function applyLanguage() {
  document.documentElement.lang = app.language;
  $$('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); });
}

function fitDeck() {
  const grid = $("#deck-grid");
  if (!grid) return;
  const count = $$(".deck-key", grid).filter((el) => !el.hidden).length;
  const width = grid.clientWidth;
  const height = grid.clientHeight;
  const portrait = innerHeight > innerWidth;
  let best = 4;
  let bestScore = -Infinity;
  const maxColumns = portrait ? 5 : 10;
  const minColumns = portrait ? 2 : 4;
  for (let columns = minColumns; columns <= maxColumns; columns += 1) {
    const rows = Math.ceil(count / columns);
    const cellW = (width - (columns - 1) * 8) / columns;
    const cellH = (height - (rows - 1) * 8) / Math.max(rows,1);
    const score = Math.min(cellW / 1.8, cellH) - Math.abs(cellW / Math.max(cellH,1) - 1.8) * 8;
    if (cellW >= 105 && cellH >= 60 && score > bestScore) { bestScore = score; best = columns; }
  }
  grid.style.setProperty("--deck-columns", String(best));
}

function renderScenes(obs = {}) {
  const host = $("#scene-grid");
  const signature = JSON.stringify([obs.connected, obs.scenes, obs.program, app.language]);
  if (host.dataset.signature === signature) return;
  host.dataset.signature = signature;
  host.replaceChildren();
  if (!obs.connected) return;
  (obs.scenes || []).forEach((scene, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `deck-key scene-key${scene === obs.program ? " is-active" : ""}`;
    button.dataset.scene = scene;
    button.innerHTML = `<span>S${index+1}</span><b>${escapeHTML(scene)}</b><small>${scene === obs.program ? t("program") : t("scene")}</small>`;
    host.appendChild(button);
  });
}

function renderPowerplayDeck(powerplay = {}) {
  const host = $("#active-pp-deck");
  host.replaceChildren();
  ["team1","team2"].forEach((team) => {
    const info = powerplay[team] || {};
    if (!info.status) return;
    const seconds = Math.max(0, Number(info.remaining_seconds ?? 120));
    const time = `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,"0")}`;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "deck-key penalty-key";
    button.dataset.endPp = team;
    button.innerHTML = `<span>${team === "team1" ? "PL" : "PV"}</span><b>${t("ppCancel")} · ${teamName(team)}</b><small>#${escapeHTML(info.player_number || "—")} · ${time}</small>`;
    host.appendChild(button);
  });
  host.hidden = !host.children.length;
}

function renderLive(live) {
  if (!app.snapshot) return;
  Object.assign(app.snapshot, { scores: live.scores, graphic_scores: live.graphic_scores, score_control: live.score_control });
  app.snapshot.state = { ...app.snapshot.state, powerplay: live.powerplay };
  const scores = live.scores || {};
  $("#score-copy").textContent = `${scores.team1_score ?? 0}–${scores.team2_score ?? 0} · ${scores.time || "00:00"}`;
}

function render(snapshot) {
  app.snapshot = snapshot;
  app.language = ["es","en","sv","cs","fi","de"].includes(snapshot?.settings?.language) ? snapshot.settings.language : "es";
  app.players.team1 = roster("team1");
  app.players.team2 = roster("team2");
  applyLanguage();

  const online = snapshot.online || {};
  const match = online.match || {};
  $("#match-name").textContent = match.label || snapshot.state?.online?.match_label || t("noMatch");
  const scores = snapshot.scores || {};
  $("#score-copy").textContent = `${scores.team1_score ?? 0}–${scores.team2_score ?? 0} · ${scores.time || "00:00"}`;
  $("#api-chip").classList.add("is-ok");
  $("#obs-chip").classList.toggle("is-ok", Boolean(snapshot.obs?.connected));
  $("#obs-chip b").textContent = snapshot.obs?.connected ? "OBS" : "OBS OFF";

  renderScenes(snapshot.obs || {});
  const overlays = snapshot.overlays || {};
  $$('[data-overlay]').forEach((button) => {
    const panel = button.dataset.overlay;
    let active = Boolean(overlays[panel]);
    if (panel === "lineups") active = Boolean(snapshot.state?.statistics?.lineups?.[`${button.dataset.lineupTeam}_status`]);
    button.classList.toggle("is-active", active);
    const small = button.querySelector("small");
    if (small) small.textContent = active ? t("onAir") : t("ready");
  });
  const profile = snapshot.state?.statistics?.player_profile || {};
  $$('[data-profile-team]').forEach((button) => button.classList.toggle("is-active", Boolean(profile.status) && profile.team_key === button.dataset.profileTeam));
  renderPowerplayDeck(snapshot.state?.powerplay || {});
  $("[data-extra=mark]").hidden = !snapshot.replays?.status?.available || snapshot.replays?.status?.backend !== "multicam-plugin";
  if (app.flow.kind === "replay" && app.flow.step === "ready") renderReplayFlow();
  requestAnimationFrame(fitDeck);
}

function openWorkflow(kind, team) {
  const players = kind === "profile" ? profilePlayers(team) : calledUp(team);
  if (!players.length) return toast(t("noRoster"), true);
  app.flow = { markerPromise: kind === "goal" ? captureNow("Gol", team) : null, requestId: requestId(), scoreBefore:Number(app.snapshot?.graphic_scores?.[team === "team1" ? "team1_score" : "team2_score"] || 0), eventTime:app.snapshot?.scores?.time || "", kind, team, step: kind === "goal" ? "scorer" : kind === "penalty" ? "penalty-type" : "profile", penaltyType:"", scorerId:"", offenderId:"" };
  $("#workflow").hidden = false;
  renderWorkflow();
}
function closeWorkflow() { if (app.flow.goalFlow) api("/api/replays/goal/skip",{method:"POST"}).then(render).catch(e=>toast(e.message,true)); $("#workflow").hidden = true; app.flow = {kind:"",team:"",step:"",penaltyType:"",scorerId:"",offenderId:""}; }

function workflowPlayerButton(player, action) {
  return `<button class="workflow-choice" type="button" data-action="${action}" data-player-id="${escapeHTML(player.player_id)}"><strong>${escapeHTML(player.number || "—")}</strong><span>${escapeHTML(player.name)}</span></button>`;
}

function fitWorkflow(count) {
  const grid = $("#workflow-grid");
  const portrait = innerHeight > innerWidth;
  const columns = Math.max(portrait ? 2 : 4, Math.min(portrait ? 4 : 8, Math.ceil(Math.sqrt(Math.max(1,count) * (portrait ? 1 : 1.8)))));
  grid.style.setProperty("--workflow-columns", String(columns));
}

function renderWorkflow() {
  const flow = app.flow;
  if (flow.kind === "replay") return renderReplayFlow();
  const players = flow.kind === "profile" ? profilePlayers(flow.team) : calledUp(flow.team);
  const title = $("#workflow-title");
  const help = $("#workflow-help");
  const grid = $("#workflow-grid");
  $("#workflow-kicker").textContent = flow.kind === "goal" ? "GOL" : flow.kind === "penalty" ? "PP" : "FICHA";
  $("#workflow-summary").textContent = `${teamName(flow.team)} · ${players.length} ${t("players")} · ${app.snapshot?.scores?.time || "00:00"}`;
  $("#workflow-back").hidden = ["scorer","penalty-type","profile"].includes(flow.step);

  if (flow.step === "profile") {
    title.textContent = t("profile"); help.textContent = teamName(flow.team);
    grid.innerHTML = players.map((p) => workflowPlayerButton(p,"profile-player")).join(""); fitWorkflow(players.length); return;
  }
  if (flow.step === "scorer") {
    title.textContent = t("scorer"); help.textContent = teamName(flow.team);
    grid.innerHTML = players.map((p) => workflowPlayerButton(p,"goal-scorer")).join(""); fitWorkflow(players.length); return;
  }
  if (flow.step === "assistant") {
    const scorer = playerById(flow.team, flow.scorerId);
    title.textContent = t("assistant"); help.textContent = `#${scorer?.number || "—"} ${scorer?.name || ""}`;
    const available = players.filter((p) => p.player_id !== flow.scorerId);
    grid.innerHTML = `<button class="workflow-choice" type="button" data-action="goal-no-assist"><strong>Ø</strong><span>${t("noAssist")}</span></button>${available.map((p) => workflowPlayerButton(p,"goal-assistant")).join("")}`;
    fitWorkflow(available.length + 1); return;
  }
  if (flow.step === "penalty-type") {
    title.textContent = t("penaltyType"); help.textContent = teamName(flow.team);
    grid.innerHTML = `<button class="workflow-choice type-choice" data-action="penalty-type" data-type="2"><strong>2</strong><span>${t("penalty2")}</span></button><button class="workflow-choice type-choice" data-action="penalty-type" data-type="2+2"><strong>2+2</strong><span>${t("penalty22")}</span></button><button class="workflow-choice type-choice" data-action="penalty-type" data-type="2+10"><strong>2+10</strong><span>${t("penalty210")}</span></button>`;
    fitWorkflow(3); return;
  }
  if (flow.step === "offender") {
    title.textContent = t("offender"); help.textContent = `${teamName(flow.team)} · ${flow.penaltyType}`;
    grid.innerHTML = players.map((p) => workflowPlayerButton(p,"penalty-player")).join(""); fitWorkflow(players.length); return;
  }
  if (flow.step === "serving") {
    const offender = playerById(flow.team, flow.offenderId);
    title.textContent = t("serving"); help.textContent = `#${offender?.number || "—"} ${offender?.name || ""}`;
    const available = players.filter((p) => p.player_id !== flow.offenderId);
    grid.innerHTML = available.map((p) => workflowPlayerButton(p,"penalty-serving")).join(""); fitWorkflow(available.length);
  }
}

async function submitGoal(assistantId = null) {
  const flow = app.flow;
  const scorer = playerById(flow.team, flow.scorerId);
  try {
    const result = await api("/api/events/goal", { method:"POST", body:JSON.stringify({ team:flow.team, scorer_id:flow.scorerId, assistant_id:assistantId || null, match_time:flow.eventTime, marker_id:await flow.markerPromise || "", request_id:flow.requestId, score_before:flow.scoreBefore }) });
    render(result); closeWorkflow();
    if (result.goal_replay_flow && result.goal_replay_marker_id) openReplay(result.goal_replay_marker_id, true);
    toast(`${t("goalSaved")} · #${scorer?.number || "—"}`);
  } catch (error) { toast(error.message, true); }
}

async function submitPenalty(servingId = "") {
  const flow = app.flow;
  try {
    render(await api(`/api/powerplays/${flow.team}/start`, { method:"POST", body:JSON.stringify({ player_id:flow.offenderId, penalty_type:flow.penaltyType, serving_player_id:flow.penaltyType === "2+10" ? servingId : "" }) }));
    closeWorkflow(); toast(`${t("penaltyStarted")} · ${flow.penaltyType}`);
  } catch (error) { toast(error.message, true); }
}

async function handleWorkflow(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action.startsWith("extra-")) return handleExtraChoice(button);
  const id = button.dataset.playerId || "";
  if (action === "profile-player") {
    try { render(await api("/api/player-profile", {method:"POST",body:JSON.stringify({team:app.flow.team,player_id:id,show:true})})); closeWorkflow(); }
    catch (error) { toast(error.message,true); }
  } else if (action === "goal-scorer") { app.flow.scorerId = id; app.flow.step = "assistant"; renderWorkflow(); }
  else if (action === "goal-assistant") await submitGoal(id);
  else if (action === "goal-no-assist") await submitGoal(null);
  else if (action === "penalty-type") { app.flow.penaltyType = button.dataset.type; app.flow.step = "offender"; renderWorkflow(); }
  else if (action === "penalty-player") { app.flow.offenderId = id; if (app.flow.penaltyType === "2+10") { app.flow.step = "serving"; renderWorkflow(); } else await submitPenalty(); }
  else if (action === "penalty-serving") await submitPenalty(id);
}

async function handleDeck(event) {
  const button = event.target.closest("button");
  if (!button) return;
  try {
    if (button.dataset.extra) return openExtra(button.dataset.extra);
    if (button.dataset.scene) {
      if (!app.snapshot?.obs?.connected) return toast(t("obsDisconnected"), true);
      render(await api("/api/obs/scenes/program", {method:"POST",body:JSON.stringify({scene_name:button.dataset.scene})}));
    } else if (button.dataset.overlay) {
      const body = button.dataset.overlay === "lineups" ? {lineup_team:button.dataset.lineupTeam} : {};
      render(await api(`/api/overlays/${button.dataset.overlay}/toggle`, {method:"POST",body:JSON.stringify(body)}));
    } else if (button.dataset.goalTeam) openWorkflow("goal", button.dataset.goalTeam);
    else if (button.dataset.penaltyTeam) openWorkflow("penalty", button.dataset.penaltyTeam);
    else if (button.dataset.profileTeam) openWorkflow("profile", button.dataset.profileTeam);
    else if (button.hasAttribute("data-hide-all")) { render(await api("/api/overlays/hide-all", {method:"POST"})); toast(t("cleared")); }
    else if (button.dataset.endPp) render(await api(`/api/powerplays/${button.dataset.endPp}/end`, {method:"POST"}));
  } catch (error) { toast(error.message, true); }
}

function workflowBack() {
  if (app.flow.kind === "replay") { app.flow.step = ({seconds:"camera",speed:"seconds",ready:"camera"})[app.flow.step] || "camera"; return renderReplayFlow(); }
  if (app.flow.step === "assistant") app.flow.step = "scorer";
  else if (app.flow.step === "offender") app.flow.step = "penalty-type";
  else if (app.flow.step === "serving") app.flow.step = "offender";
  renderWorkflow();
}

async function refreshOBSStatus() {
  try {
    const obs = await api(`/api/obs/status?_=${Date.now()}`);
    if (!app.snapshot) return;
    app.snapshot.obs = obs;
    $("#obs-chip").classList.toggle("is-ok", Boolean(obs.connected));
    $("#obs-chip b").textContent = obs.connected ? "OBS" : "OBS OFF";
    renderScenes(obs);
    requestAnimationFrame(fitDeck);
  } catch (_) {
    $("#obs-chip").classList.remove("is-ok");
  }
}

function connectSocket() {
  clearTimeout(app.reconnectTimer);
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/api/ws`);
  app.socket = socket;
  socket.onopen = () => { $("#api-chip").classList.add("is-ok"); clearInterval(app.pollTimer); app.pollTimer = null; };
  socket.onmessage = (event) => { const message = JSON.parse(event.data); if (message.type === "state") render(message.payload); if (message.type === "live") renderLive(message.payload); };
  socket.onclose = () => {
    $("#api-chip").classList.remove("is-ok");
    if (!app.pollTimer) app.pollTimer = setInterval(() => api("/api/state").then(render).catch(() => {}), 2500);
    app.reconnectTimer = setTimeout(connectSocket, 1400);
  };
  socket.onerror = () => socket.close();
}

async function boot() {
  const invite = new URLSearchParams(location.hash.slice(1)).get("pair");
  const existing = await api("/api/tablet/session").catch(() => ({paired:false}));
  if (invite && !existing.paired) {
    try {
      await api("/api/tablet/pair", {method:"POST", body:JSON.stringify({code:invite})});
      history.replaceState(null, "", location.pathname + location.search);
    } catch (error) {
      showPairingMessage(error.message);
      return;
    }
  }
  try {
    const session = await api("/api/tablet/session");
    if (!session.paired) { showPairingMessage("Escanea el QR nuevo desde Configuración → Tablet / iPad en el ordenador."); return; }
  } catch (error) { showPairingMessage(error.message); return; }
  $("#deck-grid").addEventListener("click", handleDeck);
  $("#active-pp-deck").addEventListener("click", handleDeck);
  $("#workflow-grid").addEventListener("click", handleWorkflow);
  $("#workflow-close").addEventListener("click", closeWorkflow);
  $("#workflow-cancel").addEventListener("click", closeWorkflow);
  $("#workflow-back").addEventListener("click", workflowBack);
  window.addEventListener("resize", () => requestAnimationFrame(() => { fitDeck(); if (!$("#workflow").hidden) renderWorkflow(); }));
  document.addEventListener("visibilitychange", () => { if (!document.hidden && app.socket?.readyState !== WebSocket.OPEN) connectSocket(); });
  try { render(await api("/api/state")); } catch (error) { toast(t("pcDisconnected"), true); }
  connectSocket();
  refreshOBSStatus();
  setInterval(refreshOBSStatus, 1500);
  setInterval(() => { if (app.socket?.readyState === WebSocket.OPEN) app.socket.send("ping"); }, 20000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/tablet/sw.js", {scope:"/tablet/"}).catch(() => {});
}

function showPairingMessage(message) {
  document.querySelector(".tablet-shell")?.remove();
  const main = document.createElement("main");
  main.className = "tablet-pairing-message";
  const title = document.createElement("h1");
  title.textContent = "Tablet sin emparejar";
  const copy = document.createElement("p");
  copy.textContent = message;
  main.append(title, copy);
  document.body.prepend(main);
}

const extraWords = {
 es:['MARCAR','REPETICIONES','Periodo','Empty net · 1','Empty net · 2','Cola de gráficos','Secuencias','Cámara','Segundos','Velocidad','Otro plano','LANZAR + GUARDAR','Guardar vídeo','SIN REPETICIÓN','Generar highlights','Nombre del vídeo','Esperando cámaras…','Selecciona vídeos','Lanzar','Añadir','Detener','Iniciar búfer','Volver al directo'],
 en:['MARK','REPLAYS','Period','Empty net · 1','Empty net · 2','Graphics queue','Sequences','Camera','Seconds','Speed','Another shot','PLAY + SAVE','Save video','NO REPLAY','Generate highlights','Video name','Waiting for cameras…','Select videos','Play','Add','Stop','Start buffer','Return to live'],
 sv:['MARKERA','REPRISER','Period','Tom bur · 1','Tom bur · 2','Grafikkö','Sekvenser','Kamera','Sekunder','Hastighet','Nytt klipp','SPELA + SPARA','Spara video','UTAN REPRIS','Skapa höjdpunkter','Videonamn','Väntar på kameror…','Välj videor','Spela','Lägg till','Stoppa','Starta buffert','Tillbaka till live'],
 cs:['OZNAČIT','OPAKOVÁNÍ','Perioda','Prázdná branka · 1','Prázdná branka · 2','Fronta grafiky','Sekvence','Kamera','Sekundy','Rychlost','Další záběr','PŘEHRÁT + ULOŽIT','Uložit video','BEZ OPAKOVÁNÍ','Vytvořit sestřih','Název videa','Čekání na kamery…','Vyberte videa','Přehrát','Přidat','Zastavit','Spustit buffer','Zpět do živého vysílání'],
 fi:['MERKITSE','UUSINNAT','Erä','Tyhjä maali · 1','Tyhjä maali · 2','Grafiikkajono','Sarjat','Kamera','Sekunnit','Nopeus','Uusi otos','TOISTA + TALLENNA','Tallenna video','EI UUSINTAA','Luo kooste','Videon nimi','Odotetaan kameroita…','Valitse videot','Toista','Lisää','Pysäytä','Käynnistä puskuri','Palaa suoraan lähetykseen'],
 de:['MARKIEREN','WIEDERHOLUNGEN','Spielabschnitt','Leeres Tor · 1','Leeres Tor · 2','Grafikwarteschlange','Sequenzen','Kamera','Sekunden','Geschwindigkeit','Weitere Einstellung','ABSPIELEN + SPEICHERN','Video speichern','OHNE WIEDERHOLUNG','Highlights erstellen','Videoname','Warte auf Kameras…','Videos auswählen','Abspielen','Hinzufügen','Stoppen','Puffer starten','Zurück zu Live']
};
const extraKeys=['mark','library','period','empty1','empty2','queue','sequences','camera','seconds','speed','another','playSave','save','skip','highlights','videoName','waiting','selectVideos','play','add','stop','buffer','live'];
for (const [lang, words] of Object.entries(extraWords)) extraKeys.forEach((key,i)=>I18N[lang][key]=words[i]);
function eventLabelText(label) {
 const keys=['Gol','Parada','Ocasión','Penalti','Falta','Otro'];
 const words={en:['Goal','Save','Chance','Penalty','Foul','Other'],sv:['Mål','Räddning','Målchans','Straff','Regelbrott','Annat'],cs:['Gól','Zákrok','Šance','Trestné střílení','Faul','Jiné'],fi:['Maali','Torjunta','Maalipaikka','Rangaistuslaukaus','Rike','Muu'],de:['Tor','Parade','Chance','Strafstoß','Foul','Andere']};
 return words[app.language]?.[keys.indexOf(label)] || label;
}
for (const [lang, value] of Object.entries({es:'Eliminar',en:'Delete',sv:'Ta bort',cs:'Odstranit',fi:'Poista',de:'Löschen'})) I18N[lang].delete=value;
function requestId() { return Array.from(crypto.getRandomValues(new Uint8Array(16)), b=>b.toString(16).padStart(2,'0')).join(''); }
function captureNow(label, team='') {
 if (!app.snapshot?.replays?.status?.active) return Promise.resolve('');
 return api('/api/replays/mark',{method:'POST',body:JSON.stringify({label,team,match_time:app.snapshot?.scores?.time || ''})}).then(p=>p.marker?.id || '').catch(e=>{toast(e.message,true);return '';});
}
function extraPanel(kind, title, content) {
 app.flow={kind,step:''}; $('#workflow').hidden=false;
 $('#workflow-title').textContent=title; $('#workflow-kicker').textContent='SECRETARIATDECK';
 $('#workflow-help').textContent=''; $('#workflow-summary').textContent=''; $('#workflow-back').hidden=true;
 $('#workflow-grid').innerHTML=content; fitWorkflow($('#workflow-grid').children.length);
}
function extraButton(action,value,label) { return `<button class="workflow-choice" data-action="extra-${action}" data-value="${escapeHTML(value)}"><span>${escapeHTML(label)}</span></button>`; }
function openReplay(id,goalFlow=false) { app.flow={kind:'replay',step:'camera',clipId:id,goalFlow,segments:[]}; $('#workflow').hidden=false; renderReplayFlow(); }
function renderReplayFlow() {
 const f=app.flow, status=app.snapshot?.replays?.status || {}, rows=app.snapshot?.replays?.clips || [], clip=rows.find(c=>c.id===f.clipId);
 $('#workflow-kicker').textContent='REPLAY'; $('#workflow-title').textContent=t(f.step==='ready'?'library':f.step);
 $('#workflow-help').textContent=f.segments.map(s=>`CAM ${s.camera} · ${s.duration_seconds}s · ${s.speed_percent}%`).join(' → ');
 $('#workflow-summary').textContent=clip?.status==='failed'?clip.error:clip?.status!=='ready'?t('waiting'):'';
 $('#workflow-back').hidden=f.step==='camera';
 let html='';
 if(f.step==='camera') html=Array.from({length:Number(status.camera_count || 1)},(_,i)=>extraButton('camera',i+1,`CAM ${i+1}`)).join('');
 if(f.step==='seconds') html=[3,5,7,10].map(n=>extraButton('seconds',n,`${n}s`)).join('')+`<label>${t('seconds')}<input id="custom-seconds" type="number" min="1" max="60" value="5"></label>`+extraButton('seconds','custom',t('add'));
 if(f.step==='speed') html=[100,75,50,25].map(n=>extraButton('speed',n,`${n}%`)).join('');
 if(f.step==='ready') html=(f.segments.length<6?extraButton('another','',t('another')):'')+(clip?.status==='ready'?extraButton('compose','play',t('playSave'))+extraButton('compose','save',t('save')):'');
 if(f.goalFlow) html+=extraButton('skip','',t('skip'));
 $('#workflow-grid').innerHTML=html;fitWorkflow($('#workflow-grid').children.length);
}
async function openExtra(kind) {
 try {
  if(kind.startsWith('empty')) return render(await api(`/api/empty-net/team${kind.slice(-1)}/toggle`,{method:'POST'}));
  if(kind==='mark') { const pending=captureNow('Replay'); extraPanel('capture',t('mark'),t('waiting')); const id=await pending; if(id && app.flow.kind === "capture") extraPanel("label",t("mark"),["Gol","Parada","Ocasión","Penalti","Falta","Otro"].map(label=>extraButton("label",id+"|"+label,eventLabelText(label))).join("")); else if(app.flow.kind === "capture") closeWorkflow();return; }
  if(kind==='period') { const count=app.snapshot?.settings?.appearance?.period_strip?.segments || 3; return extraPanel(kind,t(kind),Array.from({length:count},(_,i)=>extraButton('period',i+1,String(i+1))).join('')); }
  if(kind==='library') {
   app.snapshot.replays=await api('/api/replays');
   const rows=app.snapshot.replays.highlights || [];
   const content=rows.map(row=>`<article><label><input type="checkbox" data-event-video="${escapeHTML(row.id)}">P${row.period || 1} · ${escapeHTML(row.title || row.label)}</label><video controls preload="none" src="/api/replays/media/${encodeURIComponent(row.id)}"></video>${extraButton('launch',row.id,t('play'))}${extraButton('delete',row.id,t('delete'))}<a download href="/api/replays/media/${encodeURIComponent(row.id)}">${t('save')}</a></article>`).join('');
   return extraPanel(kind,t(kind),content+`<label>${t('videoName')}<input id="montage-title" maxlength="120" value="Highlights"></label>`+extraButton('montage','',t('highlights'))+extraButton('buffer','',t(app.snapshot.replays.status?.active?'stop':'buffer'))+extraButton('live','',t('live')));
  }
  if(kind==='queue') {
   const rows=app.snapshot?.state?.graphics_queue || [];
   return extraPanel(kind,t(kind),rows.map(c=>extraButton('cue',c.id,`${t('play')} · ${c.label || c.panel}`)).join('')+['scoreboard','prematch','intermission','lineups','top_scorers','standings','bottom_bar'].map(p=>extraButton('addcue',p,`${t('add')} · ${p}`)).join(''));
  }
  if(kind==='sequences') return extraPanel(kind,t(kind),(app.snapshot?.settings?.graphics_sequences || []).map(s=>extraButton('sequence',s.id,s.name)).join('')+extraButton('stopseq','',t('stop')));
 } catch(e) {toast(e.message,true);}
}
async function handleExtraChoice(button) {
 if(app.extraBusy) return;
 const action=button.dataset.action.slice(6), value=button.dataset.value, f=app.flow;
 try {
  if(action==='camera'){f.camera=Number(value);f.step='seconds';return renderReplayFlow();}
  if(action==='seconds'){f.seconds=Number(value==='custom'?$('#custom-seconds').value:value);if(f.seconds<1||f.seconds>60)return;f.step='speed';return renderReplayFlow();}
  if(action==='speed'){f.segments.push({camera:f.camera,duration_seconds:f.seconds,speed_percent:Number(value)});f.step='ready';return renderReplayFlow();}
  if(action==='another'){f.step='camera';return renderReplayFlow();}
  app.extraBusy=true;button.disabled=true;
  if(action==='label') {const [id,label]=value.split('|');await api(`/api/replays/${encodeURIComponent(id)}`,{method:'PATCH',body:JSON.stringify({label})});openReplay(id);}
  if(action==='compose') { await api('/api/replays/composition',{method:'POST',body:JSON.stringify({clip_id:f.clipId,segments:f.segments,play_now:value==='play',save_video:true,goal_flow:f.goalFlow})}); f.goalFlow=false;closeWorkflow(); }
  if(action==='skip') closeWorkflow();
  if(action==='period') {render(await api('/api/match/period',{method:'POST',body:JSON.stringify({value:Number(value)})}));closeWorkflow();}
  if(action==='delete') {await api(`/api/replays/library/${encodeURIComponent(value)}`,{method:'DELETE'});await openExtra('library');}
  if(action==='launch') {await api(`/api/replays/library/${encodeURIComponent(value)}/take`,{method:'POST'});closeWorkflow();}
  if(action==='live') {await api('/api/replays/out',{method:'POST'});closeWorkflow();}
  if(action==='buffer') {await api(`/api/replays/${app.snapshot.replays.status?.active?'stop':'start'}`,{method:'POST'});await openExtra('library');}
  if(action==='montage') {const ids=$$('[data-event-video]:checked').map(el=>el.dataset.eventVideo);if(!ids.length)return;await api('/api/replays/highlights',{method:'POST',body:JSON.stringify({title:$('#montage-title').value || 'Highlights',clip_ids:ids})});await openExtra('library');}
  if(action==='cue') {render(await api(`/api/graphics/cues/${encodeURIComponent(value)}/take`,{method:'POST'}));closeWorkflow();}
  if(action==='addcue') {render(await api('/api/graphics/cues',{method:'POST',body:JSON.stringify({panel:value,lineup_team:'team1',duration_seconds:5})}));await openExtra('queue');}
  if(action==='sequence') {await api(`/api/graphics/sequences/${encodeURIComponent(value)}/run`,{method:'POST'});closeWorkflow();}
  if(action==='stopseq') {await api('/api/graphics/sequences/stop',{method:'POST'});closeWorkflow();}
 }catch(e){toast(e.message,true);}finally{app.extraBusy=false;button.disabled=false;}
}

boot();
