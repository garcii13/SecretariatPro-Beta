document.addEventListener("DOMContentLoaded", () => {
  // -------------------- Helpers --------------------
  const safeGet = id => document.getElementById(id);
  const safeQ = sel => document.querySelector(sel);
  const cueId = new URLSearchParams(location.search).get("cue");
  const overlayDataURL = cueId ? `/api/graphics/preview/${encodeURIComponent(cueId)}` : "data.json";


  let overlayLanguage = "es";
  const overlayAppearanceDefaults = {
    scoreboard: { background: "#2a2d34", name_box: "#3b3f47", text: "#ffffff" },
    bottom_bar: { body: "#24272e", middle: "#30333b", text: "#ffffff", secondary_text: "#c6cad2" },
    panels: { background: "#171c25", surface: "#232a35", accent: "#59606c", text: "#ffffff" },
  };
  const OVERLAY_TRANSLATIONS = {
    sv: {
      "EVENTOS":"HÄNDELSER","LOCAL":"HEMMA","VISITANTE":"BORTA","PREMATCH":"INFÖR MATCH",
      "POSICIÓN":"PLACERING","PUNTOS":"POÄNG","V · E · D":"V · O · F","GOLES A FAVOR":"GJORDA MÅL",
      "GOLES EN CONTRA":"INSLÄPPTA MÅL","PABELLÓN":"ARENA","INICIO":"START","ALINEACIONES":"LAGUPPSTÄLLNINGAR",
      "MÁXIMOS PUNTUADORES":"POÄNGLIGA","CLASIFICACIÓN":"TABELL","GOLES":"MÅL","ASIST.":"ASSIST",
      "PENALTIS":"STRAFFLÄGGNING","FECHA NAC.":"FÖDELSEDATUM","NACIONALIDAD":"NATIONALITET",
      "PARTIDOS":"MATCHER","ENTRENADOR":"TRÄNARE","ENTRENADORES":"TRÄNARE","Goles a favor":"Gjorda mål",
      "Goles en contra":"Insläppta mål","Posición":"Placering","Puntos":"Poäng","Victorias":"Vinster"
    },
    cs: {
      "EVENTOS":"UDÁLOSTI","LOCAL":"DOMÁCÍ","VISITANTE":"HOSTÉ","PREMATCH":"PŘED ZÁPASEM",
      "POSICIÓN":"POŘADÍ","PUNTOS":"BODY","V · E · D":"V · R · P","GOLES A FAVOR":"VSTŘELENÉ GÓLY",
      "GOLES EN CONTRA":"INKASOVANÉ GÓLY","PABELLÓN":"HALA","INICIO":"ZAČÁTEK","ALINEACIONES":"SESTAVY",
      "MÁXIMOS PUNTUADORES":"NEJPRODUKTIVNĚJŠÍ HRÁČI","CLASIFICACIÓN":"TABULKA","GOLES":"GÓLY","ASIST.":"ASIST.",
      "PENALTIS":"NÁJEZDY","FECHA NAC.":"DATUM NAR.","NACIONALIDAD":"NÁRODNOST",
      "PARTIDOS":"ZÁPASY","ENTRENADOR":"TRENÉR","ENTRENADORES":"TRENÉŘI","Goles a favor":"Vstřelené góly",
      "Goles en contra":"Inkasované góly","Posición":"Pořadí","Puntos":"Body","Victorias":"Výhry"
    },
    fi: {
      "EVENTOS":"TAPAHTUMAT","LOCAL":"KOTI","VISITANTE":"VIERAS","PREMATCH":"ENNEN OTTELUA",
      "POSICIÓN":"SIJOITUS","PUNTOS":"PISTEET","V · E · D":"V · T · H","GOLES A FAVOR":"TEHDYT MAALIT",
      "GOLES EN CONTRA":"PÄÄSTETYT MAALIT","PABELLÓN":"AREENA","INICIO":"ALKU","ALINEACIONES":"KOKOONPANOT",
      "MÁXIMOS PUNTUADORES":"PISTEPAIKKA","CLASIFICACIÓN":"SARJATAULUKKO","GOLES":"MAALIT","ASIST.":"SYÖTÖT",
      "PENALTIS":"RANGAISTUSLAUKAUKSET","FECHA NAC.":"SYNTYMÄAIKA","NACIONALIDAD":"KANSALAISUUS",
      "PARTIDOS":"OTTELUT","ENTRENADOR":"VALMENTAJA","ENTRENADORES":"VALMENTAJAT","Goles a favor":"Tehdyt maalit",
      "Goles en contra":"Päästetyt maalit","Posición":"Sijoitus","Puntos":"Pisteet","Victorias":"Voitot"
    },
    de: {
      "EVENTOS":"EREIGNISSE","LOCAL":"HEIM","VISITANTE":"GAST","PREMATCH":"VOR DEM SPIEL",
      "POSICIÓN":"PLATZ","PUNTOS":"PUNKTE","V · E · D":"S · U · N","GOLES A FAVOR":"TORE",
      "GOLES EN CONTRA":"GEGENTORE","PABELLÓN":"HALLE","INICIO":"BEGINN","ALINEACIONES":"AUFSTELLUNGEN",
      "MÁXIMOS PUNTUADORES":"TOPSCORER","CLASIFICACIÓN":"TABELLE","GOLES":"TORE","ASIST.":"VORLAGEN",
      "PENALTIS":"PENALTYSCHIESSEN","FECHA NAC.":"GEBURTSDATUM","NACIONALIDAD":"NATIONALITÄT",
      "PARTIDOS":"SPIELE","ENTRENADOR":"TRAINER","ENTRENADORES":"TRAINER","Goles a favor":"Tore",
      "Goles en contra":"Gegentore","Posición":"Platz","Puntos":"Punkte","Victorias":"Siege"
    }
  };
  let overlayAppearanceSignature = "";
  let periodStripConfig = { enabled: false, segments: 3, labels: ["1", "2", "3"] };
  const t = (es, en) => overlayLanguage === "es" ? es : overlayLanguage === "en" ? en : (OVERLAY_TRANSLATIONS[overlayLanguage]?.[es] || en || es);
  const POSITION_TRANSLATIONS = {
    es: { goalkeeper: "Portero", defender: "Defensa", midfielder: "Medio", forward: "Delantero", coach: "Entrenador", player_coach: "Jugador-entrenador", left_back: "Lateral izquierdo", center_back: "Central", right_back: "Lateral derecho", pivot: "Pivote", left_wing: "Extremo izquierdo", right_wing: "Extremo derecho" },
    en: { goalkeeper: "Goalkeeper", defender: "Defender", midfielder: "Midfielder", forward: "Forward", coach: "Coach", player_coach: "Player-coach", left_back: "Left back", center_back: "Centre back", right_back: "Right back", pivot: "Pivot", left_wing: "Left wing", right_wing: "Right wing" },
    sv: { goalkeeper: "Målvakt", defender: "Back", midfielder: "Center", forward: "Forward", coach: "Tränare", player_coach: "Spelande tränare", left_back: "Vänsternia", center_back: "Mittnia", right_back: "Högernia", pivot: "Mittsexa", left_wing: "Vänstersexa", right_wing: "Högersexa" },
    cs: { goalkeeper: "Brankář", defender: "Obránce", midfielder: "Střední hráč", forward: "Útočník", coach: "Trenér", player_coach: "Hrající trenér", left_back: "Levá spojka", center_back: "Střední spojka", right_back: "Pravá spojka", pivot: "Pivot", left_wing: "Levé křídlo", right_wing: "Pravé křídlo" },
    fi: { goalkeeper: "Maalivahti", defender: "Puolustaja", midfielder: "Keskushyökkääjä", forward: "Hyökkääjä", coach: "Valmentaja", player_coach: "Pelaajavalmentaja", left_back: "Vasen takapelaaja", center_back: "Keskustakapelaaja", right_back: "Oikea takapelaaja", pivot: "Viivapelaaja", left_wing: "Vasen laituri", right_wing: "Oikea laituri" },
    de: { goalkeeper: "Torhüter", defender: "Verteidiger", midfielder: "Center", forward: "Stürmer", coach: "Trainer", player_coach: "Spielertrainer", left_back: "Rückraum links", center_back: "Rückraum Mitte", right_back: "Rückraum rechts", pivot: "Kreisläufer", left_wing: "Linksaußen", right_wing: "Rechtsaußen" },
  };
  function canonicalPosition(value) {
    const raw = String(value || "").trim();
    const normalized = raw.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[._-]+/g, " ").replace(/\s+/g, " ");
    if (!normalized) return "";
    if (["por", "portero", "portera", "goalkeeper", "goalie", "keeper", "gk", "mv", "br", "tw", "maalivahti", "malvakt", "brankar", "torhuter"].includes(normalized)) return "goalkeeper";
    if (["def", "defensa", "defender", "defence", "defense", "back", "obr", "obrance", "puolustaja", "verteidiger"].includes(normalized)) return "defender";
    if (["med", "medio", "mediocentro", "mid", "midfielder", "center", "centre", "stredni hrac", "keskushyokkaaja"].includes(normalized)) return "midfielder";
    if (["lateral izquierdo", "left back", "leftback"].includes(normalized)) return "left_back";
    if (["central", "center back", "centre back", "centerback"].includes(normalized)) return "center_back";
    if (["lateral derecho", "right back", "rightback"].includes(normalized)) return "right_back";
    if (["pivote", "pivot", "kreislaufer"].includes(normalized)) return "pivot";
    if (["extremo izquierdo", "left wing", "leftwing"].includes(normalized)) return "left_wing";
    if (["extremo derecho", "right wing", "rightwing"].includes(normalized)) return "right_wing";
    if (["del", "delantero", "delantera", "forward", "striker", "wing", "utocnik", "hyokkaaja", "sturmer"].includes(normalized)) return "forward";
    if (["player coach", "jugador entrenador", "jugador y entrenador", "spelande tranare", "hrajici trener", "pelaajavalmentaja", "spielertrainer"].includes(normalized)) return "player_coach";
  if (["coach", "entrenador", "entrenadora", "trainer", "tranare", "trener", "valmentaja"].includes(normalized)) return "coach";
    return "";
  }
  function translatePosition(value) {
    const combined = String(value || "").trim();
    if (combined.endsWith("_coach") && combined !== "player_coach") return translatePosition(combined.slice(0,-6)) + " + " + (POSITION_TRANSLATIONS[overlayLanguage]?.coach || "Coach");
    const raw = String(value || "").trim();
    if (!raw) return "";
    const canonical = canonicalPosition(raw);
    return canonical ? (POSITION_TRANSLATIONS[overlayLanguage]?.[canonical] || POSITION_TRANSLATIONS.en[canonical]) : raw;
  }
  function applyOverlayLanguage(language) {
    overlayLanguage = ["es", "en", "sv", "cs", "fi", "de"].includes(language) ? language : "es";
    document.documentElement.lang = overlayLanguage;
    const set = (selector, es, en) => document.querySelectorAll(selector).forEach((element) => { element.textContent = t(es, en); });
    set(".intermission-events-title", "EVENTOS", "EVENTS");
    const sideTitles = document.querySelectorAll(".intermission-side-title");
    if (sideTitles[0]) sideTitles[0].textContent = t("LOCAL", "HOME");
    if (sideTitles[1]) sideTitles[1].textContent = t("VISITANTE", "AWAY");
    set(".prematch-kicker", "PREMATCH", "PRE-MATCH");
    const roles = document.querySelectorAll(".prematch-team-role");
    if (roles[0]) roles[0].textContent = t("LOCAL", "HOME");
    if (roles[1]) roles[1].textContent = t("VISITANTE", "AWAY");
    const prematchLabels = [
      ["POSICIÓN", "POSITION"], ["PUNTOS", "POINTS"], ["V · E · D", "W · D · L"],
      ["GOLES A FAVOR", "GOALS FOR"], ["GOLES EN CONTRA", "GOALS AGAINST"],
    ];
    document.querySelectorAll(".prematch-stat-label").forEach((element, index) => {
      const values = prematchLabels[index]; if (values) element.textContent = t(values[0], values[1]);
    });
    const infoLabels = document.querySelectorAll(".prematch-info-label");
    if (infoLabels[0]) infoLabels[0].textContent = t("PABELLÓN", "VENUE");
    if (infoLabels[1]) infoLabels[1].textContent = t("INICIO", "START");
    set(".lineups-title", "ALINEACIONES", "LINEUPS");
    const lineupNames = document.querySelectorAll(".lineups-team-name");
    if (lineupNames[0] && ["LOCAL", "HOME"].includes(lineupNames[0].textContent)) lineupNames[0].textContent = t("LOCAL", "HOME");
    if (lineupNames[1] && ["VISITANTE", "AWAY"].includes(lineupNames[1].textContent)) lineupNames[1].textContent = t("VISITANTE", "AWAY");
    const statsTitles = document.querySelectorAll(".stats-title");
    if (statsTitles[0]) statsTitles[0].textContent = t("MÁXIMOS PUNTUADORES", "TOP SCORERS");
    if (statsTitles[1]) statsTitles[1].textContent = t("CLASIFICACIÓN", "STANDINGS");
    document.querySelectorAll(".scorer-stats span").forEach((element) => {
      const original = element.textContent.trim();
      if (["GOLES", "GOALS"].includes(original)) element.textContent = t("GOLES", "GOALS");
      else if (["ASIST.", "ASSISTS"].includes(original)) element.textContent = t("ASIST.", "ASSISTS");
      else if (["PUNTOS", "POINTS"].includes(original)) element.textContent = t("PUNTOS", "POINTS");
    });
    set(".penalties-kicker", "PENALTIS", "PENALTY SHOOTOUT");
    const profileLabels = document.querySelectorAll(".player-profile-details span");
    const profileCopies = [["FECHA NAC.", "BIRTH DATE"], ["NACIONALIDAD", "NATIONALITY"], ["POSICIÓN", "POSITION"]];
    profileLabels.forEach((element, index) => { const values = profileCopies[index]; if (values) element.textContent = t(values[0], values[1]); });
    const profileStats = document.querySelectorAll(".player-profile-stats span");
    const profileStatCopies = [["PARTIDOS", "MATCHES"], ["GOLES", "GOALS"], ["ASIST.", "ASSISTS"]];
    profileStats.forEach((element, index) => { const values = profileStatCopies[index]; if (values) element.textContent = t(values[0], values[1]); });
  }
  function safeColour(value, fallback) {
    const colour = String(value || "").trim();
    return /^#[0-9a-f]{6}$/i.test(colour) ? colour : fallback;
  }
  function applyOverlayAppearance(settings = {}) {
    const appearance = settings.appearance || {};
    const signature = JSON.stringify({ language: settings.language || "es", appearance });
    if (signature === overlayAppearanceSignature) return;
    overlayAppearanceSignature = signature;
    const scoreboardRaw = { ...overlayAppearanceDefaults.scoreboard, ...(appearance.scoreboard || {}) };
    const bottomRaw = { ...overlayAppearanceDefaults.bottom_bar, ...(appearance.bottom_bar || {}) };
    const panelsRaw = { ...overlayAppearanceDefaults.panels, ...(appearance.panels || {}) };
    const scoreboard = {
      background: safeColour(scoreboardRaw.background, overlayAppearanceDefaults.scoreboard.background),
      name_box: safeColour(scoreboardRaw.name_box, overlayAppearanceDefaults.scoreboard.name_box),
      text: safeColour(scoreboardRaw.text, overlayAppearanceDefaults.scoreboard.text),
    };
    const bottom = {
      body: safeColour(bottomRaw.body, overlayAppearanceDefaults.bottom_bar.body),
      middle: safeColour(bottomRaw.middle, overlayAppearanceDefaults.bottom_bar.middle),
      text: safeColour(bottomRaw.text, overlayAppearanceDefaults.bottom_bar.text),
      secondary_text: safeColour(bottomRaw.secondary_text, overlayAppearanceDefaults.bottom_bar.secondary_text),
    };
    const panels = {
      background: safeColour(panelsRaw.background, overlayAppearanceDefaults.panels.background),
      surface: safeColour(panelsRaw.surface, overlayAppearanceDefaults.panels.surface),
      accent: safeColour(panelsRaw.accent, overlayAppearanceDefaults.panels.accent),
      text: safeColour(panelsRaw.text, overlayAppearanceDefaults.panels.text),
    };
    const periodRaw = appearance.period_strip || {};
    const periodSegments = settings.sport_mode === "handball" ? 2 : Math.max(1, Math.min(12, Number(periodRaw.segments || 3)));
    periodStripConfig = {
      enabled: Boolean(periodRaw.enabled),
      show_number: Boolean(periodRaw.show_number),
      segments: periodSegments,
      labels: Array.from({length: periodSegments}, (_, index) => String(periodRaw.labels?.[index] || index + 1).slice(0, 8)),
    };
    const periodStrip = safeGet("period-strip");
    if (periodStrip) {
      periodStrip.closest(".time-box")?.classList.toggle("has-period-strip", periodStripConfig.enabled);
      periodStrip.style.setProperty("--period-active-color", safeColour(periodRaw.active_color, "#8cff00"));
      periodStrip.style.setProperty("--period-text-color", safeColour(periodRaw.text_color, "#102000"));
      periodStrip.classList.toggle("hidden", !periodStripConfig.enabled);
      periodStrip.setAttribute("aria-hidden", periodStripConfig.enabled ? "false" : "true");
      periodStrip.innerHTML = periodStripConfig.labels.map((label, index) => `<span data-period-index="${index + 1}">${String(label).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]))}</span>`).join("");
    }
    const elementSelectors = {scoreboard: "#scoreboard-wrapper", bottom_bar: "#bottom-bar", player_profile: "#player-profile-bar", prematch: "#prematch-modal .prematch-panel", intermission: "#intermission-modal .intermission-content", lineups_home: "#lineups-team1-modal .lineups-panel", lineups_away: "#lineups-team2-modal .lineups-panel", top_scorers: "#top-scorers-modal .stats-panel", standings: "#standings-modal .stats-panel", penalties: "#penalties-modal .penalties-panel"};
    let typography = document.getElementById("secretariat-overlay-elements");
    if (!typography) { typography = document.createElement("style"); typography.id = "secretariat-overlay-elements"; document.head.appendChild(typography); }
    typography.textContent = Object.entries(elementSelectors).map(([key, selector]) => {
      const config = appearance.elements?.[key] || {};
      const value = Number(config.scale ?? 1);
      const scale = Number.isFinite(value) ? Math.max(.5, Math.min(1.5, value)) : 1;
      const font = ["Arial", "Verdana", "Georgia", "Trebuchet MS", "Courier New"].includes(config.font) ? config.font : null;
      const origin = key === "scoreboard" ? "top center" : ["bottom_bar", "player_profile"].includes(key) ? "bottom center" : "center";
      return `${selector} { scale: ${scale}; transform-origin: ${origin}; }` + (font ? `${selector}, ${selector} * { font-family: "${font}" !important; }` : "");
    }).join("\n");
    const root = document.documentElement;
    root.style.setProperty("--overlay-score-bg", scoreboard.background);
    root.style.setProperty("--overlay-score-name", scoreboard.name_box);
    root.style.setProperty("--overlay-score-text", scoreboard.text);
    root.style.setProperty("--bottom-body-color", bottom.body);
    root.style.setProperty("--bottom-middle-color", bottom.middle);
    root.style.setProperty("--bottom-text-color", bottom.text);
    root.style.setProperty("--bottom-secondary-color", bottom.secondary_text);
    root.style.setProperty("--overlay-panel-bg", panels.background);
    root.style.setProperty("--overlay-panel-surface", panels.surface);
    root.style.setProperty("--overlay-panel-accent", panels.accent);
    root.style.setProperty("--overlay-panel-text", panels.text);

    // A final style element is deliberately used instead of relying only on
    // inherited variables. OBS may retain old browser-source CSS; these rules
    // are appended after it and therefore apply the saved palette reliably.
    let style = document.getElementById("secretariat-overlay-palette");
    if (!style) {
      style = document.createElement("style");
      style.id = "secretariat-overlay-palette";
      document.head.appendChild(style);
    }
    style.textContent = `
      .scoreboard .grey, .scoreboard .center {
        background-color: ${scoreboard.background} !important; color: ${scoreboard.text} !important;
      }
      .scoreboard .score-box { background: transparent !important; color: ${scoreboard.text} !important; }
      .scoreboard .time-box {
        background: color-mix(in srgb, ${scoreboard.background} 72%, #05070b 28%) !important;
        color: ${scoreboard.text} !important;
      }
      .scoreboard .team1-name-box, .scoreboard .team2-name-box, .scoreboard .score-input {
        background-color: ${scoreboard.name_box} !important; color: ${scoreboard.text} !important;
      }
      #bottom-bar .bottom-event-copy { background: ${bottom.body} !important; }
      #bottom-bar .bottom-match-state { background: ${bottom.middle} !important; }
      #bottom-bar .bottom-current-score, #bottom-bar .bottom-person-name { color: ${bottom.text} !important; }
      #bottom-bar .bottom-match-time, #bottom-bar .bottom-goal-count,
      #bottom-bar #bottom-assistant-row .bottom-person-number,
      #bottom-bar #bottom-assistant-row .bottom-person-name { color: ${bottom.secondary_text} !important; }
      .prematch-panel, .prematch-content, .intermission-panel, .intermission-content,
      .stats-panel, .player-profile-bar {
        background-color: ${panels.background} !important; color: ${panels.text} !important;
      }
      .prematch-team, .prematch-stat, .intermission-side, .intermission-event,
      .lineups-panel, .lineups-panel.team-lineup-panel, .stats-content, .stats-list,
      .standings-table, .penalties-team-row, .player-profile-main, .player-profile-stats {
        background-color: ${panels.surface} !important; color: ${panels.text} !important;
      }
      .stats-header, .intermission-header, .prematch-header, .penalties-header,
      .lineups-header, .prematch-top-accent, .penalties-top-accent {
        border-color: ${panels.accent} !important;
      }
      .stats-title, .lineups-title, .prematch-kicker, .penalties-kicker,
      .intermission-events-title { color: ${panels.text} !important; }
    `;
    applyOverlayLanguage(settings.language || "es");
  }

  async function refreshOverlaySettings() {
    try {
      const response = await fetch(`/api/settings?_=${Date.now()}`, { cache: "no-store" });
      if (response.ok) applyOverlayAppearance(await response.json());
    } catch (_) { /* The overlay remains operational with defaults. */ }
  }

  // -------------------- ELEMENTS --------------------
  const wrapper = safeGet("scoreboard-wrapper");

  // Scoreboard elements
  const team1Name = safeQ('.team1-name');
  const team2Name = safeQ('.team2-name');
  const team1Score = safeQ('.team1-score'); // INPUT shown in scoreboard (treated as display)
  const team2Score = safeQ('.team2-score');
  const team1Logo = safeGet("team1-logo");
  const team2Logo = safeGet("team2-logo");
  const team1Bar = team1Logo ? team1Logo.parentElement : null;
  const team2Bar = team2Logo ? team2Logo.parentElement : null;
  const leagueLogo = safeGet('scoreboard-league-logo');
  const bottomBar = safeGet("bottom-bar");
  const bottomTeamBlock = safeGet("bottom-team-block");
  const bottomTeamLogo = safeGet("bottom-team-logo");
  const bottomMatchTime = safeGet("bottom-match-time");
  const bottomCurrentScore = safeGet("bottom-current-score");
  let goalGraphicScores = null;
  let graphicScores = null;
  const bottomScorerNumber = safeGet("bottom-scorer-number");
  const bottomScorerName = safeGet("bottom-scorer-name");
  const bottomGoalCount = safeGet("bottom-goal-count");
  const bottomAssistantNumber = safeGet("bottom-assistant-number");
  const bottomAssistantName = safeGet("bottom-assistant-name");
  const bottomAssistantRow = safeGet("bottom-assistant-row");
  const playerProfileBar = safeGet("player-profile-bar");
  const playerProfileTeamBlock = safeGet("player-profile-team-block");
  const playerProfileTeamLogo = safeGet("player-profile-team-logo");
  const playerProfileNumber = safeGet("player-profile-number");
  const playerProfileName = safeGet("player-profile-name");
  const playerProfileBirth = safeGet("player-profile-birth");
  const playerProfileNationality = safeGet("player-profile-nationality");
  const playerProfilePosition = safeGet("player-profile-position");
  const playerProfilePlayed = safeGet("player-profile-played");
  const playerProfileGoals = safeGet("player-profile-goals");
  const playerProfileAssists = safeGet("player-profile-assists");
  const penaltiesModal = safeGet("penalties-modal");
  const penaltiesLeagueLogo = safeGet("penalties-league-logo");
  const penaltiesTeam1Logo = safeGet("penalties-team1-logo");
  const penaltiesTeam1LogoBox = safeGet("penalties-team1-logo-box");
  const penaltiesTeam2Logo = safeGet("penalties-team2-logo");
  const penaltiesTeam2LogoBox = safeGet("penalties-team2-logo-box");
  const penaltiesTeam1Name = safeGet("penalties-team1-name");
  const penaltiesTeam2Name = safeGet("penalties-team2-name");
  const penaltiesTeam1Attempts = safeGet("penalties-team1-attempts");
  const penaltiesTeam2Attempts = safeGet("penalties-team2-attempts");
  const penaltiesHomeRow = document.querySelector(".penalties-home-row");
  const penaltiesAwayRow = document.querySelector(".penalties-away-row");
  const ppStack1 = safeGet("team1-status-stack");
  const ppStack2 = safeGet("team2-status-stack");
  const timeDiv = safeGet("match-time") || safeQ('.time-box');
  const periodStrip = safeGet("period-strip");

  // Statistics panels
  const lineupsTeam1Modal = safeGet("lineups-team1-modal");
  const lineupsTeam2Modal = safeGet("lineups-team2-modal");
  const lineupsTitle1 = safeGet("lineups-title-1");
  const lineupsTitle2 = safeGet("lineups-title-2");
  const lineupsTeam1Name = safeGet("lineups-team1-name");
  const lineupsTeam2Name = safeGet("lineups-team2-name");
  const lineupsTeam1List = safeGet("lineups-team1-list");
  const lineupsTeam2List = safeGet("lineups-team2-list");
  const lineupsTeam1Coach = safeGet("lineups-team1-coach");
  const lineupsTeam2Coach = safeGet("lineups-team2-coach");
  const lineupsTeam1Starting = safeGet("lineups-team1-starting");
  const lineupsTeam2Starting = safeGet("lineups-team2-starting");
  const lineupsTeam1Logo = safeGet("lineups-team1-logo");
  const lineupsTeam2Logo = safeGet("lineups-team2-logo");
  const lineupsTeam1Stripe = safeGet("lineups-team1-stripe");
  const lineupsTeam2Stripe = safeGet("lineups-team2-stripe");
  const lineupsCompetitionLogo1 = safeGet("lineups-competition-logo-1");
  const lineupsCompetitionLogo2 = safeGet("lineups-competition-logo-2");
  const lineupsCompetitionName1 = safeGet("lineups-competition-name-1");
  const lineupsCompetitionName2 = safeGet("lineups-competition-name-2");
  const topScorersModal = safeGet("top-scorers-modal");
  const topScorersLogo = safeGet("top-scorers-logo");
  const topScorersCompetition = safeGet("top-scorers-competition");
  const standingsModal = safeGet("standings-modal");
  const standingsLogo = safeGet("standings-logo");
  const standingsCompetition = safeGet("standings-competition");
  const standingsRows = safeGet("standings-rows");
  const lineupSequenceTimers = new WeakMap();
  const LINEUP_STARTING_DURATION_MS = 6500;

  function clearLineupSequence(modal) {
    const timers = lineupSequenceTimers.get(modal) || [];
    timers.forEach(clearTimeout);
    lineupSequenceTimers.delete(modal);
    if (modal) modal.classList.remove("phase-starting", "phase-squad");
  }

  function startLineupSequence(modal) {
    if (!modal) return;
    clearLineupSequence(modal);
    modal.classList.add("phase-starting");
    const toSquad = setTimeout(() => {
      modal.classList.remove("phase-starting");
      modal.classList.add("phase-squad");
    }, LINEUP_STARTING_DURATION_MS);
    lineupSequenceTimers.set(modal, [toSquad]);
  }

  // Intermission elements
  const intermissionModal = safeGet("intermission-modal");
  const intermissionTeam1Stripe = safeGet("intermission-team1-stripe");
  const intermissionTeam2Stripe = safeGet("intermission-team2-stripe");
  const intermissionTeam1Logo = safeGet("intermission-team1-logo");
  const intermissionTeam2Logo = safeGet("intermission-team2-logo");
  const intermissionTeam1Name = safeGet("intermission-team1-name");
  const intermissionTeam2Name = safeGet("intermission-team2-name");
  const intermissionTeam1Score = safeGet("intermission-team1-score");
  const intermissionTeam2Score = safeGet("intermission-team2-score");
  const intermissionEventsHomeViewport = safeGet("intermission-events-home-viewport");
  const intermissionEventsAwayViewport = safeGet("intermission-events-away-viewport");
  const intermissionEventsHomeList = safeGet("intermission-events-home-list");
  const intermissionEventsAwayList = safeGet("intermission-events-away-list");
  const intermissionEventsHomeTitle = safeGet("intermission-events-home-title");
  const intermissionEventsAwayTitle = safeGet("intermission-events-away-title");
  const intermissionLeagueLogo = safeGet("intermission-league-logo");

  // Prematch elements
  const prematchModal = safeGet("prematch-modal");
  const prematchTeam1Text = safeGet("prematch-team1-text");
  const prematchTeam2Text = safeGet("prematch-team2-text");
  const prematchLeagueName = safeGet("prematch-league-name");
  const prematchLeagueLogo = safeGet("prematch-league-logo");
  const prematchTeam1Stats = safeGet("prematch-team1-stats");
  const prematchTeam2Stats = safeGet("prematch-team2-stats");
  const prematchVenue = safeGet("prematch-venue");
  const prematchKickoff = safeGet("prematch-kickoff");

  // Individual prematch stat cells
  const pmCells = {
    team1: {
      position: safeGet("prematch-team1-position"),
      points: safeGet("prematch-team1-points"),
      wins: safeGet("prematch-team1-wins"),
      goals_for: safeGet("prematch-team1-goals-for"),
      goals_against: safeGet("prematch-team1-goals-against"),
    },
    team2: {
      position: safeGet("prematch-team2-position"),
      points: safeGet("prematch-team2-points"),
      wins: safeGet("prematch-team2-wins"),
      goals_for: safeGet("prematch-team2-goals-for"),
      goals_against: safeGet("prematch-team2-goals-against"),
    }
  };

  // Prematch logos/names/stripes
  const pmTeam1Stripe = safeGet("prematch-team1-stripe");
  const pmTeam2Stripe = safeGet("prematch-team2-stripe");
  const pmTeam1Logo = safeGet("prematch-team1-logo");
  const pmTeam2Logo = safeGet("prematch-team2-logo");
  const pmTeam1Name = safeGet("prematch-team1-name");
  const pmTeam2Name = safeGet("prematch-team2-name");
  const pmTeam1Score = safeGet("prematch-team1-score");
  const pmTeam2Score = safeGet("prematch-team2-score");


  const intermissionScrollStates = new Map();

  function stopIntermissionAutoScroll(viewport) {
    if (!viewport) return;
    const state = intermissionScrollStates.get(viewport);
    if (state?.frame) cancelAnimationFrame(state.frame);
    intermissionScrollStates.delete(viewport);
    const list = viewport.querySelector(".intermission-events-list");
    if (list) {
      list.style.transform = "translate3d(0, 0, 0)";
      list.style.willChange = "auto";
    }
  }

  function startIntermissionAutoScroll(viewport, list) {
    stopIntermissionAutoScroll(viewport);
    if (!viewport || !list) return;

    // Force layout after the modal and equal-height columns are visible.
    const maxOffset = Math.max(0, list.getBoundingClientRect().height - viewport.getBoundingClientRect().height);
    if (maxOffset <= 6) return;

    const state = {
      frame: null,
      direction: 1,
      offset: 0,
      pauseUntil: performance.now() + 1500,
      last: performance.now()
    };
    intermissionScrollStates.set(viewport, state);
    list.style.willChange = "transform";

    const step = now => {
      if (!intermissionModal || !intermissionModal.classList.contains("show")) {
        state.frame = null;
        return;
      }

      const currentMax = Math.max(0, list.getBoundingClientRect().height - viewport.getBoundingClientRect().height);
      if (currentMax <= 6) {
        list.style.transform = "translate3d(0, 0, 0)";
        state.frame = null;
        return;
      }

      if (now < state.pauseUntil) {
        state.last = now;
        state.frame = requestAnimationFrame(step);
        return;
      }

      const delta = Math.min(50, now - state.last);
      state.last = now;
      state.offset += state.direction * delta * 0.030;

      if (state.offset >= currentMax) {
        state.offset = currentMax;
        state.direction = -1;
        state.pauseUntil = now + 1600;
      } else if (state.offset <= 0) {
        state.offset = 0;
        state.direction = 1;
        state.pauseUntil = now + 1600;
      }

      list.style.transform = `translate3d(0, ${-state.offset}px, 0)`;
      state.frame = requestAnimationFrame(step);
    };

    state.frame = requestAnimationFrame(step);
  }

  function eventPerson(number, lastName) {
    const clean = String(number || "").replace(/^#\s*/, "").trim();
    const numberText = clean ? `#${clean}` : "";
    return [numberText, String(lastName || "").trim()].filter(Boolean).join(" ");
  }

  function renderIntermissionSide(list, viewport, rows) {
    if (!list) return;
    list.innerHTML = "";
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "intermission-event-empty";
      empty.textContent = "SIN EVENTOS";
      list.appendChild(empty);
    } else {
      rows.forEach(event => {
        const row = document.createElement("div");
        row.className = `intermission-event-row ${event.type === "penalty" ? "is-penalty" : "is-goal"}`;
        const score = document.createElement("span");
        score.className = "event-score";
        score.textContent = event.score || "";
        const minute = document.createElement("span");
        minute.className = "event-minute";
        minute.textContent = event.minute || "--:--";
        const detail = document.createElement("span");
        detail.className = "event-detail";
        if (event.type === "penalty") {
          const penaltyLine = document.createElement("span");
          penaltyLine.className = "event-person-line event-penalty-line";
          penaltyLine.textContent = `PP · ${eventPerson(event.number, event.last_name)} · ${event.penalty_type || "2"}`;
          detail.appendChild(penaltyLine);
        } else {
          const scorerLine = document.createElement("span");
          scorerLine.className = "event-person-line event-scorer-line";
          scorerLine.textContent = eventPerson(event.number, event.last_name);
          if (event.powerplay_goal) {
            const ppMark = document.createElement("span");
            ppMark.className = "event-pp-mark";
            ppMark.textContent = " PP";
            scorerLine.appendChild(ppMark);
          }
          detail.appendChild(scorerLine);

          const assistant = eventPerson(event.assistant_number, event.assistant_last_name);
          if (assistant) {
            const assistantLine = document.createElement("span");
            assistantLine.className = "event-person-line event-assistant-line";
            assistantLine.textContent = assistant;
            detail.appendChild(assistantLine);
          }
        }
        row.append(score, minute, detail);
        list.appendChild(row);
      });
    }
  }

  function syncIntermissionColumnHeights() {
    const viewports = [intermissionEventsHomeViewport, intermissionEventsAwayViewport].filter(Boolean);
    const lists = [intermissionEventsHomeList, intermissionEventsAwayList].filter(Boolean);
    if (viewports.length !== 2 || lists.length !== 2) return;

    viewports.forEach(viewport => {
      stopIntermissionAutoScroll(viewport);
      viewport.style.height = "auto";
    });

    const naturalHeight = Math.max(...lists.map(list => list.scrollHeight), 150);
    const availableHeight = Math.max(220, Math.min(560, window.innerHeight * 0.50));
    const sharedHeight = Math.min(naturalHeight, availableHeight);

    viewports.forEach(viewport => {
      viewport.style.height = `${Math.ceil(sharedHeight)}px`;
      viewport.scrollTop = 0;
    });

    requestAnimationFrame(() => requestAnimationFrame(() => {
      startIntermissionAutoScroll(intermissionEventsHomeViewport, intermissionEventsHomeList);
      startIntermissionAutoScroll(intermissionEventsAwayViewport, intermissionEventsAwayList);
    }));
  }

  function renderIntermissionEvents(events, team1Name, team2Name) {
    const rows = Array.isArray(events) ? events : [];
    const signature = JSON.stringify(rows);
    if (intermissionEventsHomeList?.dataset.signature === signature &&
        intermissionEventsAwayList?.dataset.signature === signature) return;
    if (intermissionEventsHomeList) intermissionEventsHomeList.dataset.signature = signature;
    if (intermissionEventsAwayList) intermissionEventsAwayList.dataset.signature = signature;
    if (intermissionEventsHomeTitle) intermissionEventsHomeTitle.textContent = team1Name || t("LOCAL", "HOME");
    if (intermissionEventsAwayTitle) intermissionEventsAwayTitle.textContent = team2Name || t("VISITANTE", "AWAY");
    const homeRows = rows.filter(event => event.side === "home");
    const awayRows = rows.filter(event => event.side === "away");
    renderIntermissionSide(intermissionEventsHomeList, intermissionEventsHomeViewport, homeRows);
    renderIntermissionSide(intermissionEventsAwayList, intermissionEventsAwayViewport, awayRows);
    requestAnimationFrame(() => requestAnimationFrame(syncIntermissionColumnHeights));
  }


  function renderPenaltyAttempts(container, values) {
    if (!container) return;
    const normalized = Array.from({ length: 5 }, (_, index) => (values || [])[index] || null);
    const signature = JSON.stringify(normalized);
    if (container.dataset.signature === signature) return;
    container.dataset.signature = signature;
    container.innerHTML = "";
    normalized.forEach((value, index) => {
      const attempt = document.createElement("div");
      attempt.className = `penalty-attempt ${value === "goal" ? "is-goal" : value === "miss" ? "is-miss" : "is-pending"}`;
      attempt.textContent = value === "goal" ? "✓" : value === "miss" ? "✕" : String(index + 1);
      container.appendChild(attempt);
    });
  }

  // -------------------- State trackers (avoid unnecessary DOM writes) --------------------
  function normalizeOverlayColor(value, fallback) {
    if (typeof value !== "string") return fallback;
    const color = value.trim();
    if (!color) return fallback;
    if (/^#[0-9a-f]{3,8}$/i.test(color)) return color;
    if (/^(rgb|hsl)a?\(/i.test(color)) return color;
    return fallback;
  }

  function applyPenaltyTeamColor(row, logoBox, color, squareWidth) {
    if (!row || !logoBox) return;
    const gray = "rgba(42,45,53,.98)";
    row.style.setProperty(
      "background",
      `linear-gradient(90deg, ${color} 0 ${squareWidth}px, ${gray} ${squareWidth}px 100%)`,
      "important"
    );
    row.style.setProperty("box-shadow", `inset 7px 0 0 ${color}, inset 0 1px 0 rgba(255,255,255,.10), 0 8px 22px rgba(0,0,0,.22)`, "important");
    logoBox.style.setProperty("background", color, "important");
    logoBox.style.setProperty("background-color", color, "important");
  }

  let prevStatus = { anim: null, pp1: null, pp2: null, intermission: null, prematch: null, lineupsTeam1: null, lineupsTeam2: null, topScorers: null, standings: null, playerProfile: null, penalties: null };
  let prevTxt = { home: null, away: null, time: null };
  let prevJson = {}; // keep last JSON to allow diffing if needed

  // -------------------- Utilities --------------------
  function triggerAnimation(el, className = "show") {
    if (!el) return;
    const isLineups = el.classList.contains("lineups-modal");
    if (isLineups) {
      if (className === "hide" || className === "hidden") el.classList.add("lineups-exiting");
      else el.classList.remove("lineups-exiting");
    }
    el.classList.remove("show", "hide", "visible", "hidden");
    void el.offsetWidth; // reflow
    el.classList.add(className);
  }

  // El contador de expulsión lo calcula Python usando el reloj OCR ascendente.
  // El navegador solo representa remaining_seconds, por lo que si el reloj del
  // pabellón se detiene, el powerplay se detiene exactamente igual.
  function normalizePlayerNumber(info) {
    const raw = info?.player_number ?? info?.serving_player_number ?? info?.player_number_raw ?? "";
    const clean = String(raw).replace(/^#\s*/, "").trim();
    return clean ? `#${clean}` : "";
  }

  function activePenaltyItems(info) {
    const queued = Array.isArray(info?.penalties) ? info.penalties.filter((item) => item && item.status) : [];
    if (queued.length) return queued;
    return info?.status ? [info] : [];
  }

  function penaltyStableKey(item, index) {
    const supplied = item?.overlay_id || item?.penalty_id || item?.id;
    if (supplied) return `penalty:${String(supplied)}`;
    return `penalty:${[
      item?.start_match_seconds ?? item?.block_start_match_seconds ?? "",
      item?.player_id ?? "",
      item?.player_number_raw ?? item?.player_number ?? "",
      item?.serving_player_id ?? "",
      item?.penalty_type ?? "2",
      index,
    ].join("|")}`;
  }

  function statusDesiredItems(info, emptyNetActive) {
    const penalties = activePenaltyItems(info).map((item, index) => ({
      key: penaltyStableKey(item, index),
      kind: "penalty",
      info: item,
    }));
    if (emptyNetActive) penalties.push({ key: "empty-net", kind: "empty-net", info: null });
    return penalties;
  }

  function statusSlideOffset(teamKey, distance = 24) {
    return `${teamKey === "team2" ? distance : -distance}px`;
  }

  function animateStatusEntry(node, teamKey) {
    if (!node || typeof node.animate !== "function") return;
    const animation = node.animate([
      { opacity: 0, transform: `translateX(${statusSlideOffset(teamKey)})` },
      { opacity: 1, transform: "translateX(0px)" },
    ], {
      duration: 230,
      easing: "cubic-bezier(.2,.8,.2,1)",
      fill: "none",
    });
    animation.finished.catch(() => {});
  }

  function animateStatusExit(node, teamKey, onDone) {
    if (!node) return;
    if (node.dataset.spExiting === "1") return;
    node.dataset.spExiting = "1";
    const done = () => {
      if (!node.isConnected) return;
      node.remove();
      if (typeof onDone === "function") onDone();
    };
    if (typeof node.animate !== "function") {
      done();
      return;
    }
    const animation = node.animate([
      { opacity: 1, transform: "translateX(0px)", height: "44px", maxHeight: "44px" },
      { opacity: 0, transform: `translateX(${statusSlideOffset(teamKey)})`, height: "0px", maxHeight: "0px" },
    ], {
      duration: 300,
      easing: "cubic-bezier(.45,.05,.55,.95)",
      fill: "forwards",
    });
    animation.finished.then(done).catch(done);
  }

  function buildStatusNode(item, teamKey) {
    const node = document.createElement("div");
    node.className = `sp-status-item sp-status-item--${item.kind}`;
    node.dataset.spStatusKey = item.key;
    node.dataset.spTeam = teamKey;
    node.dataset.spExiting = "0";
    node.setAttribute("aria-hidden", "false");

    const content = document.createElement("div");
    content.className = "sp-status-item__content";
    if (item.kind === "penalty") {
      content.innerHTML = '<span class="sp-status-number"></span><span class="sp-status-timer">2:00</span>';
    } else {
      content.innerHTML = '<span class="sp-status-empty-copy">EMPTY NET</span>';
    }
    node.appendChild(content);
    return node;
  }

  function updateStatusNode(node, item) {
    if (!node || item.kind !== "penalty") return;
    const timerEl = node.querySelector(".sp-status-timer");
    const numberEl = node.querySelector(".sp-status-number");
    const parsed = Number(item.info?.remaining_seconds);
    const remaining = Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 120;
    const mm = Math.floor(remaining / 60);
    const ss = String(remaining % 60).padStart(2, "0");
    if (numberEl) setTextIfChanged(numberEl, normalizePlayerNumber(item.info));
    if (timerEl) setTextIfChanged(timerEl, `${mm}:${ss}`);
    node.classList.toggle("sp-status-item--ending", remaining <= 10 && remaining > 0);
  }

  function applyStatusGeometry(stack) {
    if (!stack) return;
    const nodes = [...stack.querySelectorAll(":scope > .sp-status-item")];
    nodes.forEach((node) => node.classList.remove("sp-status-item--bottom"));
    if (nodes.length) nodes[nodes.length - 1].classList.add("sp-status-item--bottom");
    stack.dataset.spCount = String(nodes.length);
  }

  function reorderStatusNodesWhenStable(stack, desiredKeys) {
    if (!stack) return;
    const hasExiting = Boolean(stack.querySelector(":scope > .sp-status-item[data-sp-exiting='1']"));
    if (hasExiting) return;
    desiredKeys.forEach((key) => {
      const node = [...stack.querySelectorAll(":scope > .sp-status-item")]
        .find((candidate) => candidate.dataset.spStatusKey === key);
      if (node) stack.appendChild(node);
    });
  }

  function renderTeamStatusStack(stack, info, emptyNetActive, teamKey) {
    if (!stack) return;
    const desired = statusDesiredItems(info, Boolean(emptyNetActive));
    const desiredKeys = desired.map((item) => item.key);
    const desiredSet = new Set(desiredKeys);
    const current = new Map(
      [...stack.querySelectorAll(":scope > .sp-status-item")]
        .map((node) => [node.dataset.spStatusKey, node])
    );

    desired.forEach((item) => {
      let node = current.get(item.key);
      const isNew = !node;
      if (!node) {
        node = buildStatusNode(item, teamKey);
        current.set(item.key, node);
      }
      if (node.dataset.spExiting === "1") {
        node.getAnimations?.().forEach((animation) => animation.cancel());
        node.dataset.spExiting = "0";
        node.style.removeProperty("opacity");
        node.style.removeProperty("transform");
        node.style.removeProperty("height");
        node.style.removeProperty("max-height");
      }
      if (isNew && !node.isConnected) stack.appendChild(node);
      updateStatusNode(node, item);
      if (isNew) animateStatusEntry(node, teamKey);
    });

    [...stack.querySelectorAll(":scope > .sp-status-item")].forEach((node) => {
      const key = node.dataset.spStatusKey;
      if (desiredSet.has(key)) return;
      animateStatusExit(node, teamKey, () => {
        reorderStatusNodesWhenStable(stack, desiredKeys);
        applyStatusGeometry(stack);
      });
    });

    reorderStatusNodesWhenStable(stack, desiredKeys);
    applyStatusGeometry(stack);
  }

  function getPrematchVal(data, team, field) {
    if (!data || !data.prematch) return null;
    if (data.prematch[team] && data.prematch[team][field] !== undefined && data.prematch[team][field] !== "") {
      return data.prematch[team][field];
    }
    const flatKey = `${team}_${field}`;
    if (data.prematch[flatKey] !== undefined && data.prematch[flatKey] !== "") return data.prematch[flatKey];
    return null;
  }

  // Safe setter helpers (only write if changed)
  function setInputValueIfChanged(inputEl, val) {
    if (!inputEl) return;
    const s = String(val ?? "");
    if (inputEl.value !== s && document.activeElement !== inputEl) {
      inputEl.value = s;
    }
  }
  function setTextIfChanged(el, val) {
    if (!el) return;
    const s = String(val ?? "");
    if (el.textContent !== s) el.textContent = s;
  }
  function setSrcIfChanged(imgEl, val) {
    if (!imgEl) return;
    const s = val ?? "";
    if (imgEl.src === "" && s === "") return;
    // compare last path part to avoid absolute-url differences
    const prev = imgEl.getAttribute("data-src") || "";
    if (prev !== s) {
      imgEl.setAttribute("data-src", s);
      imgEl.src = s;
    }
  }

  // -------------------- Update DOM from data.json (non-score fields primarily) --------------------
  function renderCoach(container, coaches) {
    if (!container) return;
    const list = Array.isArray(coaches) ? coaches : (coaches ? [coaches] : []);
    const names = list
      .map(coach => coach && (coach.name || [coach.first_name, coach.last_name].filter(Boolean).join(" ")))
      .filter(Boolean);
    container.innerHTML = "";
    if (names.length) {
      const label = document.createElement("span");
      label.className = "coach-label";
      label.textContent = names.length > 1 ? t("ENTRENADORES", "COACHES") : t("ENTRENADOR", "COACH");
      const coachName = document.createElement("span");
      coachName.className = "coach-name";
      coachName.textContent = names.join(" · ");
      container.append(label, coachName);
    }
    container.classList.toggle("empty", names.length === 0);
  }

  function updateDynamicSquadHeight(modal, playerCount, hasCoach) {
    if (!modal) return;
    const panel = modal.querySelector(".lineups-panel");
    const list = modal.querySelector(".team-only-list");
    if (!panel || !list) return;

    // Base estable anterior al rediseño: siempre dos columnas, filas cómodas
    // y altura calculada por el contenido real. Evita solapamientos.
    const rows = Math.max(1, Math.ceil((Number(playerCount) || 0) / 2));
    const viewportHeight = Math.max(600, window.innerHeight || 1080);
    const rowHeight = viewportHeight < 760 ? 35 : 42;
    const rowGap = viewportHeight < 760 ? 5 : 7;
    const listHeight = rows * rowHeight + Math.max(0, rows - 1) * rowGap;
    const coachHeight = hasCoach ? 72 : 0;
    const fixedHeight = viewportHeight < 760 ? 250 : 292;
    const naturalHeight = fixedHeight + listHeight + coachHeight;
    const maxHeight = Math.floor(viewportHeight * 0.96);
    const target = Math.max(500, Math.min(maxHeight, naturalHeight));

    modal.classList.toggle("lineups-compact", viewportHeight < 720);
    modal.dataset.columns = "2";
    panel.style.setProperty("--squad-panel-height", `${Math.round(target)}px`);
    panel.style.setProperty("--squad-panel-width", "1120px");
    list.style.setProperty("--lineup-columns", "2");
    list.style.setProperty("--lineup-row-height", `${rowHeight}px`);
    list.style.setProperty("--lineup-row-gap", `${rowGap}px`);
    list.style.setProperty("--squad-list-height", `${Math.round(listHeight)}px`);
  }

  function renderLineupList(container, players) {
    if (!container) return;
    const signature = JSON.stringify({ language: overlayLanguage, players: players || [] });
    if (container.dataset.signature === signature) return;
    container.dataset.signature = signature;
    container.innerHTML = "";
    (players || []).forEach(player => {
      const row = document.createElement("div");
      row.className = "lineup-row";
      const number = document.createElement("div");
      number.className = "lineup-number";
      number.textContent = player.number || "—";
      const name = document.createElement("div");
      name.className = "lineup-name";
      const firstName = document.createElement("span");
      firstName.className = "lineup-first-name";
      firstName.textContent = player.first_name || "";
      const lastName = document.createElement("strong");
      lastName.className = "lineup-last-name";
      lastName.textContent = player.last_name || "";
      name.append(firstName);
      if (firstName.textContent && lastName.textContent) name.append(document.createTextNode(" "));
      name.append(lastName);
      if (!firstName.textContent && !lastName.textContent) name.textContent = player.name || "";
      if (player.captain) {
        const captain = document.createElement("span");
        captain.className = "lineup-captain";
        captain.textContent = " C";
        name.appendChild(captain);
      }
      const position = document.createElement("div");
      position.className = "lineup-position";
      position.textContent = translatePosition(player.position || "");
      row.append(number, name, position);
      container.appendChild(row);
    });
  }

  function createStarterCard(player, slotClass) {
    const card = document.createElement("div");
    card.className = `starter-card ${slotClass}`;
    if (!player) { card.classList.add("empty"); return card; }

    const badge = document.createElement("div");
    badge.className = "starter-number-badge";

    const number = document.createElement("span");
    number.className = "starter-number";
    number.textContent = player.number || "—";
    badge.appendChild(number);

    const surname = document.createElement("div");
    surname.className = "starter-name";
    const surnameText = document.createElement("span");
    surnameText.textContent = player.last_name || player.name || player.first_name || "";
    surname.appendChild(surnameText);
    if (player.captain) {
      const captain = document.createElement("span");
      captain.className = "starter-captain";
      captain.textContent = " C";
      surname.appendChild(captain);
    }

    card.append(badge, surname);
    return card;
  }

  function renderStartingFormation(container, starters, sportMode = "floorball") {
    if (!container) return;
    const mode = sportMode === "handball" ? "handball" : "floorball";
    const signature = JSON.stringify({ mode, starters: starters || {} });
    if (container.dataset.signature === signature) return;
    container.dataset.signature = signature;
    container.dataset.sportMode = mode;
    container.innerHTML = "";
    if (mode === "handball") {
      const front = document.createElement("div"); front.className = "formation-row handball-front-row";
      front.append(
        createStarterCard(starters.left_wing, "wing"),
        createStarterCard(starters.pivot, "pivot"),
        createStarterCard(starters.right_wing, "wing")
      );
      const back = document.createElement("div"); back.className = "formation-row handball-back-row";
      back.append(
        createStarterCard(starters.left_back, "back"),
        createStarterCard(starters.center_back, "centre"),
        createStarterCard(starters.right_back, "back")
      );
      const gk = document.createElement("div"); gk.className = "formation-row goalkeeper-row";
      gk.append(createStarterCard(starters.goalkeeper, "goalkeeper"));
      container.append(front, back, gk);
      return;
    }
    const forwards = document.createElement("div"); forwards.className = "formation-row forwards-row";
    forwards.append(
      createStarterCard(starters.forward_left, "forward"),
      createStarterCard(starters.forward_right, "forward")
    );
    const centre = document.createElement("div"); centre.className = "formation-row centre-row";
    centre.append(createStarterCard(starters.centre, "centre"));
    const def = document.createElement("div"); def.className = "formation-row defenders-row";
    def.append(
      createStarterCard(starters.defender_left, "defender"),
      createStarterCard(starters.defender_right, "defender")
    );
    const gk = document.createElement("div"); gk.className = "formation-row goalkeeper-row";
    gk.append(createStarterCard(starters.goalkeeper, "goalkeeper"));
    container.append(forwards, centre, def, gk);
  }

  function renderScorerSide(id, info) {
    const side=safeGet(id); if(!side) return;
    const scorerColor = info?.team_color || "#333333";
    side.style.setProperty("--scorer-color", scorerColor);
    const color=side.querySelector(".scorer-color"); if(color) color.style.backgroundColor=scorerColor;
    const logo=side.querySelector(".scorer-team-logo"); if(logo) setSrcIfChanged(logo,info?.team_logo||"");
    const team=side.querySelector(".scorer-team-name"); if(team) setTextIfChanged(team,info?.team_name||"");
    const player=side.querySelector(".scorer-player-name"); if(player) setTextIfChanged(player,info?.player_name||"—");
    const prefix = id === "top-team1" ? "home" : "away";
    ["goals", "assists", "points"].forEach(k => {
      document.querySelectorAll(`.${prefix}-${k}`).forEach(el => setTextIfChanged(el, String(info?.[k] ?? 0)));
    });
    const panel = topScorersModal?.querySelector(".scorer-prematch-panel");
    if (panel) panel.style.setProperty(prefix === "home" ? "--home-scorer-color" : "--away-scorer-color", scorerColor);
  }

  function renderStandings(rows) {
    if(!standingsRows) return;
    const signature=JSON.stringify(rows||[]); if(standingsRows.dataset.signature===signature) return;
    standingsRows.dataset.signature=signature; standingsRows.innerHTML="";
    (rows||[]).forEach(row=>{
      const el=document.createElement("div"); el.className="standings-row";
      [row.position,row.team_name,row.played,row.goal_difference>0?`+${row.goal_difference}`:row.goal_difference,row.points].forEach((v,i)=>{const s=document.createElement("span");s.textContent=v??"";if(i===1)s.className="standing-team";el.appendChild(s);});
      standingsRows.appendChild(el);
    });
  }

  function getCalculatedMatchScore(data) {
    const events = Array.isArray(data?.intermission?.events) ? data.intermission.events : [];
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const score = String(events[index]?.score || "").trim();
      const match = score.match(/^(\d+)\s*[–—-]\s*(\d+)$/);
      if (match) return `${match[1]} - ${match[2]}`;
    }
    return "0 - 0";
  }

  function updateFromJSON(data) {
    if (data?.overlay_settings) {
      data.overlay_settings.sport_mode = data.match?.sport_mode || data.overlay_settings.sport_mode;
      applyOverlayAppearance(data.overlay_settings);
    }
    const lineups = data.statistics?.lineups || {};
    const team1Now = lineups.team1_status === true || lineups.team1_status === "true" || lineups.team1_status === 1;
    const team2Now = lineups.team2_status === true || lineups.team2_status === "true" || lineups.team2_status === 1;
    if (team1Now !== prevStatus.lineupsTeam1) {
      triggerAnimation(lineupsTeam1Modal, team1Now ? "show" : "hide");
      if (team1Now) startLineupSequence(lineupsTeam1Modal);
      else clearLineupSequence(lineupsTeam1Modal);
      prevStatus.lineupsTeam1 = team1Now;
    }
    if (team2Now !== prevStatus.lineupsTeam2) {
      triggerAnimation(lineupsTeam2Modal, team2Now ? "show" : "hide");
      if (team2Now) startLineupSequence(lineupsTeam2Modal);
      else clearLineupSequence(lineupsTeam2Modal);
      prevStatus.lineupsTeam2 = team2Now;
    }
    if (lineupsTitle1) setTextIfChanged(lineupsTitle1, lineups.title || t("ALINEACIONES", "LINEUPS"));
    if (lineupsTitle2) setTextIfChanged(lineupsTitle2, lineups.title || t("ALINEACIONES", "LINEUPS"));
    if (lineupsTeam1Name) setTextIfChanged(lineupsTeam1Name, lineups.team1_name || "HOME");
    if (lineupsTeam2Name) setTextIfChanged(lineupsTeam2Name, lineups.team2_name || "AWAY");
    if (lineupsCompetitionName1) setTextIfChanged(lineupsCompetitionName1, lineups.competition_name || "");
    if (lineupsCompetitionName2) setTextIfChanged(lineupsCompetitionName2, lineups.competition_name || "");
    if (lineupsCompetitionLogo1) setSrcIfChanged(lineupsCompetitionLogo1, lineups.competition_logo || "");
    if (lineupsCompetitionLogo2) setSrcIfChanged(lineupsCompetitionLogo2, lineups.competition_logo || "");
    if (lineupsTeam1Logo) setSrcIfChanged(lineupsTeam1Logo, lineups.team1_logo || "");
    if (lineupsTeam2Logo) setSrcIfChanged(lineupsTeam2Logo, lineups.team2_logo || "");
    const lineupColor1 = lineups.team1_color || "#333333";
    const lineupColor2 = lineups.team2_color || "#333333";
    if (lineupsTeam1Stripe) lineupsTeam1Stripe.style.backgroundColor = lineupColor1;
    if (lineupsTeam2Stripe) lineupsTeam2Stripe.style.backgroundColor = lineupColor2;
    if (lineupsTeam1Modal) lineupsTeam1Modal.style.setProperty("--lineup-color", lineupColor1);
    if (lineupsTeam2Modal) lineupsTeam2Modal.style.setProperty("--lineup-color", lineupColor2);

    if (lineupsTeam1Starting) {
      lineupsTeam1Starting.style.setProperty("--team-color", lineups.team1_color || "#333333");
      lineupsTeam1Starting.style.setProperty("--team-secondary-color", lineups.team1_number_color || lineups.team1_secondary_color || "#FFFFFF");
      lineupsTeam1Starting.style.setProperty("--formation-logo", lineups.team1_logo ? `url("${lineups.team1_logo}")` : "none");
    }
    if (lineupsTeam2Starting) {
      lineupsTeam2Starting.style.setProperty("--team-color", lineups.team2_color || "#333333");
      lineupsTeam2Starting.style.setProperty("--team-secondary-color", lineups.team2_number_color || lineups.team2_secondary_color || "#FFFFFF");
      lineupsTeam2Starting.style.setProperty("--formation-logo", lineups.team2_logo ? `url("${lineups.team2_logo}")` : "none");
    }

    renderStartingFormation(lineupsTeam1Starting, lineups.team1_starters || {}, data.match?.sport_mode || "floorball");
    renderStartingFormation(lineupsTeam2Starting, lineups.team2_starters || {}, data.match?.sport_mode || "floorball");
    const team1Players = lineups.team1_players || [];
    const team2Players = lineups.team2_players || [];
    renderLineupList(lineupsTeam1List, team1Players);
    renderLineupList(lineupsTeam2List, team2Players);
    const team1Coaches = lineups.team1_coaches || [];
    const team2Coaches = lineups.team2_coaches || [];
    renderCoach(lineupsTeam1Coach, team1Coaches);
    renderCoach(lineupsTeam2Coach, team2Coaches);
    updateDynamicSquadHeight(lineupsTeam1Modal, team1Players.length, Array.isArray(team1Coaches) && team1Coaches.length > 0);
    updateDynamicSquadHeight(lineupsTeam2Modal, team2Players.length, Array.isArray(team2Coaches) && team2Coaches.length > 0);
    if (!data) return;
    prevJson = data; // keep reference (not deep clone)

    // Scoreboard: names, logos, stripes, text colors (but NOT scores/time - those come from .txt)
    if (team1Name) setInputValueIfChanged(team1Name, data.team1?.name || "");
    if (team2Name) setInputValueIfChanged(team2Name, data.team2?.name || "");
    if (team1Name) team1Name.style.color = data.team1?.text_color || "white";
    if (team2Name) team2Name.style.color = data.team2?.text_color || "white";
    if (team1Logo) setSrcIfChanged(team1Logo, data.team1?.logo || "");
    if (team2Logo) setSrcIfChanged(team2Logo, data.team2?.logo || "");
    if (team1Bar) team1Bar.style.backgroundColor = data.team1?.stripe_color || "#000";
    if (team2Bar) team2Bar.style.backgroundColor = data.team2?.stripe_color || "#000";
    if (leagueLogo) setSrcIfChanged(leagueLogo, data.match?.logo || "");
    const manual = data.overlay_settings?.score_control?.mode === "manual";
    document.body.classList.toggle("manual-score-mode", manual);
    const clockPeriod = safeGet("clock-period");
    if (clockPeriod) { clockPeriod.hidden = !periodStripConfig.show_number; clockPeriod.textContent = `${Math.max(1, Number(data.match?.period || 1))}${manual ? "" : " · "}`; }
    if (periodStrip) {
      const activePeriod = Math.max(1, Math.min(periodStripConfig.segments, Number(data.match?.period || 1)));
      periodStrip.querySelectorAll("[data-period-index]").forEach((segment) => segment.classList.toggle("active", Number(segment.dataset.periodIndex) <= activePeriod));
    }

    // Animations (show/hide scoreboard)
    const animNow = data.animation?.status;
    if (animNow !== prevStatus.anim) {
      triggerAnimation(wrapper, animNow === "show" ? "visible" : "hidden");
      prevStatus.anim = animNow;
    }

    // Bottom bar: identidad de equipo + estado del partido + gol/asistencia.
    if (bottomBar) {
      const bar = data.bottombar || {};
      goalGraphicScores = bar.graphic_scores || null;
      graphicScores = data.graphic_scores || null;
      if (intermissionTeam1Score) setTextIfChanged(intermissionTeam1Score, graphicScores?.team1_score ?? prevTxt.home);
      if (intermissionTeam2Score) setTextIfChanged(intermissionTeam2Score, graphicScores?.team2_score ?? prevTxt.away);
      bottomBar.classList.toggle("show", bar.status === "show");
      const stateTeamColor = bar.team_key === "team2"
        ? data.team2?.stripe_color
        : bar.team_key === "team1" ? data.team1?.stripe_color : "";
      // The goal payload is the source of truth. This is especially important
      // for the visitor, whose lower third must use its visitor/secondary colour.
      const teamColor = bar.team_color || stateTeamColor || "#555b66";
      bottomBar.dataset.team = bar.team_key || "";
      bottomBar.style.setProperty("--bottom-team-color", teamColor);
      if (bottomTeamBlock) bottomTeamBlock.style.setProperty("--bottom-team-color", teamColor);
      if (bottomTeamLogo) setSrcIfChanged(bottomTeamLogo, bar.team_logo || "");
      // Formato fijo: #DORSAL APELLIDOS (GOLES EN EL PARTIDO).
      if (bottomScorerNumber) setTextIfChanged(bottomScorerNumber, bar.scorer_number ? `#${bar.scorer_number}` : "");
      if (bottomScorerName) setTextIfChanged(bottomScorerName, bar.scorer_last_name || bar.scorer || "");
      const goalCount = Math.max(1, Number(bar.scorer_match_goals || 1));
      if (bottomGoalCount) setTextIfChanged(bottomGoalCount, `(${goalCount})`);
      if (bottomAssistantNumber) setTextIfChanged(bottomAssistantNumber, bar.assistant_number ? `#${bar.assistant_number}` : "");
      if (bottomAssistantName) setTextIfChanged(bottomAssistantName, bar.assistant_last_name || bar.assistant || "");
      const hasAssistant = Boolean(bar.assistant_last_name || bar.assistant || bar.assistant_number);
      if (bottomAssistantRow) {
        bottomAssistantRow.hidden = !hasAssistant;
        bottomAssistantRow.classList.toggle("has-assistant", hasAssistant);
      }
      bottomBar.classList.toggle("no-assistant", !hasAssistant);
      if (bottomMatchTime) setTextIfChanged(bottomMatchTime, prevTxt.time || "00:00");
      if (bottomCurrentScore) setTextIfChanged(bottomCurrentScore, `${goalGraphicScores?.team1_score ?? prevTxt.home ?? "0"}–${goalGraphicScores?.team2_score ?? prevTxt.away ?? "0"}`);
    }


    const profile = data.statistics?.player_profile || {};
    const profileShow = profile.status === true || profile.status === "true" || profile.status === 1;
    if (playerProfileBar && profileShow !== prevStatus.playerProfile) {
      playerProfileBar.classList.toggle("show", profileShow);
      prevStatus.playerProfile = profileShow;
    }
    if (playerProfileBar) {
      const profileColor = profile.team_color || "#59606c";
      playerProfileBar.style.setProperty("--profile-team-color", profileColor);
      if (playerProfileTeamBlock) playerProfileTeamBlock.style.setProperty("--profile-team-color", profileColor);
      if (playerProfileTeamLogo) setSrcIfChanged(playerProfileTeamLogo, profile.team_logo || "");
      if (playerProfileNumber) setTextIfChanged(playerProfileNumber, profile.number ? `#${profile.number}` : "#—");
      if (playerProfileName) setTextIfChanged(playerProfileName, profile.name || "JUGADOR");
      if (playerProfileBirth) setTextIfChanged(playerProfileBirth, profile.birth_date || "—");
      if (playerProfileNationality) setTextIfChanged(playerProfileNationality, profile.nationality || "—");
      if (playerProfilePosition) setTextIfChanged(playerProfilePosition, translatePosition(profile.position) || "—");
      if (playerProfilePlayed) setTextIfChanged(playerProfilePlayed, String(profile.played ?? 0));
      if (playerProfileGoals) setTextIfChanged(playerProfileGoals, String(profile.goals ?? 0));
      if (playerProfileAssists) setTextIfChanged(playerProfileAssists, String(profile.assists ?? 0));
    }

    const top=data.statistics?.top_scorers||{};
    const topShow=top.status===true||top.status==="true"||top.status===1;
    if(topScorersModal && topShow !== prevStatus.topScorers) { triggerAnimation(topScorersModal,topShow?"show":"hide"); prevStatus.topScorers=topShow; }
    if(topScorersLogo) setSrcIfChanged(topScorersLogo,top.competition_logo||"");
    if(topScorersCompetition) setTextIfChanged(topScorersCompetition,top.competition_name||"");
    // Fuerza la misma identidad visual del scoreboard, también si data.json
    // conserva una comparativa generada antes de corregir el color visitante.
    const homeScorerInfo = {
      ...(top.team1 || {}),
      team_color: data.team1?.stripe_color || data.team1?.primary_color || top.team1?.team_color || "#333333"
    };
    const awayScorerInfo = {
      ...(top.team2 || {}),
      team_color: data.team2?.stripe_color || data.team2?.secondary_color || data.team2?.primary_color || top.team2?.team_color || "#333333"
    };
    renderScorerSide("top-team1", homeScorerInfo);
    renderScorerSide("top-team2", awayScorerInfo);

    const standings=data.statistics?.standings||{};
    const standShow=standings.status===true||standings.status==="true"||standings.status===1;
    if(standingsModal && standShow !== prevStatus.standings) { triggerAnimation(standingsModal,standShow?"show":"hide"); prevStatus.standings=standShow; }
    if(standingsLogo) setSrcIfChanged(standingsLogo,standings.competition_logo||"");
    if(standingsCompetition) setTextIfChanged(standingsCompetition,standings.competition_name||"");
    if (standingsModal) {
      const standingsPanel = standingsModal.querySelector(".standings-panel");
      if (standingsPanel) {
        standingsPanel.style.setProperty("--stats-home-color", data.team1?.stripe_color || data.team1?.primary_color || "#3b82f6");
        standingsPanel.style.setProperty("--stats-away-color", data.team2?.stripe_color || data.team2?.secondary_color || data.team2?.primary_color || "#ef4444");
      }
    }
    renderStandings(standings.rows||[]);

    // Simultaneous penalties are rendered as a vertical queue. When the first
    // penalty expires (or is burned by a floorball PP goal), the next one
    // naturally becomes index 0 and moves into the top position.
    const pp1Info = data.powerplay?.team1 || {};
    const pp2Info = data.powerplay?.team2 || {};
    renderTeamStatusStack(ppStack1, pp1Info, data.empty_net?.team1, "team1");
    renderTeamStatusStack(ppStack2, pp2Info, data.empty_net?.team2, "team2");
    prevStatus.pp1 = Boolean(activePenaltyItems(pp1Info).length);
    prevStatus.pp2 = Boolean(activePenaltyItems(pp2Info).length);

    // Intermission modal visibility (status)
    const penaltyData = data.penalty_shootout || {};
    const penaltiesNow = !!penaltyData.status;
    if (penaltiesNow !== prevStatus.penalties) {
      triggerAnimation(penaltiesModal, penaltiesNow ? "show" : "hide");
      prevStatus.penalties = penaltiesNow;
    }
    if (penaltiesModal) {
      const homeColor = normalizeOverlayColor(
        data.team1?.stripe_color || data.team1?.primary_color || data.team1?.secondary_color,
        "#315c9b"
      );
      const awayColor = normalizeOverlayColor(
        data.team2?.stripe_color || data.team2?.secondary_color || data.team2?.primary_color,
        "#8a3546"
      );
      penaltiesModal.style.setProperty("--pen-home-color", homeColor);
      penaltiesModal.style.setProperty("--pen-away-color", awayColor);
      const compact = window.matchMedia("(max-width: 900px)").matches;
      const squareWidth = compact ? 68 : 84;
      applyPenaltyTeamColor(penaltiesHomeRow, penaltiesTeam1LogoBox, homeColor, squareWidth);
      applyPenaltyTeamColor(penaltiesAwayRow, penaltiesTeam2LogoBox, awayColor, squareWidth);
    }
    if (penaltiesLeagueLogo) setSrcIfChanged(penaltiesLeagueLogo, data.match?.logo || "");
    if (penaltiesTeam1Logo) setSrcIfChanged(penaltiesTeam1Logo, data.team1?.logo || "");
    if (penaltiesTeam2Logo) setSrcIfChanged(penaltiesTeam2Logo, data.team2?.logo || "");
    if (penaltiesTeam1Name) setTextIfChanged(penaltiesTeam1Name, data.team1?.name || t("LOCAL", "HOME"));
    if (penaltiesTeam2Name) setTextIfChanged(penaltiesTeam2Name, data.team2?.name || t("VISITANTE", "AWAY"));
    renderPenaltyAttempts(penaltiesTeam1Attempts, penaltyData.team1);
    renderPenaltyAttempts(penaltiesTeam2Attempts, penaltyData.team2);

    const interNow = !!(data.intermission?.status);
    if (interNow !== prevStatus.intermission) {
      triggerAnimation(intermissionModal, interNow ? "show" : "hide");
      if (interNow) requestAnimationFrame(() => requestAnimationFrame(syncIntermissionColumnHeights));
      else {
        stopIntermissionAutoScroll(intermissionEventsHomeViewport);
        stopIntermissionAutoScroll(intermissionEventsAwayViewport);
      }
      prevStatus.intermission = interNow;
    }

    // Intermission content. Scores still come from TXT; events come from Supabase via data.json.
    const intermissionHomeColor = data.team1?.stripe_color || "#252832";
    const intermissionAwayColor = data.team2?.stripe_color || "#252832";
    if (intermissionTeam1Stripe) intermissionTeam1Stripe.style.backgroundColor = intermissionHomeColor;
    if (intermissionTeam2Stripe) intermissionTeam2Stripe.style.backgroundColor = intermissionAwayColor;
    const intermissionHomeSide = document.querySelector(".intermission-events-home");
    const intermissionAwaySide = document.querySelector(".intermission-events-away");
    if (intermissionHomeSide) intermissionHomeSide.style.setProperty("--team-event-color", intermissionHomeColor);
    if (intermissionAwaySide) intermissionAwaySide.style.setProperty("--team-event-color", intermissionAwayColor);
    if (intermissionTeam1Logo) setSrcIfChanged(intermissionTeam1Logo, data.team1?.logo || "");
    if (intermissionTeam2Logo) setSrcIfChanged(intermissionTeam2Logo, data.team2?.logo || "");
    if (intermissionTeam1Name) {
      setTextIfChanged(intermissionTeam1Name, data.team1?.name || "");
      intermissionTeam1Name.style.color = "#FFFFFF";
    }
    if (intermissionTeam2Name) {
      setTextIfChanged(intermissionTeam2Name, data.team2?.name || "");
      intermissionTeam2Name.style.color = "#FFFFFF";
    }
    if (intermissionEventsHomeTitle) {
      intermissionEventsHomeTitle.style.color = data.team1?.alternate_text_color || "#FFFFFF";
    }
    if (intermissionEventsAwayTitle) {
      intermissionEventsAwayTitle.style.color = data.team2?.alternate_text_color || "#FFFFFF";
    }
    renderIntermissionEvents(data.intermission?.events || [], data.team1?.name, data.team2?.name);
    if (intermissionLeagueLogo) setSrcIfChanged(intermissionLeagueLogo, data.match?.logo || "");

    // Prematch modal: show/hide and content
    const pmNow = !!(data.prematch?.status);
    if (pmNow !== prevStatus.prematch) {
      triggerAnimation(prematchModal, pmNow ? "show" : "hide");
      prevStatus.prematch = pmNow;
    }

    if (prematchTeam1Text) setTextIfChanged(prematchTeam1Text, data.prematch?.team1_text || "");
    if (prematchTeam2Text) setTextIfChanged(prematchTeam2Text, data.prematch?.team2_text || "");
    if (prematchLeagueName) setTextIfChanged(prematchLeagueName, data.prematch?.league_name || "");
    if (prematchLeagueLogo) setSrcIfChanged(prematchLeagueLogo, data.match?.logo || "");

    const pmHomeColor = data.team1?.stripe_color || data.team1?.primary_color || "#2c72d6";
    const pmAwayColor = data.team2?.stripe_color || data.team2?.secondary_color || data.team2?.primary_color || "#d92929";
    if (pmTeam1Stripe) pmTeam1Stripe.style.backgroundColor = pmHomeColor;
    if (pmTeam2Stripe) pmTeam2Stripe.style.backgroundColor = pmAwayColor;
    if (prematchModal) {
      const panel = prematchModal.querySelector(".prematch-panel");
      if (panel) {
        panel.style.setProperty("--home-color", pmHomeColor);
        panel.style.setProperty("--away-color", pmAwayColor);
      }
    }
    if (pmTeam1Logo) setSrcIfChanged(pmTeam1Logo, data.team1?.logo || "");
    if (pmTeam2Logo) setSrcIfChanged(pmTeam2Logo, data.team2?.logo || "");
    if (pmTeam1Name) setTextIfChanged(pmTeam1Name, data.team1?.name || "");
    if (pmTeam2Name) setTextIfChanged(pmTeam2Name, data.team2?.name || "");
    // prematch scores (if you want them to reflect last known JSON scores)
    if (pmTeam1Score) setTextIfChanged(pmTeam1Score, String(data.team1?.score ?? ""));
    if (pmTeam2Score) setTextIfChanged(pmTeam2Score, String(data.team2?.score ?? ""));

    // Prematch stats (container or individual cells)
    const nested = !!(data.prematch && data.prematch.team1 && data.prematch.team2);
    if (prematchTeam1Stats || prematchTeam2Stats) {
      if (prematchTeam1Stats) {
        if (nested) {
          prematchTeam1Stats.innerHTML = `
            ${t("Posición", "Position")}: ${data.prematch.team1.position || "-"}<br>
            ${t("Puntos", "Points")}: ${data.prematch.team1.points || "-"}<br>
            ${t("Victorias", "Wins")}: ${data.prematch.team1.wins || "-"}<br>
            ${t("Goles a favor", "Goals for")}: ${data.prematch.team1.goals_for || "-"}<br>
            ${t("Goles en contra", "Goals against")}: ${data.prematch.team1.goals_against || "-"}
          `;
        } else {
          prematchTeam1Stats.innerHTML = `
            ${t("Posición", "Position")}: ${data.prematch?.team1_position || "-"}<br>
            ${t("Puntos", "Points")}: ${data.prematch?.team1_points || "-"}<br>
            ${t("Victorias", "Wins")}: ${data.prematch?.team1_wins || "-"}<br>
            ${t("Goles a favor", "Goals for")}: ${data.prematch?.team1_goals_for || "-"}<br>
            ${t("Goles en contra", "Goals against")}: ${data.prematch?.team1_goals_against || "-"}
          `;
        }
      }
      if (prematchTeam2Stats) {
        if (nested) {
          prematchTeam2Stats.innerHTML = `
            ${t("Posición", "Position")}: ${data.prematch.team2.position || "-"}<br>
            ${t("Puntos", "Points")}: ${data.prematch.team2.points || "-"}<br>
            ${t("Victorias", "Wins")}: ${data.prematch.team2.wins || "-"}<br>
            ${t("Goles a favor", "Goals for")}: ${data.prematch.team2.goals_for || "-"}<br>
            ${t("Goles en contra", "Goals against")}: ${data.prematch.team2.goals_against || "-"}
          `;
        } else {
          prematchTeam2Stats.innerHTML = `
            ${t("Posición", "Position")}: ${data.prematch?.team2_position || "-"}<br>
            ${t("Puntos", "Points")}: ${data.prematch?.team2_points || "-"}<br>
            ${t("Victorias", "Wins")}: ${data.prematch?.team2_wins || "-"}<br>
            ${t("Goles a favor", "Goals for")}: ${data.prematch?.team2_goals_for || "-"}<br>
            ${t("Goles en contra", "Goals against")}: ${data.prematch?.team2_goals_against || "-"}
          `;
        }
      }
    } else {
      const fields = ["position", "points", "wins", "goals_for", "goals_against"];
      fields.forEach(f => {
        const v1 = getPrematchVal(data, "team1", f) ?? "-";
        const v2 = getPrematchVal(data, "team2", f) ?? "-";
        if (pmCells.team1[f]) setTextIfChanged(pmCells.team1[f], v1);
        if (pmCells.team2[f]) setTextIfChanged(pmCells.team2[f], v2);
      });
    }

    if (prematchVenue) setTextIfChanged(prematchVenue, data.prematch?.venue || "");
    if (prematchKickoff) {
      const rawKickoff = String(data.prematch?.kickoff || "").trim();
      const timeMatch = rawKickoff.match(/(?:^|\s)([01]?\d|2[0-3]):[0-5]\d(?:\s*h)?(?:$|\s)/i);
      setTextIfChanged(prematchKickoff, timeMatch ? timeMatch[0].trim().replace(/\s*h$/i, "h") : rawKickoff);
    }

    // Dynamic rendering can replace labels after a language switch. Reapply
    // the selected language at the end of each state update.
    applyOverlayLanguage(overlayLanguage);
  }

  // Settings are independent from match state: language and graphic palette.
  refreshOverlaySettings();
  setInterval(refreshOverlaySettings, 1200);

  // -------------------- Poll JSON + TXT (main loop) --------------------
  const POLL_MS = 250;
  setInterval(() => {
    // 1) data.json (non-score fields)
    fetch(overlayDataURL, { cache: "no-store" })
      .then(res => res.ok ? res.json() : null)
      .then(j => {
        if (j) updateFromJSON(j);
      })
      .catch(err => console.error("JSON fetch error:", err));

    // 2) TXT scores + timer (SOURCE OF TRUTH for score/time to avoid flicker)
    Promise.all([
      fetch(`scores/Home Score.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => ""),
      fetch(`scores/Away Score.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => ""),
      fetch(`scores/Time.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => "")
    ]).then(([t1, t2, t]) => {
      const homeScore = (t1 ?? "").trim();
      const awayScore = (t2 ?? "").trim();
      const matchTime = (t ?? "").trim();

      // Only update DOM when actual data changed (prevents flicker)
      if (prevTxt.home !== homeScore) {
        if (team1Score && document.activeElement !== team1Score) team1Score.value = homeScore;
        if (intermissionTeam1Score) setTextIfChanged(intermissionTeam1Score, graphicScores?.team1_score ?? homeScore);
        prevTxt.home = homeScore;
      }
      if (prevTxt.away !== awayScore) {
        if (team2Score && document.activeElement !== team2Score) team2Score.value = awayScore;
        if (intermissionTeam2Score) setTextIfChanged(intermissionTeam2Score, graphicScores?.team2_score ?? awayScore);
        prevTxt.away = awayScore;
      }
      if (prevTxt.time !== matchTime) {
        if (timeDiv) setTextIfChanged(timeDiv, matchTime);
        prevTxt.time = matchTime;
      }
      if (bottomMatchTime) setTextIfChanged(bottomMatchTime, matchTime || "00:00");
    }).catch(err => {
      console.error("TXT fetch error:", err);
    });

  }, POLL_MS);

  // Initial load
  fetch(overlayDataURL, { cache: "no-store" })
    .then(res => res.ok ? res.json() : null)
    .then(j => { if (j) updateFromJSON(j); })
    .catch(() => {});
  // Also populate scores immediately
  Promise.all([
    fetch(`scores/Home Score.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => ""),
    fetch(`scores/Away Score.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => ""),
    fetch(`scores/Time.txt?_=${Date.now()}`, { cache: "no-store" }).then(r => r.text()).catch(() => "")
  ]).then(([t1, t2, t]) => {
    prevTxt.home = (t1 ?? "").trim();
    prevTxt.away = (t2 ?? "").trim();
    prevTxt.time = (t ?? "").trim();
    if (team1Score && document.activeElement !== team1Score) team1Score.value = prevTxt.home;
    if (team2Score && document.activeElement !== team2Score) team2Score.value = prevTxt.away;
    if (timeDiv) setTextIfChanged(timeDiv, prevTxt.time);
    if (intermissionTeam1Score) setTextIfChanged(intermissionTeam1Score, graphicScores?.team1_score ?? prevTxt.home);
    if (intermissionTeam2Score) setTextIfChanged(intermissionTeam2Score, graphicScores?.team2_score ?? prevTxt.away);
    if (bottomMatchTime) setTextIfChanged(bottomMatchTime, prevTxt.time || "00:00");
    if (bottomCurrentScore) setTextIfChanged(bottomCurrentScore, `${goalGraphicScores?.team1_score ?? prevTxt.home ?? "0"}–${goalGraphicScores?.team2_score ?? prevTxt.away ?? "0"}`);
  }).catch(() => {});

  window.addEventListener("resize", () => {
    if (intermissionModal?.classList.contains("show")) {
      requestAnimationFrame(syncIntermissionColumnHeights);
    }
  });

}); // DOMContentLoaded end
