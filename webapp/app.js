const app = {
  snapshot: null,
  players: { team1: [], team2: [] },
  starters: { team1: {}, team2: {} },
  starterTeam: "team1",
  rosterSignature: "",
  socket: null,
  reconnectTimer: null,
  liveTimer: null,
  liveBusy: false,
  fallbackTimer: null,
  ocrRegions: {},
  activeOCRField: "team1_score",
  ocrDrag: null,
  ocrDirty: false,
  ocrPerspective: { enabled: false, points: {
    top_left: { x: 0, y: 0 }, top_right: { x: 1, y: 0 },
    bottom_right: { x: 1, y: 1 }, bottom_left: { x: 0, y: 1 },
  } },
  ocrPerspectiveEdit: false,
  ocrPerspectiveDraft: [],
  goalTeam: "team1",
  activeView: "live",
  previousView: "live",
  obsSceneSignature: "",
  obsTimer: null,
  visualState: { homeScore: null, awayScore: null, clock: null, ppHome: null, ppAway: null },
  productionFlow: {
    kind: "",
    team: "",
    step: "",
    penaltyType: "",
    scorerId: "",
    offenderId: "",
  },
  appearanceDraft: null,
  appearanceDirty: false,
  language: "en",
  graphicsPreviewCue: "",
  replayComposer: { clipId: "", goalFlow: false, segments: [] },
  sequenceDraft: { id: "", steps: [] },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const SHORTCUT_FIELDS = {
  scoreboard: "#shortcut-scoreboard",
  prematch: "#shortcut-prematch",
  intermission: "#shortcut-intermission",
  lineups_home: "#shortcut-lineups-home",
  lineups_away: "#shortcut-lineups-away",
  top_scorers: "#shortcut-top-scorers",
  standings: "#shortcut-standings",
  bottom_bar: "#shortcut-bottom-bar",
  penalties: "#shortcut-penalties",
  hide_all: "#shortcut-hide-all",
};


const DEFAULT_APPEARANCE = {
  app_theme: "system",
  scoreboard: { background: "#2a2d34", name_box: "#3b3f47", text: "#ffffff" },
  bottom_bar: { body: "#24272e", middle: "#30333b", text: "#ffffff", secondary_text: "#c6cad2" },
  panels: { background: "#171c25", surface: "#232a35", accent: "#59606c", text: "#ffffff" },
};


const APP_TRANSLATIONS = {
  "Idioma y tema": "Language and theme",
  "Colores del overlay": "Overlay colours",
  "Restablecer overlay": "Reset overlay",
  "Tiempo y resultado": "Time and score",
  "Guardar configuración": "Save settings",
  "Configuración local": "Local settings",
  "Directo": "Live",
  "Motor local": "Local engine",
  "Online conectado": "Online connected",
  "Modo local": "Local mode",
  "OCR activo": "OCR active",
  "OCR detenido": "OCR stopped",
  "OCR pendiente": "OCR pending",
  "OBS conectado": "OBS connected",
  "OBS desconectado": "OBS disconnected",
  "Emisión limpia": "Clean output",
  "Sin paneles a pantalla completa": "No full-screen panels",
  "Realización": "Production",
  "Equipo": "Team",
  "Estadísticas": "Statistics",
  "Configuración": "Settings",
  "Partido actual": "Current match",
  "Seleccionar partido": "Select match",
  "Control operativo del partido y de los gráficos en emisión.": "Match and on-air graphics control.",
  "Vista de gráficos": "Graphics preview",
  "Marcador": "Scoreboard",
  "Fuente del resultado": "Score source",
  "Manual": "Manual",
  "Registrar gol local": "Register home goal",
  "Registrar gol visitante": "Register away goal",
  "Expulsiones": "Penalties",
  "Eventos registrados": "Recorded events",
  "Todavía no hay eventos registrados para este partido.": "No events have been recorded for this match yet.",
  "Accesos rápidos": "Quick controls",
  "UNA PULSACIÓN": "ONE PRESS",
  "GRÁFICOS Y EVENTOS": "GRAPHICS & EVENTS",
  "GRÁFICOS ACTIVOS": "ACTIVE GRAPHICS",
  "Ninguno": "None",
  "Alineación local": "Home lineup",
  "Alineación visitante": "Away lineup",
  "Puntuadores": "Top scorers",
  "Clasificación": "Standings",
  "Jugador local": "Home player",
  "Jugador visitante": "Away player",
  "Gol local": "Home goal",
  "Gol visitante": "Away goal",
  "Expulsión local": "Home penalty",
  "Expulsión visitante": "Away penalty",
  "Limpiar todo": "Clear all",
  "Preparación de partido": "Match preparation",
  "Plantilla, convocatoria y quinteto en un único flujo.": "Roster, call-up and starting five in one workflow.",
  "Guardar convocatoria": "Save call-up",
  "Quinteto inicial": "Starting five",
  "Siete inicial": "Starting seven",
  "Selección de titulares": "Starting lineup selection",
  "Selección de 7 titulares": "Seven-player starting lineup",
  "Actualizar fuentes": "Refresh sources",
  "Vídeo del marcador": "Scoreboard video",
  "Sin fuente seleccionada": "No source selected",
  "Selecciona una ventana o cámara, captura un preview y arrastra sobre cada valor del marcador.": "Select a window or camera, capture a preview and drag over each scoreboard value.",
  "Paneles de datos": "Data panels",
  "Actualiza la información deportiva y lánzala a emisión.": "Update sports information and send it on air.",
  "Actualizar estadísticas": "Refresh statistics",
  "Estadísticas de jugador": "Player statistics",
  "Mostrar ficha": "Show profile",
  "Ocultar ficha": "Hide profile",
  "Captura de marcador": "Scoreboard capture",
  "Selecciona la ventana, dibuja las regiones y controla el lector.": "Select the window, draw the areas and control the reader.",
  "Actualizar ventanas": "Refresh windows",
  "Iniciar OCR": "Start OCR",
  "Detener": "Stop",
  "Ventana del marcador": "Scoreboard window",
  "Capturar preview": "Capture preview",
  "Configuración visual": "Visual setup",
  "Selecciona Local, Tiempo o Visitante y dibuja directamente sobre la imagen. No necesitas editar coordenadas.": "Select Home, Time or Away and draw directly on the image. No coordinate editing is required.",
  "Guardar configuración": "Save settings",
  "Última lectura": "Latest reading",
  "Valores": "Values",
  "Preferencias": "Preferences",
  "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.": "Account, OBS, shortcuts, language and appearance in one screen.",
  "Configuración local": "Local settings",
  "Restablecer colores": "Reset colours",
  "General": "General",
  "Aplicación": "Application",
  "Idioma": "Language",
  "Tema de la aplicación": "Application theme",
  "Oscuro": "Dark",
  "Claro": "Light",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.": "Light mode only affects the application, never the overlay.",
  "Integración": "Integration",
  "Contraseña": "Password",
  "Proyector OBS": "OBS projector",
  "Conectar automáticamente": "Connect automatically",
  "Conectar OBS": "Connect OBS",
  "Desconectar": "Disconnect",
  "Control rápido": "Quick control",
  "Atajos de teclado": "Keyboard shortcuts",
  "Haz clic en un campo y pulsa la combinación": "Click a field and press the combination",
  "Máximos puntuadores": "Top scorers",
  "Limpiar emisión": "Clear broadcast",
  "Personalización": "Customisation",
  "Colores y previsualización": "Colours and preview",
  "POR CUENTA": "PER ACCOUNT",
  "Principal": "Primary",
  "Acento": "Accent",
  "Fondo": "Background",
  "Tarjetas": "Cards",
  "Texto": "Text",
  "Nombres": "Names",
  "Mesa de realización": "Production desk",
  "Tecla": "Key",
  "Tecla activa": "Active key",
  "Cuerpo": "Body",
  "Bloque central": "Centre block",
  "Texto secundario": "Secondary text",
  "Paneles del overlay": "Overlay panels",
  "Superficie": "Surface",
  "Configuración guardada.": "Settings saved.",
  "Configuración vinculada a": "Settings linked to",
  "Sin asistencia": "No assist",
  "Registrar gol": "Register goal",
  "Goleador": "Scorer",
  "Asistencia": "Assist",
  "Tiempo": "Time",
  "Cerrar sesión": "Log out",
  "Iniciar sesión": "Log in",
  "Correo electrónico": "Email",
  "Olvidé mi contraseña": "I forgot my password",
  "Mi cuenta": "My account",
  "Nombre visible": "Display name",
  "Protegida": "Protected",
  "La contraseña actual nunca puede consultarse. Sólo puede sustituirse por una nueva.": "The current password can never be viewed. It can only be replaced with a new one.",
  "Guardar perfil": "Save profile",
  "Eliminar foto": "Remove photo",
  "Seguridad": "Security",
  "Cambiar contraseña": "Change password",
  "Nueva contraseña": "New password",
  "Repetir contraseña": "Repeat password",
  "Actualizar contraseña": "Update password",
  "Cambiar foto de perfil": "Change profile picture",
};

Object.assign(APP_TRANSLATIONS, {
  "Broadcast control": "Broadcast control",
  "Monitor": "Monitor",
  "Vista previa del overlay": "Overlay preview",
  "Abre un proyector de programa en OBS para mostrar aquí la señal emitida.": "Open an OBS Program Projector to display the live output here.",
  "PROGRAMA": "PROGRAM",
  "PREVIEW": "PREVIEW",
  "Recargar preview": "Reload preview",
  "Partido": "Match",
  "FUENTE DEL RESULTADO": "SCORE SOURCE",
  "El resultado procede del marcador físico.": "The score comes from the physical scoreboard.",
  "Local": "Home",
  "Visitante": "Away",
  "LOCAL": "HOME",
  "VISITANTE": "AWAY",
  "Equipo local": "Home team",
  "Equipo visitante": "Away team",
  "Acta en vivo": "Live match log",
  "Actualizar": "Refresh",
  "Carga un partido online para registrar goles y asistencias.": "Load an online match to record goals and assists.",
  "Registrar gol": "Register goal",
  "Evento de partido": "Match event",
  "Incrementar también el resultado manual": "Also increase the manual score",
  "En modo OCR el gol se registra en el acta, pero no modifica el resultado.": "In OCR mode the goal is recorded but does not change the score.",
  "EXPULSIONES ACTIVAS": "ACTIVE PENALTIES",
  "Sanción": "Penalty",
  "Jugador convocado": "Called-up player",
  "Cumple 2 min": "Serves 2 min",
  "Mismo jugador": "Same player",
  "Selecciona jugador": "Select player",
  "Iniciar expulsión": "Start penalty",
  "Sin PP": "No PP",
  "Cancelar PP local": "Cancel home PP",
  "Cancelar PP visitante": "Cancel away PP",
  "El contador utiliza el reloj ascendente del OCR. Sólo pueden sancionarse jugadores de la convocatoria guardada.": "The timer uses the ascending OCR clock. Only called-up players can be penalised.",
  "Vista del directo": "Live output",
  "PROGRAMA OBS": "OBS PROGRAM",
  "Sin señal de programa": "No program signal",
  "Conecta OBS y selecciona una ventana de proyector.": "Connect OBS and select a projector window.",
  "TIEMPO OCR": "OCR TIME",
  "GRÁFICOS ACTIVOS": "ACTIVE GRAPHICS",
  "EXPULSIONES ACTIVAS": "ACTIVE PENALTIES",
  "Cancelar rápidamente": "Quick cancel",
  "Sin expulsión activa": "No active penalty",
  "Broadcast switcher": "Broadcast switcher",
  "Prepara y envía datos a emisión sin abandonar el contexto del partido.": "Prepare and send graphics on air without leaving the match context.",
  "Mostrar / ocultar": "Show / hide",
  "Mostrar / ocultar panel": "Show / hide panel",
  "Prematch": "Pre-match",
  "Intermission": "Intermission",
  "Alineaciones": "Lineups",
  "Panel de penaltis": "Penalty shootout panel",
  "Bottom bar": "Bottom bar",
  "Penaltis": "Penalty shootout",
  "Toda la convocatoria disponible.": "Full called-up roster available.",
  "Restablecer paneles": "Reset panels",
  "MASTER": "MASTER",
  "Emisión limpia": "Clean output",
  "Control de partido": "Match control",
  "Preparación de partido": "Match preparation",
  "Quinteto inicial, convocados y entrenador.": "Starting five, called-up players and coach.",
  "Carga un partido para ver la plantilla.": "Load a match to view the roster.",
  "Guardar convocatoria": "Save call-up",
  "Quinteto inicial": "Starting five",
  "POR": "GK",
  "DEF IZQ": "LEFT DEF",
  "DEF DER": "RIGHT DEF",
  "MED": "MID",
  "DEL IZQ": "LEFT FWD",
  "DEL DER": "RIGHT FWD",
  "Paneles de datos": "Data panels",
  "Contenido editorial": "Editorial content",
  "Actualizar desde Supabase": "Refresh from Supabase",
  "Comparativa de goles, asistencias y puntos.": "Goals, assists and points comparison.",
  "Posición, puntos, goles y diferencia.": "Position, points, goals and goal difference.",
  "Clasificación disponible": "Available standings",
  "Carga un partido online para obtener la clasificación.": "Load an online match to retrieve the standings.",
  "Ficha individual con partidos, goles, asistencias y datos personales.": "Individual profile with matches, goals, assists and personal details.",
  "Jugador": "Player",
  "Actualizar ficha": "Refresh profile",
  "Mostrar en emisión": "Show on air",
  "Ocultar": "Hide",
  "Sin ficha seleccionada": "No player profile selected",
  "Selecciona un jugador para consultar sus estadísticas.": "Select a player to view their statistics.",
  "Captura de marcador": "Scoreboard capture",
  "Selecciona la ventana, dibuja las regiones y controla el lector.": "Select the window, draw the areas and control the reader.",
  "Actualizar ventanas": "Refresh windows",
  "Iniciar OCR": "Start OCR",
  "Detener": "Stop",
  "Fuente": "Source",
  "Ventana del marcador": "Scoreboard window",
  "Capturar preview": "Capture preview",
  "Sin ventana seleccionada": "No window selected",
  "Captura un preview y arrastra sobre cada valor del marcador.": "Capture a preview and drag over each scoreboard value.",
  "OCR detenido": "OCR stopped",
  "El reloj y el resultado se actualizarán al iniciar.": "The clock and score will update when started.",
  "Lectura": "Reading",
  "Intervalo de lectura (ms)": "Reading interval (ms)",
  "Configuración visual": "Visual setup",
  "Selecciona Local, Tiempo o Visitante y dibuja directamente sobre la imagen. No necesitas editar coordenadas.": "Select Home, Time or Away and draw directly on the image. You do not need to edit coordinates.",
  "Guardar configuración": "Save settings",
  "Última lectura": "Latest reading",
  "Valores": "Values",
  "TIEMPO": "TIME",
  "Preferencias": "Preferences",
  "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.": "Account, OBS, shortcuts, language and appearance on one screen.",
  "Configuración local": "Local settings",
  "Restablecer colores": "Reset colours",
  "General": "General",
  "Idioma y aplicación": "Language and application",
  "Idioma": "Language",
  "Español": "Spanish",
  "English": "English",
  "Se aplica a la aplicación y a los textos del overlay.": "Applies to the app and overlay text.",
  "Tema de la app": "App theme",
  "Oscuro": "Dark",
  "Claro": "Light",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.": "Light mode only affects the application, never the overlay.",
  "Integración": "Integration",
  "OBS WebSocket": "OBS WebSocket",
  "Host": "Host",
  "Puerto": "Port",
  "Contraseña": "Password",
  "Proyector OBS": "OBS projector",
  "Se prioriza Programa a pantalla completa; el modo ventana queda como respaldo.": "Fullscreen Program is prioritised; windowed mode remains the fallback.",
  "Conectar automáticamente": "Connect automatically",
  "Conectar OBS": "Connect OBS",
  "Desconectar": "Disconnect",
  "POR CUENTA": "PER ACCOUNT",
  "Control rápido": "Quick control",
  "Atajos de teclado": "Keyboard shortcuts",
  "Haz clic en un campo y pulsa la combinación": "Click a field and press the combination",
  "Esc cancela la captura. Supr o Retroceso elimina el atajo. Las combinaciones duplicadas se rechazan.": "Esc cancels capture. Delete or Backspace removes the shortcut. Duplicate combinations are rejected.",
  "Personalización": "Customisation",
  "Colores y previsualización": "Colours and preview",
  "Aplicación": "Application",
  "Principal": "Primary",
  "Acento": "Accent",
  "Fondo": "Background",
  "Tarjetas": "Cards",
  "Texto": "Text",
  "Nombres": "Names",
  "Mesa de realización": "Production deck",
  "Tecla": "Key",
  "Tecla activa": "Active key",
  "Cuerpo": "Body",
  "Bloque central": "Middle block",
  "Texto secundario": "Secondary text",
  "Paneles del overlay": "Overlay panels",
  "Superficie": "Surface",
  "APLICACIÓN": "APPLICATION",
  "Vista de la interfaz": "Interface preview",
  "Tarjetas, navegación y botones": "Cards, navigation and buttons",
  "Acción": "Action",
  "MARCADOR": "SCOREBOARD",
  "REALIZACIÓN": "PRODUCTION",
  "BOTTOM BAR": "BOTTOM BAR",
  "PANELES": "PANELS",
  "Acceso de realizador": "Operator access",
  "Control de emisión": "Broadcast control",
  "Debes iniciar sesión con una membresía activa para utilizar SecretariatPro.": "You must sign in with an active membership to use SecretariatPro.",
  "Contexto global": "Global context",
  "Competición": "Competition",
  "Selecciona una competición": "Select a competition",
  "Cargar partido": "Load match",
  "El partido seleccionado alimentará Directo, Equipo, Estadísticas y overlays.": "The selected match feeds Live, Team, Statistics and overlays.",
  "Inicia sesión para cargar competiciones": "Log in to load competitions",
  "Carga un partido": "Load a match",
  "Volver": "Back",
  "Cancelar": "Cancel",
  "Recargar": "Reload",
  "Reiniciar tanda": "Reset shootout",
  "Desempate": "Tie-break",
  "Selecciona directamente pendiente, gol o fallo en cada lanzamiento.": "Select pending, goal or miss directly for each attempt.",
});


const APP_TRANSLATIONS_BY_LANGUAGE = {
  en: APP_TRANSLATIONS,
  sv: {
    "Directo":"Live", "Realización":"Produktion", "Equipo":"Lag", "Estadísticas":"Statistik", "Configuración":"Inställningar",
    "Partido actual":"Aktuell match", "Seleccionar partido":"Välj match", "Marcador":"Resultattavla", "Vista de gráficos":"Grafikförhandsvisning",
    "Motor local":"Lokal motor", "Online conectado":"Online ansluten", "Modo local":"Lokalt läge", "OCR activo":"OCR aktiv",
    "OCR detenido":"OCR stoppad", "OCR pendiente":"OCR väntar", "OBS conectado":"OBS ansluten", "OBS desconectado":"OBS frånkopplad",
    "Emisión limpia":"Ren sändning", "Accesos rápidos":"Snabbkontroller", "GRÁFICOS Y EVENTOS":"GRAFIK OCH HÄNDELSER",
    "GRÁFICOS ACTIVOS":"AKTIV GRAFIK", "Ninguno":"Ingen", "Alineación local":"Hemmauppställning", "Alineación visitante":"Bortauppställning",
    "Puntuadores":"Poängliga", "Clasificación":"Tabell", "Jugador local":"Hemmaspelare", "Jugador visitante":"Bortaspelare",
    "Gol local":"Hemmamål", "Gol visitante":"Bortamål", "Expulsión local":"Hemmautvisning", "Expulsión visitante":"Bortautvisning",
    "Limpiar todo":"Rensa allt", "Preparación de partido":"Matchförberedelse", "Guardar convocatoria":"Spara laguttagning",
    "Quinteto inicial":"Startfemma", "Selección de titulares":"Välj startspelare", "Paneles de datos":"Datapaneler",
    "Actualizar estadísticas":"Uppdatera statistik", "Estadísticas de jugador":"Spelarstatistik", "Mostrar ficha":"Visa profil", "Ocultar ficha":"Dölj profil",
    "Captura de marcador":"Resultattavlebild", "Actualizar ventanas":"Uppdatera fönster", "Iniciar OCR":"Starta OCR", "Detener":"Stoppa",
    "Ventana del marcador":"Resultattavlefönster", "Capturar preview":"Ta förhandsvisning", "Configuración visual":"Visuell inställning",
    "Guardar configuración":"Spara inställningar", "Última lectura":"Senaste avläsning", "Valores":"Värden", "Preferencias":"Inställningar",
    "Idioma":"Språk", "Tema de la aplicación":"Appens tema", "Oscuro":"Mörkt", "Claro":"Ljust", "Integración":"Integration",
    "Contraseña":"Lösenord", "Proyector OBS":"OBS-projektor", "Conectar automáticamente":"Anslut automatiskt", "Conectar OBS":"Anslut OBS",
    "Desconectar":"Koppla från", "Atajos de teclado":"Kortkommandon", "Máximos puntuadores":"Poängliga", "Limpiar emisión":"Rensa sändning",
    "Personalización":"Anpassning", "Colores y previsualización":"Färger och förhandsvisning", "Principal":"Primär", "Acento":"Accent",
    "Fondo":"Bakgrund", "Texto":"Text", "Nombres":"Namn", "Cuerpo":"Huvuddel", "Tiempo y resultado":"Tid och resultat",
    "Texto secundario":"Sekundär text", "Paneles del overlay":"Overlaypaneler", "Superficie":"Yta", "Configuración guardada.":"Inställningarna sparades.",
    "Sin asistencia":"Ingen assist", "Registrar gol":"Registrera mål", "Goleador":"Målskytt", "Asistencia":"Assist", "Tiempo":"Tid",
    "Cerrar sesión":"Logga ut", "Iniciar sesión":"Logga in", "Correo electrónico":"E-post", "Local":"Hemma", "Visitante":"Borta",
    "LOCAL":"HEMMA", "VISITANTE":"BORTA", "Actualizar":"Uppdatera", "Expulsiones":"Utvisningar", "Eventos registrados":"Registrerade händelser",
    "Sanción":"Utvisning", "Jugador convocado":"Uttagen spelare", "Selecciona jugador":"Välj spelare", "Iniciar expulsión":"Starta utvisning",
    "Sin PP":"Inget PP", "Cancelar PP local":"Avbryt hemma-PP", "Cancelar PP visitante":"Avbryt borta-PP", "Vista del directo":"Livesignal",
    "Sin señal de programa":"Ingen programsignal", "Cancelar rápidamente":"Snabbavsluta", "Sin expulsión activa":"Ingen aktiv utvisning",
    "Mostrar / ocultar":"Visa / dölj", "Prematch":"Inför match", "Intermission":"Paus", "Alineaciones":"Laguppställningar",
    "Panel de penaltis":"Straffläggningspanel", "Penaltis":"Straffläggning", "Restablecer paneles":"Återställ paneler",
    "Carga un partido para ver la plantilla.":"Ladda en match för att visa truppen.", "Contenido editorial":"Redaktionellt innehåll",
    "Actualizar desde Supabase":"Uppdatera från Supabase", "Jugador":"Spelare", "Actualizar ficha":"Uppdatera profil", "Mostrar en emisión":"Visa i sändning",
    "Ocultar":"Dölj", "Fuente":"Källa", "Sin ventana seleccionada":"Inget fönster valt", "Lectura":"Avläsning", "Intervalo de lectura (ms)":"Avläsningsintervall (ms)",
    "Español":"Spanska", "English":"Engelska", "Sueco":"Svenska", "Checo":"Tjeckiska", "Finés":"Finska", "Alemán":"Tyska",
    "Host":"Värd", "Puerto":"Port", "Volver":"Tillbaka", "Cancelar":"Avbryt", "Recargar":"Ladda om", "Competición":"Tävling",
    "Cargar partido":"Ladda match", "Reiniciar tanda":"Återställ straffläggning", "Desempate":"Avgörande"
  },
  cs: {
    "Directo":"Živě", "Realización":"Režie", "Equipo":"Tým", "Estadísticas":"Statistiky", "Configuración":"Nastavení",
    "Partido actual":"Aktuální zápas", "Seleccionar partido":"Vybrat zápas", "Marcador":"Skóre", "Vista de gráficos":"Náhled grafiky",
    "Motor local":"Místní modul", "Online conectado":"Online připojeno", "Modo local":"Místní režim", "OCR activo":"OCR aktivní",
    "OCR detenido":"OCR zastaveno", "OCR pendiente":"OCR čeká", "OBS conectado":"OBS připojeno", "OBS desconectado":"OBS odpojeno",
    "Emisión limpia":"Čistý výstup", "Accesos rápidos":"Rychlé ovládání", "GRÁFICOS Y EVENTOS":"GRAFIKA A UDÁLOSTI",
    "GRÁFICOS ACTIVOS":"AKTIVNÍ GRAFIKA", "Ninguno":"Žádné", "Alineación local":"Sestava domácích", "Alineación visitante":"Sestava hostů",
    "Puntuadores":"Produktivita", "Clasificación":"Tabulka", "Jugador local":"Hráč domácích", "Jugador visitante":"Hráč hostů",
    "Gol local":"Gól domácích", "Gol visitante":"Gól hostů", "Expulsión local":"Vyloučení domácích", "Expulsión visitante":"Vyloučení hostů",
    "Limpiar todo":"Vyčistit vše", "Preparación de partido":"Příprava zápasu", "Guardar convocatoria":"Uložit nominaci",
    "Quinteto inicial":"Základní pětka", "Selección de titulares":"Výběr základní sestavy", "Paneles de datos":"Datové panely",
    "Actualizar estadísticas":"Aktualizovat statistiky", "Estadísticas de jugador":"Statistiky hráče", "Mostrar ficha":"Zobrazit profil", "Ocultar ficha":"Skrýt profil",
    "Captura de marcador":"Snímání časomíry", "Actualizar ventanas":"Aktualizovat okna", "Iniciar OCR":"Spustit OCR", "Detener":"Zastavit",
    "Ventana del marcador":"Okno časomíry", "Capturar preview":"Zachytit náhled", "Configuración visual":"Vizuální nastavení",
    "Guardar configuración":"Uložit nastavení", "Última lectura":"Poslední čtení", "Valores":"Hodnoty", "Preferencias":"Předvolby",
    "Idioma":"Jazyk", "Tema de la aplicación":"Motiv aplikace", "Oscuro":"Tmavý", "Claro":"Světlý", "Integración":"Integrace",
    "Contraseña":"Heslo", "Proyector OBS":"Projektor OBS", "Conectar automáticamente":"Připojit automaticky", "Conectar OBS":"Připojit OBS",
    "Desconectar":"Odpojit", "Atajos de teclado":"Klávesové zkratky", "Máximos puntuadores":"Nejproduktivnější hráči", "Limpiar emisión":"Vyčistit vysílání",
    "Personalización":"Přizpůsobení", "Colores y previsualización":"Barvy a náhled", "Principal":"Hlavní", "Acento":"Akcent",
    "Fondo":"Pozadí", "Texto":"Text", "Nombres":"Názvy", "Cuerpo":"Tělo", "Tiempo y resultado":"Čas a skóre",
    "Texto secundario":"Sekundární text", "Paneles del overlay":"Panely overlaye", "Superficie":"Plocha", "Configuración guardada.":"Nastavení uloženo.",
    "Sin asistencia":"Bez asistence", "Registrar gol":"Zapsat gól", "Goleador":"Střelec", "Asistencia":"Asistence", "Tiempo":"Čas",
    "Cerrar sesión":"Odhlásit se", "Iniciar sesión":"Přihlásit se", "Correo electrónico":"E-mail", "Local":"Domácí", "Visitante":"Hosté",
    "LOCAL":"DOMÁCÍ", "VISITANTE":"HOSTÉ", "Actualizar":"Aktualizovat", "Expulsiones":"Vyloučení", "Eventos registrados":"Zapsané události",
    "Sanción":"Trest", "Jugador convocado":"Nominovaný hráč", "Selecciona jugador":"Vyberte hráče", "Iniciar expulsión":"Spustit trest",
    "Sin PP":"Bez přesilovky", "Cancelar PP local":"Zrušit přesilovku domácích", "Cancelar PP visitante":"Zrušit přesilovku hostů", "Vista del directo":"Živý výstup",
    "Sin señal de programa":"Bez programového signálu", "Cancelar rápidamente":"Rychlé zrušení", "Sin expulsión activa":"Žádný aktivní trest",
    "Mostrar / ocultar":"Zobrazit / skrýt", "Prematch":"Před zápasem", "Intermission":"Přestávka", "Alineaciones":"Sestavy",
    "Panel de penaltis":"Panel nájezdů", "Penaltis":"Nájezdy", "Restablecer paneles":"Obnovit panely",
    "Carga un partido para ver la plantilla.":"Načtěte zápas pro zobrazení soupisky.", "Contenido editorial":"Redakční obsah",
    "Actualizar desde Supabase":"Aktualizovat ze Supabase", "Jugador":"Hráč", "Actualizar ficha":"Aktualizovat profil", "Mostrar en emisión":"Zobrazit ve vysílání",
    "Ocultar":"Skrýt", "Fuente":"Zdroj", "Sin ventana seleccionada":"Není vybráno okno", "Lectura":"Čtení", "Intervalo de lectura (ms)":"Interval čtení (ms)",
    "Español":"Španělština", "English":"Angličtina", "Sueco":"Švédština", "Checo":"Čeština", "Finés":"Finština", "Alemán":"Němčina",
    "Host":"Hostitel", "Puerto":"Port", "Volver":"Zpět", "Cancelar":"Zrušit", "Recargar":"Načíst znovu", "Competición":"Soutěž",
    "Cargar partido":"Načíst zápas", "Reiniciar tanda":"Resetovat nájezdy", "Desempate":"Rozhodující série"
  },
  fi: {
    "Directo":"Live", "Realización":"Tuotanto", "Equipo":"Joukkue", "Estadísticas":"Tilastot", "Configuración":"Asetukset",
    "Partido actual":"Nykyinen ottelu", "Seleccionar partido":"Valitse ottelu", "Marcador":"Tulostaulu", "Vista de gráficos":"Grafiikan esikatselu",
    "Motor local":"Paikallinen moottori", "Online conectado":"Online-yhteys", "Modo local":"Paikallinen tila", "OCR activo":"OCR aktiivinen",
    "OCR detenido":"OCR pysäytetty", "OCR pendiente":"OCR odottaa", "OBS conectado":"OBS yhdistetty", "OBS desconectado":"OBS ei yhdistetty",
    "Emisión limpia":"Puhdas lähetys", "Accesos rápidos":"Pikaohjaimet", "GRÁFICOS Y EVENTOS":"GRAFIIKAT JA TAPAHTUMAT",
    "GRÁFICOS ACTIVOS":"AKTIIVISET GRAFIIKAT", "Ninguno":"Ei mitään", "Alineación local":"Kotijoukkueen kokoonpano", "Alineación visitante":"Vierasjoukkueen kokoonpano",
    "Puntuadores":"Pistepörssi", "Clasificación":"Sarjataulukko", "Jugador local":"Kotijoukkueen pelaaja", "Jugador visitante":"Vierasjoukkueen pelaaja",
    "Gol local":"Kotijoukkueen maali", "Gol visitante":"Vierasjoukkueen maali", "Expulsión local":"Kotijoukkueen jäähy", "Expulsión visitante":"Vierasjoukkueen jäähy",
    "Limpiar todo":"Tyhjennä kaikki", "Preparación de partido":"Ottelun valmistelu", "Guardar convocatoria":"Tallenna kokoonpano",
    "Quinteto inicial":"Aloitusviisikko", "Selección de titulares":"Aloituskokoonpanon valinta", "Paneles de datos":"Tietopaneelit",
    "Actualizar estadísticas":"Päivitä tilastot", "Estadísticas de jugador":"Pelaajatilastot", "Mostrar ficha":"Näytä profiili", "Ocultar ficha":"Piilota profiili",
    "Captura de marcador":"Tulostaulun kaappaus", "Actualizar ventanas":"Päivitä ikkunat", "Iniciar OCR":"Käynnistä OCR", "Detener":"Pysäytä",
    "Ventana del marcador":"Tulostauluikkuna", "Capturar preview":"Kaappaa esikatselu", "Configuración visual":"Visuaalinen määritys",
    "Guardar configuración":"Tallenna asetukset", "Última lectura":"Viimeisin lukema", "Valores":"Arvot", "Preferencias":"Asetukset",
    "Idioma":"Kieli", "Tema de la aplicación":"Sovelluksen teema", "Oscuro":"Tumma", "Claro":"Vaalea", "Integración":"Integraatio",
    "Contraseña":"Salasana", "Proyector OBS":"OBS-projektori", "Conectar automáticamente":"Yhdistä automaattisesti", "Conectar OBS":"Yhdistä OBS",
    "Desconectar":"Katkaise yhteys", "Atajos de teclado":"Pikanäppäimet", "Máximos puntuadores":"Pistepörssi", "Limpiar emisión":"Tyhjennä lähetys",
    "Personalización":"Mukautus", "Colores y previsualización":"Värit ja esikatselu", "Principal":"Pääväri", "Acento":"Korostus",
    "Fondo":"Tausta", "Texto":"Teksti", "Nombres":"Nimet", "Cuerpo":"Runko", "Tiempo y resultado":"Aika ja tulos",
    "Texto secundario":"Toissijainen teksti", "Paneles del overlay":"Overlay-paneelit", "Superficie":"Pinta", "Configuración guardada.":"Asetukset tallennettu.",
    "Sin asistencia":"Ei syöttäjää", "Registrar gol":"Kirjaa maali", "Goleador":"Maalintekijä", "Asistencia":"Syöttäjä", "Tiempo":"Aika",
    "Cerrar sesión":"Kirjaudu ulos", "Iniciar sesión":"Kirjaudu sisään", "Correo electrónico":"Sähköposti", "Local":"Koti", "Visitante":"Vieras",
    "LOCAL":"KOTI", "VISITANTE":"VIERAS", "Actualizar":"Päivitä", "Expulsiones":"Jäähyt", "Eventos registrados":"Kirjatut tapahtumat",
    "Sanción":"Rangaistus", "Jugador convocado":"Kokoonpanoon valittu pelaaja", "Selecciona jugador":"Valitse pelaaja", "Iniciar expulsión":"Käynnistä jäähy",
    "Sin PP":"Ei ylivoimaa", "Cancelar PP local":"Peru kotijoukkueen ylivoima", "Cancelar PP visitante":"Peru vierasjoukkueen ylivoima", "Vista del directo":"Livelähtö",
    "Sin señal de programa":"Ei ohjelmasignaalia", "Cancelar rápidamente":"Pikaperuutus", "Sin expulsión activa":"Ei aktiivista jäähyä",
    "Mostrar / ocultar":"Näytä / piilota", "Prematch":"Ennen ottelua", "Intermission":"Erätauko", "Alineaciones":"Kokoonpanot",
    "Panel de penaltis":"Rangaistuslaukauspaneeli", "Penaltis":"Rangaistuslaukaukset", "Restablecer paneles":"Palauta paneelit",
    "Carga un partido para ver la plantilla.":"Lataa ottelu nähdäksesi joukkueen.", "Contenido editorial":"Toimituksellinen sisältö",
    "Actualizar desde Supabase":"Päivitä Supabasesta", "Jugador":"Pelaaja", "Actualizar ficha":"Päivitä profiili", "Mostrar en emisión":"Näytä lähetyksessä",
    "Ocultar":"Piilota", "Fuente":"Lähde", "Sin ventana seleccionada":"Ikkunaa ei ole valittu", "Lectura":"Lukema", "Intervalo de lectura (ms)":"Lukuväli (ms)",
    "Español":"Espanja", "English":"Englanti", "Sueco":"Ruotsi", "Checo":"Tšekki", "Finés":"Suomi", "Alemán":"Saksa",
    "Host":"Palvelin", "Puerto":"Portti", "Volver":"Takaisin", "Cancelar":"Peruuta", "Recargar":"Lataa uudelleen", "Competición":"Kilpailu",
    "Cargar partido":"Lataa ottelu", "Reiniciar tanda":"Nollaa laukaukset", "Desempate":"Ratkaisusarja"
  },
  de: {
    "Directo":"Live", "Realización":"Regie", "Equipo":"Team", "Estadísticas":"Statistiken", "Configuración":"Einstellungen",
    "Partido actual":"Aktuelles Spiel", "Seleccionar partido":"Spiel auswählen", "Marcador":"Anzeigetafel", "Vista de gráficos":"Grafikvorschau",
    "Motor local":"Lokaler Dienst", "Online conectado":"Online verbunden", "Modo local":"Lokaler Modus", "OCR activo":"OCR aktiv",
    "OCR detenido":"OCR gestoppt", "OCR pendiente":"OCR ausstehend", "OBS conectado":"OBS verbunden", "OBS desconectado":"OBS getrennt",
    "Emisión limpia":"Saubere Ausgabe", "Accesos rápidos":"Schnellsteuerung", "GRÁFICOS Y EVENTOS":"GRAFIKEN UND EREIGNISSE",
    "GRÁFICOS ACTIVOS":"AKTIVE GRAFIKEN", "Ninguno":"Keine", "Alineación local":"Heimaufstellung", "Alineación visitante":"Gastaufstellung",
    "Puntuadores":"Topscorer", "Clasificación":"Tabelle", "Jugador local":"Heimspieler", "Jugador visitante":"Gastspieler",
    "Gol local":"Heimtor", "Gol visitante":"Gasttor", "Expulsión local":"Heimstrafe", "Expulsión visitante":"Gaststrafe",
    "Limpiar todo":"Alles löschen", "Preparación de partido":"Spielvorbereitung", "Guardar convocatoria":"Kader speichern",
    "Quinteto inicial":"Startformation", "Selección de titulares":"Startaufstellung auswählen", "Paneles de datos":"Datenpanels",
    "Actualizar estadísticas":"Statistiken aktualisieren", "Estadísticas de jugador":"Spielerstatistiken", "Mostrar ficha":"Profil anzeigen", "Ocultar ficha":"Profil ausblenden",
    "Captura de marcador":"Anzeigetafel erfassen", "Actualizar ventanas":"Fenster aktualisieren", "Iniciar OCR":"OCR starten", "Detener":"Stoppen",
    "Ventana del marcador":"Anzeigetafelfenster", "Capturar preview":"Vorschau erfassen", "Configuración visual":"Visuelle Einrichtung",
    "Guardar configuración":"Einstellungen speichern", "Última lectura":"Letzte Erkennung", "Valores":"Werte", "Preferencias":"Einstellungen",
    "Idioma":"Sprache", "Tema de la aplicación":"App-Design", "Oscuro":"Dunkel", "Claro":"Hell", "Integración":"Integration",
    "Contraseña":"Passwort", "Proyector OBS":"OBS-Projektor", "Conectar automáticamente":"Automatisch verbinden", "Conectar OBS":"OBS verbinden",
    "Desconectar":"Trennen", "Atajos de teclado":"Tastenkürzel", "Máximos puntuadores":"Topscorer", "Limpiar emisión":"Ausgabe leeren",
    "Personalización":"Anpassung", "Colores y previsualización":"Farben und Vorschau", "Principal":"Primär", "Acento":"Akzent",
    "Fondo":"Hintergrund", "Texto":"Text", "Nombres":"Namen", "Cuerpo":"Hauptbereich", "Tiempo y resultado":"Zeit und Ergebnis",
    "Texto secundario":"Sekundärtext", "Paneles del overlay":"Overlay-Panels", "Superficie":"Fläche", "Configuración guardada.":"Einstellungen gespeichert.",
    "Sin asistencia":"Ohne Vorlage", "Registrar gol":"Tor eintragen", "Goleador":"Torschütze", "Asistencia":"Vorlage", "Tiempo":"Zeit",
    "Cerrar sesión":"Abmelden", "Iniciar sesión":"Anmelden", "Correo electrónico":"E-Mail", "Local":"Heim", "Visitante":"Gast",
    "LOCAL":"HEIM", "VISITANTE":"GAST", "Actualizar":"Aktualisieren", "Expulsiones":"Strafen", "Eventos registrados":"Erfasste Ereignisse",
    "Sanción":"Strafe", "Jugador convocado":"Kaderspieler", "Selecciona jugador":"Spieler auswählen", "Iniciar expulsión":"Strafe starten",
    "Sin PP":"Kein PP", "Cancelar PP local":"Heim-PP beenden", "Cancelar PP visitante":"Gast-PP beenden", "Vista del directo":"Live-Ausgabe",
    "Sin señal de programa":"Kein Programmsignal", "Cancelar rápidamente":"Schnell beenden", "Sin expulsión activa":"Keine aktive Strafe",
    "Mostrar / ocultar":"Ein-/ausblenden", "Prematch":"Vor dem Spiel", "Intermission":"Pause", "Alineaciones":"Aufstellungen",
    "Panel de penaltis":"Penalty-Panel", "Penaltis":"Penaltyschießen", "Restablecer paneles":"Panels zurücksetzen",
    "Carga un partido para ver la plantilla.":"Lade ein Spiel, um den Kader zu sehen.", "Contenido editorial":"Redaktioneller Inhalt",
    "Actualizar desde Supabase":"Aus Supabase aktualisieren", "Jugador":"Spieler", "Actualizar ficha":"Profil aktualisieren", "Mostrar en emisión":"In Sendung anzeigen",
    "Ocultar":"Ausblenden", "Fuente":"Quelle", "Sin ventana seleccionada":"Kein Fenster ausgewählt", "Lectura":"Erkennung", "Intervalo de lectura (ms)":"Erkennungsintervall (ms)",
    "Español":"Spanisch", "English":"Englisch", "Sueco":"Schwedisch", "Checo":"Tschechisch", "Finés":"Finnisch", "Alemán":"Deutsch",
    "Host":"Host", "Puerto":"Port", "Volver":"Zurück", "Cancelar":"Abbrechen", "Recargar":"Neu laden", "Competición":"Wettbewerb",
    "Cargar partido":"Spiel laden", "Reiniciar tanda":"Penaltyserie zurücksetzen", "Desempate":"Entscheidungsrunde"
  }
};


Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Abre un proyector de programa en OBS para mostrar aquí la señal emitida.":"Öppna en programprojektor i OBS för att visa den sända signalen här.",
  "Acceso de realizador":"Operatörsåtkomst", "Acta en vivo":"Liveprotokoll", "BOTTOM BAR":"BOTTOM BAR", "Bottom bar":"Bottom bar",
  "Broadcast control":"Sändningskontroll", "Broadcast switcher":"Bildväxlare",
  "Captura un preview y arrastra sobre cada valor del marcador.":"Ta en förhandsvisning och dra över varje värde på resultattavlan.",
  "Carga un partido":"Ladda en match", "Carga un partido online para obtener la clasificación.":"Ladda en onlinematch för att hämta tabellen.",
  "Carga un partido online para registrar goles y asistencias.":"Ladda en onlinematch för att registrera mål och assist.",
  "Clasificación disponible":"Tillgänglig tabell", "Colores del overlay":"Overlayfärger",
  "Comparativa de goles, asistencias y puntos.":"Jämförelse av mål, assist och poäng.",
  "Conecta OBS y selecciona una ventana de proyector.":"Anslut OBS och välj ett projektorfönster.",
  "Configuración local":"Lokala inställningar", "Contexto global":"Globalt sammanhang", "Control de emisión":"Sändningskontroll",
  "Control de partido":"Matchkontroll", "Control operativo del partido y de los gráficos en emisión.":"Operativ kontroll av matchen och grafiken i sändning.",
  "Control rápido":"Snabbkontroll", "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.":"Konto, OBS, kortkommandon, språk och utseende på en enda skärm.",
  "Cumple 2 min":"Avtjänar 2 min", "DEF DER":"HÖ DEF", "DEF IZQ":"VÄ DEF", "DEL DER":"HÖ ANF", "DEL IZQ":"VÄ ANF",
  "EXPULSIONES ACTIVAS":"AKTIVA UTVISNINGAR",
  "El contador utiliza el reloj ascendente del OCR. Sólo pueden sancionarse jugadores de la convocatoria guardada.":"Timern använder OCR-klockan som räknar uppåt. Endast uttagna spelare kan utvisas.",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.":"Ljust läge påverkar bara appen, aldrig overlayn.",
  "Debes iniciar sesión con una membresía activa para utilizar SecretariatPro.":"Du måste logga in med ett aktivt medlemskap för att använda SecretariatPro.",
  "El partido seleccionado alimentará Directo, Equipo, Estadísticas y overlays.":"Den valda matchen matar Live, Lag, Statistik och overlaygrafik.",
  "El reloj y el resultado se actualizarán al iniciar.":"Klockan och resultatet uppdateras när du startar.",
  "El resultado procede del marcador físico.":"Resultatet kommer från den fysiska resultattavlan.",
  "En modo OCR el gol se registra en el acta, pero no modifica el resultado.":"I OCR-läge registreras målet i protokollet men ändrar inte resultatet.",
  "Equipo local":"Hemmalag", "Equipo visitante":"Bortalag",
  "Esc cancela la captura. Supr o Retroceso elimina el atajo. Las combinaciones duplicadas se rechazan.":"Esc avbryter fångsten. Delete eller Backspace tar bort kortkommandot. Dubbletter avvisas.",
  "Evento de partido":"Matchhändelse", "FUENTE DEL RESULTADO":"RESULTATKÄLLA",
  "Ficha individual con partidos, goles, asistencias y datos personales.":"Individuell profil med matcher, mål, assist och personuppgifter.",
  "General":"Allmänt", "Haz clic en un campo y pulsa la combinación":"Klicka i ett fält och tryck kombinationen", "Idioma y tema":"Språk och tema",
  "Incrementar también el resultado manual":"Öka även det manuella resultatet", "Inicia sesión para cargar competiciones":"Logga in för att ladda tävlingar",
  "MARCADOR":"RESULTATTAVLA", "MASTER":"MASTER", "MED":"MITT", "Manual":"Manuell", "Mismo jugador":"Samma spelare", "Monitor":"Monitor",
  "Mostrar / ocultar panel":"Visa / dölj panel", "OBS WebSocket":"OBS WebSocket", "PANELES":"PANELER", "POR":"MV", "POR CUENTA":"PER KONTO",
  "PREVIEW":"FÖRHANDSVISNING", "PROGRAMA":"PROGRAM", "PROGRAMA OBS":"OBS-PROGRAM", "Partido":"Match",
  "Plantilla, convocatoria y quinteto en un único flujo.":"Trupp, uttagning och startfemma i ett enda flöde.",
  "Posición, puntos, goles y diferencia.":"Placering, poäng, mål och målskillnad.",
  "Prepara y envía datos a emisión sin abandonar el contexto del partido.":"Förbered och skicka data till sändning utan att lämna matchläget.",
  "Quinteto inicial, convocados y entrenador.":"Startfemma, uttagna spelare och tränare.", "Recargar preview":"Ladda om förhandsvisning",
  "Registrar gol local":"Registrera hemmamål", "Registrar gol visitante":"Registrera bortamål", "Restablecer overlay":"Återställ overlay",
  "Se aplica a la aplicación y a los textos del overlay.":"Gäller appen och overlaytexterna.",
  "Se prioriza Programa a pantalla completa; el modo ventana queda como respaldo.":"Program i helskärm prioriteras; fönsterläge används som reserv.",
  "Selecciona directamente pendiente, gol o fallo en cada lanzamiento.":"Välj direkt väntande, mål eller miss för varje försök.",
  "Selecciona la ventana, dibuja las regiones y controla el lector.":"Välj fönstret, markera områdena och styr läsaren.",
  "Selecciona un jugador para consultar sus estadísticas.":"Välj en spelare för att se statistiken.", "Selecciona una competición":"Välj en tävling",
  "Sin ficha seleccionada":"Ingen profil vald", "Sin paneles a pantalla completa":"Inga helskärmspaneler", "TIEMPO":"TID", "TIEMPO OCR":"OCR-TID",
  "Toda la convocatoria disponible.":"Hela uttagningen är tillgänglig.", "UNA PULSACIÓN":"ETT TRYCK", "Vista previa del overlay":"Overlayförhandsvisning"
});

Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Abre un proyector de programa en OBS para mostrar aquí la señal emitida.":"Otevřete v OBS projektor programu, aby se zde zobrazil vysílaný signál.",
  "Acceso de realizador":"Přístup režie", "Acta en vivo":"Živý zápis", "BOTTOM BAR":"BOTTOM BAR", "Bottom bar":"Bottom bar",
  "Broadcast control":"Řízení vysílání", "Broadcast switcher":"Přepínač vysílání",
  "Captura un preview y arrastra sobre cada valor del marcador.":"Pořiďte náhled a přetáhněte oblast přes každou hodnotu časomíry.",
  "Carga un partido":"Načíst zápas", "Carga un partido online para obtener la clasificación.":"Načtěte online zápas pro získání tabulky.",
  "Carga un partido online para registrar goles y asistencias.":"Načtěte online zápas pro zápis gólů a asistencí.",
  "Clasificación disponible":"Dostupná tabulka", "Colores del overlay":"Barvy overlaye",
  "Comparativa de goles, asistencias y puntos.":"Porovnání gólů, asistencí a bodů.",
  "Conecta OBS y selecciona una ventana de proyector.":"Připojte OBS a vyberte okno projektoru.",
  "Configuración local":"Místní nastavení", "Contexto global":"Globální kontext", "Control de emisión":"Řízení vysílání",
  "Control de partido":"Řízení zápasu", "Control operativo del partido y de los gráficos en emisión.":"Provozní řízení zápasu a grafiky ve vysílání.",
  "Control rápido":"Rychlé ovládání", "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.":"Účet, OBS, zkratky, jazyk a vzhled na jedné obrazovce.",
  "Cumple 2 min":"Odpykává 2 min", "DEF DER":"PRAVÝ OBR", "DEF IZQ":"LEVÝ OBR", "DEL DER":"PRAVÝ ÚT", "DEL IZQ":"LEVÝ ÚT",
  "EXPULSIONES ACTIVAS":"AKTIVNÍ TRESTY",
  "El contador utiliza el reloj ascendente del OCR. Sólo pueden sancionarse jugadores de la convocatoria guardada.":"Časovač používá vzestupný čas OCR. Potrestáni mohou být pouze nominovaní hráči.",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.":"Světlý režim ovlivňuje pouze aplikaci, nikdy overlay.",
  "Debes iniciar sesión con una membresía activa para utilizar SecretariatPro.":"Pro použití SecretariatPro se musíte přihlásit s aktivním členstvím.",
  "El partido seleccionado alimentará Directo, Equipo, Estadísticas y overlays.":"Vybraný zápas naplní Živě, Tým, Statistiky a overlaye.",
  "El reloj y el resultado se actualizarán al iniciar.":"Čas a skóre se aktualizují po spuštění.",
  "El resultado procede del marcador físico.":"Skóre pochází z fyzické časomíry.",
  "En modo OCR el gol se registra en el acta, pero no modifica el resultado.":"V režimu OCR se gól zapíše, ale nezmění skóre.",
  "Equipo local":"Domácí tým", "Equipo visitante":"Hostující tým",
  "Esc cancela la captura. Supr o Retroceso elimina el atajo. Las combinaciones duplicadas se rechazan.":"Esc zruší zachycení. Delete nebo Backspace smaže zkratku. Duplicitní kombinace jsou odmítnuty.",
  "Evento de partido":"Událost zápasu", "FUENTE DEL RESULTADO":"ZDROJ SKÓRE",
  "Ficha individual con partidos, goles, asistencias y datos personales.":"Individuální profil se zápasy, góly, asistencemi a osobními údaji.",
  "General":"Obecné", "Haz clic en un campo y pulsa la combinación":"Klikněte do pole a stiskněte kombinaci", "Idioma y tema":"Jazyk a motiv",
  "Incrementar también el resultado manual":"Zvýšit také ruční skóre", "Inicia sesión para cargar competiciones":"Přihlaste se pro načtení soutěží",
  "MARCADOR":"SKÓRE", "MASTER":"MASTER", "MED":"STŘ", "Manual":"Ruční", "Mismo jugador":"Stejný hráč", "Monitor":"Monitor",
  "Mostrar / ocultar panel":"Zobrazit / skrýt panel", "OBS WebSocket":"OBS WebSocket", "PANELES":"PANELY", "POR":"BR", "POR CUENTA":"PRO ÚČET",
  "PREVIEW":"NÁHLED", "PROGRAMA":"PROGRAM", "PROGRAMA OBS":"PROGRAM OBS", "Partido":"Zápas",
  "Plantilla, convocatoria y quinteto en un único flujo.":"Soupiska, nominace a základní pětka v jednom postupu.",
  "Posición, puntos, goles y diferencia.":"Pořadí, body, góly a rozdíl.",
  "Prepara y envía datos a emisión sin abandonar el contexto del partido.":"Připravujte a posílejte data do vysílání bez opuštění kontextu zápasu.",
  "Quinteto inicial, convocados y entrenador.":"Základní pětka, nominovaní hráči a trenér.", "Recargar preview":"Obnovit náhled",
  "Registrar gol local":"Zapsat gól domácích", "Registrar gol visitante":"Zapsat gól hostů", "Restablecer overlay":"Obnovit overlay",
  "Se aplica a la aplicación y a los textos del overlay.":"Platí pro aplikaci a texty overlaye.",
  "Se prioriza Programa a pantalla completa; el modo ventana queda como respaldo.":"Přednost má program na celé obrazovce; okno slouží jako záloha.",
  "Selecciona directamente pendiente, gol o fallo en cada lanzamiento.":"U každého pokusu vyberte přímo čekající, gól nebo neúspěch.",
  "Selecciona la ventana, dibuja las regiones y controla el lector.":"Vyberte okno, vyznačte oblasti a ovládejte čtečku.",
  "Selecciona un jugador para consultar sus estadísticas.":"Vyberte hráče pro zobrazení statistik.", "Selecciona una competición":"Vyberte soutěž",
  "Sin ficha seleccionada":"Není vybrán profil", "Sin paneles a pantalla completa":"Žádné panely na celou obrazovku", "TIEMPO":"ČAS", "TIEMPO OCR":"ČAS OCR",
  "Toda la convocatoria disponible.":"K dispozici je celá nominace.", "UNA PULSACIÓN":"JEDNO STISKNUTÍ", "Vista previa del overlay":"Náhled overlaye"
});

Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Abre un proyector de programa en OBS para mostrar aquí la señal emitida.":"Avaa OBS:n ohjelmaprojektori näyttääksesi lähetettävän signaalin tässä.",
  "Acceso de realizador":"Tuotannon käyttö", "Acta en vivo":"Live-pöytäkirja", "BOTTOM BAR":"BOTTOM BAR", "Bottom bar":"Bottom bar",
  "Broadcast control":"Lähetyksen ohjaus", "Broadcast switcher":"Lähetysvaihdin",
  "Captura un preview y arrastra sobre cada valor del marcador.":"Kaappaa esikatselu ja vedä alue jokaisen tulostaulun arvon päälle.",
  "Carga un partido":"Lataa ottelu", "Carga un partido online para obtener la clasificación.":"Lataa online-ottelu saadaksesi sarjataulukon.",
  "Carga un partido online para registrar goles y asistencias.":"Lataa online-ottelu kirjataksesi maalit ja syötöt.",
  "Clasificación disponible":"Sarjataulukko saatavilla", "Colores del overlay":"Overlayn värit",
  "Comparativa de goles, asistencias y puntos.":"Maalien, syöttöjen ja pisteiden vertailu.",
  "Conecta OBS y selecciona una ventana de proyector.":"Yhdistä OBS ja valitse projektori-ikkuna.",
  "Configuración local":"Paikalliset asetukset", "Contexto global":"Yleinen konteksti", "Control de emisión":"Lähetyksen ohjaus",
  "Control de partido":"Ottelun ohjaus", "Control operativo del partido y de los gráficos en emisión.":"Ottelun ja lähetysgrafiikan operatiivinen ohjaus.",
  "Control rápido":"Pikaohjaus", "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.":"Tili, OBS, pikanäppäimet, kieli ja ulkoasu yhdellä näytöllä.",
  "Cumple 2 min":"Kärsii 2 min", "DEF DER":"OIKEA PUOL", "DEF IZQ":"VASEN PUOL", "DEL DER":"OIKEA HYÖK", "DEL IZQ":"VASEN HYÖK",
  "EXPULSIONES ACTIVAS":"AKTIIVISET JÄÄHYT",
  "El contador utiliza el reloj ascendente del OCR. Sólo pueden sancionarse jugadores de la convocatoria guardada.":"Ajastin käyttää ylöspäin käyvää OCR-kelloa. Vain kokoonpanoon valittuja pelaajia voidaan rangaista.",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.":"Vaalea tila vaikuttaa vain sovellukseen, ei koskaan overlayhin.",
  "Debes iniciar sesión con una membresía activa para utilizar SecretariatPro.":"SecretariatPron käyttö edellyttää kirjautumista ja aktiivista jäsenyyttä.",
  "El partido seleccionado alimentará Directo, Equipo, Estadísticas y overlays.":"Valittu ottelu syöttää Live-, Joukkue-, Tilasto- ja overlay-näkymät.",
  "El reloj y el resultado se actualizarán al iniciar.":"Kello ja tulos päivittyvät käynnistyksen jälkeen.",
  "El resultado procede del marcador físico.":"Tulos tulee fyysiseltä tulostaululta.",
  "En modo OCR el gol se registra en el acta, pero no modifica el resultado.":"OCR-tilassa maali kirjataan pöytäkirjaan, mutta se ei muuta tulosta.",
  "Equipo local":"Kotijoukkue", "Equipo visitante":"Vierasjoukkue",
  "Esc cancela la captura. Supr o Retroceso elimina el atajo. Las combinaciones duplicadas se rechazan.":"Esc peruuttaa kaappauksen. Delete tai Backspace poistaa pikanäppäimen. Kaksoiskombinaatiot hylätään.",
  "Evento de partido":"Ottelutapahtuma", "FUENTE DEL RESULTADO":"TULOKSEN LÄHDE",
  "Ficha individual con partidos, goles, asistencias y datos personales.":"Pelaajaprofiili, jossa ottelut, maalit, syötöt ja henkilötiedot.",
  "General":"Yleiset", "Haz clic en un campo y pulsa la combinación":"Napsauta kenttää ja paina näppäinyhdistelmää", "Idioma y tema":"Kieli ja teema",
  "Incrementar también el resultado manual":"Kasvata myös manuaalista tulosta", "Inicia sesión para cargar competiciones":"Kirjaudu sisään ladataksesi kilpailut",
  "MARCADOR":"TULOSTAULU", "MASTER":"MASTER", "MED":"KESK", "Manual":"Manuaalinen", "Mismo jugador":"Sama pelaaja", "Monitor":"Monitori",
  "Mostrar / ocultar panel":"Näytä / piilota paneeli", "OBS WebSocket":"OBS WebSocket", "PANELES":"PANEELIT", "POR":"MV", "POR CUENTA":"TILIKOHTAINEN",
  "PREVIEW":"ESIKATSELU", "PROGRAMA":"OHJELMA", "PROGRAMA OBS":"OBS-OHJELMA", "Partido":"Ottelu",
  "Plantilla, convocatoria y quinteto en un único flujo.":"Joukkue, kokoonpano ja aloitusviisikko yhdessä työnkulussa.",
  "Posición, puntos, goles y diferencia.":"Sijoitus, pisteet, maalit ja maaliero.",
  "Prepara y envía datos a emisión sin abandonar el contexto del partido.":"Valmistele ja lähetä tiedot lähetykseen poistumatta ottelunäkymästä.",
  "Quinteto inicial, convocados y entrenador.":"Aloitusviisikko, kokoonpano ja valmentaja.", "Recargar preview":"Lataa esikatselu uudelleen",
  "Registrar gol local":"Kirjaa kotijoukkueen maali", "Registrar gol visitante":"Kirjaa vierasjoukkueen maali", "Restablecer overlay":"Palauta overlay",
  "Se aplica a la aplicación y a los textos del overlay.":"Koskee sovellusta ja overlayn tekstejä.",
  "Se prioriza Programa a pantalla completa; el modo ventana queda como respaldo.":"Koko näytön ohjelma priorisoidaan; ikkunatila toimii varalla.",
  "Selecciona directamente pendiente, gol o fallo en cada lanzamiento.":"Valitse jokaiselle yritykselle suoraan odottaa, maali tai ohi.",
  "Selecciona la ventana, dibuja las regiones y controla el lector.":"Valitse ikkuna, piirrä alueet ja ohjaa lukijaa.",
  "Selecciona un jugador para consultar sus estadísticas.":"Valitse pelaaja nähdäksesi tilastot.", "Selecciona una competición":"Valitse kilpailu",
  "Sin ficha seleccionada":"Profiilia ei ole valittu", "Sin paneles a pantalla completa":"Ei koko näytön paneeleja", "TIEMPO":"AIKA", "TIEMPO OCR":"OCR-AIKA",
  "Toda la convocatoria disponible.":"Koko kokoonpano on käytettävissä.", "UNA PULSACIÓN":"YKSI PAINALLUS", "Vista previa del overlay":"Overlayn esikatselu"
});

Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Abre un proyector de programa en OBS para mostrar aquí la señal emitida.":"Öffne einen Programmprojektor in OBS, um hier das Sendesignal anzuzeigen.",
  "Acceso de realizador":"Regiezugang", "Acta en vivo":"Live-Spielbericht", "BOTTOM BAR":"BOTTOM BAR", "Bottom bar":"Bottom bar",
  "Broadcast control":"Sendesteuerung", "Broadcast switcher":"Bildmischer",
  "Captura un preview y arrastra sobre cada valor del marcador.":"Erfasse eine Vorschau und ziehe einen Bereich über jeden Wert der Anzeigetafel.",
  "Carga un partido":"Spiel laden", "Carga un partido online para obtener la clasificación.":"Lade ein Online-Spiel, um die Tabelle abzurufen.",
  "Carga un partido online para registrar goles y asistencias.":"Lade ein Online-Spiel, um Tore und Vorlagen zu erfassen.",
  "Clasificación disponible":"Tabelle verfügbar", "Colores del overlay":"Overlay-Farben",
  "Comparativa de goles, asistencias y puntos.":"Vergleich von Toren, Vorlagen und Punkten.",
  "Conecta OBS y selecciona una ventana de proyector.":"Verbinde OBS und wähle ein Projektorfenster.",
  "Configuración local":"Lokale Einstellungen", "Contexto global":"Globaler Kontext", "Control de emisión":"Sendesteuerung",
  "Control de partido":"Spielsteuerung", "Control operativo del partido y de los gráficos en emisión.":"Operative Steuerung des Spiels und der On-Air-Grafiken.",
  "Control rápido":"Schnellsteuerung", "Cuenta, OBS, atajos, idioma y apariencia desde una única pantalla.":"Konto, OBS, Tastenkürzel, Sprache und Darstellung auf einem Bildschirm.",
  "Cumple 2 min":"Sitzt 2 Min ab", "DEF DER":"RE VER", "DEF IZQ":"LI VER", "DEL DER":"RE ANG", "DEL IZQ":"LI ANG",
  "EXPULSIONES ACTIVAS":"AKTIVE STRAFEN",
  "El contador utiliza el reloj ascendente del OCR. Sólo pueden sancionarse jugadores de la convocatoria guardada.":"Der Timer verwendet die aufwärts laufende OCR-Uhr. Bestraft werden können nur nominierte Spieler.",
  "El modo claro sólo afecta a la aplicación, nunca al overlay.":"Der helle Modus betrifft nur die App, niemals das Overlay.",
  "Debes iniciar sesión con una membresía activa para utilizar SecretariatPro.":"Für SecretariatPro musst du dich mit einer aktiven Mitgliedschaft anmelden.",
  "El partido seleccionado alimentará Directo, Equipo, Estadísticas y overlays.":"Das ausgewählte Spiel versorgt Live, Team, Statistiken und Overlays.",
  "El reloj y el resultado se actualizarán al iniciar.":"Uhr und Ergebnis werden nach dem Start aktualisiert.",
  "El resultado procede del marcador físico.":"Das Ergebnis stammt von der physischen Anzeigetafel.",
  "En modo OCR el gol se registra en el acta, pero no modifica el resultado.":"Im OCR-Modus wird das Tor erfasst, ändert aber nicht das Ergebnis.",
  "Equipo local":"Heimteam", "Equipo visitante":"Gastteam",
  "Esc cancela la captura. Supr o Retroceso elimina el atajo. Las combinaciones duplicadas se rechazan.":"Esc bricht die Erfassung ab. Entf oder Rücktaste löscht das Kürzel. Doppelte Kombinationen werden abgelehnt.",
  "Evento de partido":"Spielereignis", "FUENTE DEL RESULTADO":"ERGEBNISQUELLE",
  "Ficha individual con partidos, goles, asistencias y datos personales.":"Einzelprofil mit Spielen, Toren, Vorlagen und persönlichen Daten.",
  "General":"Allgemein", "Haz clic en un campo y pulsa la combinación":"Klicke in ein Feld und drücke die Kombination", "Idioma y tema":"Sprache und Design",
  "Incrementar también el resultado manual":"Auch das manuelle Ergebnis erhöhen", "Inicia sesión para cargar competiciones":"Anmelden, um Wettbewerbe zu laden",
  "MARCADOR":"ANZEIGETAFEL", "MASTER":"MASTER", "MED":"MIT", "Manual":"Manuell", "Mismo jugador":"Gleicher Spieler", "Monitor":"Monitor",
  "Mostrar / ocultar panel":"Panel ein-/ausblenden", "OBS WebSocket":"OBS WebSocket", "PANELES":"PANELS", "POR":"TW", "POR CUENTA":"PRO KONTO",
  "PREVIEW":"VORSCHAU", "PROGRAMA":"PROGRAMM", "PROGRAMA OBS":"OBS-PROGRAMM", "Partido":"Spiel",
  "Plantilla, convocatoria y quinteto en un único flujo.":"Kader, Nominierung und Startformation in einem Ablauf.",
  "Posición, puntos, goles y diferencia.":"Platz, Punkte, Tore und Differenz.",
  "Prepara y envía datos a emisión sin abandonar el contexto del partido.":"Daten vorbereiten und senden, ohne den Spielkontext zu verlassen.",
  "Quinteto inicial, convocados y entrenador.":"Startformation, nominierte Spieler und Trainer.", "Recargar preview":"Vorschau neu laden",
  "Registrar gol local":"Heimtor erfassen", "Registrar gol visitante":"Gasttor erfassen", "Restablecer overlay":"Overlay zurücksetzen",
  "Se aplica a la aplicación y a los textos del overlay.":"Gilt für die App und die Overlay-Texte.",
  "Se prioriza Programa a pantalla completa; el modo ventana queda como respaldo.":"Vollbild-Programm wird bevorzugt; der Fenstermodus dient als Reserve.",
  "Selecciona directamente pendiente, gol o fallo en cada lanzamiento.":"Für jeden Versuch direkt offen, Tor oder Fehlschuss wählen.",
  "Selecciona la ventana, dibuja las regiones y controla el lector.":"Fenster wählen, Bereiche markieren und den Leser steuern.",
  "Selecciona un jugador para consultar sus estadísticas.":"Spieler auswählen, um seine Statistiken anzuzeigen.", "Selecciona una competición":"Wettbewerb auswählen",
  "Sin ficha seleccionada":"Kein Profil ausgewählt", "Sin paneles a pantalla completa":"Keine Vollbild-Panels", "TIEMPO":"ZEIT", "TIEMPO OCR":"OCR-ZEIT",
  "Toda la convocatoria disponible.":"Der vollständige Kader ist verfügbar.", "UNA PULSACIÓN":"EIN KLICK", "Vista previa del overlay":"Overlay-Vorschau"
});

Object.assign(APP_TRANSLATIONS, {
  "Abre SecretariatDeck desde la tablet":"Open SecretariatDeck on your tablet", "Marca":"Marker",
  "Secuencias personales":"Personal sequences", "Se guardan en la cuenta del realizador.":"Saved to the producer's account.",
  "Nueva secuencia":"New sequence", "Nombre":"Name", "Añadir gráfico":"Add graphic", "Guardar secuencia":"Save sequence",
  "Todavía no hay secuencias personales.":"There are no personal sequences yet.", "gráficos":"graphics", "En emisión":"On air", "Lanzar":"Run",
  "Visible":"Visible", "Intervalo":"Interval", "Pon un nombre a la secuencia":"Name the sequence", "Secuencia guardada.":"Sequence saved.",
  "MONTAJE RÁPIDO":"QUICK EDIT", "Componer repetición":"Compose replay", "Esperando cámaras…":"Waiting for cameras…",
  "Elige cámara, duración y velocidad para cada plano. Puedes lanzarla ahora o guardarla para el vídeo de highlights.":"Choose the camera, duration and speed for each shot. Play it now or save it for the highlights video.",
  "Añadir plano":"Add shot", "Guardar para highlights":"Save for highlights", "Guardar y lanzar":"Save and play", "Cámara":"Camera",
  "Duración":"Duration", "Velocidad":"Speed", "Lista para componer":"Ready to compose", "Repetición del gol":"Goal replay",
  "Añade al menos un plano.":"Add at least one shot.", "Repetición en programa.":"Replay on air.",
  "Composición guardada para highlights.":"Composition saved for highlights."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Abre SecretariatDeck desde la tablet":"Öppna SecretariatDeck på surfplattan", "Marca":"Markering", "Secuencias personales":"Personliga sekvenser", "Se guardan en la cuenta del realizador.":"Sparas i producentens konto.", "Nueva secuencia":"Ny sekvens", "Nombre":"Namn", "Añadir gráfico":"Lägg till grafik", "Guardar secuencia":"Spara sekvens", "Todavía no hay secuencias personales.":"Det finns inga personliga sekvenser ännu.", "gráficos":"grafik", "En emisión":"I sändning", "Lanzar":"Starta", "Visible":"Synlig", "Intervalo":"Intervall", "Pon un nombre a la secuencia":"Namnge sekvensen", "Secuencia guardada.":"Sekvensen sparades.", "MONTAJE RÁPIDO":"SNABBREDIGERING", "Componer repetición":"Sätt ihop repris", "Esperando cámaras…":"Väntar på kameror…", "Elige cámara, duración y velocidad para cada plano. Puedes lanzarla ahora o guardarla para el vídeo de highlights.":"Välj kamera, längd och hastighet för varje bild. Spela upp nu eller spara till highlightvideon.", "Añadir plano":"Lägg till bild", "Guardar para highlights":"Spara till highlights", "Guardar y lanzar":"Spara och spela", "Cámara":"Kamera", "Duración":"Längd", "Velocidad":"Hastighet", "Lista para componer":"Klar att redigera", "Repetición del gol":"Målrepris", "Añade al menos un plano.":"Lägg till minst en bild.", "Repetición en programa.":"Repris i sändning.", "Composición guardada para highlights.":"Redigeringen sparades för highlights."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Abre SecretariatDeck desde la tablet":"Otevřít SecretariatDeck na tabletu", "Marca":"Značka", "Secuencias personales":"Osobní sekvence", "Se guardan en la cuenta del realizador.":"Ukládají se k účtu režiséra.", "Nueva secuencia":"Nová sekvence", "Nombre":"Název", "Añadir gráfico":"Přidat grafiku", "Guardar secuencia":"Uložit sekvenci", "Todavía no hay secuencias personales.":"Zatím nejsou žádné osobní sekvence.", "gráficos":"grafik", "En emisión":"Ve vysílání", "Lanzar":"Spustit", "Visible":"Zobrazení", "Intervalo":"Interval", "Pon un nombre a la secuencia":"Pojmenujte sekvenci", "Secuencia guardada.":"Sekvence uložena.", "MONTAJE RÁPIDO":"RYCHLÝ STŘIH", "Componer repetición":"Sestavit opakování", "Esperando cámaras…":"Čekání na kamery…", "Elige cámara, duración y velocidad para cada plano. Puedes lanzarla ahora o guardarla para el vídeo de highlights.":"Vyberte kameru, délku a rychlost každého záběru. Přehrajte jej hned nebo uložte do sestřihu.", "Añadir plano":"Přidat záběr", "Guardar para highlights":"Uložit do sestřihu", "Guardar y lanzar":"Uložit a přehrát", "Cámara":"Kamera", "Duración":"Délka", "Velocidad":"Rychlost", "Lista para componer":"Připraveno ke střihu", "Repetición del gol":"Opakování gólu", "Añade al menos un plano.":"Přidejte alespoň jeden záběr.", "Repetición en programa.":"Opakování ve vysílání.", "Composición guardada para highlights.":"Sestava uložena do highlights."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Abre SecretariatDeck desde la tablet":"Avaa SecretariatDeck tabletilla", "Marca":"Merkki", "Secuencias personales":"Omat jaksot", "Se guardan en la cuenta del realizador.":"Tallennetaan tuottajan tilille.", "Nueva secuencia":"Uusi jakso", "Nombre":"Nimi", "Añadir gráfico":"Lisää grafiikka", "Guardar secuencia":"Tallenna jakso", "Todavía no hay secuencias personales.":"Omia jaksoja ei vielä ole.", "gráficos":"grafiikkaa", "En emisión":"Lähetyksessä", "Lanzar":"Käynnistä", "Visible":"Näkyvissä", "Intervalo":"Väli", "Pon un nombre a la secuencia":"Nimeä jakso", "Secuencia guardada.":"Jakso tallennettu.", "MONTAJE RÁPIDO":"PIKALEIKKAUS", "Componer repetición":"Koosta uusinta", "Esperando cámaras…":"Odotetaan kameroita…", "Elige cámara, duración y velocidad para cada plano. Puedes lanzarla ahora o guardarla para el vídeo de highlights.":"Valitse jokaiselle otokselle kamera, kesto ja nopeus. Toista nyt tai tallenna koostevideoon.", "Añadir plano":"Lisää otos", "Guardar para highlights":"Tallenna koosteeseen", "Guardar y lanzar":"Tallenna ja toista", "Cámara":"Kamera", "Duración":"Kesto", "Velocidad":"Nopeus", "Lista para componer":"Valmis leikattavaksi", "Repetición del gol":"Maalin uusinta", "Añade al menos un plano.":"Lisää vähintään yksi otos.", "Repetición en programa.":"Uusinta lähetyksessä.", "Composición guardada para highlights.":"Leikkaus tallennettu koosteeseen."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Abre SecretariatDeck desde la tablet":"SecretariatDeck auf dem Tablet öffnen", "Marca":"Marker", "Secuencias personales":"Persönliche Sequenzen", "Se guardan en la cuenta del realizador.":"Werden im Konto des Regisseurs gespeichert.", "Nueva secuencia":"Neue Sequenz", "Nombre":"Name", "Añadir gráfico":"Grafik hinzufügen", "Guardar secuencia":"Sequenz speichern", "Todavía no hay secuencias personales.":"Noch keine persönlichen Sequenzen vorhanden.", "gráficos":"Grafiken", "En emisión":"Auf Sendung", "Lanzar":"Starten", "Visible":"Sichtbar", "Intervalo":"Abstand", "Pon un nombre a la secuencia":"Sequenz benennen", "Secuencia guardada.":"Sequenz gespeichert.", "MONTAJE RÁPIDO":"SCHNELLSCHNITT", "Componer repetición":"Wiederholung zusammenstellen", "Esperando cámaras…":"Warten auf Kameras…", "Elige cámara, duración y velocidad para cada plano. Puedes lanzarla ahora o guardarla para el vídeo de highlights.":"Kamera, Dauer und Geschwindigkeit für jede Einstellung wählen. Jetzt abspielen oder für das Highlightvideo speichern.", "Añadir plano":"Einstellung hinzufügen", "Guardar para highlights":"Für Highlights speichern", "Guardar y lanzar":"Speichern und abspielen", "Cámara":"Kamera", "Duración":"Dauer", "Velocidad":"Geschwindigkeit", "Lista para componer":"Bereit zum Schneiden", "Repetición del gol":"Torwiederholung", "Añade al menos un plano.":"Mindestens eine Einstellung hinzufügen.", "Repetición en programa.":"Wiederholung auf Sendung.", "Composición guardada para highlights.":"Schnitt für Highlights gespeichert."
});


Object.assign(APP_TRANSLATIONS, {
  "Activa el modo manual para editar el resultado.":"Enable manual mode to edit the score.",
  "Carga primero un partido online.":"Load an online match first.", "Conecta OBS para ver sus escenas.":"Connect OBS to view its scenes.",
  "Configuración OCR guardada.":"OCR settings saved.", "Convocatoria y alineación guardadas.":"Call-up and starting lineup saved.",
  "El 2+10 debe cumplirlo otro jugador convocado.":"The 2+10 must be served by another called-up player.",
  "El goleador ya no está disponible.":"The scorer is no longer available.", "El jugador sancionado ya no está disponible.":"The penalised player is no longer available.",
  "Emisión limpia.":"Output cleared.", "En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.":"For 2+10, select another called-up player to serve the 2 minutes.",
  "Estadísticas actualizadas desde Supabase.":"Statistics updated from Supabase.", "Evento anulado.":"Event cancelled.", "Eventos actualizados.":"Events updated.",
  "Expulsión enlazada al reloj OCR.":"Penalty linked to the OCR clock.", "Gol registrado en el acta.":"Goal recorded.",
  "Goleador y asistente no pueden ser el mismo jugador.":"Scorer and assistant cannot be the same player.",
  "La convocatoria ya no está disponible.":"The call-up is no longer available.", "No hay jugadores disponibles para este equipo.":"No players are available for this team.",
  "No se pudo obtener el preview OCR.":"The OCR preview could not be obtained.", "OBS conectado y configuración guardada.":"OBS connected and settings saved.",
  "OBS desconectado.":"OBS disconnected.", "OCR detenido.":"OCR stopped.", "OCR iniciado.":"OCR started.", "Partido cargado.":"Match loaded.",
  "Selecciona competición y partido.":"Select a competition and match.", "Selecciona el goleador.":"Select the scorer.",
  "Selecciona otro convocado para cumplir los 2 minutos.":"Select another called-up player to serve the 2 minutes.",
  "Selecciona un jugador de la convocatoria guardada.":"Select a player from the saved call-up.", "Selecciona un jugador.":"Select a player.",
  "Selecciona una ventana OCR.":"Select an OCR window.", "Sesión cerrada.":"Session closed.", "Sesión iniciada.":"Session started.",
  "Tanda reiniciada.":"Shootout reset."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Activa el modo manual para editar el resultado.":"Aktivera manuellt läge för att ändra resultatet.", "Carga primero un partido online.":"Ladda först en onlinematch.",
  "Conecta OBS para ver sus escenas.":"Anslut OBS för att visa scenerna.", "Configuración OCR guardada.":"OCR-inställningarna sparades.",
  "Convocatoria y quinteto guardados.":"Uttagning och startfemma sparades.", "El 2+10 debe cumplirlo otro jugador convocado.":"2+10 måste avtjänas av en annan uttagen spelare.",
  "El goleador ya no está disponible.":"Målskytten är inte längre tillgänglig.", "El jugador sancionado ya no está disponible.":"Den utvisade spelaren är inte längre tillgänglig.",
  "Emisión limpia.":"Sändningen är rensad.", "En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.":"Vid 2+10 väljer du en annan uttagen spelare som avtjänar 2 minuter.",
  "Estadísticas actualizadas desde Supabase.":"Statistiken uppdaterades från Supabase.", "Evento anulado.":"Händelsen annullerades.", "Eventos actualizados.":"Händelserna uppdaterades.",
  "Expulsión enlazada al reloj OCR.":"Utvisningen kopplades till OCR-klockan.", "Gol registrado en el acta.":"Målet registrerades.",
  "Goleador y asistente no pueden ser el mismo jugador.":"Målskytt och framspelare kan inte vara samma spelare.", "La convocatoria ya no está disponible.":"Uttagningen är inte längre tillgänglig.",
  "No hay jugadores disponibles para este equipo.":"Inga spelare är tillgängliga för laget.", "No se pudo obtener el preview OCR.":"OCR-förhandsvisningen kunde inte hämtas.",
  "OBS conectado y configuración guardada.":"OBS anslutet och inställningarna sparade.", "OBS desconectado.":"OBS frånkopplat.", "OCR detenido.":"OCR stoppat.",
  "OCR iniciado.":"OCR startat.", "Partido cargado.":"Matchen laddades.", "Selecciona competición y partido.":"Välj tävling och match.",
  "Selecciona el goleador.":"Välj målskytt.", "Selecciona otro convocado para cumplir los 2 minutos.":"Välj en annan uttagen spelare som avtjänar 2 minuter.",
  "Selecciona un jugador de la convocatoria guardada.":"Välj en spelare från den sparade uttagningen.", "Selecciona un jugador.":"Välj en spelare.",
  "Selecciona una ventana OCR.":"Välj ett OCR-fönster.", "Sesión cerrada.":"Sessionen avslutades.", "Sesión iniciada.":"Sessionen startades.", "Tanda reiniciada.":"Straffläggningen återställdes."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Activa el modo manual para editar el resultado.":"Zapněte ruční režim pro úpravu skóre.", "Carga primero un partido online.":"Nejprve načtěte online zápas.",
  "Conecta OBS para ver sus escenas.":"Připojte OBS pro zobrazení scén.", "Configuración OCR guardada.":"Nastavení OCR uloženo.",
  "Convocatoria y quinteto guardados.":"Nominace a základní pětka uloženy.", "El 2+10 debe cumplirlo otro jugador convocado.":"Trest 2+10 musí odpykat jiný nominovaný hráč.",
  "El goleador ya no está disponible.":"Střelec již není dostupný.", "El jugador sancionado ya no está disponible.":"Potrestaný hráč již není dostupný.",
  "Emisión limpia.":"Výstup vyčištěn.", "En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.":"U 2+10 vyberte jiného nominovaného hráče pro odpykání 2 minut.",
  "Estadísticas actualizadas desde Supabase.":"Statistiky aktualizovány ze Supabase.", "Evento anulado.":"Událost zrušena.", "Eventos actualizados.":"Události aktualizovány.",
  "Expulsión enlazada al reloj OCR.":"Trest propojen s časem OCR.", "Gol registrado en el acta.":"Gól zapsán.",
  "Goleador y asistente no pueden ser el mismo jugador.":"Střelec a asistující hráč nemohou být stejná osoba.", "La convocatoria ya no está disponible.":"Nominace již není dostupná.",
  "No hay jugadores disponibles para este equipo.":"Pro tento tým nejsou dostupní hráči.", "No se pudo obtener el preview OCR.":"Náhled OCR se nepodařilo získat.",
  "OBS conectado y configuración guardada.":"OBS připojeno a nastavení uloženo.", "OBS desconectado.":"OBS odpojeno.", "OCR detenido.":"OCR zastaveno.",
  "OCR iniciado.":"OCR spuštěno.", "Partido cargado.":"Zápas načten.", "Selecciona competición y partido.":"Vyberte soutěž a zápas.",
  "Selecciona el goleador.":"Vyberte střelce.", "Selecciona otro convocado para cumplir los 2 minutos.":"Vyberte jiného nominovaného hráče pro odpykání 2 minut.",
  "Selecciona un jugador de la convocatoria guardada.":"Vyberte hráče z uložené nominace.", "Selecciona un jugador.":"Vyberte hráče.",
  "Selecciona una ventana OCR.":"Vyberte okno OCR.", "Sesión cerrada.":"Relace ukončena.", "Sesión iniciada.":"Relace zahájena.", "Tanda reiniciada.":"Nájezdy resetovány."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Activa el modo manual para editar el resultado.":"Ota manuaalinen tila käyttöön tuloksen muokkaamiseksi.", "Carga primero un partido online.":"Lataa ensin online-ottelu.",
  "Conecta OBS para ver sus escenas.":"Yhdistä OBS nähdäksesi kohtaukset.", "Configuración OCR guardada.":"OCR-asetukset tallennettu.",
  "Convocatoria y quinteto guardados.":"Kokoonpano ja aloitusviisikko tallennettu.", "El 2+10 debe cumplirlo otro jugador convocado.":"Toisen kokoonpanoon valitun pelaajan on kärsittävä 2+10-rangaistus.",
  "El goleador ya no está disponible.":"Maalintekijä ei ole enää käytettävissä.", "El jugador sancionado ya no está disponible.":"Rangaistu pelaaja ei ole enää käytettävissä.",
  "Emisión limpia.":"Lähetys tyhjennetty.", "En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.":"Valitse 2+10-rangaistuksessa toinen kokoonpanoon kuuluva pelaaja kärsimään 2 minuuttia.",
  "Estadísticas actualizadas desde Supabase.":"Tilastot päivitetty Supabasesta.", "Evento anulado.":"Tapahtuma peruttu.", "Eventos actualizados.":"Tapahtumat päivitetty.",
  "Expulsión enlazada al reloj OCR.":"Jäähy yhdistetty OCR-kelloon.", "Gol registrado en el acta.":"Maali kirjattu.",
  "Goleador y asistente no pueden ser el mismo jugador.":"Maalintekijä ja syöttäjä eivät voi olla sama pelaaja.", "La convocatoria ya no está disponible.":"Kokoonpano ei ole enää käytettävissä.",
  "No hay jugadores disponibles para este equipo.":"Tälle joukkueelle ei ole pelaajia.", "No se pudo obtener el preview OCR.":"OCR-esikatselua ei voitu hakea.",
  "OBS conectado y configuración guardada.":"OBS yhdistetty ja asetukset tallennettu.", "OBS desconectado.":"OBS-yhteys katkaistu.", "OCR detenido.":"OCR pysäytetty.",
  "OCR iniciado.":"OCR käynnistetty.", "Partido cargado.":"Ottelu ladattu.", "Selecciona competición y partido.":"Valitse kilpailu ja ottelu.",
  "Selecciona el goleador.":"Valitse maalintekijä.", "Selecciona otro convocado para cumplir los 2 minutos.":"Valitse toinen kokoonpanoon kuuluva pelaaja kärsimään 2 minuuttia.",
  "Selecciona un jugador de la convocatoria guardada.":"Valitse pelaaja tallennetusta kokoonpanosta.", "Selecciona un jugador.":"Valitse pelaaja.",
  "Selecciona una ventana OCR.":"Valitse OCR-ikkuna.", "Sesión cerrada.":"Istunto suljettu.", "Sesión iniciada.":"Istunto aloitettu.", "Tanda reiniciada.":"Rangaistuslaukaukset nollattu."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Activa el modo manual para editar el resultado.":"Aktiviere den manuellen Modus, um das Ergebnis zu bearbeiten.", "Carga primero un partido online.":"Lade zuerst ein Online-Spiel.",
  "Conecta OBS para ver sus escenas.":"Verbinde OBS, um die Szenen anzuzeigen.", "Configuración OCR guardada.":"OCR-Einstellungen gespeichert.",
  "Convocatoria y quinteto guardados.":"Kader und Startformation gespeichert.", "El 2+10 debe cumplirlo otro jugador convocado.":"Die 2+10-Strafe muss von einem anderen nominierten Spieler abgesessen werden.",
  "El goleador ya no está disponible.":"Der Torschütze ist nicht mehr verfügbar.", "El jugador sancionado ya no está disponible.":"Der bestrafte Spieler ist nicht mehr verfügbar.",
  "Emisión limpia.":"Ausgabe geleert.", "En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.":"Wähle bei 2+10 einen anderen nominierten Spieler für die 2 Minuten.",
  "Estadísticas actualizadas desde Supabase.":"Statistiken aus Supabase aktualisiert.", "Evento anulado.":"Ereignis annulliert.", "Eventos actualizados.":"Ereignisse aktualisiert.",
  "Expulsión enlazada al reloj OCR.":"Strafe mit der OCR-Uhr verknüpft.", "Gol registrado en el acta.":"Tor erfasst.",
  "Goleador y asistente no pueden ser el mismo jugador.":"Torschütze und Vorlagengeber dürfen nicht derselbe Spieler sein.", "La convocatoria ya no está disponible.":"Der Kader ist nicht mehr verfügbar.",
  "No hay jugadores disponibles para este equipo.":"Für dieses Team sind keine Spieler verfügbar.", "No se pudo obtener el preview OCR.":"Die OCR-Vorschau konnte nicht geladen werden.",
  "OBS conectado y configuración guardada.":"OBS verbunden und Einstellungen gespeichert.", "OBS desconectado.":"OBS getrennt.", "OCR detenido.":"OCR gestoppt.",
  "OCR iniciado.":"OCR gestartet.", "Partido cargado.":"Spiel geladen.", "Selecciona competición y partido.":"Wettbewerb und Spiel auswählen.",
  "Selecciona el goleador.":"Torschützen auswählen.", "Selecciona otro convocado para cumplir los 2 minutos.":"Einen anderen nominierten Spieler für die 2 Minuten auswählen.",
  "Selecciona un jugador de la convocatoria guardada.":"Einen Spieler aus dem gespeicherten Kader auswählen.", "Selecciona un jugador.":"Spieler auswählen.",
  "Selecciona una ventana OCR.":"OCR-Fenster auswählen.", "Sesión cerrada.":"Sitzung beendet.", "Sesión iniciada.":"Sitzung gestartet.", "Tanda reiniciada.":"Penaltyserie zurückgesetzt."
});

Object.assign(APP_TRANSLATIONS, {
  "Acceso remoto": "Remote access",
  "MISMA RED": "SAME NETWORK",
  "Abre el panel desde la tablet": "Open the panel on your tablet",
  "Conecta el iPad o la tablet a la misma red Wi-Fi que este ordenador y escanea el código QR.": "Connect the iPad or tablet to the same Wi-Fi network as this computer and scan the QR code.",
  "Calculando dirección…": "Calculating address…",
  "Copiar dirección": "Copy address",
  "Actualizar QR": "Refresh QR",
  "Dirección copiada.": "Address copied.",
  "Enlace del overlay copiado. Pégalo como fuente de navegador (1920 × 1080).": "Overlay link copied. Paste it as a browser source (1920 × 1080).",
  "No se pudo copiar el enlace. Vuelve a intentarlo.": "The link could not be copied. Please try again."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Acceso remoto": "Fjärråtkomst", "MISMA RED": "SAMMA NÄTVERK", "Abre el panel desde la tablet": "Öppna panelen på surfplattan",
  "Conecta el iPad o la tablet a la misma red Wi-Fi que este ordenador y escanea el código QR.": "Anslut iPad eller surfplattan till samma Wi‑Fi-nätverk som datorn och skanna QR-koden.",
  "Calculando dirección…": "Beräknar adress…", "Copiar dirección": "Kopiera adress", "Actualizar QR": "Uppdatera QR", "Dirección copiada.": "Adressen kopierad."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Acceso remoto": "Vzdálený přístup", "MISMA RED": "STEJNÁ SÍŤ", "Abre el panel desde la tablet": "Otevřete panel na tabletu",
  "Conecta el iPad o la tablet a la misma red Wi-Fi que este ordenador y escanea el código QR.": "Připojte iPad nebo tablet ke stejné Wi‑Fi síti jako tento počítač a naskenujte QR kód.",
  "Calculando dirección…": "Zjišťuji adresu…", "Copiar dirección": "Kopírovat adresu", "Actualizar QR": "Obnovit QR", "Dirección copiada.": "Adresa zkopírována."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Acceso remoto": "Etäkäyttö", "MISMA RED": "SAMA VERKKO", "Abre el panel desde la tablet": "Avaa hallinta tabletilla",
  "Conecta el iPad o la tablet a la misma red Wi-Fi que este ordenador y escanea el código QR.": "Yhdistä iPad tai tabletti samaan Wi‑Fi-verkkoon tämän tietokoneen kanssa ja skannaa QR-koodi.",
  "Calculando dirección…": "Lasketaan osoitetta…", "Copiar dirección": "Kopioi osoite", "Actualizar QR": "Päivitä QR", "Dirección copiada.": "Osoite kopioitu."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Acceso remoto": "Fernzugriff", "MISMA RED": "GLEICHES NETZWERK", "Abre el panel desde la tablet": "Bedienfeld auf dem Tablet öffnen",
  "Conecta el iPad o la tablet a la misma red Wi-Fi que este ordenador y escanea el código QR.": "Verbinde das iPad oder Tablet mit demselben WLAN wie diesen Computer und scanne den QR-Code.",
  "Calculando dirección…": "Adresse wird ermittelt…", "Copiar dirección": "Adresse kopieren", "Actualizar QR": "QR aktualisieren", "Dirección copiada.": "Adresse kopiert."
});
Object.assign(APP_TRANSLATIONS, {"Continuar sin repetición":"Continue without replay"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"Continuar sin repetición":"Fortsätt utan repris"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"Continuar sin repetición":"Pokračovat bez opakování"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"Continuar sin repetición":"Jatka ilman uusintaa"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"Continuar sin repetición":"Ohne Wiederholung fortfahren"});

Object.assign(APP_TRANSLATIONS, {"Abrir carpeta de vídeos": "Open videos folder", "Guardar vídeo del evento": "Save event video", "Cada evento se guarda como un vídeo independiente con sus cámaras y velocidades.": "Each event is saved as a separate video with its cameras and speeds."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"Abrir carpeta de vídeos": "Öppna videomapp", "Guardar vídeo del evento": "Spara händelsens video", "Cada evento se guarda como un vídeo independiente con sus cámaras y velocidades.": "Varje händelse sparas som en separat video med sina kameror och hastigheter."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"Abrir carpeta de vídeos": "Otevřít složku videí", "Guardar vídeo del evento": "Uložit video události", "Cada evento se guarda como un vídeo independiente con sus cámaras y velocidades.": "Každá událost se uloží jako samostatné video s vybranými kamerami a rychlostmi."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"Abrir carpeta de vídeos": "Avaa videokansio", "Guardar vídeo del evento": "Tallenna tapahtuman video", "Cada evento se guarda como un vídeo independiente con sus cámaras y velocidades.": "Jokainen tapahtuma tallennetaan omaksi videoksi valituilla kameroilla ja nopeuksilla."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"Abrir carpeta de vídeos": "Videoordner öffnen", "Guardar vídeo del evento": "Ereignisvideo speichern", "Cada evento se guarda como un vídeo independiente con sus cámaras y velocidades.": "Jedes Ereignis wird als eigenes Video mit seinen Kameras und Geschwindigkeiten gespeichert."});

Object.assign(APP_TRANSLATIONS, {"Guardando vídeo del evento…":"Saving event video…"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"Guardando vídeo del evento…":"Sparar händelsens video…"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"Guardando vídeo del evento…":"Ukládání videa události…"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"Guardando vídeo del evento…":"Tallennetaan tapahtuman videota…"});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"Guardando vídeo del evento…":"Ereignisvideo wird gespeichert…"});
const originalTextNodes = new WeakMap();

function cloneObject(value) { return JSON.parse(JSON.stringify(value)); }
function mergeObject(base, incoming) {
  const result = cloneObject(base);
  Object.entries(incoming || {}).forEach(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value) && result[key] && typeof result[key] === "object") result[key] = mergeObject(result[key], value);
    else result[key] = value;
  });
  return result;
}
function getByPath(object, path) { return path.split(".").reduce((value, key) => value?.[key], object); }
function setByPath(object, path, value) {
  const keys = path.split(".");
  let cursor = object;
  keys.slice(0, -1).forEach((key) => { cursor[key] = cursor[key] || {}; cursor = cursor[key]; });
  cursor[keys.at(-1)] = value;
}
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.en, {"REPETICIONES": "REPLAYS", "MARCAR": "MARK", "LANZAR + GUARDAR": "PLAY + SAVE", "SIN REPETICIÓN": "NO REPLAY", "Plugin conectado": "Plugin connected", "Todos los eventos": "All events", "Planos": "Shots", "Preview": "Preview", "Lanzar": "Play on air", "Guardar vídeo": "Save video", "Abrir carpeta": "Open folder", "Segundos": "Seconds", "¿Añadir otro plano?": "Add another shot?", "Continuar": "Continue", "Terminar": "Finish", "Editar": "Edit", "Eliminar": "Delete", "Parada": "Save", "Ocasión": "Chance", "Penalti": "Penalty", "Falta": "Foul", "Otro": "Other", "Gol": "Goal", "Plantillas personales": "Personal templates", "Etiqueta del evento": "Event label", "Etiqueta personalizada": "Custom label", "Nombre": "Name", "Predeterminada": "Default", "Crear": "Create", "Guardar cambios": "Save changes", "Duplicar": "Duplicate", "Buscar repetición": "Search replays", "Mostrar número dentro del reloj": "Show period number inside the clock", "El marcador vuelve después de retirar el bottom del gol.": "The scoreboard returns after the goal lower third clears."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"REPETICIONES": "REPRISER", "MARCAR": "MARKERA", "LANZAR + GUARDAR": "SPELA + SPARA", "SIN REPETICIÓN": "UTAN REPRIS", "Plugin conectado": "Plugin ansluten", "Todos los eventos": "Alla händelser", "Planos": "Klipp", "Preview": "Förhandsvisning", "Lanzar": "Sänd", "Guardar vídeo": "Spara video", "Abrir carpeta": "Öppna mapp", "Segundos": "Sekunder", "¿Añadir otro plano?": "Lägga till ett klipp till?", "Continuar": "Fortsätt", "Terminar": "Slutför", "Editar": "Redigera", "Eliminar": "Ta bort", "Parada": "Räddning", "Ocasión": "Målchans", "Penalti": "Straff", "Falta": "Regelbrott", "Otro": "Annat", "Gol": "Mål", "Plantillas personales": "Personliga mallar", "Etiqueta del evento": "Händelsetyp", "Etiqueta personalizada": "Egen etikett", "Nombre": "Namn", "Predeterminada": "Standard", "Crear": "Skapa", "Guardar cambios": "Spara ändringar", "Duplicar": "Duplicera", "Buscar repetición": "Sök repriser", "Mostrar número dentro del reloj": "Visa periodnumret i klockan", "El marcador vuelve después de retirar el bottom del gol.": "Resultattavlan återkommer när målgrafiken har försvunnit."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"REPETICIONES": "OPAKOVÁNÍ", "MARCAR": "OZNAČIT", "LANZAR + GUARDAR": "PŘEHRÁT + ULOŽIT", "SIN REPETICIÓN": "BEZ OPAKOVÁNÍ", "Plugin conectado": "Plugin připojen", "Todos los eventos": "Všechny události", "Planos": "Záběry", "Preview": "Náhled", "Lanzar": "Odvysílat", "Guardar vídeo": "Uložit video", "Abrir carpeta": "Otevřít složku", "Segundos": "Sekundy", "¿Añadir otro plano?": "Přidat další záběr?", "Continuar": "Pokračovat", "Terminar": "Dokončit", "Editar": "Upravit", "Eliminar": "Odstranit", "Parada": "Zákrok", "Ocasión": "Šance", "Penalti": "Trestné střílení", "Falta": "Faul", "Otro": "Jiné", "Gol": "Gól", "Plantillas personales": "Osobní šablony", "Etiqueta del evento": "Štítek události", "Etiqueta personalizada": "Vlastní štítek", "Nombre": "Název", "Predeterminada": "Výchozí", "Crear": "Vytvořit", "Guardar cambios": "Uložit změny", "Duplicar": "Duplikovat", "Buscar repetición": "Hledat opakování", "Mostrar número dentro del reloj": "Zobrazit číslo periody v hodinách", "El marcador vuelve después de retirar el bottom del gol.": "Ukazatel skóre se vrátí po skrytí gólové grafiky."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"REPETICIONES": "UUSINNAT", "MARCAR": "MERKITSE", "LANZAR + GUARDAR": "TOISTA + TALLENNA", "SIN REPETICIÓN": "EI UUSINTAA", "Plugin conectado": "Plugin yhdistetty", "Todos los eventos": "Kaikki tapahtumat", "Planos": "Otokset", "Preview": "Esikatselu", "Lanzar": "Lähetä", "Guardar vídeo": "Tallenna video", "Abrir carpeta": "Avaa kansio", "Segundos": "Sekunnit", "¿Añadir otro plano?": "Lisätäänkö toinen otos?", "Continuar": "Jatka", "Terminar": "Valmis", "Editar": "Muokkaa", "Eliminar": "Poista", "Parada": "Torjunta", "Ocasión": "Maalipaikka", "Penalti": "Rangaistuslaukaus", "Falta": "Rike", "Otro": "Muu", "Gol": "Maali", "Plantillas personales": "Omat mallipohjat", "Etiqueta del evento": "Tapahtuman tunniste", "Etiqueta personalizada": "Oma tunniste", "Nombre": "Nimi", "Predeterminada": "Oletus", "Crear": "Luo", "Guardar cambios": "Tallenna muutokset", "Duplicar": "Monista", "Buscar repetición": "Hae uusintoja", "Mostrar número dentro del reloj": "Näytä erän numero kellossa", "El marcador vuelve después de retirar el bottom del gol.": "Tulostaulu palaa maaligrafiikan poistuttua."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"REPETICIONES": "WIEDERHOLUNGEN", "MARCAR": "MARKIEREN", "LANZAR + GUARDAR": "ABSPIELEN + SPEICHERN", "SIN REPETICIÓN": "OHNE WIEDERHOLUNG", "Plugin conectado": "Plugin verbunden", "Todos los eventos": "Alle Ereignisse", "Planos": "Einstellungen", "Preview": "Vorschau", "Lanzar": "Senden", "Guardar vídeo": "Video speichern", "Abrir carpeta": "Ordner öffnen", "Segundos": "Sekunden", "¿Añadir otro plano?": "Weitere Einstellung hinzufügen?", "Continuar": "Weiter", "Terminar": "Fertig", "Editar": "Bearbeiten", "Eliminar": "Löschen", "Parada": "Parade", "Ocasión": "Torchance", "Penalti": "Strafstoß", "Falta": "Foul", "Otro": "Sonstiges", "Gol": "Tor", "Plantillas personales": "Persönliche Vorlagen", "Etiqueta del evento": "Ereignisbezeichnung", "Etiqueta personalizada": "Eigene Bezeichnung", "Nombre": "Name", "Predeterminada": "Standard", "Crear": "Erstellen", "Guardar cambios": "Änderungen speichern", "Duplicar": "Duplizieren", "Buscar repetición": "Wiederholungen suchen", "Mostrar número dentro del reloj": "Spielabschnitt in der Uhr anzeigen", "El marcador vuelve después de retirar el bottom del gol.": "Die Anzeigetafel erscheint nach dem Ausblenden der Torgrafik."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.en, {"Red local": "Local network", "Deshacer eliminación": "Undo deletion", "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos.": "The computer responds at this address. Use the same Wi-Fi network without device isolation.", "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.": "The server is not responding over the local network. Check local network permission and that Live is accessible to other devices."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"Red local": "Lokalt nätverk", "Deshacer eliminación": "Ångra borttagning", "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos.": "Datorn svarar på denna adress. Använd samma Wi-Fi utan isolering mellan enheter.", "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.": "Servern svarar inte på det lokala nätverket. Kontrollera nätverksbehörigheten och att Live är tillgängligt för andra enheter."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"Red local": "Místní síť", "Deshacer eliminación": "Vrátit smazání", "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos.": "Počítač na této adrese odpovídá. Použijte stejnou Wi-Fi bez izolace zařízení.", "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.": "Server v místní síti neodpovídá. Zkontrolujte oprávnění místní sítě a dostupnost Live pro ostatní zařízení."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"Red local": "Lähiverkko", "Deshacer eliminación": "Kumoa poisto", "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos.": "Tietokone vastaa tässä osoitteessa. Käytä samaa Wi-Fi-verkkoa ilman laitteiden eristystä.", "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.": "Palvelin ei vastaa lähiverkossa. Tarkista lähiverkon käyttöoikeus ja että Live on muiden laitteiden käytettävissä."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"Red local": "Lokales Netzwerk", "Deshacer eliminación": "Löschen rückgängig machen", "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos.": "Der Computer antwortet unter dieser Adresse. Verwende dasselbe WLAN ohne Geräteisolierung.", "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.": "Der Server antwortet nicht im lokalen Netzwerk. Prüfe die Netzwerkberechtigung und ob Live für andere Geräte erreichbar ist."});
function textTranslation(value, language) {
  if (language === "es") return value;
  return APP_TRANSLATIONS_BY_LANGUAGE[language]?.[value] || APP_TRANSLATIONS[value] || value;
}

const PLAYER_POSITION_TRANSLATIONS = {
  es: { goalkeeper: "Portero", defender: "Defensa", midfielder: "Medio", forward: "Delantero", coach: "Entrenador", player_coach: "Jugador-entrenador", none: "Sin posición", left_back: "Lateral izquierdo", center_back: "Central", right_back: "Lateral derecho", pivot: "Pivote", left_wing: "Extremo izquierdo", right_wing: "Extremo derecho" },
  en: { goalkeeper: "Goalkeeper", defender: "Defender", midfielder: "Midfielder", forward: "Forward", coach: "Coach", player_coach: "Player-coach", none: "No position", left_back: "Left back", center_back: "Centre back", right_back: "Right back", pivot: "Pivot", left_wing: "Left wing", right_wing: "Right wing" },
  sv: { goalkeeper: "Målvakt", defender: "Back", midfielder: "Center", forward: "Forward", coach: "Tränare", player_coach: "Spelande tränare", none: "Ingen position", left_back: "Vänsternia", center_back: "Mittnia", right_back: "Högernia", pivot: "Mittsexa", left_wing: "Vänstersexa", right_wing: "Högersexa" },
  cs: { goalkeeper: "Brankář", defender: "Obránce", midfielder: "Střední hráč", forward: "Útočník", coach: "Trenér", player_coach: "Hrající trenér", none: "Bez pozice", left_back: "Levá spojka", center_back: "Střední spojka", right_back: "Pravá spojka", pivot: "Pivot", left_wing: "Levé křídlo", right_wing: "Pravé křídlo" },
  fi: { goalkeeper: "Maalivahti", defender: "Puolustaja", midfielder: "Keskushyökkääjä", forward: "Hyökkääjä", coach: "Valmentaja", player_coach: "Pelaajavalmentaja", none: "Ei pelipaikkaa", left_back: "Vasen takapelaaja", center_back: "Keskustakapelaaja", right_back: "Oikea takapelaaja", pivot: "Viivapelaaja", left_wing: "Vasen laituri", right_wing: "Oikea laituri" },
  de: { goalkeeper: "Torhüter", defender: "Verteidiger", midfielder: "Center", forward: "Stürmer", coach: "Trainer", player_coach: "Spielertrainer", none: "Keine Position", left_back: "Rückraum links", center_back: "Rückraum Mitte", right_back: "Rückraum rechts", pivot: "Kreisläufer", left_wing: "Linksaußen", right_wing: "Rechtsaußen" },
};


Object.assign(APP_TRANSLATIONS, {
  "Introduce un correo electrónico válido.": "Enter a valid email address.",
  "Si la cuenta existe, recibirás un correo para restablecer la contraseña.": "If the account exists, you will receive a password reset email.",
  "Perfil actualizado.": "Profile updated.",
  "Foto de perfil actualizada.": "Profile picture updated.",
  "Foto de perfil eliminada.": "Profile picture removed.",
  "Selecciona una imagen válida.": "Select a valid image.",
  "La imagen no puede superar 8 MB.": "The image cannot exceed 8 MB.",
  "No se ha podido leer la imagen seleccionada.": "The selected image could not be read.",
  "La nueva contraseña debe tener al menos 8 caracteres.": "The new password must be at least 8 characters long.",
  "Las contraseñas no coinciden.": "The passwords do not match.",
  "Contraseña actualizada correctamente.": "Password updated successfully."
});

Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Olvidé mi contraseña":"Jag har glömt mitt lösenord", "Mi cuenta":"Mitt konto", "Nombre visible":"Visningsnamn",
  "Protegida":"Skyddat", "La contraseña actual nunca puede consultarse. Sólo puede sustituirse por una nueva.":"Det nuvarande lösenordet kan aldrig visas. Det kan bara ersättas med ett nytt.",
  "Guardar perfil":"Spara profil", "Eliminar foto":"Ta bort foto", "Seguridad":"Säkerhet", "Cambiar contraseña":"Byt lösenord",
  "Nueva contraseña":"Nytt lösenord", "Repetir contraseña":"Upprepa lösenord", "Actualizar contraseña":"Uppdatera lösenord",
  "Cambiar foto de perfil":"Byt profilbild", "Perfil actualizado.":"Profilen har uppdaterats.", "Foto de perfil actualizada.":"Profilbilden har uppdaterats.",
  "Foto de perfil eliminada.":"Profilbilden har tagits bort.", "Las contraseñas no coinciden.":"Lösenorden matchar inte."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Olvidé mi contraseña":"Zapomněl jsem heslo", "Mi cuenta":"Můj účet", "Nombre visible":"Zobrazované jméno",
  "Protegida":"Chráněno", "La contraseña actual nunca puede consultarse. Sólo puede sustituirse por una nueva.":"Aktuální heslo nelze zobrazit. Lze jej pouze nahradit novým.",
  "Guardar perfil":"Uložit profil", "Eliminar foto":"Odstranit fotografii", "Seguridad":"Zabezpečení", "Cambiar contraseña":"Změnit heslo",
  "Nueva contraseña":"Nové heslo", "Repetir contraseña":"Zopakovat heslo", "Actualizar contraseña":"Aktualizovat heslo",
  "Cambiar foto de perfil":"Změnit profilovou fotografii", "Perfil actualizado.":"Profil byl aktualizován.", "Foto de perfil actualizada.":"Profilová fotografie byla aktualizována.",
  "Foto de perfil eliminada.":"Profilová fotografie byla odstraněna.", "Las contraseñas no coinciden.":"Hesla se neshodují."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Olvidé mi contraseña":"Unohdin salasanani", "Mi cuenta":"Oma tili", "Nombre visible":"Näyttönimi",
  "Protegida":"Suojattu", "La contraseña actual nunca puede consultarse. Sólo puede sustituirse por una nueva.":"Nykyistä salasanaa ei voi tarkastella. Sen voi vain korvata uudella.",
  "Guardar perfil":"Tallenna profiili", "Eliminar foto":"Poista kuva", "Seguridad":"Tietoturva", "Cambiar contraseña":"Vaihda salasana",
  "Nueva contraseña":"Uusi salasana", "Repetir contraseña":"Toista salasana", "Actualizar contraseña":"Päivitä salasana",
  "Cambiar foto de perfil":"Vaihda profiilikuva", "Perfil actualizado.":"Profiili päivitetty.", "Foto de perfil actualizada.":"Profiilikuva päivitetty.",
  "Foto de perfil eliminada.":"Profiilikuva poistettu.", "Las contraseñas no coinciden.":"Salasanat eivät täsmää."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Olvidé mi contraseña":"Passwort vergessen", "Mi cuenta":"Mein Konto", "Nombre visible":"Anzeigename",
  "Protegida":"Geschützt", "La contraseña actual nunca puede consultarse. Sólo puede sustituirse por una nueva.":"Das aktuelle Passwort kann nie angezeigt werden. Es kann nur durch ein neues ersetzt werden.",
  "Guardar perfil":"Profil speichern", "Eliminar foto":"Foto entfernen", "Seguridad":"Sicherheit", "Cambiar contraseña":"Passwort ändern",
  "Nueva contraseña":"Neues Passwort", "Repetir contraseña":"Passwort wiederholen", "Actualizar contraseña":"Passwort aktualisieren",
  "Cambiar foto de perfil":"Profilbild ändern", "Perfil actualizado.":"Profil aktualisiert.", "Foto de perfil actualizada.":"Profilbild aktualisiert.",
  "Foto de perfil eliminada.":"Profilbild entfernt.", "Las contraseñas no coinciden.":"Die Passwörter stimmen nicht überein."
});


// Phase 47 · OCR perspective + opt-in privacy vocabulary
Object.assign(APP_TRANSLATIONS, {
  "Ajustar perspectiva":"Adjust perspective", "Quitar perspectiva":"Remove perspective",
  "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.":"Perspective correction is off. If the scoreboard is viewed at an angle, select its four corners.",
  "Perspectiva activa. El preview y el OCR trabajan sobre el marcador rectificado.":"Perspective active. Preview and OCR use the rectified scoreboard.",
  "Perspectiva OCR eliminada.":"OCR perspective removed.",
  "Perspectiva aplicada. Vuelve a dibujar Local, Tiempo y Visitante sobre la imagen rectificada.":"Perspective applied. Draw Home, Time and Away again on the rectified image.",
  "Privacidad":"Privacy", "Mejora colaborativa del OCR":"Collaborative OCR improvement", "VOLUNTARIO":"OPTIONAL",
  "Compartir muestras OCR difíciles para ayudar a mejorar SecretariatPro":"Share difficult OCR samples to help improve SecretariatPro",
  "Si está activado, sólo se envían pequeños recortes del marcador correspondientes a Local, Tiempo o Visitante cuando la lectura resulta difícil. No se envían vídeo completo, audio, nombres de equipos, jugadores, pabellón ni datos del partido.":"When enabled, only small Home, Time or Away scoreboard crops are sent when recognition is difficult. Full video, audio, team names, players, venue and match data are never sent.",
  "La compartición está desactivada.":"Sharing is disabled.",
  "Compartición OCR activada para este espacio de trabajo.":"OCR sharing is enabled for this workspace.",
  "La asociación gestiona esta preferencia para todos sus realizadores.":"The organisation manages this preference for all of its producers.",
  "La migración de privacidad OCR todavía no está disponible.":"The OCR privacy migration is not available yet."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {
  "Ajustar perspectiva":"Justera perspektiv", "Quitar perspectiva":"Ta bort perspektiv",
  "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.":"Perspektivkorrigering är avstängd. Om resultattavlan ses snett, välj dess fyra hörn.",
  "Privacidad":"Integritet", "Mejora colaborativa del OCR":"Gemensam OCR-förbättring", "VOLUNTARIO":"FRIVILLIGT",
  "Compartir muestras OCR difíciles para ayudar a mejorar SecretariatPro":"Dela svåra OCR-exempel för att förbättra SecretariatPro",
  "Si está activado, sólo se envían pequeños recortes del marcador correspondientes a Local, Tiempo o Visitante cuando la lectura resulta difícil. No se envían vídeo completo, audio, nombres de equipos, jugadores, pabellón ni datos del partido.":"När funktionen är aktiverad skickas endast små utsnitt för Hemma, Tid eller Borta när avläsningen är svår. Full video, ljud, lagnamn, spelare, arena och matchdata skickas aldrig.",
  "La compartición está desactivada.":"Delning är avstängd.", "Compartición OCR activada para este espacio de trabajo.":"OCR-delning är aktiverad för denna arbetsyta.",
  "La asociación gestiona esta preferencia para todos sus realizadores.":"Organisationen hanterar denna inställning för alla sina producenter."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {
  "Ajustar perspectiva":"Upravit perspektivu", "Quitar perspectiva":"Odebrat perspektivu",
  "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.":"Korekce perspektivy je vypnutá. Pokud je časomíra snímána zešikma, vyberte její čtyři rohy.",
  "Privacidad":"Soukromí", "Mejora colaborativa del OCR":"Společné zlepšování OCR", "VOLUNTARIO":"DOBROVOLNÉ",
  "Compartir muestras OCR difíciles para ayudar a mejorar SecretariatPro":"Sdílet obtížné vzorky OCR a pomoci zlepšit SecretariatPro",
  "Si está activado, sólo se envían pequeños recortes del marcador correspondientes a Local, Tiempo o Visitante cuando la lectura resulta difícil. No se envían vídeo completo, audio, nombres de equipos, jugadores, pabellón ni datos del partido.":"Je-li funkce zapnutá, odesílají se pouze malé výřezy Domácí, Čas nebo Hosté při obtížném rozpoznání. Celé video, zvuk, názvy týmů, hráči, hala ani údaje o utkání se nikdy neodesílají.",
  "La compartición está desactivada.":"Sdílení je vypnuté.", "Compartición OCR activada para este espacio de trabajo.":"Sdílení OCR je pro tento pracovní prostor zapnuté.",
  "La asociación gestiona esta preferencia para todos sus realizadores.":"Organizace spravuje toto nastavení pro všechny své producenty."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {
  "Ajustar perspectiva":"Säädä perspektiiviä", "Quitar perspectiva":"Poista perspektiivi",
  "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.":"Perspektiivikorjaus ei ole käytössä. Jos tulostaulu näkyy vinossa, valitse sen neljä kulmaa.",
  "Privacidad":"Tietosuoja", "Mejora colaborativa del OCR":"Yhteinen OCR-parannus", "VOLUNTARIO":"VAPAAEHTOINEN",
  "Compartir muestras OCR difíciles para ayudar a mejorar SecretariatPro":"Jaa vaikeita OCR-näytteitä SecretariatPron parantamiseksi",
  "Si está activado, sólo se envían pequeños recortes del marcador correspondientes a Local, Tiempo o Visitante cuando la lectura resulta difícil. No se envían vídeo completo, audio, nombres de equipos, jugadores, pabellón ni datos del partido.":"Kun toiminto on käytössä, lähetetään vain pieniä Koti-, Aika- tai Vieras-rajauksia vaikeista tunnistuksista. Koko videota, ääntä, joukkueiden nimiä, pelaajia, hallia tai ottelutietoja ei koskaan lähetetä.",
  "La compartición está desactivada.":"Jakaminen on pois käytöstä.", "Compartición OCR activada para este espacio de trabajo.":"OCR-jakaminen on käytössä tässä työtilassa.",
  "La asociación gestiona esta preferencia para todos sus realizadores.":"Organisaatio hallitsee tätä asetusta kaikkien tuottajiensa puolesta."
});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {
  "Ajustar perspectiva":"Perspektive anpassen", "Quitar perspectiva":"Perspektive entfernen",
  "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.":"Die Perspektivkorrektur ist deaktiviert. Wenn die Anzeigetafel schräg aufgenommen wird, wähle ihre vier Ecken.",
  "Privacidad":"Datenschutz", "Mejora colaborativa del OCR":"Gemeinsame OCR-Verbesserung", "VOLUNTARIO":"FREIWILLIG",
  "Compartir muestras OCR difíciles para ayudar a mejorar SecretariatPro":"Schwierige OCR-Beispiele teilen, um SecretariatPro zu verbessern",
  "Si está activado, sólo se envían pequeños recortes del marcador correspondientes a Local, Tiempo o Visitante cuando la lectura resulta difícil. No se envían vídeo completo, audio, nombres de equipos, jugadores, pabellón ni datos del partido.":"Wenn aktiviert, werden bei schwieriger Erkennung nur kleine Ausschnitte für Heim, Zeit oder Gast gesendet. Vollständiges Video, Audio, Teamnamen, Spieler, Halle und Spieldaten werden niemals gesendet.",
  "La compartición está desactivada.":"Teilen ist deaktiviert.", "Compartición OCR activada para este espacio de trabajo.":"OCR-Teilen ist für diesen Arbeitsbereich aktiviert.",
  "La asociación gestiona esta preferencia para todos sus realizadores.":"Die Organisation verwaltet diese Einstellung für alle Produzenten."
});

Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.sv, {"Siete inicial":"Startsjua","Selección de 7 titulares":"Välj sju startspelare","Actualizar fuentes":"Uppdatera källor","Vídeo del marcador":"Resultattavlevideo","Sin fuente seleccionada":"Ingen källa vald","Selecciona una ventana o cámara, captura un preview y arrastra sobre cada valor del marcador.":"Välj ett fönster eller en kamera, ta en förhandsvisning och dra över varje värde på resultattavlan."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.cs, {"Siete inicial":"Základní sedmička","Selección de 7 titulares":"Výběr sedmi hráčů základní sestavy","Actualizar fuentes":"Obnovit zdroje","Vídeo del marcador":"Video výsledkové tabule","Sin fuente seleccionada":"Není vybrán zdroj","Selecciona una ventana o cámara, captura un preview y arrastra sobre cada valor del marcador.":"Vyber okno nebo kameru, vytvoř náhled a označ každou hodnotu výsledkové tabule."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.fi, {"Siete inicial":"Aloitusseitsikko","Selección de 7 titulares":"Valitse seitsemän avauspelaajaa","Actualizar fuentes":"Päivitä lähteet","Vídeo del marcador":"Tulostauluvideo","Sin fuente seleccionada":"Lähdettä ei ole valittu","Selecciona una ventana o cámara, captura un preview y arrastra sobre cada valor del marcador.":"Valitse ikkuna tai kamera, ota esikatselu ja rajaa jokainen tulostaulun arvo."});
Object.assign(APP_TRANSLATIONS_BY_LANGUAGE.de, {"Siete inicial":"Start-Sieben","Selección de 7 titulares":"Sieben Startspieler auswählen","Actualizar fuentes":"Quellen aktualisieren","Vídeo del marcador":"Anzeigetafel-Video","Sin fuente seleccionada":"Keine Quelle ausgewählt","Selecciona una ventana o cámara, captura un preview y arrastra sobre cada valor del marcador.":"Wähle ein Fenster oder eine Kamera, erstelle eine Vorschau und markiere jeden Wert der Anzeigetafel."});


Object.assign(APP_TRANSLATIONS, {
  "Finalizar partido":"Finish match",
  "Partido finalizado":"Match finished",
  "Cierre de partido":"Match closure",
  "Confirmar resultado final":"Confirm final score",
  "Comprueba el resultado antes de cerrar el partido.":"Check the score before closing the match.",
  "Al confirmar, el partido se marcará como finalizado y este resultado alimentará clasificación y estadísticas.":"Once confirmed, the match will be marked as finished and this score will feed standings and statistics.",
  "El partido se ha finalizado correctamente.":"The match has been finished successfully.",
  "Carga primero un partido online.":"Load an online match first."
});

Object.assign(APP_TRANSLATIONS, {
  "PERIODO":"PERIOD", "Cola de gráficos":"Graphics queue", "Prepara el siguiente gráfico y compruébalo antes de enviarlo a emisión.":"Prepare and check the next graphic before sending it on air.",
  "Gráfico":"Graphic", "Nombre de la entrada":"Cue name", "Retirar tras":"Hide after", "Añadir a la cola":"Add to queue",
  "Siguiente en emisión":"Next on air", "Lanzar siguiente gráfico":"Take next graphic", "Orden de emisión":"Running order", "Vaciar":"Clear",
  "La cola está vacía.":"The queue is empty.", "Subir":"Move up", "Bajar":"Move down", "Retirar":"Remove", "retirada manual":"manual hide",
  "Clips y highlights":"Clips and highlights", "Las marcas guardan el búfer de repetición de OBS. Los clips seleccionados se unen en orden cronológico.":"Markers save the OBS replay buffer. Selected clips are joined in chronological order.",
  "Búfer activo":"Buffer active", "Búfer detenido":"Buffer stopped", "Iniciar búfer":"Start buffer", "Detener búfer":"Stop buffer", "Marcar jugada":"Mark play",
  "Todavía no hay clips guardados.":"No clips have been saved yet.", "Nombre del vídeo":"Video name", "Generar vídeo seleccionado":"Build selected video",
  "Guardando después de la marca…":"Saving after the marker…", "Clip guardado":"Saved clip", "Ver":"View", "Abrir vídeo":"Open video",
  "Guardar replay automáticamente al registrar un gol":"Automatically save a replay when a goal is recorded", "Post-roll del replay (segundos)":"Replay post-roll (seconds)",
  "Fuente de navegador para tus directos":"Browser source for your broadcasts", "Copiar enlace del overlay":"Copy overlay link",
  "En OBS o en otro programa de emisión, añade una fuente de navegador de 1920 × 1080 y pega este enlace. Mantén SecretariatPro abierto en este ordenador.":"In OBS or another broadcasting app, add a 1920 × 1080 browser source and paste this link. Keep SecretariatPro open on this computer."
});

function canonicalPlayerPosition(value) {
  const raw = String(value || "").trim();
  const normalized = raw.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[._-]+/g, " ").replace(/\s+/g, " ");
  if (!normalized) return "none";
  if (["por", "portero", "portera", "goalkeeper", "goalie", "keeper", "gk", "mv", "br", "tw", "maalivahti", "malvakt", "brankar", "torhuter"].includes(normalized)) return "goalkeeper";
  if (["lateral izquierdo", "left back", "leftback", "izquierdo lateral", "li"].includes(normalized)) return "left_back";
  if (["central", "center back", "centre back", "centerback", "centreback", "cb"].includes(normalized)) return "center_back";
  if (["lateral derecho", "right back", "rightback", "derecho lateral", "ld"].includes(normalized)) return "right_back";
  if (["pivote", "pivot", "line player", "lineplayer"].includes(normalized)) return "pivot";
  if (["extremo izquierdo", "left wing", "leftwing", "ei"].includes(normalized)) return "left_wing";
  if (["extremo derecho", "right wing", "rightwing", "ed"].includes(normalized)) return "right_wing";
  if (["def", "defensa", "defender", "defence", "defense", "back", "obr", "obrance", "puolustaja", "verteidiger"].includes(normalized)) return "defender";
  if (["med", "medio", "mediocentro", "mid", "midfielder", "center", "centre", "stredni hrac", "keskushyokkaaja"].includes(normalized)) return "midfielder";
  if (["del", "delantero", "delantera", "forward", "striker", "wing", "utocnik", "hyokkaaja", "sturmer"].includes(normalized)) return "forward";
  if (["player coach", "jugador entrenador", "jugador y entrenador", "spelande tranare", "hrajici trener", "pelaajavalmentaja", "spielertrainer"].includes(normalized)) return "player_coach";
  if (["coach", "entrenador", "entrenadora", "trainer", "tranare", "trener", "valmentaja"].includes(normalized)) return "coach";
  return "";
}
function translatePlayerPosition(value) {
    const combined = String(value || "").trim();
    if (combined.endsWith("_coach") && combined !== "player_coach") return translatePlayerPosition(combined.slice(0,-6)) + " + " + (PLAYER_POSITION_TRANSLATIONS[app.language]?.coach || "Coach");
  const raw = String(value || "").trim();
  const canonical = canonicalPlayerPosition(raw);
  if (!canonical) return raw;
  return PLAYER_POSITION_TRANSLATIONS[app.language]?.[canonical] || PLAYER_POSITION_TRANSLATIONS.en[canonical] || raw;
}
function applyLanguage(language = "en") {
  const previousLanguage = app.language;
  app.language = ["es", "en", "sv", "cs", "fi", "de"].includes(language) ? language : "en";
  document.documentElement.lang = app.language;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (["SCRIPT", "STYLE"].includes(node.parentElement?.tagName)) continue;
    if (!originalTextNodes.has(node)) originalTextNodes.set(node, node.nodeValue);
    const original = originalTextNodes.get(node);
    const trimmed = original.trim();
    if (!trimmed || !APP_TRANSLATIONS[trimmed]) continue;
    node.nodeValue = original.replace(trimmed, textTranslation(trimmed, app.language));
  }
  const titleMap = { "Configuración": "Settings", "Cuenta": "Account", "Minimizar": "Minimise", "Cerrar": "Close" };
  $$('[title], [aria-label]').forEach((element) => {
    ["title", "aria-label"].forEach((attribute) => {
      const current = element.getAttribute(attribute);
      if (!current) return;
      const originalKey = `i18nOriginal${attribute.replace(/-./g, (m) => m[1].toUpperCase())}`;
      if (!element.dataset[originalKey]) element.dataset[originalKey] = current;
      const original = element.dataset[originalKey];
      const translated = app.language === "es" ? original : (APP_TRANSLATIONS_BY_LANGUAGE[app.language]?.[original] || titleMap[original] || APP_TRANSLATIONS[original] || original);
      element.setAttribute(attribute, translated);
    });
  });
  if (previousLanguage !== app.language) {
    app.rosterSignature = "";
    queueMicrotask(() => {
      if (!app.snapshot) return;
      renderRosters();
      renderPlayerProfile(app.snapshot?.state?.statistics?.player_profile || {});
      if (app.productionFlow.kind) renderProductionWorkflow();
    });
  }
}
const systemThemeQuery = window.matchMedia("(prefers-color-scheme: light)");
function resolveAppTheme(preference) {
  if (preference === "system") return systemThemeQuery.matches ? "light" : "dark";
  return preference === "light" ? "light" : "dark";
}
function applyAppAppearance(appearance = DEFAULT_APPEARANCE) {
  const merged = mergeObject(DEFAULT_APPEARANCE, appearance);
  const preference = ["dark", "light", "system"].includes(merged.app_theme) ? merged.app_theme : "system";
  const theme = resolveAppTheme(preference);
  document.documentElement.dataset.themePreference = preference;
  document.documentElement.dataset.appTheme = theme;
  // Phase 24: app colours are fixed by the selected dark/light theme.
  // Overlay colour customisation must never leak into the control interface.
  ["--primary", "--primary-2", "--cyan", "--app-accent", "--bg", "--surface", "--surface-2", "--text", "--deck-key", "--deck-key-active", "--deck-accent", "--deck-text"]
    .forEach((name) => document.documentElement.style.removeProperty(name));
  updateAppearancePreviews(merged);
}
function updateAppearancePreviews(appearance = DEFAULT_APPEARANCE) {
  const merged = mergeObject(DEFAULT_APPEARANCE, appearance);
  const map = {
    "--preview-score-bg": merged.scoreboard.background,
    "--preview-score-name": merged.scoreboard.name_box,
    "--preview-score-text": merged.scoreboard.text,
    "--preview-bottom-body": merged.bottom_bar.body,
    "--preview-bottom-middle": merged.bottom_bar.middle,
    "--preview-bottom-text": merged.bottom_bar.text,
    "--preview-bottom-secondary": merged.bottom_bar.secondary_text,
    "--preview-panel-bg": merged.panels.background,
    "--preview-panel-surface": merged.panels.surface,
    "--preview-panel-accent": merged.panels.accent,
    "--preview-panel-text": merged.panels.text,
  };
  Object.entries(map).forEach(([key, value]) => document.documentElement.style.setProperty(key, value));
}

function populateAppearanceFields(appearance) {
  const merged = mergeObject(DEFAULT_APPEARANCE, appearance || {});
  $$('[data-appearance-path]').forEach((field) => {
    if (document.activeElement !== field) field.value = getByPath(merged, field.dataset.appearancePath) || "#000000";
  });
  if (document.activeElement !== $("#settings-app-theme")) $("#settings-app-theme").value = merged.app_theme;
  return merged;
}
function collectAppearance() {
  const draft = mergeObject(DEFAULT_APPEARANCE, app.appearanceDraft || {});
  draft.app_theme = $("#settings-app-theme")?.value || "system";
  $$('[data-appearance-path]').forEach((field) => setByPath(draft, field.dataset.appearancePath, field.value));
  return draft;
}


async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = payload?.detail || payload?.message || payload || `Error ${response.status}`;
    const error = new Error(String(message)); error.status = response.status; throw error;
  }
  return payload;
}

function toast(message, error = false) {
  const region = $("#toast-region");
  const element = document.createElement("div");
  element.className = `toast${error ? " is-error" : ""}`;
  element.textContent = textTranslation(String(message), app.language);
  region.appendChild(element);
  setTimeout(() => {
    element.style.opacity = "0";
    element.style.transform = "translateX(12px)";
    setTimeout(() => element.remove(), 220);
  }, 3400);
}

function logoUrl(value) {
  if (!value) return "";
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  return value.startsWith("/") ? value : `/${value}`;
}

function initials(value = "") {
  const raw = String(value || "").trim();
  const source = raw.includes("@") ? raw.split("@")[0] : raw;
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  if (!parts.length) return "?";
  return (parts.length > 1 ? parts.slice(0, 2).map((part) => part[0]).join("") : parts[0].slice(0, 2)).toUpperCase();
}

function setProfileAvatar(image, container, url = "") {
  const cleanUrl = String(url || "").trim();
  if (image) {
    image.hidden = !cleanUrl;
    if (cleanUrl && image.src !== cleanUrl) image.src = cleanUrl;
    if (!cleanUrl) image.removeAttribute("src");
  }
  container?.classList.toggle("has-avatar", Boolean(cleanUrl));
}

function normalizedRosterRow(row) {
  const player = row.player || row;
  const first = player.first_name || "";
  const last = player.last_name || "";
  const name = player.display_name || [first, last].filter(Boolean).join(" ") || player.name || "Jugador";
  return {
    player_id: String(row.player_id || player.id || ""),
    number: String(row.shirt_number ?? row.number ?? ""),
    name,
    first_name: first,
    last_name: last,
    position: String(player.position || row.position || "").toUpperCase(),
    captain: Boolean(row.captain || row.is_captain),
    member_type: String(row.member_type || "player").toLowerCase(),
  };
}

function stateRoster(teamKey) {
  const onlineRows = app.snapshot?.online?.rosters?.[teamKey] || [];
  if (onlineRows.length) return onlineRows.map(normalizedRosterRow);
  return (app.snapshot?.state?.statistics?.lineups?.[`${teamKey}_players`] || []).map(normalizedRosterRow);
}

function attendanceSet(teamKey) {
  return new Set((app.snapshot?.online?.attendance?.[teamKey] || []).map(String));
}

function calledUpPlayers(teamKey) {
  const selected = attendanceSet(teamKey);
  return (app.players[teamKey] || []).filter((player) => selected.has(String(player.player_id)));
}

function renderLive(live) {
  const scores = live?.scores || {};
  const powerplay = live?.powerplay || {};
  const ocrRuntime = live?.ocr_runtime || {};

  setAnimatedValue("#home-score", scores.team1_score ?? "0", "homeScore");
  setAnimatedValue("#away-score", scores.team2_score ?? "0", "awayScore");
  setAnimatedValue("#match-clock", scores.time ?? "00:00", "clock");
  const productionHome = $("#production-home-score");
  const productionAway = $("#production-away-score");
  const productionClock = $("#production-clock");
  if (productionHome) productionHome.textContent = scores.team1_score ?? "0";
  if (productionAway) productionAway.textContent = scores.team2_score ?? "0";
  if (productionClock) productionClock.textContent = scores.time ?? "00:00";

  const rawOCR = ocrRuntime.readings || {};
  const homeReading = $("#ocr-home-reading");
  const awayReading = $("#ocr-away-reading");
  const timeReading = $("#ocr-time-reading");
  if (homeReading) homeReading.textContent = rawOCR.team1_score || scores.team1_score || "0";
  if (awayReading) awayReading.textContent = rawOCR.team2_score || scores.team2_score || "0";
  if (timeReading) timeReading.textContent = rawOCR.time || scores.time || "00:00";
  updateOCRReadingMeta(ocrRuntime);

  renderPowerplay("home", powerplay.team1 || {});
  renderPowerplay("away", powerplay.team2 || {});

  const ocrStatus = $("#ocr-status");
  if (ocrStatus) {
    const configured = Boolean(app.snapshot?.ocr?.source_id || app.snapshot?.ocr?.window_title);
    const running = Boolean(ocrRuntime.running);
    ocrStatus.className = `status-pill ${running ? "is-ok" : configured ? "is-warn" : ""}`;
    ocrStatus.innerHTML = `<i></i>${running ? "OCR activo" : configured ? "OCR detenido" : "OCR pendiente"}`;
  }

  if (app.snapshot) {
    app.snapshot.scores = { ...(app.snapshot.scores || {}), ...scores };
    app.snapshot.ocr_runtime = { ...(app.snapshot.ocr_runtime || {}), ...ocrRuntime };
    app.snapshot.state = app.snapshot.state || {};
    app.snapshot.state.powerplay = powerplay;
    if (live.score_control) app.snapshot.score_control = live.score_control;
    if (live.graphic_scores) app.snapshot.graphic_scores = live.graphic_scores;
  }
}

function renderGraphicsQueue(queue) {
  const tr = (value) => textTranslation(value, app.language);
  const count = $("#graphics-queue-count");
  if (count) count.textContent = String(queue.length);
  const list = $("#graphics-cue-list");
  const preview = $("#graphics-cue-preview");
  const take = $("#graphics-cue-take");
  if (!list || !preview || !take) return;
  list.replaceChildren();
  if (!queue.length) {
    list.textContent = tr("La cola está vacía.");
    take.disabled = true;
    if (preview.dataset.cueId) { preview.dataset.cueId = ""; preview.src = "about:blank"; }
    return;
  }
  if (!queue.some((cue) => cue.id === app.graphicsPreviewCue)) app.graphicsPreviewCue = queue[0].id;
  queue.forEach((cue, index) => {
    const row = document.createElement("div");
    row.className = `graphics-cue-row${cue.id === app.graphicsPreviewCue ? " is-previewing" : ""}`;
    const copy = document.createElement("button");
    copy.type = "button"; copy.className = "graphics-cue-copy"; copy.dataset.previewCue = cue.id;
    const base = cue.label || friendlyPanel(cue.panel);
    const detail = `${cue.panel === "lineups" ? tr(cue.lineup_team === "team2" ? "Visitante" : "Local") : tr(friendlyPanel(cue.panel))}${cue.duration_seconds ? ` · ${cue.duration_seconds} s` : ` · ${tr("retirada manual")}`}`;
    copy.innerHTML = `<b>${index + 1}. ${escapeHTML(base)}</b><small>${escapeHTML(detail)}</small>`;
    const actions = document.createElement("div"); actions.className = "graphics-cue-actions";
    actions.innerHTML = `<button type="button" class="cue-icon" data-move-cue="${escapeHTML(cue.id)}" data-position="${index - 1}" ${index === 0 ? "disabled" : ""} title="${tr("Subir")}">↑</button><button type="button" class="cue-icon" data-move-cue="${escapeHTML(cue.id)}" data-position="${index + 1}" ${index === queue.length - 1 ? "disabled" : ""} title="${tr("Bajar")}">↓</button><button type="button" class="cue-icon danger" data-discard-cue="${escapeHTML(cue.id)}" title="${tr("Retirar")}">×</button>`;
    row.append(copy, actions); list.appendChild(row);
  });
  take.disabled = false;
  if (preview.dataset.cueId !== app.graphicsPreviewCue) {
    preview.dataset.cueId = app.graphicsPreviewCue;
    preview.src = `/overlay.html?cue=${encodeURIComponent(app.graphicsPreviewCue)}`;
  }
}

function sequenceStepRow(step = {}) {
  const panels = ["scoreboard", "prematch", "intermission", "lineups", "top_scorers", "standings", "penalties", "bottom_bar"];
  return `<div class="graphics-sequence-step"><select data-sequence-panel>${panels.map((panel) => `<option value="${panel}" ${panel === (step.panel || "scoreboard") ? "selected" : ""}>${escapeHTML(textTranslation(friendlyPanel(panel), app.language))}</option>`).join("")}</select><select data-sequence-team ${step.panel === "lineups" ? "" : "hidden"}><option value="team1" ${step.lineup_team !== "team2" ? "selected" : ""}>${textTranslation("Local", app.language)}</option><option value="team2" ${step.lineup_team === "team2" ? "selected" : ""}>${textTranslation("Visitante", app.language)}</option></select><label>${textTranslation("Visible", app.language)}<input data-sequence-duration type="number" min="1" max="120" value="${Number(step.duration_seconds || 5)}"> s</label><label>${textTranslation("Intervalo", app.language)}<input data-sequence-interval type="number" min="0" max="60" value="${Number(step.interval_seconds || 0)}"> s</label><button class="cue-icon danger" data-remove-sequence-step type="button" title="${textTranslation("Retirar", app.language)}">×</button></div>`;
}

function renderGraphicsSequences(sequences = [], active = null) {
  const list = $("#graphics-sequence-list");
  if (!list) return;
  list.innerHTML = sequences.length ? sequences.map((sequence) => `<article class="graphics-sequence-row"><div><b>${escapeHTML(sequence.name)}</b><small>${sequence.steps.length} ${textTranslation("gráficos", app.language)}${active?.id === sequence.id ? ` · ${textTranslation("En emisión", app.language)} ${active.step}/${active.total}` : ""}</small></div><div><button class="button primary compact-button" data-run-sequence="${escapeHTML(sequence.id)}" type="button">${textTranslation("Lanzar", app.language)}</button><button class="button secondary compact-button" data-edit-sequence="${escapeHTML(sequence.id)}" type="button">${textTranslation("Editar", app.language)}</button><button class="cue-icon danger" data-delete-sequence="${escapeHTML(sequence.id)}" type="button">×</button></div></article>`).join("") : `<div class="empty-state">${textTranslation("Todavía no hay secuencias personales.", app.language)}</div>`;
}

function openSequenceEditor(sequence = null) {
  app.sequenceDraft = {id: sequence?.id || "", steps: (sequence?.steps || [{panel:"scoreboard", duration_seconds:5, interval_seconds:0, lineup_team:"team1"}]).map((step) => ({...step}))};
  $("#graphics-sequence-name").value = sequence?.name || "";
  $("#graphics-sequence-editor").hidden = false;
  renderSequenceDraft();
}

function renderSequenceDraft() {
  $("#graphics-sequence-steps").innerHTML = app.sequenceDraft.steps.map(sequenceStepRow).join("");
}

function readSequenceDraft() {
  return $$(".graphics-sequence-step", $("#graphics-sequence-steps")).map((row) => ({panel:$("[data-sequence-panel]", row).value, lineup_team:$("[data-sequence-team]", row).value, duration_seconds:Number($("[data-sequence-duration]", row).value || 5), interval_seconds:Number($("[data-sequence-interval]", row).value || 0)}));
}

async function saveGraphicsSequence() {
  const body = {name:$("#graphics-sequence-name").value.trim(), steps:readSequenceDraft()};
  if (!body.name) return toast(textTranslation("Pon un nombre a la secuencia", app.language), true);
  try {
    const id = app.sequenceDraft.id;
    const payload = await api(`/api/graphics/sequences${id ? `/${encodeURIComponent(id)}` : ""}`, {method:id ? "PATCH" : "POST", body:JSON.stringify(body)});
    app.snapshot.settings.graphics_sequences = payload.sequences;
    $("#graphics-sequence-editor").hidden = true;
    renderGraphicsSequences(payload.sequences, app.snapshot?.state?.graphics_sequence_run);
    toast(textTranslation("Secuencia guardada.", app.language));
  } catch (error) { toast(error.message, true); }
}

async function addGraphicsCue() {
  try {
    const snapshot = await api("/api/graphics/cues", {method:"POST", body:JSON.stringify({
      panel: $("#graphics-cue-panel").value, lineup_team: $("#graphics-cue-team").value,
      label: $("#graphics-cue-label").value.trim(),
      duration_seconds: Number($("#graphics-cue-duration").value || 0),
    })});
    $("#graphics-cue-label").value = "";
    render(snapshot); toast("Gráfico preparado en la cola.");
  } catch (error) { toast(error.message, true); }
}

function renderPeriodControl(state, settings) {
  const select = $("#match-period-control");
  if (!select) return;
  const config = settings?.appearance?.period_strip || {segments: 3, labels: ["1", "2", "3"]};
  const segments = Math.max(1, Math.min(12, Number(config.segments || 3)));
  const current = Math.max(1, Number(state?.match?.period || 1));
  select.innerHTML = Array.from({length: segments}, (_, index) => `<option value="${index + 1}">${escapeHTML(config.labels?.[index] || String(index + 1))}</option>`).join("");
  select.value = String(Math.min(current, segments));
}

const replayText = (text) => textTranslation(text, app.language);
function renderReplays(replays = {}) {
  app.replayLibrary = replays;
  const clips = replays.clips || [];
  const multicam = replays.status?.backend === "multicam-plugin" && Boolean(replays.status?.available);
  $("#secretariatdeck-highlight").hidden = !multicam;
  $("#replay-connection-indicator").hidden = !multicam;
  $("#replay-connection-indicator").textContent = replayText("Plugin conectado");
  $("#replay-mark").disabled = !multicam || !replays.status?.active || Boolean(replays.status?.playing);
  $("#replay-ready-count").textContent = String((replays.highlights || []).length);
  const status = $("#replay-buffer-status");
  status.hidden = !multicam;
  status.className = "status-pill replay-connected";
  status.textContent = `${replayText("Plugin conectado")} · ${Number(replays.status?.camera_count || 0)} CAM`;
  $("#replay-buffer-toggle").hidden = !multicam;
  $("#replay-buffer-toggle").dataset.active = replays.status?.active ? "1" : "0";
  $("#replay-buffer-toggle").textContent = replayText(replays.status?.active ? "Detener búfer" : "Iniciar búfer");
  $("#replay-plugin-controls").hidden = !multicam || !replays.status?.playing;
  $("#replay-plugin-detail").textContent = replayText("Repetición en programa.");
  $("#replay-out").disabled = !replays.status?.playing;
  $("#replay-take").hidden = true;
  $("#replay-previous-camera").hidden = Boolean(replays.status?.library_playback);
  $("#replay-next-camera").hidden = Boolean(replays.status?.library_playback);
  $("#replay-list").innerHTML = clips.filter(c => c.status === "pending" || c.status === "failed").map(c => `<div class="replay-row"><b>${escapeHTML(c.label)}</b><small>${escapeHTML(c.status === "failed" ? c.error : replayText("Guardando después de la marca…"))}</small></div>`).join("");
  renderReplayLibrary();
  renderReplayComposer(replays);
}
function renderReplayLibrary() {
  const replays = app.replayLibrary || {};
  const signature = JSON.stringify([replays.highlights, replays.status?.available, replays.status?.playing, $("#replay-search")?.value, $("#replay-filter")?.value, $("#replay-period-filter")?.value, app.language]);
  if (app.libraryRenderSignature === signature) return;
  app.libraryRenderSignature = signature;
  const query = ($("#replay-search")?.value || "").toLocaleLowerCase();
  const filter = $("#replay-filter")?.value || "";
  const all = replays.highlights || [];
  const periodSelect = $("#replay-period-filter"), period = periodSelect?.value || "";
  const checked = new Set($$("[data-replay-include]:checked").map(el => el.dataset.replayInclude));
  if (periodSelect) {
    const periods = [...new Set(all.map(x => Number(x.period || 1)))].sort((a,b)=>a-b);
    periodSelect.innerHTML = '<option value="">—</option>' + periods.map(p => `<option value="${p}">${p}</option>`).join("");
    periodSelect.value = period;
  }
  const options = [...new Set(all.map(x => x.event_type || "Replay"))];
  const select = $("#replay-filter");
  if (select) { select.innerHTML = `<option value="">${replayText("Todos los eventos")}</option>` + options.map(x => `<option ${x === filter ? "selected" : ""} value="${escapeHTML(x)}">${escapeHTML(replayText(x))}</option>`).join(""); }
  const rows = all.filter(x => (!period || Number(x.period || 1) === Number(period)) && (!filter || (x.event_type || "Replay") === filter) && `${x.title} ${x.player} ${x.assistant} ${(x.tags || []).join(" ")} ${x.match_time}`.toLocaleLowerCase().includes(query));
  $("#replay-exports").innerHTML = rows.map(item => {
    const id = escapeHTML(item.id), url = `/api/replays/media/${encodeURIComponent(item.id)}`;
    return `<article class="replay-library-card"><input type="checkbox" data-replay-include="${id}" aria-label="${escapeHTML(item.title || item.label || "Replay")}" ${checked.has(item.id) ? "checked" : ""}>${item.thumbnail ? `<img loading="lazy" src="/api/replays/thumbnail/${encodeURIComponent(item.id)}" alt="">` : '<div class="replay-thumb-placeholder">▶</div>'}<div><small>${escapeHTML(replayText(item.event_type || "Replay"))} · P${Number(item.period || 1)} · ${escapeHTML(item.match_time || "--:--")}</small><h3>${escapeHTML(item.title || item.label || "Replay")}</h3><p>${Number(item.duration_seconds || 0).toFixed(1)} s · ${Number(item.shot_count || 1)} ${replayText("Planos")}</p><div class="action-row"><button class="button secondary compact-button" data-replay-preview="${id}">${replayText("Preview")}</button><button class="button primary compact-button" data-replay-launch="${id}" ${!replays.status?.available || replays.status?.playing ? "disabled" : ""}>${replayText("Lanzar")}</button><a class="button secondary compact-button" download="${escapeHTML(item.filename || 'replay.mp4')}" href="${url}">${replayText("Guardar vídeo")}</a><button class="text-button" data-replay-folder>${replayText("Abrir carpeta")}</button><button class="text-button" data-replay-delete="${id}">${replayText("Eliminar")}</button></div></div></article>`;
  }).join("") || `<p class="empty-state">${replayText("Todavía no hay clips guardados.")}</p>`;
}
function defaultReplaySegments() { return []; }
function readReplayComposition() { return (app.replayComposer.segments || []).map(s => ({...s})); }
function mountReplayDeck() {
  closeModal("replay-modal");
  if (app.activeView !== "production") switchView("production");
  app.productionFlow = {kind:"replay"};
  $("#production-bottom-row").classList.add("is-workflow");
  const card = $("#production-workflow-card"); card.hidden = false; card.classList.add("is-replay-workflow");
  const grid = $("#production-workflow-grid");
  if (!grid.contains($("#replay-composer"))) {
    grid.replaceChildren($("#replay-label-picker"), $("#replay-composer"));
  }
}
function closeReplayDeck() {
  const modal = $("#replay-modal .modal-card");
  modal.insertBefore($("#replay-label-picker"), $("#replay-library-area"));
  modal.insertBefore($("#replay-composer"), $("#replay-library-area"));
  $("#production-workflow-card").classList.remove("is-replay-workflow");
  app.replayComposer = {clipId:"",goalFlow:false,segments:[]};
  app.replayPickingLabel = false;
  app.productionFlow = {};
  $("#production-workflow-close").textContent = replayText("Cancelar");
  closeProductionWorkflow();
}
async function skipReplayDeck() {
  try {
    if (app.replayComposer.goalFlow) render(await api("/api/replays/goal/skip",{method:"POST"}));
    closeReplayDeck();
  } catch(error) { toast(error.message,true); }
}
function renderReplayComposer(replays = app.replayLibrary || {}) {
  const c = app.replayComposer;
  const host = $("#replay-composer");
  host.hidden = !c.clipId;
  $("#replay-label-picker").hidden = !app.replayPickingLabel;
  $("#replay-library-area").hidden = Boolean(c.clipId || app.replayPickingLabel);
  $("#replay-modal-close").hidden = Boolean(c.goalFlow);
  if (app.productionFlow.kind === "replay") {
    $("#production-workflow-kicker").textContent = "SecretariatDeck";
    $("#production-workflow-title").textContent = replayText(app.replayPickingLabel ? "Etiqueta del evento" : ({camera:"Cámara",duration:"Segundos",speed:"Velocidad",next:"¿Añadir otro plano?",done:"Componer repetición"}[c.stage || "camera"]));
    $("#production-workflow-help").textContent = replayText(c.goalFlow ? "Repetición del gol" : "Componer repetición");
    $("#production-workflow-summary").textContent = (c.segments || []).map(s=>`CAM ${s.camera} · ${s.duration_seconds}s · ${s.speed_percent}%`).join(" → ");
    $("#production-workflow-back").hidden = app.replayPickingLabel || c.stage === "camera";
    $("#production-workflow-close").textContent = replayText(c.goalFlow ? "SIN REPETICIÓN" : "Cancelar");
    $("#production-workflow-close").disabled = Boolean(app.replaySubmitting);
  }
  if (!c.clipId) return;
  const clip = (replays.clips || []).find(row => row.id === c.clipId);
  const ready = clip?.status === "ready" && replays.status?.event_ready && !replays.status?.library_playback;
  const cameras = (clip?.angles || []).map(x => Number(x.camera));
  if (!cameras.length) for (let i=1; i<=Number(replays.status?.camera_count || 1); i++) cameras.push(i);
  $("#replay-composer-state").textContent = replayText(ready ? "Lista para componer" : "Esperando cámaras…");
  $("#replay-composer-title").textContent = clip?.label || replayText(c.goalFlow ? "Repetición del gol" : "Componer repetición");
  $("#replay-goal-skip").hidden = false;
  $("#replay-composer-save").hidden = true;
  $("#replay-composer-add").hidden = true;
  $("#replay-composer-take").disabled = !ready || !c.segments?.length || app.replaySubmitting;
  const stage = c.stage || "camera";
  host.dataset.stage = stage;
  const stepTitle = {camera:"Cámara", duration:"Segundos", speed:"Velocidad", next:"¿Añadir otro plano?"};
  let body = "";
  if (stage === "camera") body = cameras.map(n => `<button class="button secondary" data-shot-camera="${n}">CAM ${n}</button>`).join("");
  if (stage === "duration") body = [3,5,7,10].map(n => `<button class="button secondary" data-shot-duration="${n}">${n}s</button>`).join("") + `<label>${replayText("Segundos")}<input id="shot-manual-seconds" type="number" min="1" max="60" value="5"></label><button class="button secondary" data-shot-manual>${replayText("Continuar")}</button>`;
  if (stage === "speed") body = [100,75,50,25].map(n => `<button class="button secondary" data-shot-speed="${n}">${n}%</button>`).join("");
  if (stage === "next") body = `<button class="button secondary" data-shot-another ${c.segments.length >= 6 ? "disabled" : ""}>${replayText("Añadir plano")}</button><button class="button primary" data-shot-finish>${replayText("Terminar")}</button>`;
  const guideSignature = JSON.stringify([stage,cameras,c.segments?.length,app.language]);
  if ($("#replay-guide").dataset.signature !== guideSignature) {
    $("#replay-guide").dataset.signature = guideSignature;
    $("#replay-guide").innerHTML = stage === "done" ? "" : `<h3>${replayText(stepTitle[stage])}</h3><div class="replay-choice-grid">${body}</div>`;
  }
  const signature = JSON.stringify(c.segments);
  if ($("#replay-composer-segments").dataset.signature !== signature) {
    $("#replay-composer-segments").dataset.signature = signature;
    $("#replay-composer-segments").innerHTML = (c.segments || []).map((s,i) => `<div class="replay-shot-summary"><b>${i+1} · CAM ${s.camera}</b><span>${s.duration_seconds}s · ${s.speed_percent}%</span><button class="text-button" data-shot-edit="${i}">${replayText("Editar")}</button><button class="text-button" data-shot-delete="${i}">${replayText("Eliminar")}</button></div>`).join("");
  }
  renderReplayTemplates();
}
async function syncReplayComposition() { /* Drafts stay local until the producer finishes; OBS playback is never touched by preview. */ }
async function saveReplayComposition(playNow = true) {
  if (app.replaySubmitting) return;
  const segments = readReplayComposition();
  if (!segments.length) return;
  app.replaySubmitting = true;
  renderReplayComposer();
  try {
    await api("/api/replays/composition", {method:"POST", body:JSON.stringify({clip_id:app.replayComposer.clipId, segments, play_now:playNow, save_video:true, goal_flow:app.replayComposer.goalFlow})});
    closeReplayDeck();
    toast(replayText("Guardando vídeo del evento…"));
  } catch(error) { toast(error.message, true); }
  finally { app.replaySubmitting = false; renderReplayComposer(); }
}
function captureReplayNow(label, team = "") {
  if (!app.snapshot?.replays?.status?.active && !app.replayLibrary?.status?.active) return Promise.resolve("");
  return api("/api/replays/mark", {method:"POST", body:JSON.stringify({label, team, match_time:app.snapshot?.scores?.time || "", post_roll_seconds:0})})
    .then(payload => payload.marker?.id || "").catch(error => { toast(error.message, true); return ""; });
}
function chooseReplayLabel() {
  if (app.replayComposer.goalFlow) return;
  app.replayComposer = {clipId:"",goalFlow:false,segments:[]};
  app.pendingReplayCapture = captureReplayNow("Replay");
  app.replayPickingLabel = true;
  $("#replay-label-options").innerHTML = ["Parada","Ocasión","Penalti","Falta","Otro"].map(x => `<button class="button secondary" data-event-label="${x}">${replayText(x)}</button>`).join("");
  mountReplayDeck();
  renderReplayComposer();
}
function renderReplayTemplates() {
  const select = $("#replay-template-select");
  const value = select.value;
  select.innerHTML = `<option value="">${replayText("Plantillas personales")}</option>` + (app.replayTemplates || []).map(t => `<option value="${escapeHTML(t.id)}">${t.default ? "★ " : ""}${escapeHTML(t.name)}</option>`).join("");
  select.value = value;
}
async function loadReplayTemplates() {
  try { app.replayTemplates = await api("/api/replays/templates"); renderReplayTemplates(); } catch(error) { toast(error.message,true); }
}
async function replayTemplateAction(action) {
  const selected = (app.replayTemplates || []).find(t => t.id === $("#replay-template-select").value);
  try {
    if (action === "delete" && selected) app.replayTemplates = await api(`/api/replays/templates/${encodeURIComponent(selected.id)}`,{method:"DELETE"});
    else {
      const name = $("#replay-template-name").value.trim() || selected?.name;
      if (!name || !readReplayComposition().length) return;
      const payload = {name, segments:readReplayComposition(), default:$("#replay-template-default").checked};
      if (action === "update" && selected) payload.id = selected.id;
      if (action === "duplicate" && selected) { payload.name = `${selected.name} (2)`; payload.default = false; }
      app.replayTemplates = await api("/api/replays/templates",{method:"POST",body:JSON.stringify(payload)});
    }
    renderReplayTemplates();
  } catch(error) { toast(error.message,true); }
}

async function controlReplay(action) {
  try {
    renderReplays(await api(`/api/replays/${action}`, {method:"POST"}));
    if (action === "out" && app.replayComposer.goalFlow) {
      app.replayComposer = {clipId:"", goalFlow:false, segments:[]};
      closeModal("replay-modal");
    }
  }
  catch (error) { toast(error.message, true); }
}

async function toggleReplayBuffer() {
  const active = $("#replay-buffer-toggle")?.dataset.active === "1";
  try { renderReplays(await api(`/api/replays/${active ? "stop" : "start"}`, {method:"POST"})); }
  catch (error) { toast(error.message, true); }
}

async function markReplay({goalFlow = false, markerId = "", label = ""} = {}) {
  if (!goalFlow && !markerId && !label) return chooseReplayLabel();
  if (app.replayMarking) return;
  app.replayMarking = true;
  try {
    if (!markerId && app.pendingReplayCapture) { markerId = await app.pendingReplayCapture; app.pendingReplayCapture = null; if (!markerId) return; }
    if (markerId && label) await api(`/api/replays/${encodeURIComponent(markerId)}`, {method:"PATCH", body:JSON.stringify({label})});
    let payload;
    if (markerId) payload = await api("/api/replays");
    else { const time = app.snapshot?.scores?.time || ""; payload = await api("/api/replays/mark", {method:"POST", body:JSON.stringify({label, match_time:time, post_roll_seconds:Number(app.snapshot?.settings?.obs?.replay_post_roll_seconds || 0)})}); markerId = payload.marker?.id || ""; }
    const preset = (app.replayTemplates || []).find(t => t.default);
    app.replayComposer = {clipId:markerId, goalFlow, segments:preset ? preset.segments.map(s=>({...s})) : [], stage:preset ? "done" : "camera"};
    app.replayPickingLabel = false;
    mountReplayDeck();
    renderReplays(payload);
  } catch(error) { toast(error.message,true); }
  finally { app.replayMarking = false; }
}

async function buildHighlights() {
  const ids = $$('[data-replay-include]:checked').map((input) => input.dataset.replayInclude);
  if (!ids.length) return;
  const button = $("#replay-build-highlights"); button.disabled = true; button.textContent = "Generando…";
  try {
    const payload = await api("/api/replays/highlights", {method:"POST", body:JSON.stringify({title:$("#replay-highlight-title").value.trim() || "Highlights", clip_ids:ids})});
    renderReplays(payload); toast("Vídeo Full HD de highlights generado.");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = textTranslation("Generar vídeo seleccionado", app.language); }
}

async function takeGraphicsCue() {
  const cue = app.snapshot?.state?.graphics_queue?.[0];
  if (!cue) return;
  const button = $("#graphics-cue-take"); button.disabled = true;
  try {
    render(await api(`/api/graphics/cues/${encodeURIComponent(cue.id)}/take`, {method:"POST"}));
    toast(`${friendlyPanel(cue.panel)} en emisión.`);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = !app.snapshot?.state?.graphics_queue?.length; }
}

function render(snapshot) {
  app.snapshot = snapshot;
  if (snapshot.settings?.language) app.language = snapshot.settings.language;
  const templates = snapshot.settings?.replay_templates || [];
  const templateSignature = JSON.stringify([templates, app.language]);
  if (app.templateSignature !== templateSignature) {
    app.templateSignature = templateSignature;
    app.replayTemplates = templates;
    renderReplayTemplates();
  }
  const state = snapshot.state || {};
  const scores = snapshot.scores || {};
  const online = snapshot.online || {};
  const overlays = snapshot.overlays || {};
  const obs = snapshot.obs || {};
  const ocrRuntime = snapshot.ocr_runtime || {};
  const scoreControl = snapshot.score_control || { mode: "ocr", editable: false };

  renderSubscriptionGate(online);
  if (online.access?.allowed && (!app.socket || app.socket.readyState > WebSocket.OPEN)) connectSocket();

  $("#api-status").className = "status-pill is-ok";
  const subscriptionAllowed = Boolean(online.access?.allowed);
  $("#online-status").className = `status-pill ${subscriptionAllowed ? "is-ok" : online.connected ? "is-warn" : ""}`;
  $("#online-status").innerHTML = `<i></i>${subscriptionAllowed ? "Membresía activa" : online.connected ? "Membresía pendiente" : "Sin sesión"}`;
  const hasOCR = Boolean(snapshot.ocr?.window_title);
  const ocrRunning = Boolean(ocrRuntime.running);
  $("#ocr-status").className = `status-pill ${ocrRunning ? "is-ok" : hasOCR ? "is-warn" : ""}`;
  $("#ocr-status").innerHTML = `<i></i>${ocrRunning ? "OCR activo" : hasOCR ? "OCR detenido" : "OCR pendiente"}`;
  $("#obs-status").hidden = !obs.connected;
  $("#online-status").hidden = !online.connected;
  $("#obs-status").className = `status-pill ${obs.connected ? "is-ok" : "is-warn"}`;
  $("#obs-status").innerHTML = `<i></i>${obs.connected ? "OBS conectado" : "OBS desconectado"}`;

  const currentMatch = online.match || {};
  const hasActiveMatch = Boolean(currentMatch.id);
  const matchFinished = String(currentMatch.status || "").toLowerCase() === "finished";
  const finishButton = $("#finish-match-button");
  if (finishButton) {
    finishButton.disabled = !hasActiveMatch || matchFinished;
    finishButton.textContent = matchFinished ? "Partido finalizado" : "Finalizar partido";
  }
  const matchLabel = hasActiveMatch ? (currentMatch.label || state.online?.match_label || "Partido cargado") : "Seleccionar partido";
  $("#context-match-name").textContent = matchLabel;
  $("#match-context").classList.toggle("has-match", hasActiveMatch);

  const accountProfile = online.profile || {};
  const accountLabel = accountProfile.display_name || online.email || "";
  $("#profile-initials").textContent = online.connected ? initials(accountLabel) : "?";
  $("#profile-button").classList.toggle("is-online", Boolean(online.connected));
  setProfileAvatar($("#profile-avatar"), $("#profile-button"), online.connected ? accountProfile.avatar_url : "");

  const home = hasActiveMatch ? (state.team1 || {}) : {};
  const away = hasActiveMatch ? (state.team2 || {}) : {};
  $("#home-name").textContent = home.name || "LOCAL";
  $("#away-name").textContent = away.name || "VISITANTE";
  $("#pp-home-name").textContent = home.name || "Local";
  $("#pp-away-name").textContent = away.name || "Visitante";
  const productionHomeName = $("#production-home-name");
  const productionAwayName = $("#production-away-name");
  if (productionHomeName) productionHomeName.textContent = home.name || "LOCAL";
  if (productionAwayName) productionAwayName.textContent = away.name || "VISITANTE";
  setAnimatedValue("#home-score", scores.team1_score || "0", "homeScore");
  setAnimatedValue("#away-score", scores.team2_score || "0", "awayScore");
  setAnimatedValue("#match-clock", scores.time || "00:00", "clock");
  const productionHome = $("#production-home-score");
  const productionAway = $("#production-away-score");
  const productionClock = $("#production-clock");
  if (productionHome) productionHome.textContent = scores.team1_score || "0";
  if (productionAway) productionAway.textContent = scores.team2_score || "0";
  if (productionClock) productionClock.textContent = scores.time || "00:00";
  const rawOCR = ocrRuntime.readings || {};
  $("#ocr-home-reading").textContent = rawOCR.team1_score || scores.team1_score || "0";
  $("#ocr-away-reading").textContent = rawOCR.team2_score || scores.team2_score || "0";
  $("#ocr-time-reading").textContent = rawOCR.time || scores.time || "00:00";
  updateOCRReadingMeta(ocrRuntime);

  const manualMode = scoreControl.mode === "manual";
  $$('[data-score-mode]').forEach((button) => button.classList.toggle("is-active", button.dataset.scoreMode === scoreControl.mode));
  $$('[data-score-team]').forEach((button) => {
    button.disabled = !manualMode;
    button.title = manualMode ? "Editar resultado manual" : "Resultado bloqueado por OCR";
  });
  $("#score-source-copy").textContent = manualMode ? "MANUAL · edición activa" : "OCR · bloqueado";
  $("#score-source-help").textContent = manualMode
    ? "Los botones modifican el resultado; el OCR sigue leyendo el reloj."
    : "El resultado procede del marcador físico y no puede editarse aquí.";
  $("#score-source-copy").classList.toggle("is-manual", manualMode);
  $("#goal-increment-score").disabled = !manualMode;
  if (!manualMode) $("#goal-increment-score").checked = false;
  $("#goal-source-note").textContent = manualMode
    ? "Puedes registrar el gol y, si lo marcas, incrementar también el resultado manual."
    : "En modo OCR el gol se registra en el acta, pero no modifica el resultado.";
  $("#home-panel").style.setProperty("--team-color", home.stripe_color || "#4b7cff");
  $("#away-panel").style.setProperty("--team-color", away.stripe_color || "#f15368");
  setImage($("#home-logo"), home.logo);
  setImage($("#away-logo"), away.logo);

  const powerplayHome = state.powerplay?.team1 || {};
  const powerplayAway = state.powerplay?.team2 || {};
  renderPowerplay("home", powerplayHome);
  renderPowerplay("away", powerplayAway);
  renderEmptyNet(state.empty_net || {});
  renderShootout(state.penalty_shootout || {}, home, away);

  $$('[data-overlay]').forEach((button) => {
    const panel = button.dataset.overlay;
    let active = Boolean(overlays[panel]);
    if (panel === "lineups" && button.dataset.lineupTeam) {
      active = Boolean(state.statistics?.lineups?.[`${button.dataset.lineupTeam}_status`]);
    }
    button.classList.toggle("is-active", active);
    const deckState = button.querySelector("[data-deck-state]");
    if (deckState) deckState.textContent = active ? "ON AIR" : "LISTO";
  });

  const activeFullscreen = ["prematch", "intermission", "lineups", "top_scorers", "standings", "player_profile", "penalties"]
    .find((key) => overlays[key]);
  const activeOverlayCopy = $("#active-overlay-copy");
  if (activeOverlayCopy) activeOverlayCopy.textContent = activeFullscreen ? `Panel activo: ${friendlyPanel(activeFullscreen)}` : "Sin paneles a pantalla completa";

  const activePanels = ["scoreboard", "bottom_bar", "prematch", "intermission", "lineups", "top_scorers", "standings", "player_profile", "penalties"]
    .filter((key) => Boolean(overlays[key]));
  const deckCopy = $("#deck-status-copy");
  const deckMaster = deckCopy?.closest(".deck-master-state");
  if (deckCopy) deckCopy.textContent = activePanels.length
    ? `ON AIR · ${activePanels.map(friendlyPanel).join(" + ")}`
    : "Emisión limpia";
  if (deckMaster) deckMaster.classList.toggle("is-live", activePanels.length > 0);
  const productionActive = $("#production-active-copy");
  if (productionActive) productionActive.textContent = activePanels.length
    ? activePanels.map(friendlyPanel).join(" · ")
    : "Ninguno";
  const productionOnAir = $(".production-on-air");
  if (productionOnAir) productionOnAir.classList.toggle("is-idle", activePanels.length === 0);

  renderRosters();
  renderPlayerProfile(app.snapshot?.state?.statistics?.player_profile || {});
  renderStandings();
  renderEvents(online.events || []);
  renderOCR(snapshot.ocr || {}, ocrRuntime);
  renderProductionOBS(obs);
  renderGraphicsQueue(state.graphics_queue || []);
  renderGraphicsSequences(snapshot.settings?.graphics_sequences || [], state.graphics_sequence_run || null);
  renderPeriodControl(state, snapshot.settings || {});
  renderReplays(snapshot.replays || {});
  renderSettings(snapshot.settings || {}, snapshot.ocr_sample_delivery || {});
  renderAccount(online);
}

function setImage(image, value) {
  const url = logoUrl(value);
  if (url) {
    image.src = url;
    image.hidden = false;
  } else {
    image.removeAttribute("src");
    image.hidden = true;
  }
}

function setAnimatedValue(selector, value, key) {
  const element = $(selector);
  const text = String(value ?? "");
  if (!element) return;
  if (app.visualState[key] !== null && app.visualState[key] !== text) {
    element.classList.remove("value-pop");
    void element.offsetWidth;
    element.classList.add("value-pop");
  }
  element.textContent = text;
  app.visualState[key] = text;
}

function renderPowerplay(side, info) {
  const seconds = info.status
    ? Math.max(0, Number(info.remaining_seconds ?? 120))
    : 120;
  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  const key = side === "home" ? "ppHome" : "ppAway";
  setAnimatedValue(`#pp-${side}-time`, time, key);
  const element = $(`#pp-${side}-time`);
  if (element) element.classList.toggle("is-active", Boolean(info.status));

  const sync = $(`#pp-${side}-sync`);
  if (sync) {
    const state = String(info.clock_sync_state || (info.status ? "waiting" : "idle"));
    const detail = info.clock_sync_detail || (info.status ? "Esperando avance del reloj OCR" : "Sin expulsión activa");
    sync.className = `pp-sync-line is-${state}`;
    const copy = sync.querySelector("span");
    if (copy) copy.textContent = detail;
    sync.title = `Último OCR aceptado: ${info.last_ocr_match_seconds ?? "—"}`;
  }

  const productionBox = $(`#production-pp-${side}`);
  const productionTime = $(`#production-pp-${side}-time`);
  const productionPlayer = $(`#production-pp-${side}-player-display`);
  const productionStatus = $(`#production-pp-${side}-status`);
  if (productionBox) productionBox.classList.toggle("is-active", Boolean(info.status));
  if (productionTime) productionTime.textContent = time;
  if (productionPlayer) productionPlayer.textContent = info.status ? `#${String(info.player_number || "—").replace(/^#/, "")}` : "—";
  if (productionStatus) {
    productionStatus.textContent = info.status ? `${time} · #${String(info.player_number || "—").replace(/^#/, "")}` : "Sin PP";
    productionStatus.classList.toggle("is-active", Boolean(info.status));
  }

  const quickTeam = $(`#production-quick-pp-${side}`);
  if (quickTeam) quickTeam.hidden = !Boolean(info.status);
  refreshProductionPPCancelVisibility();
}

function renderEmptyNet(emptyNet = {}) {
  [["team1", "home"], ["team2", "away"]].forEach(([teamKey, side]) => {
    const active = Boolean(emptyNet?.[teamKey]);
    $$(`[data-empty-net="${teamKey}"]`).forEach((button) => {
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  });
}

async function toggleEmptyNet(teamKey) {
  try {
    const snapshot = await api(`/api/empty-net/${teamKey}/toggle`, { method: "POST" });
    render(snapshot);
    const active = Boolean(snapshot?.state?.empty_net?.[teamKey]);
    toast(`${teamKey === "team1" ? "Local" : "Visitante"} · EMPTY NET ${active ? "activado" : "desactivado"}`);
  } catch (error) { toast(error.message, true); }
}

function refreshProductionPPCancelVisibility() {
  const homeActive = !$("#production-quick-pp-home")?.hidden;
  const awayActive = !$("#production-quick-pp-away")?.hidden;
  const anyActive = homeActive || awayActive;
  const card = $("#production-quick-pp-card");
  const resizer = $("#production-resize-bottom");
  const row = $("#production-bottom-row");
  if (card) card.hidden = !anyActive;
  if (resizer) resizer.hidden = !anyActive;
  if (row) row.classList.toggle("has-active-pp", anyActive);
}

function sceneButtonCode(index) {
  const number = Number(index) + 1;
  return number < 100 ? `S${number}` : "OBS";
}

function fitProductionActionGrid() {
  const grid = $(".production-action-grid");
  if (!grid || grid.offsetParent === null) return;
  const buttons = $$(".production-action-key", grid).filter((button) => !button.hidden);
  const count = buttons.length;
  if (!count) return;

  const width = grid.clientWidth - 14;
  const height = grid.clientHeight - 14;
  const gap = 6;
  let best = null;
  for (let columns = 2; columns <= Math.min(count, 12); columns += 1) {
    const rows = Math.ceil(count / columns);
    const cellWidth = (width - gap * (columns - 1)) / columns;
    const cellHeight = (height - gap * (rows - 1)) / rows;
    if (cellWidth <= 0 || cellHeight <= 0) continue;
    const widthPenalty = Math.max(0, 112 - cellWidth) * 3;
    const heightPenalty = Math.max(0, 48 - cellHeight) * 4;
    const ratioPenalty = Math.abs((cellWidth / Math.max(cellHeight, 1)) - 2.15) * 7;
    const score = Math.min(cellWidth / 2.15, cellHeight) - widthPenalty - heightPenalty - ratioPenalty;
    if (!best || score > best.score) best = { columns, rows, score };
  }
  if (!best) return;
  grid.style.gridTemplateColumns = `repeat(${best.columns}, minmax(0, 1fr))`;
  grid.style.gridTemplateRows = `repeat(${best.rows}, minmax(0, 1fr))`;
}

function renderProductionOBS(obs = {}) {
  const host = $("#production-scene-buttons");
  if (!host) return;
  const connected = Boolean(obs.connected);
  const scenes = Array.isArray(obs.scenes) ? obs.scenes.map(String).filter(Boolean) : [];
  const program = String(obs.program || "");
  const signature = JSON.stringify({ connected, scenes, program });
  if (signature === app.obsSceneSignature) return;

  host.replaceChildren();
  if (connected) {
    scenes.forEach((scene, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "streamdeck-key production-action-key production-scene-key";
      button.dataset.obsScene = scene;
      button.title = `Cambiar programa de OBS a ${scene}`;
      button.setAttribute("aria-pressed", scene === program ? "true" : "false");
      button.classList.toggle("is-active", scene === program);

      const icon = document.createElement("span");
      icon.textContent = sceneButtonCode(index);
      const label = document.createElement("b");
      label.textContent = scene;
      const state = document.createElement("small");
      state.textContent = scene === program ? "EN PROGRAMA" : "ESCENA OBS";
      button.append(icon, label, state);
      host.appendChild(button);
    });
  }
  app.obsSceneSignature = signature;
  requestAnimationFrame(fitProductionActionGrid);
}

async function refreshProductionOBSStatus() {
  try {
    const obs = await api(`/api/obs/status?_=${Date.now()}`, { cache: "no-store" });
    if (app.snapshot) app.snapshot.obs = obs;
    renderProductionOBS(obs);
    const pill = $("#obs-status");
    if (pill) {
      pill.className = `status-pill ${obs.connected ? "is-ok" : "is-warn"}`;
      pill.innerHTML = `<i></i>${obs.connected ? "OBS conectado" : "OBS desconectado"}`;
    }
  } catch (_) { /* The main snapshot keeps the last known OBS state. */ }
}

function setProductionOBSPolling(active) {
  clearInterval(app.obsTimer);
  app.obsTimer = null;
  if (!active) return;
  refreshProductionOBSStatus();
  app.obsTimer = setInterval(refreshProductionOBSStatus, 1500);
}

async function setProgramScene(sceneName) {
  const requestedScene = String(sceneName || "").trim();
  if (!requestedScene) return toast("Conecta OBS para ver sus escenas.", true);
  try {
    const snapshot = await api("/api/obs/scenes/program", {
      method: "POST",
      body: JSON.stringify({ scene_name: requestedScene }),
    });
    // Force a redraw even when OBS returns the same scene list with a new Program scene.
    app.obsSceneSignature = "";
    render(snapshot);
    toast(`Escena en programa: ${requestedScene}`);
  } catch (error) { toast(error.message, true); }
}

function renderShootout(shootout, home, away) {
  $("#shootout-home-name").textContent = home.name || "LOCAL";
  $("#shootout-away-name").textContent = away.name || "VISITANTE";
  renderShootoutTeam("team1", "#shootout-home-attempts", shootout.team1 || []);
  renderShootoutTeam("team2", "#shootout-away-attempts", shootout.team2 || []);
}

function renderShootoutTeam(teamKey, selector, values) {
  const container = $(selector);
  if (!container) return;
  const normalized = Array.from({ length: 5 }, (_, index) => values[index] || null);
  container.innerHTML = "";
  normalized.forEach((value, index) => {
    const attempt = document.createElement("div");
    attempt.className = `shootout-attempt ${value === "goal" ? "is-goal" : value === "miss" ? "is-miss" : "is-pending"}`;
    attempt.innerHTML = `<span class="shootout-number">${index + 1}</span><div class="shootout-choices"></div>`;
    const choices = attempt.querySelector(".shootout-choices");
    [
      { outcome: null, label: "·", title: "Pendiente" },
      { outcome: "goal", label: "✓", title: "Gol" },
      { outcome: "miss", label: "×", title: "Fallo" },
    ].forEach((choice) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `shootout-choice is-${choice.outcome || "pending"}`;
      button.classList.toggle("is-selected", value === choice.outcome);
      button.dataset.penaltyTeam = teamKey;
      button.dataset.penaltyIndex = String(index);
      button.dataset.penaltyOutcome = choice.outcome || "";
      button.title = `Lanzamiento ${index + 1}: ${choice.title}`;
      button.textContent = choice.label;
      choices.appendChild(button);
    });
    container.appendChild(attempt);
  });
}

async function setPenaltyAttempt(button) {
  const outcome = button.dataset.penaltyOutcome || null;
  try {
    const snapshot = await api(`/api/penalties/${button.dataset.penaltyTeam}/${button.dataset.penaltyIndex}`, {
      method: "POST",
      body: JSON.stringify({ outcome }),
    });
    render(snapshot);
  } catch (error) { toast(error.message, true); }
}

function friendlyPanel(panel) {
  const labels = {
    prematch: ["Prematch", "Pre-match"],
    intermission: ["Intermission", "Intermission"],
    lineups: ["Alineaciones", "Lineups"],
    top_scorers: ["Máximos puntuadores", "Top scorers"],
    standings: ["Clasificación", "Standings"],
    player_profile: ["Perfil de jugador", "Player profile"],
    penalties: ["Penaltis", "Penalty shootout"],
    scoreboard: ["Marcador", "Scoreboard"],
    bottom_bar: ["Bottom bar", "Bottom bar"],
  };
  const values = labels[panel];
  return values ? (app.language === "en" ? values[1] : values[0]) : panel;
}

function renderRosters() {
  const rosters = { team1: stateRoster("team1"), team2: stateRoster("team2") };
  app.players = {
    team1: rosters.team1.filter((p) => p.member_type !== "coach"),
    team2: rosters.team2.filter((p) => p.member_type !== "coach"),
  };
  const signature = JSON.stringify({ language: app.language, sport_mode: liveSportMode(), players: app.players, attendance: app.snapshot?.online?.attendance || {} });
  if (signature === app.rosterSignature) {
    if (app.productionFlow.kind) renderProductionWorkflow();
    return;
  }
  app.rosterSignature = signature;
  populatePlayerProfileMenus();

  const stateLineups = app.snapshot?.state?.statistics?.lineups || {};
  app.starters = {
    team1: normalizeStarterState(stateLineups.team1_starters || {}),
    team2: normalizeStarterState(stateLineups.team2_starters || {}),
  };

  renderRosterList("team1", "#roster-home-list", "#roster-home-count");
  renderRosterList("team2", "#roster-away-list", "#roster-away-count");
  populatePowerplayMenus("team1", "home");
  populatePowerplayMenus("team2", "away");
  ["team1", "team2"].forEach((teamKey) => {
    const available = calledUpPlayers(teamKey).length > 0;
    $$(`#view-production [data-register-goal="${teamKey}"]`).forEach((button) => {
      button.disabled = !available;
      button.title = available ? "Registrar gol" : "Guarda la convocatoria antes de registrar el gol";
    });
  });
  renderFormationStructure();
  populateFormation();
  if (app.productionFlow.kind) renderProductionWorkflow();
}

function profilePlayers(teamKey) {
  return (app.players?.[teamKey] || []).filter((player) => player.member_type !== "coach");
}

function populatePlayerProfileMenus() {
  const teamSelect = $("#player-profile-team");
  const playerSelect = $("#player-profile-player");
  if (!teamSelect || !playerSelect) return;
  const teamKey = teamSelect.value === "team2" ? "team2" : "team1";
  const players = profilePlayers(teamKey);
  const previous = playerSelect.value;
  playerSelect.innerHTML = players.length ? '<option value="">Selecciona jugador</option>' : '<option value="">Carga un partido</option>';
  players.forEach((player) => playerSelect.append(new Option(playerOption(player), player.player_id)));
  if ([...playerSelect.options].some((option) => option.value === previous)) playerSelect.value = previous;
}

function renderPlayerProfile(profile = {}) {
  const preview = $("#player-profile-preview");
  if (preview) {
    if (profile.player_id) {
      preview.innerHTML = `<strong>#${escapeHTML(profile.number || "—")} ${escapeHTML(profile.name || "Jugador")}</strong>
        <span>${escapeHTML(translatePlayerPosition(profile.position) || "—")} · ${Number(profile.played || 0)} partidos · ${Number(profile.goals || 0)} goles · ${Number(profile.assists || 0)} asistencias</span>`;
    } else {
      preview.innerHTML = '<strong>Sin ficha seleccionada</strong><span>Selecciona un jugador para consultar sus estadísticas.</span>';
    }
  }
  const active = Boolean(profile.status);
  $$('[data-player-profile-team]').forEach((button) => {
    const sameTeam = profile.team_key === button.dataset.playerProfileTeam;
    button.classList.toggle("is-active", active && sameTeam);
    const state = button.querySelector("[data-profile-deck-state]");
    if (state) state.textContent = active && sameTeam ? "ON AIR" : "FICHA";
  });
}

async function updatePlayerProfileFromSelection(show = true) {
  const teamKey = $("#player-profile-team")?.value || "team1";
  const playerId = $("#player-profile-player")?.value || "";
  if (!playerId) return toast("Selecciona un jugador.", true);
  try {
    const snapshot = await api("/api/player-profile", {
      method: "POST",
      body: JSON.stringify({ team: teamKey, player_id: playerId, show }),
    });
    render(snapshot);
    toast(show ? "Ficha de jugador en emisión." : "Ficha de jugador actualizada.");
  } catch (error) { toast(error.message, true); }
}

async function showProductionPlayerProfile(teamKey, playerId) {
  try {
    const snapshot = await api("/api/player-profile", {
      method: "POST",
      body: JSON.stringify({ team: teamKey, player_id: playerId, show: true }),
    });
    closeProductionWorkflow();
    render(snapshot);
    const player = profilePlayers(teamKey).find((item) => item.player_id === playerId);
    toast(`Ficha en emisión · #${player?.number || "—"} ${player?.name || "Jugador"}`);
  } catch (error) { toast(error.message, true); }
}

function liveSportMode() {
  return app.snapshot?.state?.match?.sport_mode === "handball" ? "handball" : "floorball";
}

function formationSlotsForSport(mode = liveSportMode()) {
  if (mode === "handball") return [
    ["left_wing", translatePlayerPosition("left_wing").toUpperCase(), "handball-top left"],
    ["pivot", translatePlayerPosition("pivot").toUpperCase(), "handball-top centre"],
    ["right_wing", translatePlayerPosition("right_wing").toUpperCase(), "handball-top right"],
    ["left_back", translatePlayerPosition("left_back").toUpperCase(), "handball-middle left"],
    ["center_back", translatePlayerPosition("center_back").toUpperCase(), "handball-middle centre"],
    ["right_back", translatePlayerPosition("right_back").toUpperCase(), "handball-middle right"],
    ["goalkeeper", translatePlayerPosition("goalkeeper").toUpperCase(), "goalkeeper handball-goalkeeper"],
  ];
  return [
    ["forward_left", "DEL IZQ", "forward left"],
    ["forward_right", "DEL DER", "forward right"],
    ["centre", "MED", "centre"],
    ["defender_left", "DEF IZQ", "defender left"],
    ["defender_right", "DEF DER", "defender right"],
    ["goalkeeper", "POR", "goalkeeper"],
  ];
}

function renderFormationStructure() {
  const container = $("#formation-editor");
  if (!container) return;
  const mode = liveSportMode();
  if (container.dataset.sportMode === mode && container.querySelector("[data-slot]")) return;
  container.dataset.sportMode = mode;
  container.classList.toggle("is-handball", mode === "handball");
  container.innerHTML = formationSlotsForSport(mode).map(([slot, label, classes]) =>
    `<label class="slot ${classes}" data-formation-slot="${slot}"><span>${label}</span><select data-slot="${slot}"></select></label>`
  ).join("");
  const kicker = $("#formation-kicker");
  const title = $("#formation-title");
  if (kicker) kicker.textContent = textTranslation(mode === "handball" ? "Siete inicial" : "Quinteto inicial", app.language);
  if (title) title.textContent = textTranslation(mode === "handball" ? "Selección de 7 titulares" : "Selección de titulares", app.language);
}

function normalizeStarterState(raw) {
  const result = {};
  Object.entries(raw || {}).forEach(([slot, value]) => {
    result[slot] = typeof value === "object" ? String(value.player_id || "") : String(value || "");
  });
  return result;
}

function renderRosterList(teamKey, selector, countSelector) {
  const container = $(selector);
  const players = app.players[teamKey];
  const selected = attendanceSet(teamKey);
  $(countSelector).textContent = `${selected.size}/${players.length}`;
  container.innerHTML = "";
  if (!players.length) {
    container.innerHTML = '<div class="empty-state">Carga un partido para ver la plantilla.</div>';
    return;
  }
  players.forEach((player) => {
    const row = document.createElement("label");
    row.className = "roster-row";
    row.innerHTML = `
      <input type="checkbox" data-attendance-team="${teamKey}" value="${player.player_id}" ${selected.has(String(player.player_id)) ? "checked" : ""}>
      <span class="roster-number">${player.number ? `#${player.number}` : "—"}</span>
      <span class="roster-person"><strong>${escapeHTML(player.name)}${player.captain ? " · C" : ""}</strong><small>${escapeHTML(translatePlayerPosition(player.position))}</small></span>
      <span class="roster-position">${escapeHTML(translatePlayerPosition(player.position))}</span>`;
    container.appendChild(row);
  });
}

function playerOption(player) {
  return `${player.number ? `#${player.number} · ` : ""}${player.name}`;
}

function populatePowerplayMenus(teamKey, side) {
  const players = calledUpPlayers(teamKey);
  const prefixes = [`pp-${side}`, `production-pp-${side}`];
  prefixes.forEach((prefix) => {
    const playerSelect = $(`#${prefix}-player`);
    const servingSelect = $(`#${prefix}-serving`);
    if (!playerSelect || !servingSelect) return;
    const previousPlayer = playerSelect.value;
    const previousServing = servingSelect.value;
    playerSelect.innerHTML = players.length
      ? '<option value="">Selecciona jugador convocado</option>'
      : '<option value="">Guarda primero la convocatoria</option>';
    servingSelect.innerHTML = '<option value="">Mismo jugador</option>';
    players.forEach((player) => {
      playerSelect.append(new Option(playerOption(player), player.player_id));
      servingSelect.append(new Option(playerOption(player), player.player_id));
    });
    if ([...playerSelect.options].some((option) => option.value === previousPlayer)) playerSelect.value = previousPlayer;
    if ([...servingSelect.options].some((option) => option.value === previousServing)) servingSelect.value = previousServing;
    playerSelect.disabled = !players.length;
    servingSelect.disabled = !players.length;
  });
  $$(`[data-pp-start="${teamKey}"]`).forEach((button) => {
    button.disabled = !players.length;
    button.title = players.length ? "Iniciar expulsión" : "Guarda la convocatoria antes de sancionar";
  });
}

function populateFormation() {
  const players = calledUpPlayers(app.starterTeam);
  $$('[data-slot]').forEach((select) => {
    const slot = select.dataset.slot;
    const current = app.starters[app.starterTeam]?.[slot] || "";
    select.innerHTML = '<option value="">— Sin seleccionar —</option>';
    players.forEach((player) => select.append(new Option(playerOption(player), player.player_id)));
    select.value = current;
    select.onchange = () => {
      app.starters[app.starterTeam][slot] = select.value;
    };
  });
}

function renderStandings() {
  const rows = app.snapshot?.online?.standings?.length
    ? app.snapshot.online.standings
    : app.snapshot?.state?.statistics?.standings?.rows || [];
  const container = $("#standings-table");
  if (!rows.length) {
    container.innerHTML = '<div class="empty-state">Carga un partido online para obtener la clasificación.</div>';
    return;
  }
  container.innerHTML = '<div class="standings-row header"><span>POS</span><span>EQUIPO</span><span>PJ</span><span>DG</span><span>PTS</span><span>GF</span></div>';
  rows.forEach((row) => {
    const element = document.createElement("div");
    element.className = "standings-row";
    const teamName = row.team_name || row.name || row.team?.name || row.short_name || "Equipo";
    const played = row.played ?? row.matches_played ?? ((row.wins || 0) + (row.draws || 0) + (row.losses || 0));
    const diff = row.goal_difference ?? row.goalaverage ?? ((row.goals_for || 0) - (row.goals_against || 0));
    element.innerHTML = `<b>${row.position || "—"}</b><b>${escapeHTML(teamName)}</b><span>${played}</span><span>${diff}</span><span>${row.points || 0}</span><span>${row.goals_for || 0}</span>`;
    container.appendChild(element);
  });
}


function normalizedPerspective(value) {
  const fallback = { enabled: false, points: {
    top_left: { x: 0, y: 0 }, top_right: { x: 1, y: 0 },
    bottom_right: { x: 1, y: 1 }, bottom_left: { x: 0, y: 1 },
  } };
  if (!value || typeof value !== "object") return fallback;
  const points = value.points || {};
  Object.keys(fallback.points).forEach((key) => {
    const point = points[key];
    if (!point) return;
    fallback.points[key] = {
      x: Math.max(0, Math.min(1, Number(point.x ?? fallback.points[key].x))),
      y: Math.max(0, Math.min(1, Number(point.y ?? fallback.points[key].y))),
    };
  });
  fallback.enabled = Boolean(value.enabled);
  return fallback;
}

function updateOCRPerspectiveHelp() {
  const help = $("#ocr-perspective-help");
  if (!help) return;
  if (app.ocrPerspectiveEdit) {
    const names = ["superior izquierda", "superior derecha", "inferior derecha", "inferior izquierda"];
    const next = names[app.ocrPerspectiveDraft.length] || "finalizando";
    help.classList.add("is-editing");
    help.textContent = `Perspectiva: pulsa las cuatro esquinas en orden. Siguiente: ${next}.`;
    return;
  }
  help.classList.remove("is-editing");
  help.textContent = app.ocrPerspective?.enabled
    ? "Perspectiva activa. El preview y el OCR trabajan sobre el marcador rectificado."
    : "La perspectiva está desactivada. Si la cámara ve el marcador ladeado, selecciona sus cuatro esquinas.";
}

function confidenceText(runtime, key) {
  const value = Number(runtime?.confidence?.[key]);
  if (!Number.isFinite(value) || value <= 0) return "—";
  const pass = runtime?.ocr_pass?.[key] === "enhanced" ? " · reforzada" : "";
  return `${Math.round(value * 100)}%${pass}`;
}

function updateOCRReadingMeta(runtime = {}) {
  const map = {
    team1_score: "#ocr-home-confidence",
    time: "#ocr-time-confidence",
    team2_score: "#ocr-away-confidence",
  };
  Object.entries(map).forEach(([key, selector]) => {
    const node = $(selector);
    if (node) node.textContent = confidenceText(runtime, key);
  });
}

function selectedOCRSource() {
  const select = $("#ocr-window");
  const option = select?.selectedOptions?.[0];
  if (!option || !option.value) return { source_type: "window", source_id: "", source_label: "" };
  return {
    source_type: option.dataset.sourceType || "window",
    source_id: option.dataset.sourceId || "",
    source_label: option.dataset.sourceLabel || option.textContent || "",
  };
}

function ocrSourceKey(config = {}) {
  const type = config.source_type || "window";
  const id = String(config.source_id || "");
  return id ? `${type}:${id}` : "";
}

function renderOCR(config, runtime = {}) {
  const sourceLabel = config.source_label || config.window_title || "Sin fuente seleccionada";
  if (!previewController) $("#ocr-current-window").textContent = sourceLabel;
  if (document.activeElement !== $("#ocr-poll")) $("#ocr-poll").value = config.poll_ms || 700;
  if (!app.ocrDrag && !app.ocrDirty) {
    app.ocrRegions = structuredClone(config.regions || {});
    if (!app.ocrPerspectiveEdit) app.ocrPerspective = normalizedPerspective(config.perspective);
  }
  const select = $("#ocr-window");
  const sourceKey = ocrSourceKey(config);
  if (sourceKey && ![...select.options].some((option) => option.value === sourceKey)) {
    const option = new Option(sourceLabel, sourceKey);
    option.dataset.sourceType = config.source_type || "window";
    option.dataset.sourceId = String(config.source_id || "");
    option.dataset.sourceLabel = sourceLabel;
    select.prepend(option);
  }
  if (sourceKey && !app.ocrDirty && document.activeElement !== select) {
    if (select.value !== sourceKey && previewController) previewController.reset("Fuente cambiada. Captura un nuevo preview.");
    select.value = sourceKey;
  }

  const running = Boolean(runtime.running);
  $("#start-ocr").disabled = running;
  $("#stop-ocr").disabled = !running;
  const cameraStream = runtime?.camera_stream || {};
  const sourceError = runtime.error || ((config.source_type || "window") === "camera" ? cameraStream.error : "");
  $("#ocr-runtime-dot").className = sourceError ? "is-error" : running ? "is-running" : "";
  $("#ocr-runtime-copy").textContent = sourceError ? "OCR con incidencia" : running ? "OCR en marcha" : "OCR detenido";
  const persistentCameraCopy = !running && cameraStream.active && !cameraStream.error && (config.source_type || "window") === "camera"
    ? `Cámara encendida de forma continua${cameraStream.detail ? ` · ${cameraStream.detail}` : ""}.`
    : "";
  const modeCopy = app.snapshot?.score_control?.mode === "manual"
    ? "El reloj se aplica; las lecturas de resultado se supervisan pero no sobrescriben el modo manual."
    : "Reloj y resultado alimentan directamente la emisión.";
  $("#ocr-runtime-detail").textContent = sourceError || persistentCameraCopy || (running ? modeCopy : "La lectura está detenida. Captura un preview y configura las regiones antes de iniciar OCR.");
  updateOCRPerspectiveHelp();
  updateOCRReadingMeta(runtime);
  drawOCRRegions();
}

function renderEvents(events) {
  const container = $("#events-list");
  const rows = Array.isArray(events) ? events : [];
  if (!rows.length) {
    container.innerHTML = '<div class="empty-state">Todavía no hay eventos registrados para este partido.</div>';
    return;
  }
  const assists = new Map(rows.filter((row) => row.event_type === "assist" && row.related_event_id).map((row) => [String(row.related_event_id), row]));
  const visible = rows.filter((row) => row.event_type !== "assist");
  container.innerHTML = "";
  visible.forEach((event) => {
    const player = event.player || {};
    const person = player.display_name || [player.first_name, player.last_name].filter(Boolean).join(" ") || "Sin jugador";
    const assist = assists.get(String(event.id));
    const assistPlayer = assist?.player || {};
    const assistName = assistPlayer.display_name || [assistPlayer.first_name, assistPlayer.last_name].filter(Boolean).join(" ");
    const team = event.team?.short_name || event.team?.name || "Equipo";
    const type = event.event_type === "goal" ? "GOL" : event.event_type === "penalty" ? `EXP. ${event.penalty_type || "2"}` : String(event.event_type || "EVENTO").toUpperCase();
    const row = document.createElement("div");
    row.className = `event-row is-${event.event_type || "other"}`;
    row.innerHTML = `
      <span class="event-time">${escapeHTML(event.match_time || "--:--")}</span>
      <span class="event-type">${escapeHTML(type)}</span>
      <span class="event-copy"><strong>${escapeHTML(person)}</strong><small>${escapeHTML(team)}${assistName ? ` · ASIST. ${escapeHTML(assistName)}` : ""}</small></span>
      <button class="event-cancel" data-cancel-event="${escapeHTML(event.id || "")}" title="Anular evento">×</button>`;
    container.appendChild(row);
  });
}

async function refreshTabletAccess() {
  const urlElement = $("#tablet-access-url");
  const qrImage = $("#tablet-access-qr");
  if (!urlElement || !qrImage) return;
  try {
    const address = $("#tablet-network")?.value || "";
    let payload;
    try { payload = await api(`/api/tablet-access${address ? `?address=${encodeURIComponent(address)}` : ""}`); }
    catch(error) { if (address && error.status === 409) payload = await api("/api/tablet-access"); else throw error; }
    const network = $("#tablet-network");
    network.innerHTML = (payload.addresses || []).map(row => `<option value="${escapeHTML(row.address)}">${escapeHTML(row.interface)} · ${escapeHTML(row.address)}</option>`).join("");
    network.value = payload.selected_address || "";
    $("#tablet-network-status").textContent = textTranslation(payload.listener_reachable ? "El ordenador responde en esta dirección. Usa la misma red Wi-Fi, sin aislamiento entre dispositivos." : "El servidor no responde por la red local. Revisa el permiso de red local y que Live esté abierto para otros dispositivos.", app.language);
    const url = String(payload.url || "");
    urlElement.textContent = url || textTranslation("Calculando dirección…", app.language);
    urlElement.dataset.url = url;
    const qrURL = new URL(payload.qr || "/api/tablet-qr.svg", location.origin);
    qrURL.searchParams.set("v", String(Date.now()));
    qrImage.src = qrURL.href;
    qrImage.hidden = false;
    await refreshTabletSessions();
  } catch (error) {
    urlElement.textContent = error.message;
    urlElement.dataset.url = "";
    qrImage.removeAttribute("src");
    qrImage.hidden = true;
  }
}

async function refreshTabletSessions() {
  const host = $("#tablet-sessions");
  if (!host) return;
  try {
    const sessions = await api("/api/tablet/sessions");
    host.replaceChildren();
    if (!sessions.length) { host.textContent = "No hay tablets emparejadas."; return; }
    for (const session of sessions) {
      const row = document.createElement("div");
      row.className = "tablet-session-row";
      const label = document.createElement("span");
      label.textContent = `Tablet ${session.id.slice(0, 6)} · última conexión ${new Date(session.last_seen * 1000).toLocaleTimeString()}`;
      const revoke = document.createElement("button");
      revoke.type = "button"; revoke.className = "button secondary compact-button"; revoke.textContent = "Desconectar";
      revoke.addEventListener("click", async () => {
        try { await api(`/api/tablet/sessions/${encodeURIComponent(session.id)}`, {method:"DELETE"}); await refreshTabletSessions(); }
        catch (error) { toast(error.message, true); }
      });
      row.append(label, revoke); host.appendChild(row);
    }
  } catch (error) { host.textContent = error.message; }
}

async function refreshPreflight() {
  const host = $("#preflight-checks");
  if (!host) return;
  try {
    const report = await api("/api/preflight");
    $("#preflight-summary").textContent = report.ready
      ? `Sin bloqueos · ${report.counts.warn} avisos para revisar`
      : `${report.counts.blocking ?? report.counts.fail} puntos obligatorios impiden salir en directo · ${report.counts.warn} avisos`;
    host.replaceChildren();
    for (const check of report.checks) {
      const row = document.createElement("article"); row.className = `preflight-check is-${check.level}`;
      row.dataset.required = String(check.required !== false);
      const title = document.createElement("strong"); title.textContent = check.label;
      const detail = document.createElement("span"); detail.textContent = check.detail;
      row.append(title, detail);
      if (check.level !== "ok" && check.action) {
        const action = document.createElement("small"); action.textContent = check.action; row.appendChild(action);
      }
      host.appendChild(row);
    }
  } catch (error) { $("#preflight-summary").textContent = error.message; }
}

function setPreflightVisible(visible, persist = true) {
  const card = $("#preflight-card");
  const reopen = $("#show-preflight");
  if (!card || !reopen) return;
  card.hidden = !visible;
  reopen.hidden = visible;
  if (persist) localStorage.setItem("secretariatpro.preflight.visible", visible ? "true" : "false");
  if (visible) refreshPreflight();
}

async function copyTextToClipboard(value) {
  try {
    const result = await api("/api/system/clipboard", {
      method: "POST",
      body: JSON.stringify({ text: value }),
    });
    if (result?.copied) return true;
  } catch (_) { /* The browser fallback below also supports development servers. */ }

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch (_) { /* Older WebViews do not expose the async Clipboard API. */ }

  try {
    const input = document.createElement("textarea");
    input.value = value;
    input.style.position = "fixed";
    input.style.opacity = "0";
    input.setAttribute("readonly", "");
    document.body.appendChild(input);
    input.focus();
    input.select();
    input.setSelectionRange(0, input.value.length);
    const copied = document.execCommand("copy");
    input.remove();
    return copied;
  } catch (_) {
    return false;
  }
}

async function copyTabletAccessUrl() {
  const element = $("#tablet-access-url");
  const value = element?.dataset.url || element?.textContent || "";
  if (!value || !/^https?:\/\//i.test(value)) return;
  if (!await copyTextToClipboard(value)) {
    toast(textTranslation("No se pudo copiar el enlace. Vuelve a intentarlo.", app.language), true);
    return;
  }
  toast(textTranslation("Dirección copiada.", app.language));
}

function overlaySourceURL() {
  return `http://127.0.0.1:${location.port || "8765"}/overlay.html`;
}

async function copyOverlaySourceURL() {
  const value = overlaySourceURL();
  if (!await copyTextToClipboard(value)) {
    toast(textTranslation("No se pudo copiar el enlace. Vuelve a intentarlo.", app.language), true);
    return;
  }
  toast(textTranslation("Enlace del overlay copiado. Pégalo como fuente de navegador (1920 × 1080).", app.language));
}

function renderSettings(settings, delivery = {}) {
  const signature = JSON.stringify([settings, delivery, app.appearanceDraft, app.language]);
  if (app.settingsRenderSignature === signature) return;
  app.settingsRenderSignature = signature;
  const obs = settings.obs || {};
  const shortcuts = settings.shortcuts || {};
  const language = ["es", "en", "sv", "cs", "fi", "de"].includes(settings.language) ? settings.language : "en";
  if (document.activeElement !== $("#settings-language")) $("#settings-language").value = language;
  if (document.activeElement !== $("#settings-obs-host")) $("#settings-obs-host").value = obs.host || "127.0.0.1";
  if (document.activeElement !== $("#settings-obs-port")) $("#settings-obs-port").value = obs.port || 4455;
  if (document.activeElement !== $("#settings-projector-window")) { const projector = $("#settings-projector-window"); if (projector) projector.dataset.configuredValue = obs.projector_window || ""; }
  $("#settings-obs-password").placeholder = obs.password_configured ? "Contraseña guardada · escribe para cambiarla" : "Introduce la contraseña de OBS";
  $("#settings-obs-auto").checked = Boolean(obs.auto_connect);
  $("#settings-replay-auto-goals").checked = obs.replay_auto_mark_goals !== false;
  if (document.activeElement !== $("#settings-replay-post-roll")) $("#settings-replay-post-roll").value = Number(obs.replay_post_roll_seconds ?? 4);
  Object.entries(SHORTCUT_FIELDS).forEach(([key, selector]) => {
    const field = $(selector);
    if (field && document.activeElement !== field && field.dataset.capturing !== "true") field.value = shortcuts[key] || "";
  });
  if (!app.appearanceDirty || !app.appearanceDraft) {
    app.appearanceDraft = populateAppearanceFields(settings.appearance || DEFAULT_APPEARANCE);
  }
  $$('[data-appearance-path]').forEach((field) => { field.disabled = true; field.title = "La identidad de emisión se configura desde el Manager"; });
  if ($("#reset-appearance")) $("#reset-appearance").disabled = true;
  applyAppAppearance(app.appearanceDraft || settings.appearance || DEFAULT_APPEARANCE);
  applyLanguage(language);
  const scope = $("#settings-account-scope");
  if (scope) {
    const linked = Boolean(settings.account_scope?.linked);
    scope.classList.toggle("is-linked", linked);
    scope.textContent = linked
      ? `${textTranslation("Configuración vinculada a", language)} ${settings.account_scope.email || textTranslation("Cuenta", language)}`
      : textTranslation("Configuración local", language);
  }
  const sharing = settings.ocr_data_sharing || {};
  const sharingToggle = $("#settings-ocr-sharing");
  const sharingStatus = $("#settings-ocr-sharing-status");
  if (sharingToggle) {
    sharingToggle.checked = Boolean(sharing.enabled);
    sharingToggle.disabled = !sharing.can_manage || Boolean(sharing.unavailable);
    sharingToggle.dataset.canManage = sharing.can_manage ? "true" : "false";
  }
  if (sharingStatus) {
    const statusText = sharing.unavailable
      ? "La migración de privacidad OCR todavía no está disponible."
      : sharing.enabled
        ? "Compartición OCR activada para este espacio de trabajo."
        : "La compartición está desactivada.";
    sharingStatus.textContent = textTranslation(statusText, language);
    sharingStatus.classList.toggle("is-enabled", Boolean(sharing.enabled));
    sharingStatus.classList.toggle("is-locked", !sharing.can_manage);
    if (!sharing.can_manage && !sharing.unavailable) {
      sharingStatus.textContent += ` ${textTranslation("La asociación gestiona esta preferencia para todos sus realizadores.", language)}`;
    }
  }
  renderOCRDeliveryStatus(delivery, sharing);
}

function renderOCRDeliveryStatus(delivery = {}, sharing = {}) {
  const deliveryStatus = $("#settings-ocr-delivery-status");
  if (deliveryStatus) {
    const queued = Number(delivery.queued || 0);
    const uploaded = Number(delivery.uploaded || 0);
    const generated = Number(delivery.generated || 0);
    const lastError = String(delivery.last_error || "").trim();
    if (!sharing.enabled) {
      deliveryStatus.textContent = "Envío OCR: desactivado.";
      deliveryStatus.className = "privacy-sharing-status privacy-delivery-status";
    } else if (lastError) {
      deliveryStatus.textContent = `Envío OCR: ${queued} pendiente(s) de reintento · ${lastError}`;
      deliveryStatus.className = "privacy-sharing-status privacy-delivery-status is-error";
    } else if (uploaded > 0 || generated > 0) {
      deliveryStatus.textContent = `Envío OCR: ${uploaded} subida(s) · ${queued} pendiente(s).`;
      deliveryStatus.className = "privacy-sharing-status privacy-delivery-status is-enabled";
    } else {
      deliveryStatus.textContent = "Envío OCR: activo, esperando una lectura difícil.";
      deliveryStatus.className = "privacy-sharing-status privacy-delivery-status is-enabled";
    }
  }
}

function renderSubscriptionGate(online = {}) {
  const gate = $("#subscription-gate");
  if (!gate) return;
  const access = online.access || {};
  const connected = Boolean(online.connected);
  const allowed = Boolean(access.production_allowed || access.allowed);
  gate.hidden = allowed;
  const title = $("#subscription-gate-title");
  const message = $("#subscription-gate-message");
  const meta = $("#subscription-gate-meta");
  const loginButton = $("#subscription-login-button");
  const accountButton = $("#subscription-account-button");
  if (!connected) {
    title.textContent = "Inicia sesión para continuar";
    message.textContent = "SecretariatPro requiere una cuenta con membresía activa.";
    loginButton.hidden = false;
    accountButton.hidden = true;
    meta.hidden = true;
    return;
  }
  const workspace = online.workspace || {};
  title.textContent = access.mode === "read_only" ? "La membresía ha finalizado" : "SecretariatPro está bloqueado";
  message.textContent = access.message || "No hay una membresía activa para este espacio de trabajo.";
  loginButton.hidden = true;
  accountButton.hidden = false;
  meta.hidden = false;
  const retention = access.retention_until ? new Date(access.retention_until).toLocaleDateString("es-ES") : "—";
  meta.innerHTML = `<strong>${escapeHTML(workspace.name || "Sin espacio de trabajo")}</strong><br>Plan: ${escapeHTML(access.plan_name || "Sin plan")} · Conservación hasta: ${escapeHTML(retention)}`;
}

function renderAccount(online) {
  const connected = Boolean(online.connected);
  const signedOut = $("#signed-out-account");
  const panel = $("#account-panel");
  if (signedOut) signedOut.hidden = connected;
  if (panel) panel.hidden = !connected;
  if (!connected) return;

  const profile = online.profile || {};
  const displayName = profile.display_name || online.email?.split("@")[0] || "Operador";
  const email = profile.email || online.email || "";
  const avatarUrl = profile.avatar_url || "";

  $("#account-profile-title").textContent = displayName;
  $("#account-profile-email").textContent = email;
  $("#account-avatar-initials").textContent = initials(displayName || email);
  if (document.activeElement !== $("#account-display-name")) $("#account-display-name").value = displayName;
  $("#account-email").value = email;
  const workspaceSelect = $("#account-workspace-select");
  const workspaces = online.workspaces || [];
  if (workspaceSelect && document.activeElement !== workspaceSelect) {
    workspaceSelect.innerHTML = workspaces.length
      ? workspaces.map((item) => `<option value="${escapeHTML(item.id || "")}" ${String(item.id) === String(online.workspace?.id) ? "selected" : ""}>${escapeHTML(item.name || "Espacio")}</option>`).join("")
      : '<option value="">Sin espacios disponibles</option>';
    workspaceSelect.disabled = workspaces.length < 2;
  }
  const summary = $("#account-workspace-summary");
  if (summary) {
    const workspace = online.workspace || {};
    const access = online.access || {};
    summary.textContent = workspace.id
      ? `${workspace.workspace_type === "association" ? "Asociación" : "Particular"} · ${workspace.role || "miembro"} · ${access.plan_name || "sin plan"}`
      : "La cuenta todavía no pertenece a ningún espacio de trabajo.";
  }
  setProfileAvatar($("#account-avatar-preview"), $(".account-avatar-shell"), avatarUrl);
  $("#account-remove-avatar").disabled = !avatarUrl;
}

function applyAccountProfile(profile) {
  if (!app.snapshot?.online) return;
  app.snapshot.online.profile = { ...(app.snapshot.online.profile || {}), ...(profile || {}) };
  app.snapshot.online.email = profile?.email || app.snapshot.online.email || "";
  renderAccount(app.snapshot.online);
  const label = app.snapshot.online.profile.display_name || app.snapshot.online.email || "";
  $("#profile-initials").textContent = initials(label);
  setProfileAvatar($("#profile-avatar"), $("#profile-button"), app.snapshot.online.profile.avatar_url || "");
}

function normalizedShortcutString(value = "") {
  const tokens = String(value).split("+").map((part) => part.trim()).filter(Boolean);
  if (!tokens.length) return "";
  let key = "";
  const flags = { Ctrl: false, Alt: false, Shift: false, Meta: false };
  tokens.forEach((token) => {
    const lower = token.toLowerCase();
    if (["ctrl", "control"].includes(lower)) flags.Ctrl = true;
    else if (lower === "alt" || lower === "option") flags.Alt = true;
    else if (lower === "shift") flags.Shift = true;
    else if (["meta", "cmd", "command", "win", "super"].includes(lower)) flags.Meta = true;
    else key = token.length === 1 ? token.toUpperCase() : token.replace(/^./, (c) => c.toUpperCase());
  });
  const ordered = [];
  if (flags.Ctrl) ordered.push("Ctrl");
  if (flags.Alt) ordered.push("Alt");
  if (flags.Shift) ordered.push("Shift");
  if (flags.Meta) ordered.push("Meta");
  if (key) ordered.push(key.toUpperCase().startsWith("ARROW") ? key.replace(/^ARROW/, "Arrow") : key.toUpperCase().startsWith("F") ? key.toUpperCase() : key);
  return ordered.join("+");
}

function normalizeKeyboardEvent(event) {
  const keyValue = event.key;
  if (!keyValue) return "";
  const lower = keyValue.toLowerCase();
  if (["control", "shift", "alt", "meta"].includes(lower)) return "";
  let key = keyValue;
  if (lower === " ") key = "Space";
  else if (lower === "escape") key = "Escape";
  else if (lower.startsWith("arrow")) key = keyValue[0].toUpperCase() + keyValue.slice(1);
  else if (/^f\d{1,2}$/i.test(keyValue)) key = keyValue.toUpperCase();
  else if (keyValue.length === 1) key = keyValue.toUpperCase();
  else key = keyValue[0].toUpperCase() + keyValue.slice(1);
  return normalizedShortcutString([
    event.ctrlKey ? "Ctrl" : "",
    event.altKey ? "Alt" : "",
    event.shiftKey ? "Shift" : "",
    event.metaKey ? "Meta" : "",
    key,
  ].filter(Boolean).join("+"));
}

function currentShortcutMap() {
  const saved = app.snapshot?.settings?.shortcuts || {};
  return Object.fromEntries(Object.keys(SHORTCUT_FIELDS).map((key) => [key, normalizedShortcutString(saved[key] || "")]));
}

async function executeShortcutAction(action) {
  const lineupButtons = $$('[data-overlay="lineups"]');
  switch (action) {
    case "scoreboard": return render(await api("/api/overlays/scoreboard/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "prematch": return render(await api("/api/overlays/prematch/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "intermission": return render(await api("/api/overlays/intermission/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "lineups_home": return render(await api("/api/overlays/lineups/toggle", { method: "POST", body: JSON.stringify({ lineup_team: "team1" }) }));
    case "lineups_away": return render(await api("/api/overlays/lineups/toggle", { method: "POST", body: JSON.stringify({ lineup_team: "team2" }) }));
    case "top_scorers": return render(await api("/api/overlays/top_scorers/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "standings": return render(await api("/api/overlays/standings/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "bottom_bar": return render(await api("/api/overlays/bottom_bar/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "penalties": return render(await api("/api/overlays/penalties/toggle", { method: "POST", body: JSON.stringify({}) }));
    case "hide_all": return render(await api("/api/overlays/hide-all", { method: "POST" }));
    default: return null;
  }
}

async function handleGlobalShortcut(event) {
  const target = event.target;
  if (target && (target.closest("input, textarea, select") || target.isContentEditable)) return;
  const combo = normalizeKeyboardEvent(event);
  if (!combo) return;
  const match = Object.entries(currentShortcutMap()).find(([, value]) => value && value === combo);
  if (!match) return;
  event.preventDefault();
  try {
    await executeShortcutAction(match[0]);
  } catch (error) {
    toast(error.message, true);
  }
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function productionTeamName(teamKey) {
  const fallback = teamKey === "team1" ? "LOCAL" : "VISITANTE";
  return app.snapshot?.state?.[teamKey]?.name || fallback;
}

function resetProductionFlow() {
  app.productionFlow = {
    kind: "",
    team: "",
    step: "",
    penaltyType: "",
    scorerId: "",
    offenderId: "",
  };
}

function closeProductionWorkflow() {
  if (app.productionFlow.kind === "replay") return skipReplayDeck();
  resetProductionFlow();
  const row = $("#production-bottom-row");
  const card = $("#production-workflow-card");
  if (row) row.classList.remove("is-workflow");
  if (card) card.hidden = true;
}

function openProductionWorkflow(kind, teamKey) {
  if (!app.snapshot?.online?.match?.id) return toast("Carga primero un partido online.", true);
  const players = kind === "profile" ? profilePlayers(teamKey) : calledUpPlayers(teamKey);
  if (!players.length) return toast(kind === "profile" ? "No hay jugadores disponibles en la plantilla." : "Guarda primero la convocatoria del equipo.", true);
  app.productionFlow = {
    kind,
    team: teamKey,
    markerPromise: kind === "goal" ? captureReplayNow("Gol", teamKey) : null,
    eventTime: app.snapshot?.scores?.time || "",
    requestId: crypto.randomUUID(),
    scoreBefore: Number((app.snapshot?.graphic_scores || app.snapshot?.scores)?.[teamKey === "team1" ? "team1_score" : "team2_score"] || 0),
    step: kind === "penalty" ? "penalty_type" : kind === "profile" ? "profile_player" : "goal_scorer",
    penaltyType: "",
    scorerId: "",
    offenderId: "",
  };
  const row = $("#production-bottom-row");
  const card = $("#production-workflow-card");
  if (row) row.classList.add("is-workflow");
  if (card) card.hidden = false;
  renderProductionWorkflow();
}

function productionWorkflowBack() {
  const flow = app.productionFlow;
  if (flow.kind === "replay") {
    const c=app.replayComposer;
    c.stage = ({duration:"camera",speed:"duration",next:"camera",done:"next"})[c.stage] || "camera";
    return renderReplayComposer();
  }
  if (!flow.kind) return closeProductionWorkflow();
  if (flow.step === "goal_assistant") {
    flow.step = "goal_scorer";
    flow.scorerId = "";
  } else if (flow.step === "penalty_player") {
    flow.step = "penalty_type";
    flow.penaltyType = "";
  } else if (flow.step === "penalty_serving") {
    flow.step = "penalty_player";
    flow.offenderId = "";
  } else {
    return closeProductionWorkflow();
  }
  renderProductionWorkflow();
}

function productionPlayerButton(player, action, disabled = false) {
  const rawNumber = String(player.number || "").replace(/^#/, "").trim();
  const number = rawNumber ? escapeHTML(rawNumber) : "—";
  const digitClass = rawNumber.length >= 3 ? "is-three-digits" : rawNumber.length === 2 ? "is-two-digits" : "is-one-digit";
  return `<button class="production-player-key" type="button" data-flow-action="${action}" data-player-id="${escapeHTML(player.player_id)}" ${disabled ? "disabled" : ""}>
    <span class="production-player-number ${digitClass}" data-digits="${rawNumber.length || 1}">${number}</span>
    <strong>${escapeHTML(player.name)}</strong>
    <small>${escapeHTML(translatePlayerPosition(player.position) || textTranslation("Jugador", app.language))}</small>
  </button>`;
}

function configureProductionPickerGrid(count, typeGrid = false) {
  const grid = $("#production-workflow-grid");
  if (!grid) return;
  grid.classList.toggle("is-type-grid", typeGrid);
  if (typeGrid) {
    grid.style.removeProperty("--picker-columns");
    grid.style.removeProperty("--picker-rows");
    return;
  }
  const safeCount = Math.max(1, count);
  const columns = Math.max(4, Math.min(8, Math.ceil(Math.sqrt(safeCount * 1.7))));
  const rows = Math.max(1, Math.ceil(safeCount / columns));
  grid.style.setProperty("--picker-columns", String(columns));
  grid.style.setProperty("--picker-rows", String(rows));
}

function renderProductionWorkflow() {
  const flow = app.productionFlow;
  const card = $("#production-workflow-card");
  if (!card || !flow.kind) return;
  if (flow.kind === "replay") return renderReplayComposer();
  const players = flow.kind === "profile" ? profilePlayers(flow.team) : calledUpPlayers(flow.team);
  if (!players.length) {
    closeProductionWorkflow();
    return toast("La convocatoria ya no está disponible.", true);
  }

  const signature = JSON.stringify([flow.kind, flow.team, flow.step, flow.scorerId, flow.offenderId, flow.penaltyType, players, app.language]);
  if (flow.renderSignature === signature) return;
  flow.renderSignature = signature;
  const kicker = $("#production-workflow-kicker");
  const title = $("#production-workflow-title");
  const help = $("#production-workflow-help");
  const summary = $("#production-workflow-summary");
  const grid = $("#production-workflow-grid");
  const back = $("#production-workflow-back");
  const teamName = productionTeamName(flow.team);
  back.hidden = ["goal_scorer", "penalty_type", "profile_player"].includes(flow.step);
  summary.innerHTML = `<span>${escapeHTML(teamName)}</span><span>${players.length} convocados</span><span>Tiempo ${escapeHTML(app.snapshot?.scores?.time || "00:00")}</span>`;

  if (flow.step === "penalty_type") {
    kicker.textContent = "EXPULSIÓN";
    title.textContent = `Selecciona sanción · ${teamName}`;
    help.textContent = "Primero el tipo; después aparecerá toda la convocatoria.";
    grid.innerHTML = `
      <button class="production-penalty-type-key" data-flow-action="penalty-type" data-penalty-type="2"><strong>2</strong><span>2 minutos</span></button>
      <button class="production-penalty-type-key" data-flow-action="penalty-type" data-penalty-type="2+2"><strong>2+2</strong><span>Dos bloques consecutivos</span></button>
      <button class="production-penalty-type-key" data-flow-action="penalty-type" data-penalty-type="2+10"><strong>2+10</strong><span>Expulsado + jugador que cumple</span></button>`;
    configureProductionPickerGrid(3, true);
    return;
  }

  if (flow.step === "profile_player") {
    kicker.textContent = "FICHA DE JUGADOR";
    title.textContent = `Selecciona jugador · ${teamName}`;
    help.textContent = "Pulsa un jugador para mostrar directamente su ficha individual en emisión.";
    grid.innerHTML = players.map((player) => productionPlayerButton(player, "profile-player")).join("");
    configureProductionPickerGrid(players.length);
    return;
  }

  if (flow.step === "goal_scorer") {
    kicker.textContent = "GOL";
    title.textContent = `¿Quién ha marcado? · ${teamName}`;
    help.textContent = "Pulsa directamente el dorsal del goleador.";
    grid.innerHTML = players.map((player) => productionPlayerButton(player, "goal-scorer")).join("");
    configureProductionPickerGrid(players.length);
    return;
  }

  if (flow.step === "goal_assistant") {
    const scorer = playerById(flow.team, flow.scorerId);
    kicker.textContent = "ASISTENCIA";
    title.textContent = `Asistencia del gol · #${scorer?.number || "—"} ${scorer?.name || ""}`;
    help.textContent = "Selecciona asistente o registra el gol sin asistencia.";
    const available = players.filter((player) => player.player_id !== flow.scorerId);
    grid.innerHTML = `<button class="production-player-key production-no-assist-key" type="button" data-flow-action="goal-no-assist">
        <span class="production-player-number">Ø</span><strong>Sin asistencia</strong><small>REGISTRAR GOL</small>
      </button>${available.map((player) => productionPlayerButton(player, "goal-assistant")).join("")}`;
    configureProductionPickerGrid(available.length + 1);
    return;
  }

  if (flow.step === "penalty_player") {
    kicker.textContent = `EXPULSIÓN ${flow.penaltyType}`;
    title.textContent = `Selecciona jugador sancionado · ${teamName}`;
    help.textContent = "Sólo aparecen jugadores de la convocatoria guardada.";
    grid.innerHTML = players.map((player) => productionPlayerButton(player, "penalty-player")).join("");
    configureProductionPickerGrid(players.length);
    return;
  }

  if (flow.step === "penalty_serving") {
    const offender = playerById(flow.team, flow.offenderId);
    const available = players.filter((player) => player.player_id !== flow.offenderId);
    kicker.textContent = "EXPULSIÓN 2+10";
    title.textContent = `¿Quién cumple los 2 minutos?`;
    help.textContent = `Sancionado: #${offender?.number || "—"} ${offender?.name || ""}. Debe cumplir otro convocado.`;
    grid.innerHTML = available.map((player) => productionPlayerButton(player, "penalty-serving")).join("");
    configureProductionPickerGrid(available.length);
  }
}

async function submitProductionGoal(assistantId = null) {
  const flow = app.productionFlow;
  const scorer = playerById(flow.team, flow.scorerId);
  if (!scorer) return toast("El goleador ya no está disponible.", true);
  if (assistantId && assistantId === flow.scorerId) return toast("Goleador y asistente no pueden ser el mismo jugador.", true);
  try {
    const snapshot = await api("/api/events/goal", {
      method: "POST",
      body: JSON.stringify({
        team: flow.team,
        scorer_id: flow.scorerId,
        assistant_id: assistantId || null,
        match_time: flow.eventTime,
        increment_manual_score: true,
        score_before: flow.scoreBefore,
        request_id: flow.requestId,
        marker_id: await flow.markerPromise || "",
      }),
    });
    closeProductionWorkflow();
    render(snapshot);
    toast(`Gol registrado · #${scorer.number || "—"} ${scorer.name}`);
    if (snapshot.goal_replay_flow && snapshot.goal_replay_marker_id) markReplay({goalFlow:true, markerId:snapshot.goal_replay_marker_id});
  } catch (error) { toast(error.message, true); }
}

async function submitProductionPenalty(servingId = "") {
  const flow = app.productionFlow;
  const offender = playerById(flow.team, flow.offenderId);
  if (!offender) return toast("El jugador sancionado ya no está disponible.", true);
  if (flow.penaltyType === "2+10") {
    const serving = playerById(flow.team, servingId);
    if (!serving || serving.player_id === offender.player_id) return toast("Selecciona otro convocado para cumplir los 2 minutos.", true);
  }
  try {
    const snapshot = await api(`/api/powerplays/${flow.team}/start`, {
      method: "POST",
      body: JSON.stringify({
        player_id: offender.player_id,
        penalty_type: flow.penaltyType,
        serving_player_id: flow.penaltyType === "2+10" ? servingId : "",
      }),
    });
    closeProductionWorkflow();
    render(snapshot);
    toast(`Expulsión ${flow.penaltyType} iniciada · #${offender.number || "—"}`);
  } catch (error) { toast(error.message, true); }
}

function handleProductionWorkflowClick(event) {
  if (app.productionFlow.kind === "replay") return;
  const target = event.target.closest("[data-flow-action]");
  if (!target) return;
  const flow = app.productionFlow;
  const action = target.dataset.flowAction;
  const playerId = target.dataset.playerId || "";
  if (action === "profile-player") return showProductionPlayerProfile(flow.team, playerId);
  if (action === "penalty-type") {
    flow.penaltyType = target.dataset.penaltyType;
    flow.step = "penalty_player";
    return renderProductionWorkflow();
  }
  if (action === "goal-scorer") {
    flow.scorerId = playerId;
    flow.step = "goal_assistant";
    return renderProductionWorkflow();
  }
  if (action === "goal-assistant") return submitProductionGoal(playerId);
  if (action === "goal-no-assist") return submitProductionGoal(null);
  if (action === "penalty-player") {
    flow.offenderId = playerId;
    if (flow.penaltyType === "2+10") {
      flow.step = "penalty_serving";
      return renderProductionWorkflow();
    }
    return submitProductionPenalty("");
  }
  if (action === "penalty-serving") return submitProductionPenalty(playerId);
}


function installPremiumInteractions() {
  document.addEventListener("pointerdown", (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled) return;
    const rect = button.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "button-ripple";
    ripple.style.left = `${event.clientX - rect.left}px`;
    ripple.style.top = `${event.clientY - rect.top}px`;
    button.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
  });

  const cards = $$(".view .card");
  cards.forEach((card, index) => card.style.setProperty("--reveal-index", String(index % 8)));
}

async function pollLiveState() {
  if (!app.snapshot?.online?.access?.allowed) return;
  if (app.liveBusy) return;
  app.liveBusy = true;
  try {
    const response = await fetch(`/api/live?_=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Live ${response.status}`);
    renderLive(await response.json());
  } catch (_) {
    // The WebSocket/full-state fallback remains active. Avoid noisy toasts in live use.
  } finally {
    app.liveBusy = false;
  }
}

function startLivePolling() {
  clearTimeout(app.liveTimer);
  clearInterval(app.fallbackTimer);

  const scheduleLivePoll = () => {
    clearTimeout(app.liveTimer);
    const delay = document.visibilityState === "visible" ? 400 : 1200;
    app.liveTimer = setTimeout(async () => {
      await pollLiveState();
      scheduleLivePoll();
    }, delay);
  };

  pollLiveState().finally(scheduleLivePoll);
  app.fallbackTimer = setInterval(async () => {
    if (document.visibilityState !== "visible" || app.socket?.readyState === WebSocket.OPEN) return;
    try { render(await api(`/api/state?_=${Date.now()}`, { cache: "no-store" })); }
    catch (_) { /* reconnect UI is handled by the socket status */ }
  }, 3000);
}

function connectSocket() {
  if (!app.snapshot?.online?.access?.allowed) return;
  if (app.socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(app.socket.readyState)) return;
  clearTimeout(app.reconnectTimer);
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/api/ws`);
  app.socket = socket;
  socket.onopen = () => {
    $("#api-status").className = "status-pill is-ok";
    $("#api-status").innerHTML = "<i></i>Motor local";
  };
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "state") render(message.payload);
    if (message.type === "live") renderLive(message.payload);
  };
  socket.onclose = () => {
    $("#api-status").className = "status-pill is-warn";
    $("#api-status").innerHTML = "<i></i>Reconectando";
    if (app.snapshot?.online?.access?.allowed) app.reconnectTimer = setTimeout(connectSocket, 1200);
  };
  socket.onerror = () => socket.close();
}

function openFinishMatchModal() {
  const match = app.snapshot?.online?.match || {};
  if (!match.id) return toast("Carga primero un partido online.", true);
  if (String(match.status || "").toLowerCase() === "finished") return toast("Partido finalizado", true);
  const scores = app.snapshot?.scores || {};
  const home = app.snapshot?.state?.team1 || {};
  const away = app.snapshot?.state?.team2 || {};
  $("#finish-home-name").textContent = home.name || "LOCAL";
  $("#finish-away-name").textContent = away.name || "VISITANTE";
  $("#finish-home-score").value = String(parseInt(scores.team1_score || "0", 10) || 0);
  $("#finish-away-score").value = String(parseInt(scores.team2_score || "0", 10) || 0);
  $("#finish-match-summary").textContent = `${home.name || "LOCAL"} ${$("#finish-home-score").value} — ${$("#finish-away-score").value} ${away.name || "VISITANTE"}`;
  openModal("finish-match-modal");
}

async function submitFinishMatch(event) {
  event.preventDefault();
  const homeScore = Number($("#finish-home-score").value);
  const awayScore = Number($("#finish-away-score").value);
  if (!Number.isInteger(homeScore) || homeScore < 0 || !Number.isInteger(awayScore) || awayScore < 0) {
    return toast("Comprueba el resultado antes de cerrar el partido.", true);
  }
  const match = app.snapshot?.online?.match || {};
  if (!match.id) return toast("Carga primero un partido online.", true);
  const accepted = window.confirm(`¿Confirmar resultado final ${homeScore} — ${awayScore}? Esta acción marcará el partido como finalizado.`);
  if (!accepted) return;
  const submit = $("#confirm-finish-match");
  if (submit) submit.disabled = true;
  try {
    const snapshot = await api("/api/match/finish", {
      method: "POST",
      body: JSON.stringify({ home_score: homeScore, away_score: awayScore }),
    });
    render(snapshot);
    closeModal("finish-match-modal");
    toast("El partido se ha finalizado correctamente.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    if (submit) submit.disabled = false;
  }
}

function openModal(id) { $(id.startsWith("#") ? id : `#${id}`).hidden = false; }
function closeModal(id) { $(id.startsWith("#") ? id : `#${id}`).hidden = true; }

async function toggleOverlay(button) {
  if (button.getAttribute("aria-busy") === "true") return;
  button.setAttribute("aria-busy", "true");
  const panel = button.dataset.overlay;
  const body = panel === "lineups" ? { lineup_team: button.dataset.lineupTeam || "team1" } : {};
  try {
    const snapshot = await api(`/api/overlays/${panel}/toggle`, { method: "POST", body: JSON.stringify(body) });
    render(snapshot);
  } catch (error) { toast(error.message, true); }
  finally { button.removeAttribute("aria-busy"); }
}

async function setScoreMode(mode) {
  if (mode === app.snapshot?.score_control?.mode) return;
  if (mode === "manual") {
    const accepted = window.confirm("¿Activar el modo manual? Las lecturas OCR de resultado dejarán de sobrescribir el marcador hasta que vuelvas a OCR.");
    if (!accepted) return;
  }
  try {
    const snapshot = await api("/api/score-control", { method: "PUT", body: JSON.stringify({ mode }) });
    render(snapshot);
    toast(mode === "manual" ? "Control manual del resultado activado." : "Resultado devuelto al control OCR.");
  } catch (error) { toast(error.message, true); }
}

async function changeScore(team, delta) {
  if (app.snapshot?.score_control?.mode !== "manual") return toast("Activa el modo manual para editar el resultado.", true);
  try {
    const snapshot = await api(`/api/scores/${team}/delta`, { method: "POST", body: JSON.stringify({ delta }) });
    render(snapshot);
  } catch (error) { toast(error.message, true); }
}

function playerById(teamKey, playerId) {
  return calledUpPlayers(teamKey).find((player) => player.player_id === playerId);
}

async function startPenalty(teamKey, context = "direct") {
  const side = teamKey === "team1" ? "home" : "away";
  const prefix = context === "production" ? `production-pp-${side}` : `pp-${side}`;
  const playerId = $(`#${prefix}-player`)?.value || "";
  const type = $(`#${prefix}-type`)?.value || "2";
  const servingId = $(`#${prefix}-serving`)?.value || "";
  const player = playerById(teamKey, playerId);
  if (!player) return toast("Selecciona un jugador de la convocatoria guardada.", true);

  let serving = player;
  if (type === "2+10") {
    serving = playerById(teamKey, servingId);
    if (!serving) return toast("En 2+10 selecciona otro jugador convocado para cumplir los 2 minutos.", true);
    if (serving.player_id === player.player_id) return toast("El 2+10 debe cumplirlo otro jugador convocado.", true);
  }
  try {
    const snapshot = await api(`/api/powerplays/${teamKey}/start`, {
      method: "POST",
      body: JSON.stringify({
        player_id: player.player_id,
        penalty_type: type,
        serving_player_id: type === "2+10" ? serving.player_id : "",
      }),
    });
    render(snapshot);
    toast("Expulsión enlazada al reloj OCR.");
  } catch (error) { toast(error.message, true); }
}

async function endPenalty(teamKey) {
  try {
    const snapshot = await api(`/api/powerplays/${teamKey}/end`, { method: "POST" });
    render(snapshot);
  } catch (error) { toast(error.message, true); }
}

async function loadCompetitions(initialRows = null) {
  try {
    const rows = Array.isArray(initialRows) ? initialRows : await api("/api/competitions");
    const select = $("#competition-select");
    const matchSelect = $("#match-select");
    matchSelect.innerHTML = '<option value="">Selecciona primero una competición</option>';
    select.innerHTML = '<option value="">Selecciona una competición</option>';
    rows.forEach((row) => select.append(new Option(row.label || row.name, row.id)));
    if (rows.length === 1) {
      select.value = rows[0].id;
      await loadMatches(rows[0].id);
    }
  } catch (error) {
    toast(error.message, true);
    if (error.status === 401) openModal("login-modal");
  }
}

async function loadMatches(competitionId) {
  const select = $("#match-select");
  select.innerHTML = '<option value="">Cargando partidos…</option>';
  if (!competitionId) return;
  try {
    const rows = await api(`/api/competitions/${competitionId}/matches`);
    select.innerHTML = rows.length ? '<option value="">Selecciona un partido</option>' : '<option value="">No hay partidos asignados hoy</option>';
    rows.forEach((row) => select.append(new Option(row.label, row.id)));
    select.value = "";
  } catch (error) { toast(error.message, true); }
}

async function saveAttendance() {
  if (!app.snapshot?.online?.match?.id) return toast("Carga primero un partido online.", true);
  const selected = { team1: [], team2: [] };
  $$('[data-attendance-team]').forEach((checkbox) => {
    if (checkbox.checked) selected[checkbox.dataset.attendanceTeam].push(checkbox.value);
  });
  try {
    const snapshot = await api("/api/match/attendance", {
      method: "PUT",
      body: JSON.stringify({ ...selected, starters: app.starters }),
    });
    render(snapshot);
    toast("Convocatoria y alineación guardadas.");
  } catch (error) { toast(error.message, true); }
}

async function refreshWindows() {
  try {
    const rows = await api("/api/ocr/sources");
    const select = $("#ocr-window");
    const current = select.value || ocrSourceKey(app.snapshot?.ocr || {});
    select.innerHTML = '<option value="">Selecciona una fuente de vídeo</option>';
    const windows = rows.filter((row) => row.source_type === "window");
    const cameras = rows.filter((row) => row.source_type === "camera");
    const addGroup = (label, items) => {
      if (!items.length) return;
      const group = document.createElement("optgroup");
      group.label = label;
      items.forEach((row) => {
        const option = new Option(`${row.label}${row.detail ? ` · ${row.detail}` : ""}`, row.source_key);
        option.dataset.sourceType = row.source_type;
        option.dataset.sourceId = String(row.source_id || "");
        option.dataset.sourceLabel = row.label;
        group.appendChild(option);
      });
      select.appendChild(group);
    };
    addGroup("Ventanas", windows);
    addGroup("Cámaras", cameras);
    if (current && [...select.options].some((option) => option.value === current)) select.value = current;
    else if (current && previewController) previewController.reset("La fuente anterior ya no está disponible. Selecciona otra fuente.");
    toast(`${windows.length} ventanas · ${cameras.length} cámaras encontradas.`);
  } catch (error) { toast(error.message, true); }
}

async function refreshOBSProjectorWindows({ announce = false, force = false } = {}) {
  const select = $("#settings-projector-window");
  if (!select) return;
  const configured = app.snapshot?.settings?.obs?.projector_window || select.dataset.configuredValue || select.value || "";
  if (!force && select.dataset.windowsLoaded === "1") {
    if (document.activeElement !== select && configured && [...select.options].some((option) => option.value === configured)) select.value = configured;
    return;
  }
  try {
    const rows = await api("/api/obs/projector-windows");
    select.innerHTML = '<option value="">Selección automática de Programa</option>';
    const group = document.createElement("optgroup");
    group.label = "Ventanas abiertas";
    rows.forEach((row) => {
      const detail = Array.isArray(row.rect) && row.rect.length >= 4 ? ` · ${row.rect[2]}×${row.rect[3]}` : "";
      group.appendChild(new Option(`${row.label}${detail}`, row.selection_key || row.label));
    });
    if (rows.length) select.appendChild(group);
    select.dataset.windowsLoaded = "1";
    if (configured && ![...select.options].some((option) => option.value === configured)) {
      const saved = new Option(`${configured} · guardada`, configured);
      select.insertBefore(saved, select.children[1] || null);
    }
    select.value = configured;
    if (announce) toast(`${rows.length} ventanas abiertas encontradas.`);
  } catch (error) {
    if (configured && ![...select.options].some((option) => option.value === configured)) select.appendChild(new Option(configured, configured));
    select.value = configured;
    if (announce) toast(error.message, true);
  }
}

function openGoalRegistration(teamKey) {
  if (!app.snapshot?.online?.match?.id) return toast("Carga primero un partido online.", true);
  const players = calledUpPlayers(teamKey);
  if (!players.length) return toast("No hay jugadores disponibles para este equipo.", true);
  app.goalMarkerPromise = captureReplayNow("Gol", teamKey);
  app.goalTeam = teamKey;
  app.goalRequestId = crypto.randomUUID();
  app.goalScoreBefore = Number((app.snapshot?.graphic_scores || app.snapshot?.scores)?.[teamKey === "team1" ? "team1_score" : "team2_score"] || 0);
  $("#goal-team").value = teamKey;
  const teamName = app.snapshot?.state?.[teamKey]?.name || (teamKey === "team1" ? "Local" : "Visitante");
  $("#goal-modal-title").textContent = `Registrar gol · ${teamName}`;
  const scorer = $("#goal-scorer");
  const assistant = $("#goal-assistant");
  scorer.innerHTML = '<option value="">Selecciona goleador</option>';
  assistant.innerHTML = '<option value="">Sin asistencia</option>';
  players.forEach((player) => {
    scorer.append(new Option(playerOption(player), player.player_id));
    assistant.append(new Option(playerOption(player), player.player_id));
  });
  $("#goal-time").value = app.snapshot?.scores?.time || "";
  $("#goal-increment-score").checked = false;
  openModal("goal-modal");
}

async function submitGoal(event) {
  event.preventDefault();
  const team = $("#goal-team").value;
  const scorerId = $("#goal-scorer").value;
  const assistantId = $("#goal-assistant").value || null;
  if (!scorerId) return toast("Selecciona el goleador.", true);
  if (assistantId && assistantId === scorerId) return toast("Goleador y asistente no pueden ser el mismo jugador.", true);
  try {
    const snapshot = await api("/api/events/goal", {
      method: "POST",
      body: JSON.stringify({
        team,
        scorer_id: scorerId,
        assistant_id: assistantId,
        match_time: $("#goal-time").value.trim(),
        increment_manual_score: true,
        score_before: app.goalScoreBefore,
        request_id: app.goalRequestId,
        marker_id: await app.goalMarkerPromise || "",
      }),
    });
    render(snapshot);
    closeModal("goal-modal");
    toast("Gol registrado en el acta.");
    if (snapshot.goal_replay_flow && snapshot.goal_replay_marker_id) markReplay({goalFlow:true, markerId:snapshot.goal_replay_marker_id});
  } catch (error) { toast(error.message, true); }
}

async function refreshEvents() {
  try {
    render(await api("/api/events/refresh", { method: "POST" }));
    toast("Eventos actualizados.");
  } catch (error) { toast(error.message, true); }
}

async function cancelEvent(eventId) {
  if (!eventId || !window.confirm("¿Anular este evento del acta?")) return;
  try {
    render(await api(`/api/events/${encodeURIComponent(eventId)}`, { method: "DELETE" }));
    toast("Evento anulado.");
  } catch (error) { toast(error.message, true); }
}

async function refreshStatistics() {
  try {
    render(await api("/api/statistics/refresh", { method: "POST" }));
    toast("Estadísticas actualizadas desde Supabase.");
  } catch (error) { toast(error.message, true); }
}

function syncOCRCanvasSize() {
  const image = $("#ocr-preview-image");
  const canvas = $("#ocr-region-canvas");
  if (!image.classList.contains("is-visible") || !image.clientWidth || !image.clientHeight) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.style.width = `${image.clientWidth}px`;
  canvas.style.height = `${image.clientHeight}px`;
  canvas.width = Math.max(1, Math.round(image.clientWidth * dpr));
  canvas.height = Math.max(1, Math.round(image.clientHeight * dpr));
  const context = canvas.getContext("2d");
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawOCRRegions();
}

function drawOCRRegions() {
  const canvas = $("#ocr-region-canvas");
  if (!canvas || !canvas.clientWidth || !canvas.clientHeight) return;
  const context = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  if (!$("#ocr-preview-image").classList.contains("is-visible")) return;
  if (app.ocrPerspectiveEdit) {
    const points = app.ocrPerspectiveDraft || [];
    context.strokeStyle = "#4b7cff";
    context.fillStyle = "rgba(75,124,255,.18)";
    context.lineWidth = 2;
    if (points.length) {
      context.beginPath();
      context.moveTo(points[0].x, points[0].y);
      points.slice(1).forEach((point) => context.lineTo(point.x, point.y));
      context.stroke();
    }
    points.forEach((point, index) => {
      context.beginPath();
      context.arc(point.x, point.y, 7, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      context.fillStyle = "#ffffff";
      context.font = "800 10px Inter, sans-serif";
      context.fillText(String(index + 1), point.x - 3, point.y + 3);
      context.fillStyle = "rgba(75,124,255,.18)";
    });
    return;
  }
  const colors = { team1_score: "#4b7cff", time: "#39d98a", team2_score: "#f15368" };
  Object.entries(app.ocrRegions || {}).forEach(([key, roi]) => {
    if (!roi) return;
    const x = Number(roi.x || 0) * canvas.clientWidth;
    const y = Number(roi.y || 0) * canvas.clientHeight;
    const width = Number(roi.w || 0) * canvas.clientWidth;
    const height = Number(roi.h || 0) * canvas.clientHeight;
    context.strokeStyle = colors[key] || "#ffffff";
    context.lineWidth = key === app.activeOCRField ? 3 : 2;
    context.fillStyle = `${colors[key] || "#ffffff"}22`;
    context.fillRect(x, y, width, height);
    context.strokeRect(x, y, width, height);
    context.fillStyle = colors[key] || "#ffffff";
    context.font = "700 11px Inter, sans-serif";
    context.fillText(({ team1_score: "LOCAL", time: "TIEMPO", team2_score: "VISITANTE" })[key] || key, x + 5, Math.max(13, y - 5));
  });
  if (app.ocrDrag?.current) {
    const { x, y, width, height } = app.ocrDrag.current;
    context.strokeStyle = colors[app.activeOCRField] || "#ffffff";
    context.setLineDash([6, 4]);
    context.lineWidth = 2;
    context.strokeRect(x, y, width, height);
    context.setLineDash([]);
  }
}

function canvasPoint(event) {
  const canvas = $("#ocr-region-canvas");
  const rect = canvas.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
    y: Math.max(0, Math.min(rect.height, event.clientY - rect.top)),
  };
}

function startOCRRegionDrag(event) {
  if (!$("#ocr-preview-image").classList.contains("is-visible")) return;
  event.preventDefault();
  const start = canvasPoint(event);
  if (app.ocrPerspectiveEdit) {
    app.ocrPerspectiveDraft.push(start);
    updateOCRPerspectiveHelp();
    drawOCRRegions();
    if (app.ocrPerspectiveDraft.length === 4) {
      const canvas = $("#ocr-region-canvas");
      const [tl, tr, br, bl] = app.ocrPerspectiveDraft;
      app.ocrPerspective = { enabled: true, points: {
        top_left: { x: tl.x / canvas.clientWidth, y: tl.y / canvas.clientHeight },
        top_right: { x: tr.x / canvas.clientWidth, y: tr.y / canvas.clientHeight },
        bottom_right: { x: br.x / canvas.clientWidth, y: br.y / canvas.clientHeight },
        bottom_left: { x: bl.x / canvas.clientWidth, y: bl.y / canvas.clientHeight },
      } };
      app.ocrPerspectiveEdit = false;
      app.ocrPerspectiveDraft = [];
      // Las ROI pertenecen al espacio rectificado. Una perspectiva nueva cambia
      // ese sistema de coordenadas, por lo que obligamos a dibujarlas de nuevo.
      app.ocrRegions = { team1_score: null, time: null, team2_score: null };
      app.ocrDirty = true;
      updateOCRPerspectiveHelp();
      saveOCRConfiguration(false).then((ok) => {
        if (ok) {
          captureOCRPreview();
          toast("Perspectiva aplicada. Vuelve a dibujar Local, Tiempo y Visitante sobre la imagen rectificada.");
        }
      });
    }
    return;
  }
  app.ocrDrag = { start, current: { x: start.x, y: start.y, width: 0, height: 0 } };
  $("#ocr-region-canvas").setPointerCapture?.(event.pointerId);
}

function moveOCRRegionDrag(event) {
  if (!app.ocrDrag) return;
  const point = canvasPoint(event);
  const start = app.ocrDrag.start;
  app.ocrDrag.current = {
    x: Math.min(start.x, point.x),
    y: Math.min(start.y, point.y),
    width: Math.abs(point.x - start.x),
    height: Math.abs(point.y - start.y),
  };
  drawOCRRegions();
}

function endOCRRegionDrag(event) {
  if (!app.ocrDrag) return;
  moveOCRRegionDrag(event);
  const canvas = $("#ocr-region-canvas");
  const rect = app.ocrDrag.current;
  if (rect.width >= 5 && rect.height >= 5) {
    app.ocrRegions[app.activeOCRField] = {
      x: rect.x / canvas.clientWidth,
      y: rect.y / canvas.clientHeight,
      w: rect.width / canvas.clientWidth,
      h: rect.height / canvas.clientHeight,
    };
    app.ocrDirty = true;
  }
  app.ocrDrag = null;
  drawOCRRegions();
}

async function activateOCRSourceSelection() {
  const source = selectedOCRSource();
  if (!source.source_id) return;
  const generation = app.ocrSourceGeneration = (app.ocrSourceGeneration || 0) + 1;
  try {
    const result = await api("/api/ocr/source/activate", {
      method: "POST",
      body: JSON.stringify(source),
    });
    if (generation !== app.ocrSourceGeneration) return;
    if (result?.snapshot) render(result.snapshot);
    const camera = result?.source?.camera || {};
    if (source.source_type === "camera") {
      const detail = camera.detail ? ` · ${camera.detail}` : "";
      toast(`Cámara OCR activa de forma continua${detail}.`);
    }
  } catch (error) {
    if (generation !== app.ocrSourceGeneration) return;
    ocrPreviewController().reset(error.message || "No se pudo activar la fuente OCR.");
    toast(error.message || "No se pudo activar la fuente OCR.", true);
  }
}

let previewController;
function ocrPreviewController() {
  if (!previewController) previewController = new window.OCRPreviewController({
    image: $("#ocr-preview-image"), empty: $("#ocr-empty"), status: $("#ocr-current-window"),
    onReady: () => requestAnimationFrame(syncOCRCanvasSize),
    onReset: () => {
      app.ocrDrag = null;
      const canvas = $("#ocr-region-canvas");
      canvas.width = 1;
      canvas.height = 1;
    },
    onError: (message) => toast(message, true),
  });
  return previewController;
}

async function captureOCRPreview() {
  const selected = selectedOCRSource();
  const fallback = app.snapshot?.ocr || {};
  const source = selected.source_id ? selected : {
    source_type: fallback.source_type || "window",
    source_id: String(fallback.source_id || ""),
    source_label: fallback.source_label || fallback.window_title || "",
  };
  if (!source.source_id && !source.source_label) return toast("Selecciona una fuente OCR.", true);
  const raw = app.ocrPerspectiveEdit ? "&raw=true" : "";
  return ocrPreviewController().load(
    `/api/ocr/preview?source_type=${encodeURIComponent(source.source_type)}&source_id=${encodeURIComponent(source.source_id)}&window_title=${encodeURIComponent(source.source_label)}${raw}&v=${Date.now()}`,
    source.source_label,
  );
}


async function editOCRPerspective() {
  const selected = selectedOCRSource();
  const fallback = app.snapshot?.ocr || {};
  if (!selected.source_id && !fallback.source_id && !(fallback.source_label || fallback.window_title)) return toast("Selecciona una fuente OCR.", true);
  app.ocrPerspectiveEdit = true;
  app.ocrPerspectiveDraft = [];
  updateOCRPerspectiveHelp();
  await captureOCRPreview();
}

async function resetOCRPerspective() {
  app.ocrPerspective = normalizedPerspective(null);
  app.ocrPerspectiveEdit = false;
  app.ocrPerspectiveDraft = [];
  app.ocrRegions = { team1_score: null, time: null, team2_score: null };
  app.ocrDirty = true;
  updateOCRPerspectiveHelp();
  if (await saveOCRConfiguration(false)) {
    await captureOCRPreview();
    toast("Perspectiva OCR eliminada.");
  }
}

async function saveOCRConfiguration(showToast = true) {
  try {
    const snapshot = await api("/api/ocr/config", {
      method: "PUT",
      body: JSON.stringify({
        ...(() => {
          const selected = selectedOCRSource();
          const fallback = app.snapshot?.ocr || {};
          const source = selected.source_id ? selected : { source_type: fallback.source_type || "window", source_id: String(fallback.source_id || ""), source_label: fallback.source_label || fallback.window_title || "" };
          return { ...source, window_title: source.source_type === "window" ? source.source_label : "" };
        })(),
        poll_ms: Number($("#ocr-poll").value || 700),
        regions: app.ocrRegions || {},
        perspective: app.ocrPerspective || normalizedPerspective(null),
        model: app.snapshot?.ocr?.model || { model_name: "en_PP-OCRv4_mobile_rec", model_dir: "", min_confidence: 0.25 },
      }),
    });
    app.ocrDirty = false;
    render(snapshot);
    if (showToast) toast("Configuración OCR guardada.");
    return true;
  } catch (error) {
    toast(error.message, true);
    return false;
  }
}

async function startOCR() {
  if (!(await saveOCRConfiguration(false))) return;
  try {
    render(await api("/api/ocr/start", { method: "POST" }));
    toast("OCR iniciado.");
  } catch (error) { toast(error.message, true); }
}

async function stopOCR() {
  try {
    render(await api("/api/ocr/stop", { method: "POST" }));
    toast("OCR detenido.");
  } catch (error) { toast(error.message, true); }
}

async function clearAllOverlays() {
  try {
    render(await api("/api/overlays/hide-all", { method: "POST" }));
    toast("Emisión limpia.");
  } catch (error) { toast(error.message, true); }
}

const OVERLAY_CANVAS = Object.freeze({ width: 1920, height: 1080 });

function fitOverlayFrame(iframe) {
  if (!iframe) return;
  const stage = iframe.parentElement;
  if (!stage) return;
  const width = Math.max(1, stage.clientWidth);
  const height = Math.max(1, stage.clientHeight);
  const scale = Math.min(width / OVERLAY_CANVAS.width, height / OVERLAY_CANVAS.height);
  const renderedWidth = OVERLAY_CANVAS.width * scale;
  const renderedHeight = OVERLAY_CANVAS.height * scale;
  iframe.style.width = `${OVERLAY_CANVAS.width}px`;
  iframe.style.height = `${OVERLAY_CANVAS.height}px`;
  iframe.style.left = `${Math.max(0, (width - renderedWidth) / 2)}px`;
  iframe.style.top = `${Math.max(0, (height - renderedHeight) / 2)}px`;
  iframe.style.transform = `scale(${scale})`;
}

function fitAllOverlayFrames() {
  $$("iframe.overlay-fit-frame").forEach(fitOverlayFrame);
}

function bindOverlayFrameFitting() {
  const frames = $$("iframe.overlay-fit-frame");
  frames.forEach((frame) => {
    frame.addEventListener("load", () => requestAnimationFrame(() => fitOverlayFrame(frame)));
    if (typeof ResizeObserver !== "undefined" && frame.parentElement) {
      const observer = new ResizeObserver(() => requestAnimationFrame(() => fitOverlayFrame(frame)));
      observer.observe(frame.parentElement);
      frame._fitObserver = observer;
    }
  });
  window.addEventListener("resize", () => requestAnimationFrame(fitAllOverlayFrames));
  requestAnimationFrame(fitAllOverlayFrames);
}

const PRODUCTION_LAYOUT_KEY = "secretariatpro-production-layout-v1";
const DEFAULT_PRODUCTION_LAYOUT = { rows: 46, top: 68, bottom: 72 };

function clampNumber(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, Number(value) || 0));
}

function loadProductionLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(PRODUCTION_LAYOUT_KEY) || "null");
    return {
      rows: clampNumber(saved?.rows ?? DEFAULT_PRODUCTION_LAYOUT.rows, 33, 64),
      top: clampNumber(saved?.top ?? DEFAULT_PRODUCTION_LAYOUT.top, 43, 78),
      bottom: clampNumber(saved?.bottom ?? DEFAULT_PRODUCTION_LAYOUT.bottom, 50, 82),
    };
  } catch (_) {
    return { ...DEFAULT_PRODUCTION_LAYOUT };
  }
}

function applyProductionLayout(layout, persist = false) {
  const shell = $(".production-fixed-shell");
  const topRow = $(".production-top-row");
  const bottomRow = $("#production-bottom-row");
  if (!shell || !topRow || !bottomRow) return;
  shell.style.setProperty("--production-top-size", `${layout.rows}%`);
  topRow.style.setProperty("--production-monitor-size", `${layout.top}%`);
  bottomRow.style.setProperty("--production-actions-size", `${layout.bottom}%`);
  app.productionLayout = { ...layout };
  if (persist) {
    try { localStorage.setItem(PRODUCTION_LAYOUT_KEY, JSON.stringify(layout)); } catch (_) { /* desktop privacy mode */ }
  }
  requestAnimationFrame(fitAllOverlayFrames);
}

function productionRatioForPointer(kind, event) {
  if (kind === "rows") {
    const shell = $(".production-fixed-shell");
    const rect = shell?.getBoundingClientRect();
    if (!rect?.height) return null;
    return clampNumber(((event.clientY - rect.top) / rect.height) * 100, 33, 64);
  }
  const row = kind === "top" ? $(".production-top-row") : $("#production-bottom-row");
  const rect = row?.getBoundingClientRect();
  if (!rect?.width) return null;
  const limits = kind === "top" ? [43, 78] : [50, 82];
  return clampNumber(((event.clientX - rect.left) / rect.width) * 100, limits[0], limits[1]);
}

function bindProductionResizers() {
  applyProductionLayout(loadProductionLayout());
  $$('[data-production-resize]').forEach((handle) => {
    const kind = handle.dataset.productionResize;
    handle.addEventListener("pointerdown", (event) => {
      if (handle.hidden) return;
      event.preventDefault();
      handle.setPointerCapture?.(event.pointerId);
      document.body.classList.add("is-resizing-production");
      const move = (moveEvent) => {
        const ratio = productionRatioForPointer(kind, moveEvent);
        if (ratio === null) return;
        const layout = { ...(app.productionLayout || DEFAULT_PRODUCTION_LAYOUT) };
        if (kind === "rows") layout.rows = ratio;
        else if (kind === "top") layout.top = ratio;
        else layout.bottom = ratio;
        applyProductionLayout(layout);
      };
      const finish = () => {
        document.body.classList.remove("is-resizing-production");
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", finish);
        handle.removeEventListener("pointercancel", finish);
        applyProductionLayout(app.productionLayout || DEFAULT_PRODUCTION_LAYOUT, true);
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", finish);
      handle.addEventListener("pointercancel", finish);
    });
    handle.addEventListener("dblclick", () => applyProductionLayout({ ...DEFAULT_PRODUCTION_LAYOUT }, true));
    handle.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      const layout = { ...(app.productionLayout || DEFAULT_PRODUCTION_LAYOUT) };
      const delta = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -2 : 2;
      if (kind === "rows") layout.rows = clampNumber(layout.rows + delta, 33, 64);
      else if (kind === "top") layout.top = clampNumber(layout.top + delta, 43, 78);
      else layout.bottom = clampNumber(layout.bottom + delta, 50, 82);
      applyProductionLayout(layout, true);
    });
  });
}

function configureProgramVideo(image) {
  if (!image || image.dataset.monitorBound === "1") return;
  image.dataset.monitorBound = "1";
  image.onload = () => image.classList.add("is-live");
  image.onerror = () => {
    image.classList.remove("is-live");
    if (image.dataset.monitorWanted !== "1") return;
    clearTimeout(image._monitorRetry);
    image._monitorRetry = setTimeout(() => {
      if (image.dataset.monitorWanted === "1") image.src = `/api/obs/program-stream?v=${Date.now()}`;
    }, 900);
  };
}

function activateProgramMonitor(viewName) {
  const monitors = [
    { view: "live", image: $("#program-video") },
    { view: "production", image: $("#production-program-video") },
  ];
  monitors.forEach(({ view, image }) => {
    if (!image) return;
    configureProgramVideo(image);
    if (view === viewName) {
      image.dataset.monitorWanted = "1";
      image.classList.remove("is-live");
      image.src = `/api/obs/program-stream?v=${Date.now()}`;
    } else {
      image.dataset.monitorWanted = "0";
      clearTimeout(image._monitorRetry);
      image.removeAttribute("src");
      image.classList.remove("is-live");
    }
  });
}

function handleDocumentVisibility() {
  if (document.visibilityState !== "visible") {
    activateProgramMonitor("");
    setProductionOBSPolling(false);
    return;
  }
  setProductionOBSPolling(app.activeView === "production");
  if (app.activeView === "live" || app.activeView === "production") activateProgramMonitor(app.activeView);
}

function switchView(viewName, button = null) {
  if (viewName !== "production" && app.productionFlow.kind) closeProductionWorkflow();
  app.activeView = viewName;
  $$('[data-view]').forEach((item) => item.classList.toggle("is-active", button ? item === button : item.dataset.view === viewName));
  $$('.view').forEach((view) => view.classList.toggle("is-visible", view.id === `view-${viewName}`));
  document.body.classList.toggle("production-mode", viewName === "production");
  $("#settings-button")?.classList.toggle("is-active", viewName === "settings");
  setProductionOBSPolling(viewName === "production");
  if (viewName === "live" || viewName === "production") activateProgramMonitor(viewName);
  else activateProgramMonitor("");
  if (viewName === "live") refreshPreflight();
  requestAnimationFrame(() => {
    fitAllOverlayFrames();
    if (viewName === "production") fitProductionActionGrid();
  });
}

function bindEvents() {
  bindOverlayFrameFitting();
  bindProductionResizers();
  window.addEventListener("resize", () => requestAnimationFrame(fitProductionActionGrid));
  if (window.ResizeObserver) {
    const productionGrid = $(".production-action-grid");
    if (productionGrid) new ResizeObserver(() => requestAnimationFrame(fitProductionActionGrid)).observe(productionGrid);
  }
  $$('[data-view]').forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view, button)));
  $("#refresh-preflight")?.addEventListener("click", refreshPreflight);
  $("#close-preflight")?.addEventListener("click", () => setPreflightVisible(false));
  $("#show-preflight")?.addEventListener("click", () => setPreflightVisible(true));
  const overlayURL = $("#overlay-source-url");
  if (overlayURL) overlayURL.textContent = overlaySourceURL();
  $$('[data-copy-overlay-url]').forEach((button) => button.addEventListener("click", copyOverlaySourceURL));
  $("#open-graphics-queue")?.addEventListener("click", () => {
    openModal("graphics-queue-modal");
    requestAnimationFrame(fitAllOverlayFrames);
  });
  $("#graphics-cue-panel")?.addEventListener("change", (event) => {
    $("#graphics-cue-team-field").hidden = event.target.value !== "lineups";
  });
  $("#graphics-cue-add")?.addEventListener("click", addGraphicsCue);
  $("#graphics-cue-take")?.addEventListener("click", takeGraphicsCue);
  $("#graphics-cue-clear")?.addEventListener("click", async () => {
    try { render(await api("/api/graphics/cues", {method:"DELETE"})); }
    catch (error) { toast(error.message, true); }
  });
  $("#graphics-sequence-new")?.addEventListener("click", () => openSequenceEditor());
  $("#graphics-sequence-cancel")?.addEventListener("click", () => { $("#graphics-sequence-editor").hidden = true; });
  $("#graphics-sequence-add-step")?.addEventListener("click", () => { app.sequenceDraft.steps = readSequenceDraft(); if (app.sequenceDraft.steps.length >= 16) return; app.sequenceDraft.steps.push({panel:"scoreboard", lineup_team:"team1", duration_seconds:5, interval_seconds:0}); renderSequenceDraft(); });
  $("#graphics-sequence-save")?.addEventListener("click", saveGraphicsSequence);
  $("#graphics-sequence-steps")?.addEventListener("change", (event) => { if (!event.target.matches("[data-sequence-panel]")) return; const row = event.target.closest(".graphics-sequence-step"); $("[data-sequence-team]", row).hidden = event.target.value !== "lineups"; });
  $("#graphics-sequence-steps")?.addEventListener("click", (event) => { const remove = event.target.closest("[data-remove-sequence-step]"); if (!remove) return; app.sequenceDraft.steps = readSequenceDraft(); app.sequenceDraft.steps.splice($$(".graphics-sequence-step", $("#graphics-sequence-steps")).indexOf(remove.closest(".graphics-sequence-step")), 1); renderSequenceDraft(); });
  $("#graphics-sequence-list")?.addEventListener("click", async (event) => {
    const id = event.target.closest("[data-run-sequence],[data-edit-sequence],[data-delete-sequence]")?.dataset.runSequence || event.target.closest("[data-edit-sequence]")?.dataset.editSequence || event.target.closest("[data-delete-sequence]")?.dataset.deleteSequence;
    if (!id) return;
    const sequences = app.snapshot?.settings?.graphics_sequences || [];
    if (event.target.closest("[data-edit-sequence]")) return openSequenceEditor(sequences.find((row) => row.id === id));
    try {
      if (event.target.closest("[data-delete-sequence]")) { const payload = await api(`/api/graphics/sequences/${encodeURIComponent(id)}`, {method:"DELETE"}); app.snapshot.settings.graphics_sequences = payload.sequences; renderGraphicsSequences(payload.sequences); }
      else render(await api(`/api/graphics/sequences/${encodeURIComponent(id)}/run`, {method:"POST"}));
    } catch (error) { toast(error.message, true); }
  });
  $("#graphics-cue-list")?.addEventListener("click", async (event) => {
    const preview = event.target.closest("[data-preview-cue]");
    if (preview) { app.graphicsPreviewCue = preview.dataset.previewCue; renderGraphicsQueue(app.snapshot?.state?.graphics_queue || []); requestAnimationFrame(fitAllOverlayFrames); return; }
    const move = event.target.closest("[data-move-cue]");
    const discard = event.target.closest("[data-discard-cue]");
    if (!move && !discard) return;
    try {
      if (move) render(await api(`/api/graphics/cues/${encodeURIComponent(move.dataset.moveCue)}/position`, {method:"PATCH", body:JSON.stringify({position:Number(move.dataset.position)})}));
      else render(await api(`/api/graphics/cues/${encodeURIComponent(discard.dataset.discardCue)}`, {method:"DELETE"}));
    }
    catch (error) { toast(error.message, true); }
  });
  $("#open-replays")?.addEventListener("click", () => { if (app.productionFlow.kind === "replay") return; app.replayPickingLabel=false; openModal("replay-modal"); renderReplayComposer(); });
  $("#replay-buffer-toggle")?.addEventListener("click", toggleReplayBuffer);
  $("#replay-mark")?.addEventListener("click", markReplay);
  $("#replay-take")?.addEventListener("click", () => controlReplay("take"));
  $("#replay-out")?.addEventListener("click", () => controlReplay("out"));
  $("#replay-next-camera")?.addEventListener("click", () => controlReplay("camera/next"));
  $("#replay-previous-camera")?.addEventListener("click", () => controlReplay("camera/previous"));
  $("#replay-build-highlights")?.addEventListener("click", buildHighlights);
  $("#replay-open-folder")?.addEventListener("click", async () => { try { await api("/api/replays/folder", {method:"POST"}); } catch(error) { toast(error.message, true); } });
  window.setInterval(async () => {
    if (($("#replay-modal")?.hidden && app.productionFlow.kind !== "replay") || app.replayPolling) return;
    app.replayPolling = true;
    try { renderReplays(await api("/api/replays")); } catch (_) {} finally { app.replayPolling = false; }
  }, 1500);
  $("#secretariatdeck-highlight")?.addEventListener("click", () => markReplay());


  $("#replay-composer-save")?.addEventListener("click", () => saveReplayComposition(false));
  $("#replay-composer-take")?.addEventListener("click", () => saveReplayComposition(true));
  $("#replay-goal-skip")?.addEventListener("click", skipReplayDeck);
  $("#replay-list")?.addEventListener("change", async (event) => {
    const input = event.target.closest("[data-replay-include]"); if (!input) return;
    try { renderReplays(await api(`/api/replays/${encodeURIComponent(input.dataset.replayInclude)}`, {method:"PATCH", body:JSON.stringify({included:input.checked})})); }
    catch (error) { input.checked = !input.checked; toast(error.message, true); }
  });
  $("#replay-label-options").addEventListener("click", e => { const b=e.target.closest("[data-event-label]"); if (!b) return; if (b.dataset.eventLabel === "Otro") return $("#replay-custom-label").focus(); markReplay({label:b.dataset.eventLabel}); });
  $("#replay-use-label").addEventListener("click", () => { const label=$("#replay-custom-label").value.trim(); if (label) markReplay({label}); });
  $("#replay-composer").addEventListener("click", e => {
    const b=e.target.closest("button"); if (!b) return;
    const c=app.replayComposer;
    if (b.dataset.templateAction) return replayTemplateAction(b.dataset.templateAction);
    if (b.dataset.shotCamera) { c.draft={camera:Number(b.dataset.shotCamera)}; c.stage="duration"; }
    else if (b.dataset.shotDuration || b.hasAttribute("data-shot-manual")) { const duration=Number(b.dataset.shotDuration || $("#shot-manual-seconds").value); if (!Number.isInteger(duration)||duration<1||duration>60) return; c.draft.duration_seconds=duration; c.stage="speed"; }
    else if (b.dataset.shotSpeed) { const segment={...c.draft,speed_percent:Number(b.dataset.shotSpeed)}; if (Number.isInteger(c.editIndex)) c.segments[c.editIndex]=segment; else c.segments.push(segment); delete c.editIndex; c.stage="next"; }
    else if (b.hasAttribute("data-shot-another")) c.stage="camera";
    else if (b.hasAttribute("data-shot-finish")) c.stage="done";
    else if (b.hasAttribute("data-shot-edit")) { c.editIndex=Number(b.dataset.shotEdit); c.stage="camera"; }
    else if (b.hasAttribute("data-shot-delete")) c.segments.splice(Number(b.dataset.shotDelete),1);
    else return;
    renderReplayComposer();
  });
  $("#replay-template-select").addEventListener("change", e => {
    const row=(app.replayTemplates || []).find(t=>t.id===e.target.value); if (!row) return;
    app.replayComposer.segments=row.segments.map(s=>({...s})); app.replayComposer.stage="done";
    $("#replay-template-name").value=row.name; $("#replay-template-default").checked=Boolean(row.default);
    renderReplayComposer();
  });
  $("#replay-search").addEventListener("input",renderReplayLibrary);
  $("#replay-filter").addEventListener("change",renderReplayLibrary);
  $("#replay-period-filter").addEventListener("change",renderReplayLibrary);
  $("#replay-exports").addEventListener("click", async e => {
    const b=e.target.closest("button"); if (!b) return;
    try {
      if (b.dataset.replayPreview) {
        const row=(app.replayLibrary?.highlights || []).find(x=>x.id===b.dataset.replayPreview); if (!row) return;
        $("#replay-preview").hidden=false;
        const video=$("#replay-preview-video"); video.src=`/api/replays/media/${encodeURIComponent(row.id)}`;
        $("#replay-preview-sequence").textContent=(row.sequence || []).map(s=>`CAM ${s.camera} · ${s.duration_seconds}s · ${s.speed_percent}%`).join(" → ");
        video.scrollIntoView({block:"nearest"});
      } else if (b.dataset.replayLaunch) { b.disabled=true; await api(`/api/replays/library/${encodeURIComponent(b.dataset.replayLaunch)}/take`,{method:"POST"}); closeModal("replay-modal"); }
      else if (b.dataset.replayDelete) {
        b.disabled=true;
        $("#replay-preview-video").pause();
        const result=await api(`/api/replays/library/${encodeURIComponent(b.dataset.replayDelete)}`,{method:"DELETE"});
        app.lastDeletedReplay=result.deleted.id;
        $("#replay-undo-delete").hidden=false;
        renderReplays(result);
      }
      else if (b.hasAttribute("data-replay-folder")) await api("/api/replays/folder",{method:"POST"});
    } catch(error) { toast(error.message,true); b.disabled=false; }
  });
  $("#replay-undo-delete").addEventListener("click",async () => {
    if(!app.lastDeletedReplay)return;
    try { renderReplays(await api(`/api/replays/library/${encodeURIComponent(app.lastDeletedReplay)}/restore`,{method:"POST"})); app.lastDeletedReplay=""; $("#replay-undo-delete").hidden=true; }
    catch(error){toast(error.message,true);}
  });
  $("#replay-modal-close").addEventListener("click", () => $("#replay-preview-video").pause());
  $("#match-period-control")?.addEventListener("change", async (event) => {
    try { render(await api("/api/match/period", {method:"POST", body:JSON.stringify({value:Number(event.target.value)})})); }
    catch (error) { toast(error.message, true); }
  });

  $$('[data-overlay]').forEach((button) => button.addEventListener("click", () => toggleOverlay(button)));
  $$('[data-score-team]').forEach((button) => button.addEventListener("click", () => changeScore(button.dataset.scoreTeam, Number(button.dataset.scoreDelta))));
  $$('[data-score-mode]').forEach((button) => button.addEventListener("click", () => setScoreMode(button.dataset.scoreMode)));
  $$('[data-register-goal]').forEach((button) => button.addEventListener("click", () => {
    if (button.closest("#view-production")) openProductionWorkflow("goal", button.dataset.registerGoal);
    else openGoalRegistration(button.dataset.registerGoal);
  }));
  $$('[data-player-profile-team]').forEach((button) => button.addEventListener("click", () => {
    openProductionWorkflow("profile", button.dataset.playerProfileTeam);
  }));
  $$('[data-pp-start]').forEach((button) => button.addEventListener("click", () => {
    if ((button.dataset.ppContext || "direct") === "production") openProductionWorkflow("penalty", button.dataset.ppStart);
    else startPenalty(button.dataset.ppStart, "direct");
  }));
  $$('[data-pp-end]').forEach((button) => button.addEventListener("click", () => endPenalty(button.dataset.ppEnd)));
  $$('[data-show-lineup]').forEach((button) => button.addEventListener("click", async () => {
    try {
      const snapshot = await api("/api/overlays/lineups/toggle", {
        method: "POST",
        body: JSON.stringify({ lineup_team: button.dataset.showLineup }),
      });
      render(snapshot);
    } catch (error) { toast(error.message, true); }
  }));

  $$('[data-hide-all], #hide-all').forEach((button) => button.addEventListener("click", clearAllOverlays));
  $("#refresh-preview").addEventListener("click", () => {
    $("#overlay-preview").src = `/overlay.html?v=${Date.now()}`;
    if (app.activeView === "live") activateProgramMonitor("live");
  });
  $("#production-refresh-monitor")?.addEventListener("click", () => {
    activateProgramMonitor("production");
  });
  $("#production-reset-layout")?.addEventListener("click", () => applyProductionLayout({ ...DEFAULT_PRODUCTION_LAYOUT }, true));
  $(".production-action-grid")?.addEventListener("click", (event) => {
    const sceneButton = event.target.closest("[data-obs-scene]");
    if (sceneButton) setProgramScene(sceneButton.dataset.obsScene);
  });
  $("#production-workflow-grid")?.addEventListener("click", handleProductionWorkflowClick);
  $("#production-workflow-close")?.addEventListener("click", closeProductionWorkflow);
  $("#production-workflow-back")?.addEventListener("click", productionWorkflowBack);

  $("#profile-button").addEventListener("click", () => openModal("login-modal"));
  $("#match-context").addEventListener("click", async () => {
    if (!app.snapshot?.online?.connected) return openModal("login-modal");
    openModal("match-modal");
    await loadCompetitions();
  });
  $$('[data-close]').forEach((button) => button.addEventListener("click", () => closeModal(button.dataset.close)));
  $$('.modal-backdrop').forEach((backdrop) => backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop && !(backdrop.id === "replay-modal" && app.replayComposer.goalFlow)) backdrop.hidden = true;
  }));

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (app.loginBusy) return;
    app.loginBusy = true;
    const button = event.currentTarget.querySelector('button[type="submit"]');
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = textTranslation("Iniciando sesión…", app.language);
    event.currentTarget.setAttribute("aria-busy", "true");
    try {
      const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email: $("#login-email").value, password: $("#login-password").value }) });
      $("#login-password").value = "";
      const snapshot = result.snapshot;
      render(snapshot);
      closeModal("login-modal");
      if (snapshot.online?.access?.allowed) {
        openModal("match-modal");
        await loadCompetitions(result.competitions);
        refreshTabletAccess();
        toast("Sesión iniciada. Membresía validada.");
        (result.warnings || []).forEach((message) => toast(message, true));
      } else {
        toast(snapshot.online?.access?.message || "La membresía no está activa.", true);
      }
    } catch (error) { toast(error.message, true); }
    finally {
      app.loginBusy = false;
      button.disabled = false;
      button.textContent = originalLabel;
      $("#login-form").removeAttribute("aria-busy");
    }
  });
  $("#forgot-password-button").addEventListener("click", async () => {
    const button = $("#forgot-password-button");
    const email = $("#login-email").value.trim();
    if (!email || !email.includes("@")) return toast("Introduce un correo electrónico válido.", true);
    button.disabled = true;
    try {
      const result = await api("/api/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      toast(result.message || "Si la cuenta existe, recibirás un correo para restablecer la contraseña.");
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; }
  });

  $("#account-profile-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const displayName = $("#account-display-name").value.trim();
    try {
      const profile = await api("/api/account/profile", {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName }),
      });
      applyAccountProfile(profile);
      toast("Perfil actualizado.");
    } catch (error) { toast(error.message, true); }
  });

  $("#account-avatar-button").addEventListener("click", () => $("#account-avatar-file").click());
  $("#account-avatar-file").addEventListener("change", async (event) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { input.value = ""; return toast("Selecciona una imagen válida.", true); }
    if (file.size > 8 * 1024 * 1024) { input.value = ""; return toast("La imagen no puede superar 8 MB.", true); }
    const button = $("#account-avatar-button");
    button.disabled = true;
    try {
      const imageData = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("No se ha podido leer la imagen seleccionada."));
        reader.readAsDataURL(file);
      });
      const profile = await api("/api/account/avatar", {
        method: "POST",
        body: JSON.stringify({ image_data: imageData }),
      });
      applyAccountProfile(profile);
      toast("Foto de perfil actualizada.");
    } catch (error) { toast(error.message, true); }
    finally { input.value = ""; button.disabled = false; }
  });

  $("#account-remove-avatar").addEventListener("click", async () => {
    try {
      const profile = await api("/api/account/avatar", { method: "DELETE" });
      applyAccountProfile(profile);
      toast("Foto de perfil eliminada.");
    } catch (error) { toast(error.message, true); }
  });

  $("#account-password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = $("#account-new-password").value;
    const confirmation = $("#account-confirm-password").value;
    if (password.length < 8) return toast("La nueva contraseña debe tener al menos 8 caracteres.", true);
    if (password !== confirmation) return toast("Las contraseñas no coinciden.", true);
    try {
      const result = await api("/api/account/password", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      $("#account-new-password").value = "";
      $("#account-confirm-password").value = "";
      toast(result.message || "Contraseña actualizada correctamente.");
    } catch (error) { toast(error.message, true); }
  });

  $("#logout-button").addEventListener("click", async () => {
    try { render(await api("/api/auth/logout", { method: "POST" })); closeModal("login-modal"); toast("Sesión cerrada."); }
    catch (error) { toast(error.message, true); }
  });
  $("#account-workspace-select")?.addEventListener("change", async (event) => {
    const workspaceId = event.target.value;
    if (!workspaceId) return;
    try {
      const snapshot = await api("/api/workspaces/activate", {
        method: "POST",
        body: JSON.stringify({ workspace_id: workspaceId }),
      });
      render(snapshot);
      if (snapshot.online?.access?.allowed) await loadCompetitions();
      toast(`Espacio activo: ${snapshot.online?.workspace?.name || "SecretariatPro"}`);
    } catch (error) { toast(error.message, true); }
  });
  $("#subscription-login-button")?.addEventListener("click", () => openModal("login-modal"));
  $("#subscription-account-button")?.addEventListener("click", () => openModal("login-modal"));

  $("#competition-select").addEventListener("change", (event) => loadMatches(event.target.value));
  $("#load-match-button").addEventListener("click", async () => {
    const competition = $("#competition-select").value;
    const match = $("#match-select").value;
    if (!competition || !match) return toast("Selecciona competición y partido.", true);
    try {
      const snapshot = await api(`/api/competitions/${competition}/matches/${match}/load`, { method: "POST" });
      render(snapshot);
      closeModal("match-modal");
      toast("Partido cargado.");
    } catch (error) { toast(error.message, true); }
  });

  $$('[data-starter-team]').forEach((button) => button.addEventListener("click", () => {
    app.starterTeam = button.dataset.starterTeam;
    $$('[data-starter-team]').forEach((item) => item.classList.toggle("is-active", item === button));
    populateFormation();
  }));
  $("#save-attendance").addEventListener("click", saveAttendance);
  $("#goal-form").addEventListener("submit", submitGoal);
  $("#refresh-events").addEventListener("click", refreshEvents);
  $("#finish-match-button")?.addEventListener("click", openFinishMatchModal);
  $("#finish-match-form")?.addEventListener("submit", submitFinishMatch);
  [$("#finish-home-score"), $("#finish-away-score")].forEach((field) => field?.addEventListener("input", () => {
    const home = $("#finish-home-name")?.textContent || "LOCAL";
    const away = $("#finish-away-name")?.textContent || "VISITANTE";
    $("#finish-match-summary").textContent = `${home} ${$("#finish-home-score").value || 0} — ${$("#finish-away-score").value || 0} ${away}`;
  }));
  $("#events-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-cancel-event]");
    if (button) cancelEvent(button.dataset.cancelEvent);
  });
  $("#refresh-statistics").addEventListener("click", refreshStatistics);
  $("#player-profile-team")?.addEventListener("change", populatePlayerProfileMenus);
  $("#refresh-player-profile")?.addEventListener("click", () => updatePlayerProfileFromSelection(false));
  $("#show-player-profile")?.addEventListener("click", () => updatePlayerProfileFromSelection(true));
  $("#hide-player-profile")?.addEventListener("click", async () => {
    try { render(await api("/api/overlays/player_profile/hide", { method: "POST" })); }
    catch (error) { toast(error.message, true); }
  });
  $("#reset-penalties").addEventListener("click", async () => {
    try { render(await api("/api/penalties/reset", { method: "POST" })); toast("Tanda reiniciada."); }
    catch (error) { toast(error.message, true); }
  });
  $$(".shootout-attempts").forEach((container) => container.addEventListener("click", (event) => {
    const button = event.target.closest(".shootout-choice");
    if (button) setPenaltyAttempt(button);
  }));

  $$('[data-empty-net]').forEach((button) => button.addEventListener("click", () => toggleEmptyNet(button.dataset.emptyNet)));
  $("#refresh-windows").addEventListener("click", refreshWindows);
  $("#ocr-window").addEventListener("change", async (event) => {
    const option = event.target.selectedOptions?.[0];
    app.ocrSourceGeneration = (app.ocrSourceGeneration || 0) + 1;
    ocrPreviewController().reset(event.target.value ? "Fuente seleccionada. Pulsa Capturar preview." : "Sin fuente seleccionada");
    app.ocrDirty = true;
    if (event.target.value) await activateOCRSourceSelection();
  });
  $("#capture-ocr-preview").addEventListener("click", captureOCRPreview);
  $("#edit-ocr-perspective")?.addEventListener("click", editOCRPerspective);
  $("#reset-ocr-perspective")?.addEventListener("click", resetOCRPerspective);
  $("#save-ocr").addEventListener("click", () => saveOCRConfiguration(true));
  $("#start-ocr").addEventListener("click", startOCR);
  $("#stop-ocr").addEventListener("click", stopOCR);
  $$('[data-ocr-field]').forEach((button) => button.addEventListener("click", () => {
    app.activeOCRField = button.dataset.ocrField;
    $$('[data-ocr-field]').forEach((item) => item.classList.toggle("is-active", item === button));
    drawOCRRegions();
  }));
  const ocrCanvas = $("#ocr-region-canvas");
  ocrCanvas.addEventListener("pointerdown", startOCRRegionDrag);
  ocrCanvas.addEventListener("pointermove", moveOCRRegionDrag);
  ocrCanvas.addEventListener("pointerup", endOCRRegionDrag);
  ocrCanvas.addEventListener("pointercancel", endOCRRegionDrag);
  window.addEventListener("resize", () => requestAnimationFrame(syncOCRCanvasSize));

  $("#settings-button").addEventListener("click", () => {
    if (app.activeView !== "settings") app.previousView = app.activeView || "live";
    switchView("settings");
    refreshTabletAccess();
  });
  $("#copy-tablet-url")?.addEventListener("click", copyTabletAccessUrl);
  $("#refresh-tablet-access")?.addEventListener("click", refreshTabletAccess);
  $("#tablet-network")?.addEventListener("change", refreshTabletAccess);
  $("#settings-back-button")?.addEventListener("click", () => switchView(app.previousView && app.previousView !== "settings" ? app.previousView : "live"));
  $("#refresh-obs-windows")?.addEventListener("click", () => refreshOBSProjectorWindows({ announce: true, force: true }));
  systemThemeQuery.addEventListener?.("change", () => {
    const active = app.appearanceDraft || app.snapshot?.settings?.appearance || DEFAULT_APPEARANCE;
    if ((active?.app_theme || "system") === "system") applyAppAppearance(active);
  });

  $("#connect-obs").addEventListener("click", async () => {
    const payload = {
      host: $("#settings-obs-host").value || "127.0.0.1",
      port: Number($("#settings-obs-port").value || 4455),
      password: $("#settings-obs-password").value || null,
      projector_window: $("#settings-projector-window").value || null,
    };
    try {
      render(await api("/api/obs/connect", { method: "POST", body: JSON.stringify(payload) }));
      $("#settings-obs-password").value = "";
      toast("OBS conectado y configuración guardada.");
    } catch (error) { toast(error.message, true); }
  });
  $("#disconnect-obs").addEventListener("click", async () => {
    try { render(await api("/api/obs/disconnect", { method: "POST" })); toast("OBS desconectado."); }
    catch (error) { toast(error.message, true); }
  });

  function finishShortcutCapture(field, value, restore = false) {
    const previous = field.dataset.previousShortcut || "";
    field.dataset.capturing = "false";
    field.classList.remove("is-capturing");
    field.value = restore ? previous : normalizedShortcutString(value);
    field.dataset.previousShortcut = field.value;
  }

  function beginShortcutCapture(field) {
    if (field.dataset.capturing === "true") return;
    field.dataset.previousShortcut = normalizedShortcutString(field.value || "");
    field.dataset.capturing = "true";
    field.classList.add("is-capturing");
    field.value = "Pulsa la combinación…";
    field.select();
  }

  Object.values(SHORTCUT_FIELDS).forEach((selector) => {
    const field = $(selector);
    if (!field) return;
    field.readOnly = true;
    field.title = "Haz clic y pulsa la combinación de teclas";
    field.addEventListener("click", () => beginShortcutCapture(field));
    field.addEventListener("focus", () => beginShortcutCapture(field));
    field.addEventListener("keydown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (event.key === "Escape") {
        finishShortcutCapture(field, "", true);
        field.blur();
        return;
      }
      if (event.key === "Backspace" || event.key === "Delete") {
        finishShortcutCapture(field, "");
        field.blur();
        return;
      }
      const combo = normalizeKeyboardEvent(event);
      if (!combo) return;
      const duplicate = Object.values(SHORTCUT_FIELDS)
        .map((otherSelector) => $(otherSelector))
        .find((other) => other && other !== field && normalizedShortcutString(other.value) === combo);
      if (duplicate) {
        toast(`El atajo ${combo} ya está asignado.`, true);
        return;
      }
      finishShortcutCapture(field, combo);
      field.blur();
    });
    field.addEventListener("blur", () => {
      if (field.dataset.capturing === "true") finishShortcutCapture(field, "", true);
      else field.value = normalizedShortcutString(field.value);
    });
  });
  document.addEventListener("keydown", handleGlobalShortcut);

  $$('[data-appearance-path]').forEach((field) => {
    field.addEventListener("input", () => {
      app.appearanceDraft = collectAppearance();
      app.appearanceDirty = true;
      applyAppAppearance(app.appearanceDraft);
    });
  });
  $("#settings-app-theme")?.addEventListener("change", (event) => {
    app.appearanceDraft = collectAppearance();
    app.appearanceDraft.app_theme = ["dark", "light", "system"].includes(event.target.value) ? event.target.value : "system";
    populateAppearanceFields(app.appearanceDraft);
    app.appearanceDirty = true;
    applyAppAppearance(app.appearanceDraft);
  });
  $("#settings-language")?.addEventListener("change", (event) => applyLanguage(event.target.value));
  $("#reset-appearance")?.addEventListener("click", () => {
    const theme = ["dark", "light", "system"].includes($("#settings-app-theme")?.value) ? $("#settings-app-theme").value : "system";
    app.appearanceDraft = mergeObject(DEFAULT_APPEARANCE, { app_theme: theme });
    populateAppearanceFields(app.appearanceDraft);
    app.appearanceDirty = true;
    applyAppAppearance(app.appearanceDraft);
    toast(app.language === "en" ? "Default overlay colours restored. Save to confirm." : "Colores originales del overlay restaurados. Guarda para confirmar.");
  });

  $("#save-settings").addEventListener("click", async () => {
    try {
      const obs = { host: $("#settings-obs-host").value, port: Number($("#settings-obs-port").value || 4455), auto_connect: $("#settings-obs-auto").checked, projector_window: $("#settings-projector-window").value, replay_auto_mark_goals: $("#settings-replay-auto-goals").checked, replay_post_roll_seconds: Number($("#settings-replay-post-roll").value || 0) };
      if ($("#settings-obs-password").value) obs.password = $("#settings-obs-password").value;
      const shortcuts = Object.fromEntries(Object.entries(SHORTCUT_FIELDS).map(([key, selector]) => [key, normalizedShortcutString($(selector)?.value || "")]).filter(([, value]) => value));
      const appearance = collectAppearance();
      const sharingToggle = $("#settings-ocr-sharing");
      const payload = { language: $("#settings-language").value, obs, shortcuts, appearance };
      if (sharingToggle?.dataset.canManage === "true") payload.ocr_data_sharing = Boolean(sharingToggle.checked);
      const snapshot = await api("/api/settings", { method: "PATCH", body: JSON.stringify(payload) });
      $("#settings-obs-password").value = "";
      app.appearanceDraft = appearance;
      app.appearanceDirty = false;
      render(snapshot);
      toast(app.language === "en" ? "Settings saved." : "Configuración guardada.");
    } catch (error) { toast(error.message, true); }
  });
}

async function boot() {
  bindEvents();
  setPreflightVisible(localStorage.getItem("secretariatpro.preflight.visible") !== "false", false);
  switchView("live");
  try { render(await api("/api/state")); }
  catch (error) { toast(error.message, true); }
  if (app.snapshot?.online?.access?.allowed) refreshTabletAccess();
  installPremiumInteractions();
  startLivePolling();
  setInterval(() => { if (app.activeView === "live") refreshPreflight(); }, 10000);
  let deliveryBusy = false;
  setInterval(async () => {
    if (document.visibilityState !== "visible" || app.activeView !== "settings" || deliveryBusy || !app.snapshot?.online?.access?.allowed) return;
    deliveryBusy = true;
    try {
      const delivery = await api("/api/ocr/sample-sharing-status");
      app.snapshot.ocr_sample_delivery = delivery;
      renderOCRDeliveryStatus(delivery, app.snapshot.settings?.ocr_data_sharing || {});
    } catch (_) {} finally { deliveryBusy = false; }
  }, 5000);
  setInterval(() => {
    if (app.socket?.readyState === WebSocket.OPEN) app.socket.send("ping");
  }, 20000);
  document.addEventListener("visibilitychange", handleDocumentVisibility);
  const desktopShell = new URLSearchParams(location.search).get("desktop") === "1";
  if (!desktopShell && "serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("/app/sw.js").catch(() => {});
  }
}

boot();
