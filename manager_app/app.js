(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    session: {},
    view: "dashboard",
    cache: {},
    modal: null,
    selectedTeamId: "",
    selectedPlayerId: "",
    teamSeasonFilter: "",
    teamCompetitionFilter: "",
    selectedTeamRosterCompetitionId: "",
    pendingImportFile: null,
    pendingImportAnalysis: null,
    selectedMatchEventId: "",
    matchEventContext: null,
    pendingMatchEventImport: null,
    preferences: { language: "en", theme: "system" },
  };

  const roleLabels = {
    owner: "Propietario",
    competition_manager: "Gestor de competiciones",
    producer: "Realizador",
  };
  const statusLabels = {
    scheduled: "Programado",
    live: "En directo",
    finished: "Finalizado",
    postponed: "Aplazado",
    cancelled: "Cancelado",
    active: "Activo",
    invited: "Invitación pendiente",
    suspended: "Suspendido",
  };
  const positionLabels = {
    goalkeeper: "Portero",
    defender: "Defensa",
    midfielder: "Medio",
    forward: "Delantero",
    left_back: "Lateral izquierdo", center_back: "Central", right_back: "Lateral derecho", pivot: "Pivote", left_wing: "Extremo izquierdo", right_wing: "Extremo derecho",
    coach: "Entrenador",
    player_coach: "Jugador-entrenador",
  };
  function positionLabel(value) {
    const key = String(value || "");
    if (key.endsWith("_coach") && key !== "player_coach") return tr(positionLabels[key.slice(0,-6)] || key.slice(0,-6)) + " + " + tr("Entrenador");
    return tr(positionLabels[key] || key || "Sin posición");
  }
  const DEFAULT_APPEARANCE = {
    scoreboard: { background: "#2a2d34", name_box: "#3b3f47", text: "#ffffff" },
    bottom_bar: { body: "#24272e", middle: "#30333b", text: "#ffffff", secondary_text: "#c6cad2" },
    panels: { background: "#171c25", surface: "#232a35", accent: "#59606c", text: "#ffffff" },
    period_strip: { enabled: false, segments: 3, labels: ["1", "2", "3"], active_color: "#8cff00", text_color: "#102000" },
    goal_celebration: { delay_seconds: 4, duration_seconds: 6 },
  };
  const PALETTE_FIELDS = {
    scoreboard: [
      ["background", "Fondo"], ["name_box", "Caja de nombres"], ["text", "Texto"],
    ],
    bottom_bar: [
      ["body", "Cuerpo"], ["middle", "Tiempo y resultado"], ["text", "Texto principal"], ["secondary_text", "Texto secundario"],
    ],
    panels: [
      ["background", "Fondo"], ["surface", "Superficie"], ["accent", "Acento"], ["text", "Texto"],
    ],
  };


  const PREFERENCE_KEYS = {
    language: "secretariatpro.manager.language",
    theme: "secretariatpro.manager.theme",
  };
  const SUPPORTED_LANGUAGES = ["es", "en", "sv", "cs", "fi", "de"];
  const UI_TRANSLATIONS = {
    en: {
      "Resumen": "Overview", "Competiciones": "Competitions", "Equipos": "Teams", "Jugadores": "Players", "Partidos": "Matches", "Usuarios": "Users", "Importación masiva": "Bulk import", "Identidad visual": "Visual identity", "Configuración": "Settings", "Membresía": "Membership", "Cerrar sesión": "Sign out",
      "PANEL DE CONTROL": "CONTROL PANEL", "Todo lo que prepares aquí estará disponible para los realizadores en SecretariatPro.": "Everything prepared here will be available to producers in SecretariatPro.", "Actualizar": "Refresh", "AGENDA": "SCHEDULE", "Próximos y últimos partidos": "Upcoming and recent matches", "Ver todos": "View all", "CUENTA": "ACCOUNT", "Datos del espacio": "Workspace details", "Tipo": "Type", "Tu rol": "Your role", "Plan": "Plan", "Válida hasta": "Valid until",
      "TEMPORADAS Y LIGAS": "SEASONS AND LEAGUES", "Crea temporadas, ligas y sistemas de puntuación. La competición activa alimentará calendario, clasificación y overlays.": "Create seasons, leagues and scoring systems. The active competition feeds schedules, standings and overlays.", "Nueva temporada": "New season", "Nueva competición": "New competition", "Temporadas": "Seasons", "ESTRUCTURA DEPORTIVA": "SPORTS STRUCTURE", "Gestiona la identidad de cada club y entra en su ficha para organizar los rosters de cada temporada y competición.": "Manage each club identity and open its profile to organize rosters by season and competition.", "Nuevo equipo": "New team", "Directorio de equipos": "Team directory", "Selecciona un equipo para consultar su ficha y sus rosters.": "Select a team to view its profile and rosters.",
      "DIRECTORIO GENERAL": "GENERAL DIRECTORY", "Crea jugadores de forma independiente y consulta o modifica sus participaciones en los distintos rosters.": "Create players independently and review or edit their roster memberships.", "Nuevo jugador": "New player", "Selecciona un jugador para consultar sus equipos, competiciones y dorsales.": "Select a player to view teams, competitions and shirt numbers.", "CALENDARIO": "SCHEDULE", "Programa encuentros, asigna realizadores y revisa el estado de cada partido.": "Schedule matches, assign producers and review each match status.", "Nuevo partido": "New match", "ORGANIZACIÓN": "ORGANIZATION", "Los usuarios mantienen su propia cuenta, pero reciben el rol y la identidad visual de esta asociación.": "Users keep their own account but receive this association's role and visual identity.", "Añadir usuario existente": "Add existing user", "El usuario debe haber creado previamente su cuenta de SecretariatPro. Después puedes incorporarlo por correo.": "The user must have created a SecretariatPro account first. You can then add them by email.",
      "EXCEL Y CSV": "EXCEL AND CSV", "Importación de jugadores": "Player import", "Importa jugadores desde cualquier Excel o CSV, aunque incluya columnas de equipo, dorsal o competición.": "Import players from any Excel or CSV file, even if it includes team, shirt number or competition columns.", "Descargar plantilla Excel": "Download Excel template", "Preparando plantilla…": "Preparing template…", "Generando el archivo Excel…": "Generating the Excel file…", "Plantilla guardada en": "Template saved in", "Plantilla Excel guardada": "Excel template saved", "Idioma actualizado": "Language updated", "Tema actualizado": "Theme updated", "Se guardará en la carpeta Descargas.": "It will be saved in the Downloads folder.", "Arrastra aquí un Excel o CSV": "Drag an Excel or CSV here", "O selecciona un archivo de hasta 20 MB.": "Or select a file up to 20 MB.", "Seleccionar archivo": "Select file", "DATOS ADMITIDOS": "ACCEPTED DATA", "Solo jugadores": "Players only", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Only first name, last name, display name and position are saved. Team, club, shirt number, roster, season and competition are always ignored.", "ANÁLISIS": "ANALYSIS", "Resultado": "Result", "¿Todo correcto?": "Is everything correct?", "Confirma para guardar los datos en Supabase.": "Confirm to save the data in Supabase.", "Cancelar": "Cancel", "Confirmar importación": "Confirm import",
      "IMAGEN DE EMISIÓN": "BROADCAST IMAGE", "Crea varias personalizaciones cuando tu cuenta lo permita, conserva las anteriores y edita cada una con la vista previa completa.": "Create multiple customizations when your account allows it, keep previous versions and edit each one with a full preview.", "Nueva personalización": "New customization", "Modo contratado": "Plan mode", "Carga en SecretariatPro": "Loaded in SecretariatPro", "Automática al iniciar sesión": "Automatic at sign-in", "VERSIÓN": "VERSION", "Editor de identidad": "Identity editor", "Borrador nuevo": "New draft", "Nombre de la versión": "Version name", "Ámbito": "Scope", "Identidad general": "General identity", "Control de realizadores": "Producer control", "Bloqueada": "Locked", "Edición permitida": "Editing allowed", "Al guardar": "On save", "Guardar borrador": "Save draft", "Publicar ahora": "Publish now", "MARCADOR": "SCOREBOARD", "Marcador principal": "Main scoreboard", "Goles y avisos": "Goals and notices", "PANELES": "PANELS", "Prematch, descanso y estadísticas": "Prematch, break and statistics", "Restablecer": "Reset", "Guardar versión": "Save version", "VISTA PREVIA": "PREVIEW", "EN DIRECTO": "LIVE", "Resumen del partido y estadísticas": "Match summary and statistics",
      "PREFERENCIAS": "PREFERENCES", "Personaliza el idioma y la apariencia del Manager. Estos ajustes solo afectan a esta aplicación y no modifican los overlays.": "Customize the Manager language and appearance. These settings only affect this application and do not modify overlays.", "GENERAL": "GENERAL", "Idioma y tema": "Language and theme", "Idioma": "Language", "Tema de la aplicación": "Application theme", "Oscuro": "Dark", "Claro": "Light", "El modo claro solo afecta al Manager, nunca a los gráficos emitidos.": "Light mode only affects the Manager, never broadcast graphics.", "Restablecer preferencias": "Reset preferences", "Aspecto del Manager": "Manager appearance", "Equipos · Jugadores · Partidos": "Teams · Players · Matches", "Acción principal": "Primary action",
      "CUENTA Y ACCESO": "ACCOUNT AND ACCESS", "La membresía habilita tanto SecretariatPro como Manager. No utiliza códigos de licencia.": "Membership enables both SecretariatPro and Manager. It does not use license codes.", "PLAN ACTUAL": "CURRENT PLAN", "Inicio": "Start", "Fin": "End", "Retención": "Retention", "CAPACIDADES DEL PLAN": "PLAN CAPABILITIES",
      "Mi perfil": "My profile", "CUENTA PERSONAL": "PERSONAL ACCOUNT", "Gestiona tu nombre, foto y contraseña desde el portal web seguro de SecretariatPro.": "Manage your name, photo and password in the secure SecretariatPro web portal.", "SESIÓN ACTUAL": "CURRENT SESSION", "PORTAL WEB": "WEB PORTAL", "Gestionar mi cuenta": "Manage my account", "El portal se abre en el navegador y permite completar invitaciones, cambiar la contraseña y actualizar los datos personales.": "The browser portal lets you complete invitations, change your password and update personal details.", "Abrir portal web": "Open web portal", "Invitar usuario": "Invite user", "Invita realizadores y gestores por correo, aunque todavía no tengan una cuenta.": "Invite producers and managers by email even when they do not have an account yet.",
      "Iniciar sesión": "Sign in", "Olvidé mi contraseña": "I forgot my password", "Correo electrónico": "Email address", "Contraseña": "Password", "ESPACIO DE TRABAJO": "WORKSPACE", "Comprobando": "Checking", "Editar": "Edit", "Eliminar": "Delete", "Guardar": "Save", "Crear": "Create", "Sí": "Yes", "No": "No", "Activo": "Active", "Activa": "Active", "Inactiva": "Inactive", "Finalizado": "Finished", "Programado": "Scheduled", "En directo": "Live", "Aplazado": "Postponed", "Cancelado": "Cancelled", "Propietario": "Owner", "Gestor de competiciones": "Competition manager", "Realizador": "Producer", "Portero": "Goalkeeper", "Defensa": "Defender", "Medio": "Midfielder", "Delantero": "Forward", "Entrenador": "Coach", "Local": "Home", "Visitante": "Away", "Sin asignar": "Unassigned", "Sin temporada": "No season", "Sin competición": "No competition", "Sin categoría": "No category", "Sin pabellón": "No venue", "Cargando…": "Loading…", "Cargando partidos…": "Loading matches…", "Datos actualizados": "Data refreshed"
    },
    sv: {
      "Resumen":"Översikt","Competiciones":"Tävlingar","Equipos":"Lag","Jugadores":"Spelare","Partidos":"Matcher","Usuarios":"Användare","Importación masiva":"Massimport","Identidad visual":"Visuell identitet","Configuración":"Inställningar","Membresía":"Medlemskap","Cerrar sesión":"Logga ut","PREFERENCIAS":"INSTÄLLNINGAR","Personaliza el idioma y la apariencia del Manager. Estos ajustes solo afectan a esta aplicación y no modifican los overlays.":"Anpassa språk och utseende i Manager. Inställningarna påverkar endast denna app och ändrar inte grafiklagren.","GENERAL":"ALLMÄNT","Idioma y tema":"Språk och tema","Idioma":"Språk","Tema de la aplicación":"Apptema","Oscuro":"Mörkt","Claro":"Ljust","El modo claro solo afecta al Manager, nunca a los gráficos emitidos.":"Ljust läge påverkar endast Manager, aldrig sändningsgrafiken.","Restablecer preferencias":"Återställ inställningar","VISTA PREVIA":"FÖRHANDSVISNING","Aspecto del Manager":"Manager-utseende","Acción principal":"Primär åtgärd","Descargar plantilla Excel":"Ladda ned Excel-mall","Se guardará en la carpeta Descargas.":"Den sparas i mappen Hämtade filer.","Iniciar sesión":"Logga in","Olvidé mi contraseña":"Jag har glömt lösenordet","Correo electrónico":"E-post","Contraseña":"Lösenord","Actualizar":"Uppdatera","Editar":"Redigera","Eliminar":"Ta bort","Guardar":"Spara","Cancelar":"Avbryt","Confirmar importación":"Bekräfta import","Seleccionar archivo":"Välj fil","Nuevo equipo":"Nytt lag","Nuevo jugador":"Ny spelare","Nuevo partido":"Ny match","Nueva temporada":"Ny säsong","Nueva competición":"Ny tävling","Nueva personalización":"Ny anpassning","Sí":"Ja","No":"Nej","Activo":"Aktiv","Activa":"Aktiv","Inactiva":"Inaktiv","Programado":"Planerad","En directo":"Live","Finalizado":"Avslutad","Portero":"Målvakt","Defensa":"Back","Medio":"Mittfältare","Delantero":"Anfallare","Entrenador":"Tränare"
    },
    cs: {
      "Resumen":"Přehled","Competiciones":"Soutěže","Equipos":"Týmy","Jugadores":"Hráči","Partidos":"Zápasy","Usuarios":"Uživatelé","Importación masiva":"Hromadný import","Identidad visual":"Vizuální identita","Configuración":"Nastavení","Membresía":"Členství","Cerrar sesión":"Odhlásit se","PREFERENCIAS":"PŘEDVOLBY","Personaliza el idioma y la apariencia del Manager. Estos ajustes solo afectan a esta aplicación y no modifican los overlays.":"Přizpůsobte jazyk a vzhled Manageru. Tato nastavení ovlivňují pouze aplikaci a nemění grafické překryvy.","GENERAL":"OBECNÉ","Idioma y tema":"Jazyk a motiv","Idioma":"Jazyk","Tema de la aplicación":"Motiv aplikace","Oscuro":"Tmavý","Claro":"Světlý","El modo claro solo afecta al Manager, nunca a los gráficos emitidos.":"Světlý režim ovlivňuje pouze Manager, nikdy vysílanou grafiku.","Restablecer preferencias":"Obnovit nastavení","VISTA PREVIA":"NÁHLED","Aspecto del Manager":"Vzhled Manageru","Acción principal":"Hlavní akce","Descargar plantilla Excel":"Stáhnout šablonu Excel","Se guardará en la carpeta Descargas.":"Uloží se do složky Stažené soubory.","Iniciar sesión":"Přihlásit se","Olvidé mi contraseña":"Zapomněl jsem heslo","Correo electrónico":"E-mail","Contraseña":"Heslo","Actualizar":"Aktualizovat","Editar":"Upravit","Eliminar":"Odstranit","Guardar":"Uložit","Cancelar":"Zrušit","Confirmar importación":"Potvrdit import","Seleccionar archivo":"Vybrat soubor","Nuevo equipo":"Nový tým","Nuevo jugador":"Nový hráč","Nuevo partido":"Nový zápas","Nueva temporada":"Nová sezóna","Nueva competición":"Nová soutěž","Nueva personalización":"Nové přizpůsobení","Sí":"Ano","No":"Ne","Activo":"Aktivní","Activa":"Aktivní","Inactiva":"Neaktivní","Programado":"Naplánováno","En directo":"Živě","Finalizado":"Dokončeno","Portero":"Brankář","Defensa":"Obránce","Medio":"Záložník","Delantero":"Útočník","Entrenador":"Trenér"
    },
    fi: {
      "Resumen":"Yhteenveto","Competiciones":"Kilpailut","Equipos":"Joukkueet","Jugadores":"Pelaajat","Partidos":"Ottelut","Usuarios":"Käyttäjät","Importación masiva":"Massatuonti","Identidad visual":"Visuaalinen ilme","Configuración":"Asetukset","Membresía":"Jäsenyys","Cerrar sesión":"Kirjaudu ulos","PREFERENCIAS":"ASETUKSET","Personaliza el idioma y la apariencia del Manager. Estos ajustes solo afectan a esta aplicación y no modifican los overlays.":"Mukauta Managerin kieli ja ulkoasu. Asetukset vaikuttavat vain tähän sovellukseen eivätkä muuta grafiikkaa.","GENERAL":"YLEISET","Idioma y tema":"Kieli ja teema","Idioma":"Kieli","Tema de la aplicación":"Sovelluksen teema","Oscuro":"Tumma","Claro":"Vaalea","El modo claro solo afecta al Manager, nunca a los gráficos emitidos.":"Vaalea tila vaikuttaa vain Manageriin, ei koskaan lähetysgrafiikkaan.","Restablecer preferencias":"Palauta asetukset","VISTA PREVIA":"ESIKATSELU","Aspecto del Manager":"Managerin ulkoasu","Acción principal":"Päätoiminto","Descargar plantilla Excel":"Lataa Excel-malli","Se guardará en la carpeta Descargas.":"Se tallennetaan Lataukset-kansioon.","Iniciar sesión":"Kirjaudu sisään","Olvidé mi contraseña":"Unohdin salasanani","Correo electrónico":"Sähköposti","Contraseña":"Salasana","Actualizar":"Päivitä","Editar":"Muokkaa","Eliminar":"Poista","Guardar":"Tallenna","Cancelar":"Peruuta","Confirmar importación":"Vahvista tuonti","Seleccionar archivo":"Valitse tiedosto","Nuevo equipo":"Uusi joukkue","Nuevo jugador":"Uusi pelaaja","Nuevo partido":"Uusi ottelu","Nueva temporada":"Uusi kausi","Nueva competición":"Uusi kilpailu","Nueva personalización":"Uusi mukautus","Sí":"Kyllä","No":"Ei","Activo":"Aktiivinen","Activa":"Aktiivinen","Inactiva":"Ei aktiivinen","Programado":"Ajastettu","En directo":"Suora","Finalizado":"Päättynyt","Portero":"Maalivahti","Defensa":"Puolustaja","Medio":"Keskikenttä","Delantero":"Hyökkääjä","Entrenador":"Valmentaja"
    },
    de: {
      "Resumen":"Übersicht","Competiciones":"Wettbewerbe","Equipos":"Teams","Jugadores":"Spieler","Partidos":"Spiele","Usuarios":"Benutzer","Importación masiva":"Massenimport","Identidad visual":"Visuelle Identität","Configuración":"Einstellungen","Membresía":"Mitgliedschaft","Cerrar sesión":"Abmelden","PREFERENCIAS":"EINSTELLUNGEN","Personaliza el idioma y la apariencia del Manager. Estos ajustes solo afectan a esta aplicación y no modifican los overlays.":"Passe Sprache und Darstellung des Managers an. Diese Einstellungen betreffen nur diese Anwendung und verändern keine Overlays.","GENERAL":"ALLGEMEIN","Idioma y tema":"Sprache und Design","Idioma":"Sprache","Tema de la aplicación":"App-Design","Oscuro":"Dunkel","Claro":"Hell","El modo claro solo afecta al Manager, nunca a los gráficos emitidos.":"Der helle Modus betrifft nur den Manager, niemals die Sendegrafiken.","Restablecer preferencias":"Einstellungen zurücksetzen","VISTA PREVIA":"VORSCHAU","Aspecto del Manager":"Manager-Darstellung","Acción principal":"Hauptaktion","Descargar plantilla Excel":"Excel-Vorlage herunterladen","Se guardará en la carpeta Descargas.":"Sie wird im Downloads-Ordner gespeichert.","Iniciar sesión":"Anmelden","Olvidé mi contraseña":"Passwort vergessen","Correo electrónico":"E-Mail-Adresse","Contraseña":"Passwort","Actualizar":"Aktualisieren","Editar":"Bearbeiten","Eliminar":"Löschen","Guardar":"Speichern","Cancelar":"Abbrechen","Confirmar importación":"Import bestätigen","Seleccionar archivo":"Datei auswählen","Nuevo equipo":"Neues Team","Nuevo jugador":"Neuer Spieler","Nuevo partido":"Neues Spiel","Nueva temporada":"Neue Saison","Nueva competición":"Neuer Wettbewerb","Nueva personalización":"Neue Anpassung","Sí":"Ja","No":"Nein","Activo":"Aktiv","Activa":"Aktiv","Inactiva":"Inaktiv","Programado":"Geplant","En directo":"Live","Finalizado":"Beendet","Portero":"Torwart","Defensa":"Verteidiger","Medio":"Mittelfeldspieler","Delantero":"Stürmer","Entrenador":"Trainer"
    }
  };
  Object.assign(UI_TRANSLATIONS.en, {"Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.": "Import directly into this roster. Identical profiles are reused. You can include shirt number and captain; the team and competition selected here will be used."});
  Object.assign(UI_TRANSLATIONS.sv, {"Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.": "Importera direkt till denna trupp. Identiska profiler återanvänds. Tröjnummer och kapten kan anges; laget och tävlingen som valts här används."});
  Object.assign(UI_TRANSLATIONS.cs, {"Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.": "Importujte přímo do této soupisky. Shodné profily se použijí znovu. Lze zadat číslo dresu a kapitána; použije se zde vybraný tým a soutěž."});
  Object.assign(UI_TRANSLATIONS.fi, {"Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.": "Tuo suoraan tähän kokoonpanoon. Samat profiilit käytetään uudelleen. Voit lisätä pelinumeron ja kapteenin; tässä valittua joukkuetta ja kilpailua käytetään."});
  Object.assign(UI_TRANSLATIONS.de, {"Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.": "Direkt in diesen Kader importieren. Identische Profile werden wiederverwendet. Rückennummer und Kapitän sind möglich; es gelten das hier gewählte Team und der Wettbewerb."});
  Object.assign(UI_TRANSLATIONS.en, {"Fecha de nacimiento": "Date of birth", "Nacionalidad": "Nationality", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Name, surname, display name, position, date of birth and nationality are saved. Team, club, shirt number, roster, season and competition are ignored."});
  Object.assign(UI_TRANSLATIONS.sv, {"Fecha de nacimiento": "Födelsedatum", "Nacionalidad": "Nationalitet", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Namn, efternamn, visningsnamn, position, födelsedatum och nationalitet sparas. Lag, klubb, tröjnummer, trupp, säsong och tävling ignoreras."});
  Object.assign(UI_TRANSLATIONS.cs, {"Fecha de nacimiento": "Datum narození", "Nacionalidad": "Národnost", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Ukládá se jméno, příjmení, zobrazované jméno, pozice, datum narození a národnost. Tým, klub, číslo dresu, soupiska, sezóna a soutěž se ignorují."});
  Object.assign(UI_TRANSLATIONS.fi, {"Fecha de nacimiento": "Syntymäaika", "Nacionalidad": "Kansalaisuus", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Nimi, sukunimi, näyttönimi, pelipaikka, syntymäaika ja kansalaisuus tallennetaan. Joukkue, seura, pelinumero, kokoonpano, kausi ja kilpailu ohitetaan."});
  Object.assign(UI_TRANSLATIONS.de, {"Fecha de nacimiento": "Geburtsdatum", "Nacionalidad": "Nationalität", "Solo se guardan nombre, apellidos, nombre mostrado, posición, fecha de nacimiento y nacionalidad. Equipo, club, dorsal, roster, temporada y competición se ignoran siempre.": "Vorname, Nachname, Anzeigename, Position, Geburtsdatum und Nationalität werden gespeichert. Team, Verein, Rückennummer, Kader, Saison und Wettbewerb werden ignoriert."});
  Object.assign(UI_TRANSLATIONS.en, {"Jugador-entrenador": "Player-coach"});
  Object.assign(UI_TRANSLATIONS.sv, {"Jugador-entrenador": "Spelande tränare"});
  Object.assign(UI_TRANSLATIONS.cs, {"Jugador-entrenador": "Hrající trenér"});
  Object.assign(UI_TRANSLATIONS.fi, {"Jugador-entrenador": "Pelaajavalmentaja"});
  Object.assign(UI_TRANSLATIONS.de, {"Jugador-entrenador": "Spielertrainer"});
  Object.assign(UI_TRANSLATIONS.en, {"Entrenador": "Coach", "Sin posición": "No position", "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega.": "Tick Coach to add the tag. Keep a playing position if this person also plays."});
  Object.assign(UI_TRANSLATIONS.sv, {"Entrenador": "Tränare", "Sin posición": "Ingen position", "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega.": "Markera Tränare för att lägga till etiketten. Behåll spelpositionen om personen också spelar."});
  Object.assign(UI_TRANSLATIONS.cs, {"Entrenador": "Trenér", "Sin posición": "Bez pozice", "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega.": "Zaškrtněte Trenér pro přidání štítku. Pokud osoba také hraje, ponechte její herní pozici."});
  Object.assign(UI_TRANSLATIONS.fi, {"Entrenador": "Valmentaja", "Sin posición": "Ei pelipaikkaa", "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega.": "Lisää tunniste valitsemalla Valmentaja. Säilytä pelipaikka, jos henkilö myös pelaa."});
  Object.assign(UI_TRANSLATIONS.de, {"Entrenador": "Trainer", "Sin posición": "Keine Position", "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega.": "Aktiviere Trainer, um das Merkmal hinzuzufügen. Behalte die Spielposition bei, wenn die Person auch spielt."});
  Object.assign(UI_TRANSLATIONS.en, {"Importar": "Import", "Personas y rosters": "People and rosters", "Selecciona temporada y competición": "Select season and competition", "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir.": "Date, optional time, venue, home and away teams. Teams must already exist.", "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.": "Include Team, Shirt number and personal details. Coach accepts Yes or No.", "Crear equipo": "Create team", "Sin roster en esta competición": "No roster in this competition", "Vuelve a analizar el archivo": "Analyze the file again", "Hora pendiente": "Time pending", "Hora confirmada": "Time confirmed", "Selecciona temporada y competición antes de importar personas o partidos.": "Select a season and competition before importing people or matches.", "Las personas se asignan al equipo indicado en el archivo y al roster seleccionado. Los partidos necesitan equipos existentes; la hora puede quedar pendiente.": "People are added to the team named in the file and the selected roster. Matches require existing teams; the time can remain pending."});
  Object.assign(UI_TRANSLATIONS.sv, {"Importar": "Importera", "Personas y rosters": "Personer och trupper", "Selecciona temporada y competición": "Välj säsong och tävling", "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir.": "Datum, valfri tid, arena, hemma- och bortalag. Lagen måste finnas.", "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.": "Ange lag, tröjnummer och personuppgifter. Tränare anges med Ja eller Nej.", "Crear equipo": "Skapa lag", "Sin roster en esta competición": "Ingen trupp i denna tävling", "Vuelve a analizar el archivo": "Analysera filen igen", "Hora pendiente": "Tid ej fastställd", "Hora confirmada": "Tid bekräftad", "Selecciona temporada y competición antes de importar personas o partidos.": "Välj säsong och tävling innan du importerar personer eller matcher.", "Las personas se asignan al equipo indicado en el archivo y al roster seleccionado. Los partidos necesitan equipos existentes; la hora puede quedar pendiente.": "Personer läggs till i laget i filen och vald trupp. Matcher kräver befintliga lag; tiden kan anges senare."});
  Object.assign(UI_TRANSLATIONS.cs, {"Importar": "Importovat", "Personas y rosters": "Osoby a soupisky", "Selecciona temporada y competición": "Vyberte sezónu a soutěž", "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir.": "Datum, nepovinný čas, hala, domácí a hosté. Týmy musí existovat.", "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.": "Uveďte tým, číslo dresu a osobní údaje. Trenér přijímá Ano nebo Ne.", "Crear equipo": "Vytvořit tým", "Sin roster en esta competición": "V této soutěži není soupiska", "Vuelve a analizar el archivo": "Znovu analyzujte soubor", "Hora pendiente": "Čas neurčen", "Hora confirmada": "Čas potvrzen", "Selecciona temporada y competición antes de importar personas o partidos.": "Před importem osob nebo zápasů vyberte sezónu a soutěž.", "Las personas se asignan al equipo indicado en el archivo y al roster seleccionado. Los partidos necesitan equipos existentes; la hora puede quedar pendiente.": "Osoby se přidají do týmu uvedeného v souboru a vybrané soupisky. Zápasy vyžadují existující týmy; čas lze doplnit později."});
  Object.assign(UI_TRANSLATIONS.fi, {"Importar": "Tuo", "Personas y rosters": "Henkilöt ja kokoonpanot", "Selecciona temporada y competición": "Valitse kausi ja kilpailu", "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir.": "Päivä, valinnainen aika, pelipaikka, koti- ja vierasjoukkue. Joukkueiden on oltava olemassa.", "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.": "Lisää joukkue, pelinumero ja henkilötiedot. Valmentaja: Kyllä tai Ei.", "Crear equipo": "Luo joukkue", "Sin roster en esta competición": "Ei kokoonpanoa tässä kilpailussa", "Vuelve a analizar el archivo": "Analysoi tiedosto uudelleen", "Hora pendiente": "Aika avoinna", "Hora confirmada": "Aika vahvistettu", "Selecciona temporada y competición antes de importar personas o partidos.": "Valitse kausi ja kilpailu ennen henkilöiden tai otteluiden tuontia.", "Las personas se asignan al equipo indicado en el archivo y al roster seleccionado. Los partidos necesitan equipos existentes; la hora puede quedar pendiente.": "Henkilöt lisätään tiedostossa mainittuun joukkueeseen ja valittuun kokoonpanoon. Ottelut edellyttävät olemassa olevia joukkueita; ajan voi lisätä myöhemmin."});
  Object.assign(UI_TRANSLATIONS.de, {"Importar": "Importieren", "Personas y rosters": "Personen und Kader", "Selecciona temporada y competición": "Saison und Wettbewerb auswählen", "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir.": "Datum, optionale Uhrzeit, Spielstätte, Heim- und Gastteam. Teams müssen vorhanden sein.", "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.": "Team, Rückennummer und persönliche Daten angeben. Trainer akzeptiert Ja oder Nein.", "Crear equipo": "Team erstellen", "Sin roster en esta competición": "Kein Kader in diesem Wettbewerb", "Vuelve a analizar el archivo": "Datei erneut analysieren", "Hora pendiente": "Uhrzeit offen", "Hora confirmada": "Uhrzeit bestätigt", "Selecciona temporada y competición antes de importar personas o partidos.": "Vor dem Import von Personen oder Spielen Saison und Wettbewerb auswählen.", "Las personas se asignan al equipo indicado en el archivo y al roster seleccionado. Los partidos necesitan equipos existentes; la hora puede quedar pendiente.": "Personen werden dem Team aus der Datei und dem gewählten Kader hinzugefügt. Spiele benötigen bestehende Teams; die Uhrzeit kann offenbleiben."});
  const GOAL_TEXT_TRANSLATIONS = {
    en: {"GOLES":"GOALS","Cartel del goleador tras la repetición":"Scorer graphic after replay","Live oculta el marcador al registrar el gol. Con plugin espera a que termine la repetición; sin plugin usa la espera configurada. Después restaura el marcador, muestra el cartel y lo retira automáticamente.":"Live hides the scoreboard when the goal is recorded. With the plugin it waits for the replay; without it, it uses the configured delay. It then restores the scoreboard, shows the scorer graphic and removes it automatically.","Espera sin plugin (segundos)":"Delay without plugin (seconds)","Tiempo en pantalla (segundos)":"Time on screen (seconds)"},
    sv: {"GOLES":"MÅL","Cartel del goleador tras la repetición":"Målskyttsgrafik efter repris","Live oculta el marcador al registrar el gol. Con plugin espera a que termine la repetición; sin plugin usa la espera configurada. Después restaura el marcador, muestra el cartel y lo retira automáticamente.":"Live döljer resultattavlan när målet registreras. Med plugin väntar den tills reprisen är slut; utan plugin används den inställda väntetiden. Sedan återställs resultattavlan, målskyttsgrafiken visas och tas bort automatiskt.","Espera sin plugin (segundos)":"Väntetid utan plugin (sekunder)","Tiempo en pantalla (segundos)":"Tid på skärmen (sekunder)"},
    cs: {"GOLES":"GÓLY","Cartel del goleador tras la repetición":"Grafika střelce po opakování","Live oculta el marcador al registrar el gol. Con plugin espera a que termine la repetición; sin plugin usa la espera configurada. Después restaura el marcador, muestra el cartel y lo retira automáticamente.":"Live při zapsání gólu skryje ukazatel skóre. S pluginem čeká na konec opakování, bez něj použije nastavenou prodlevu. Poté ukazatel obnoví, zobrazí grafiku střelce a automaticky ji skryje.","Espera sin plugin (segundos)":"Prodleva bez pluginu (sekundy)","Tiempo en pantalla (segundos)":"Čas na obrazovce (sekundy)"},
    fi: {"GOLES":"MAALIT","Cartel del goleador tras la repetición":"Maalintekijän grafiikka uusinnan jälkeen","Live oculta el marcador al registrar el gol. Con plugin espera a que termine la repetición; sin plugin usa la espera configurada. Después restaura el marcador, muestra el cartel y lo retira automáticamente.":"Live piilottaa tulostaulun maalin kirjaamisen yhteydessä. Pluginin kanssa se odottaa uusinnan loppua, ilman pluginia käytetään määritettyä viivettä. Sitten tulostaulu palautetaan, maalintekijän grafiikka näytetään ja poistetaan automaattisesti.","Espera sin plugin (segundos)":"Viive ilman pluginia (sekuntia)","Tiempo en pantalla (segundos)":"Aika näytöllä (sekuntia)"},
    de: {"GOLES":"TORE","Cartel del goleador tras la repetición":"Torschützengrafik nach der Wiederholung","Live oculta el marcador al registrar el gol. Con plugin espera a que termine la repetición; sin plugin usa la espera configurada. Después restaura el marcador, muestra el cartel y lo retira automáticamente.":"Live blendet die Anzeigetafel beim Erfassen des Tores aus. Mit Plugin wartet es bis zum Ende der Wiederholung, ohne Plugin gilt die eingestellte Wartezeit. Danach erscheinen Anzeigetafel und Torschützengrafik; die Grafik wird automatisch ausgeblendet.","Espera sin plugin (segundos)":"Wartezeit ohne Plugin (Sekunden)","Tiempo en pantalla (segundos)":"Einblenddauer (Sekunden)"}
  };
  Object.entries(GOAL_TEXT_TRANSLATIONS).forEach(([language, values]) => Object.assign(UI_TRANSLATIONS[language], values));

  Object.assign(UI_TRANSLATIONS.en, {"Color de encendido": "Lit segment colour", "Color del texto de los periodos": "Period text colour"});
  Object.assign(UI_TRANSLATIONS.sv, {"Color de encendido": "Färg på tända segment", "Color del texto de los periodos": "Periodtextens färg"});
  Object.assign(UI_TRANSLATIONS.cs, {"Color de encendido": "Barva rozsvícených segmentů", "Color del texto de los periodos": "Barva textu period"});
  Object.assign(UI_TRANSLATIONS.fi, {"Color de encendido": "Aktiivisten osien väri", "Color del texto de los periodos": "Erätekstin väri"});
  Object.assign(UI_TRANSLATIONS.de, {"Color de encendido": "Farbe der leuchtenden Segmente", "Color del texto de los periodos": "Textfarbe der Spielabschnitte"});

  Object.assign(UI_TRANSLATIONS.en, {"Mostrar número dentro del reloj": "Show period number inside the clock", "El marcador vuelve después de retirar el bottom del gol.": "The scoreboard returns after the goal lower third clears."});
  Object.assign(UI_TRANSLATIONS.sv, {"Mostrar número dentro del reloj": "Visa periodnumret i klockan", "El marcador vuelve después de retirar el bottom del gol.": "Resultattavlan återkommer när målgrafiken har försvunnit."});
  Object.assign(UI_TRANSLATIONS.cs, {"Mostrar número dentro del reloj": "Zobrazit číslo periody v hodinách", "El marcador vuelve después de retirar el bottom del gol.": "Ukazatel skóre se vrátí po skrytí gólové grafiky."});
  Object.assign(UI_TRANSLATIONS.fi, {"Mostrar número dentro del reloj": "Näytä erän numero kellossa", "El marcador vuelve después de retirar el bottom del gol.": "Tulostaulu palaa maaligrafiikan poistuttua."});
  Object.assign(UI_TRANSLATIONS.de, {"Mostrar número dentro del reloj": "Spielabschnitt in der Uhr anzeigen", "El marcador vuelve después de retirar el bottom del gol.": "Die Anzeigetafel erscheint nach dem Ausblenden der Torgrafik."});
  const translatedTextNodes = new WeakMap();
  const translationExclusions = ".row-title,.row-subtitle,.match-teams,.profile,.workspace-control,.team-card h3,.player-card h3,.theme-card h3,.account-profile-copy,.logo-placeholder,#workspace-name,#profile-name,#profile-email";

  function tr(value) {
    const text = String(value ?? "");
    if (state.preferences.language === "es") return text;
    return UI_TRANSLATIONS[state.preferences.language]?.[text] || UI_TRANSLATIONS.en?.[text] || text;
  }

  function translateTextNode(node) {
    const parent = node.parentElement;
    if (!parent || parent.closest(translationExclusions) || parent.closest("#settings-language")) return;
    const current = node.data;
    const trimmed = current.trim();
    if (!trimmed) return;
    let record = translatedTextNodes.get(node);
    if (!record || (trimmed !== record.original && trimmed !== record.translated)) record = { original: trimmed, translated: trimmed };
    const translated = tr(record.original);
    record.translated = translated;
    translatedTextNodes.set(node, record);
    const leading = current.match(/^\s*/)?.[0] || "";
    const trailing = current.match(/\s*$/)?.[0] || "";
    const nextValue = `${leading}${translated}${trailing}`;
    if (node.data !== nextValue) node.data = nextValue;
  }

  function translateManagerUI(root = document.body) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) return translateTextNode(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) translateTextNode(node);
    document.title = state.preferences.language === "es" ? "SecretariatPro Manager" : `SecretariatPro Manager · ${tr("Configuración")}`;
  }

  const systemThemeQuery = window.matchMedia("(prefers-color-scheme: light)");

  function resolveThemePreference(theme) {
    if (theme === "system") return systemThemeQuery.matches ? "light" : "dark";
    return theme === "light" ? "light" : "dark";
  }

  function applyTheme(theme, persist = true) {
    const normalized = ["dark", "light", "system"].includes(theme) ? theme : "system";
    const resolved = resolveThemePreference(normalized);
    state.preferences.theme = normalized;
    document.documentElement.dataset.themePreference = normalized;
    document.documentElement.dataset.appTheme = resolved;
    if (persist) localStorage.setItem(PREFERENCE_KEYS.theme, normalized);
    if ($("#settings-theme")) $("#settings-theme").value = normalized;
  }

  function applyLanguage(language, persist = true) {
    const normalized = SUPPORTED_LANGUAGES.includes(language) ? language : "en";
    state.preferences.language = normalized;
    document.documentElement.lang = normalized;
    if (persist) localStorage.setItem(PREFERENCE_KEYS.language, normalized);
    if ($("#settings-language")) $("#settings-language").value = normalized;
    translateManagerUI();
  }

  function systemLanguage() {
    const candidates = navigator.languages || [navigator.language || "en"];
    return candidates
      .map((value) => String(value).toLowerCase().split("-")[0])
      .find((value) => SUPPORTED_LANGUAGES.includes(value)) || "en";
  }

  function initializePreferences() {
    const language = localStorage.getItem(PREFERENCE_KEYS.language) || systemLanguage();
    const theme = localStorage.getItem(PREFERENCE_KEYS.theme) || "system";
    applyTheme(theme, false);
    applyLanguage(language, false);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "characterData") translateTextNode(mutation.target);
        mutation.addedNodes.forEach((node) => translateManagerUI(node));
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  function localeForLanguage() {
    return { es: "es-ES", en: "en-GB", sv: "sv-SE", cs: "cs-CZ", fi: "fi-FI", de: "de-DE" }[state.preferences.language] || "en-GB";
  }

  function escapeHtml(value = "") {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeout || 18000);
    const headers = { ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    try {
      const response = await fetch(path, { ...options, headers, signal: controller.signal, cache: "no-store" });
      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json") ? await response.json() : await response.text();
      if (!response.ok) {
        const detail = typeof data === "object" ? data.detail : data;
        throw new Error(detail || `Error ${response.status}`);
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("El servidor tardó demasiado en responder");
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  function initials(value = "") {
    return String(value).split(/\s+|@/).filter(Boolean).slice(0, 2).map((x) => x[0]?.toUpperCase()).join("") || "?";
  }

  function formatDate(value, includeTime = false) {
    if (!value) return "—";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString(localeForLanguage(), includeTime
      ? { dateStyle: "short", timeStyle: "short" }
      : { dateStyle: "medium" });
  }

  function booleanLabel(value) { return tr(value ? "Sí" : "No"); }
  function canWrite() { return !!state.session.permissions?.write_allowed; }
  function playerName(player = {}) {
    return player.display_name || [player.first_name, player.last_name].filter(Boolean).join(" ") || "Jugador";
  }
  function competitionSeason(competition = {}) {
    return competition.seasons?.name || competition.season?.name || "Sin temporada";
  }

  function showToast(message, error = false) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.toggle("error", error);
    toast.hidden = false;
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => { toast.hidden = true; }, 3800);
  }

  function setLoginBusy(busy) {
    $("#login-button").disabled = busy;
    $("#login-email").disabled = busy;
    $("#login-password").disabled = busy;
  }

  function setLoginMessage(message, ok = false) {
    const box = $("#login-message");
    box.textContent = message || "";
    box.classList.toggle("ok", ok);
  }

  function avatarHtml(profile, className = "") {
    if (profile?.avatar_url) return `<img class="${className}" src="${escapeHtml(profile.avatar_url)}" alt="Foto de perfil">`;
    return `<span>${escapeHtml(initials(profile?.display_name || profile?.email))}</span>`;
  }

  function renderSession(next) {
    state.session = next || {};
    const connected = !!state.session.connected;
    $("#login-layer").hidden = connected;
    $("#manager-shell").hidden = !connected;
    if (!connected) {
      closeAccount();
      return;
    }

    const profile = state.session.profile || {};
    const workspace = state.session.workspace || {};
    const access = state.session.access || {};
    const app = state.session.application || {};

    $("#profile-name").textContent = profile.display_name || "Usuario";
    $("#profile-email").textContent = profile.email || "—";
    $("#profile-avatar").innerHTML = avatarHtml(profile);
    $("#workspace-name").textContent = workspace.name || "Sin espacio";
    $("#workspace-type").textContent = workspace.workspace_type === "association" ? "Asociación" : "Particular";
    $("#workspace-role").textContent = roleLabels[workspace.role] || workspace.role || "—";
    $("#plan-name").textContent = access.plan_name || "Sin plan";
    $("#plan-end").textContent = formatDate(access.ends_at);
    $("#build-label").textContent = `${app.name || "Manager"} · ${app.version || ""}`;

    const badge = $("#subscription-status");
    badge.textContent = access.allowed
      ? (access.mode === "offline_grace" ? "Offline autorizado" : "Membresía activa")
      : (access.mode === "read_only" ? "Modo consulta" : "Bloqueado");
    badge.classList.toggle("blocked", !access.allowed);
    $("#readonly-banner").hidden = !state.session.permissions?.read_only;

    const select = $("#workspace-select");
    select.innerHTML = (state.session.workspaces || []).map((item) =>
      `<option value="${escapeHtml(item.id)}" ${item.id === workspace.id ? "selected" : ""}>${escapeHtml(item.name)}</option>`
    ).join("");
    select.disabled = (state.session.workspaces || []).length < 2;

    $("#import-scopes").innerHTML = (state.session.import_scopes || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
    $("#identity-mode").textContent = workspace.visual_identity_mode === "competition" ? "Por competición" : "Identidad única";
    const sportCard = $("#sport-mode-card");
    if (sportCard) sportCard.hidden = workspace.role !== "owner";
    if ($("#settings-sport-mode")) $("#settings-sport-mode").value = workspace.sport_mode || "floorball";
    renderSubscription();
    renderAccountContent();
    updateWriteControls();
  }

  function updateWriteControls() {
    $$('[data-create], [data-delete], #identity-save, #confirm-import, #identity-form input, #identity-form select').forEach((button) => {
      button.disabled = !canWrite();
      button.title = canWrite() ? "" : "Necesitas una membresía activa y rol de gestor";
    });
  }

  function renderSubscription() {
    const access = state.session.access || {};
    $("#subscription-plan").textContent = access.plan_name || "Sin plan";
    $("#subscription-message").textContent = access.message || "No hay información de membresía";
    $("#subscription-start").textContent = formatDate(access.starts_at);
    $("#subscription-end").textContent = formatDate(access.ends_at);
    $("#subscription-retention").textContent = formatDate(access.retention_until);
    $("#subscription-offline").textContent = `${access.offline_grace_days ?? 4} días`;
    const entitlements = access.entitlements || {};
    const labels = {
      max_computers: "Ordenadores simultáneos", tablets_count: "Las tablets consumen conexión",
      max_producers: "Realizadores", visual_identity_mode: "Identidad visual",
      bulk_import: "Importación masiva", ai_import: "Asistencia de IA",
      offline_grace_days: "Días offline",
    };
    $("#entitlements-list").innerHTML = Object.entries(entitlements).length
      ? Object.entries(entitlements).map(([key, value]) => `<div class="entitlement"><span>${escapeHtml(labels[key] || key)}</span><strong>${escapeHtml(typeof value === "boolean" ? booleanLabel(value) : value ?? "Sin límite")}</strong></div>`).join("")
      : '<div class="empty-state">El plan todavía no tiene capacidades definidas.</div>';
  }

  function closeSidebarOnCompactScreens() {
    if (window.matchMedia("(max-width: 980px)").matches) {
      $("#manager-shell")?.classList.remove("sidebar-open");
      $("#sidebar-toggle")?.setAttribute("aria-expanded", "false");
    }
  }

  function switchView(name) {
    state.view = name;
    $$('[data-view]').forEach((button) => button.classList.toggle("active", button.dataset.view === name));
    $$('.view').forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
    closeSidebarOnCompactScreens();
    loadView(name).catch((error) => showToast(error.message, true));
  }

  async function loadView(name, force = false) {
    const loaders = {
      dashboard: loadDashboard,
      competitions: loadCompetitions,
      teams: loadTeams,
      players: loadPlayers,
      matches: loadMatches,
      members: loadMembers,
      imports: loadImportScope,
      identity: loadThemes,
      profile: async () => renderProfileView(),
      settings: async () => {
        $("#settings-language").value = state.preferences.language;
        $("#settings-theme").value = state.preferences.theme;
        translateManagerUI($("#view-settings"));
      },
      subscription: async () => renderSubscription(),
    };
    if (loaders[name]) await loaders[name](force);
  }

  function renderProfileView() {
    const profile = state.session.profile || {};
    $("#profile-page-avatar").innerHTML = avatarHtml(profile);
    $("#profile-page-name").textContent = profile.display_name || "Usuario";
    $("#profile-page-email").textContent = profile.email || "—";
  }

  async function openProfilePortal() {
    try {
      const result = await api("/api/account/portal");
      if (!/^https:\/\//i.test(result.url || "")) throw new Error("El portal web no está configurado");
      const opened = window.open(result.url, "_blank", "noopener,noreferrer");
      if (!opened) window.location.assign(result.url);
    } catch (error) { showToast(error.message, true); }
  }

  async function loadDashboard(force = false) {
    if (!force && state.cache.dashboard) return renderDashboard(state.cache.dashboard);
    $("#dashboard-matches").innerHTML = '<div class="empty-state">Cargando…</div>';
    const data = await api("/api/dashboard");
    state.cache.dashboard = data;
    renderDashboard(data);
  }

  function renderDashboard(data) {
    const counts = data.counts || {};
    const values = [counts.competitions, counts.teams, counts.players, counts.matches, counts.members];
    $$("#dashboard-metrics strong").forEach((node, index) => { node.textContent = values[index] ?? 0; });
    const matches = data.matches || [];
    $("#dashboard-matches").innerHTML = matches.length ? `<div class="match-list">${matches.map(renderMatchRow).join("")}</div>` : '<div class="empty-state">Todavía no hay partidos en este espacio.</div>';
  }

  function renderMatchRow(match) {
    const home = match.home_team?.short_name || match.home_team?.name || "Local";
    const away = match.away_team?.short_name || match.away_team?.name || "Visitante";
    const competition = match.competition?.name || "Sin competición";
    const status = statusLabels[match.status] || match.status || "—";
    return `<div class="match-row"><div><strong>${formatDate(match.time_confirmed === false && match.scheduled_date ? match.scheduled_date + "T12:00:00" : match.match_date, match.time_confirmed !== false) + (match.time_confirmed === false ? " · " + tr("Hora pendiente") : "")}</strong><div class="match-meta">${escapeHtml(competition)}</div></div><div><div class="match-teams">${escapeHtml(home)} · ${escapeHtml(away)}</div><div class="match-meta">${escapeHtml(match.venue || "Sin pabellón")}</div></div><div><span class="pill ${match.status === "finished" ? "green" : ""}">${escapeHtml(status)}</span></div><div>${match.status === "finished" ? `<strong>${match.home_score ?? 0} – ${match.away_score ?? 0}</strong>` : escapeHtml(match.assigned_operator?.display_name || match.assigned_operator?.email || "Sin asignar")}</div></div>`;
  }

  async function loadCompetitions(force = false) {
    if (!force && state.cache.seasons && state.cache.competitions) return renderCompetitions();
    const [seasons, competitions] = await Promise.all([api("/api/seasons"), api("/api/competitions")]);
    state.cache.seasons = seasons;
    state.cache.competitions = competitions;
    renderCompetitions();
  }

  function renderCompetitions() {
    const seasons = state.cache.seasons || [];
    const competitions = state.cache.competitions || [];
    $("#season-count").textContent = seasons.length;
    $("#competition-count").textContent = competitions.length;
    $("#seasons-list").innerHTML = seasons.length ? seasons.map((season) => `<div class="details"><div><dt><span class="row-title">${escapeHtml(season.name)}</span></dt><dd><div class="table-actions"><span class="pill ${season.active === false ? "" : "green"}">${season.active === false ? "Cerrada" : "Activa"}</span><button class="danger" data-delete="season" data-id="${escapeHtml(season.id)}" data-name="${escapeHtml(season.name)}">Eliminar</button></div></dd></div></div>`).join("") : '<div class="empty-state">Crea la primera temporada.</div>';
    $("#competitions-list").innerHTML = competitions.length ? `<table class="data-table"><thead><tr><th>Competición</th><th>Temporada</th><th>Puntuación</th><th>Estado</th><th></th></tr></thead><tbody>${competitions.map((item) => `<tr><td><div class="competition-cell">${competitionLogoMarkup(item)}<div><span class="row-title">${escapeHtml(item.name)}</span><span class="row-subtitle">${escapeHtml(item.category || "Sin categoría")}</span></div></div></td><td>${escapeHtml(competitionSeason(item))}</td><td>${item.points_win ?? 2} / ${item.points_draw ?? 1} / ${item.points_loss ?? 0}</td><td><span class="pill ${item.active ? "green" : ""}">${item.active ? "Activa" : "Inactiva"}</span></td><td><div class="table-actions"><button data-edit="competition" data-id="${escapeHtml(item.id)}">Editar</button><button class="danger" data-delete="competition" data-id="${escapeHtml(item.id)}" data-name="${escapeHtml(item.name)}">Eliminar</button></div></td></tr>`).join("")}</tbody></table>` : '<div class="empty-state">Todavía no hay competiciones.</div>';
    bindEntityActionButtons();
  }

  function normalizedLogoUrl(value = "") {
    const url = String(value || "").trim().replace(/^['"]|['"]$/g, "");
    if (!url || /^[A-Za-z]:\\/.test(url) || url.startsWith("file://") || /^\/?logos\//i.test(url)) return "";
    return url;
  }

  function entityLogoMarkup(entity, wrapperClass, fallbackText, altText) {
    const fallback = escapeHtml(String(fallbackText || entity?.short_name || entity?.name || "?").slice(0, 3).toUpperCase());
    const logo = normalizedLogoUrl(entity?.logo_url) || normalizedLogoUrl(entity?.alternate_logo_url);
    return `<div class="${wrapperClass}">${logo ? `<img src="${escapeHtml(logo)}" alt="${escapeHtml(altText || `Logo de ${entity?.name || "entidad"}`)}" loading="eager" referrerpolicy="no-referrer" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span class="logo-placeholder" hidden>${fallback}</span>` : `<span class="logo-placeholder">${fallback}</span>`}</div>`;
  }

  function teamLogoMarkup(team, wrapperClass = "team-card-logo") {
    return entityLogoMarkup(team, wrapperClass, team.short_name || team.name, `Logo de ${team.name || "equipo"}`);
  }

  function competitionLogoMarkup(competition, wrapperClass = "competition-logo") {
    return entityLogoMarkup(competition, wrapperClass, competition.name, `Logo de ${competition.name || "competición"}`);
  }

  async function ensureSportsCache() {
    const promises = [];
    if (!state.cache.teams) promises.push(api("/api/teams").then((x) => { state.cache.teams = x; }));
    if (!state.cache.players) promises.push(api("/api/players").then((x) => { state.cache.players = x; }));
    if (!state.cache.competitions) promises.push(api("/api/competitions").then((x) => { state.cache.competitions = x; }));
    if (!state.cache.rosterGroups) promises.push(api("/api/roster-groups").then(x => { state.cache.rosterGroups = x; }));
    if (!state.cache.seasons) promises.push(api("/api/seasons").then((x) => { state.cache.seasons = x; }));
    await Promise.all(promises);
  }

  async function loadTeams(force = false) {
    if (force) {
      delete state.cache.teams;
      delete state.cache.teamRosters;
      delete state.cache.rosterGroups;
    }
    await ensureSportsCache();
    renderTeams();
    if (state.selectedTeamId && (state.cache.teams || []).some((x) => x.id === state.selectedTeamId)) {
      await openTeamDetail(state.selectedTeamId, force);
    }
  }

  function renderTeams() {
    const teams = state.cache.teams || [];
    $("#team-count").textContent = teams.length;
    $("#teams-list").innerHTML = teams.length ? teams.map((team) => `
      <button type="button" class="team-card ${state.selectedTeamId === team.id ? "selected" : ""}" data-team-detail="${escapeHtml(team.id)}">
        ${teamLogoMarkup(team)}
        <div class="team-list-name"><h3>${escapeHtml(team.name)}</h3><p>${escapeHtml(team.short_name || "Sin nombre corto")}</p></div><div class="color-pair" aria-hidden="true"><span class="color-dot" style="background:${escapeHtml(team.primary_color || "#1f2937")}"></span><span class="color-dot" style="background:${escapeHtml(team.secondary_color || "#ffffff")}"></span></div>
      </button>`).join("") : '<div class="empty-state">Crea el primer equipo.</div>';
    $$('[data-team-detail]').forEach((button) => button.addEventListener("click", () => openTeamDetail(button.dataset.teamDetail)));
  }

  async function openTeamDetail(teamId, force = false) {
    if (String(state.selectedTeamId) !== String(teamId)) state.selectedTeamRosterCompetitionId = "";
    state.selectedTeamId = teamId;
    renderTeams();
    const team = (state.cache.teams || []).find((x) => String(x.id) === String(teamId));
    if (!team) return;
    $("#team-detail").innerHTML = '<div class="empty-state detail-empty">Cargando ficha del equipo…</div>';
    const cacheKey = String(teamId);
    state.cache.teamRosters ||= {};
    if (force || !state.cache.teamRosters[cacheKey]) {
      state.cache.teamRosters[cacheKey] = await api(`/api/teams/${encodeURIComponent(teamId)}/rosters`);
    }
    renderTeamDetail(team, state.cache.teamRosters[cacheKey]);
  }

  function competitionOptionsForSeason(seasonId = "") {
    return (state.cache.competitions || []).filter((item) => !seasonId || String(item.season_id || "") === String(seasonId));
  }

  function renderTeamDetail(team, rows) {
    const competitions = state.cache.competitions || [];
    const grouped = new Map();
    (rows || []).forEach((row) => {
      const key = String(row.competition_id || "");
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(row);
    });
    const rosterCompetitions = competitions.filter((competition) => (grouped.has(String(competition.id)) || (state.cache.rosterGroups || []).some(g => String(g.team_id) === String(team.id) && String(g.competition_id) === String(competition.id))) || String(state.selectedTeamRosterCompetitionId) === String(competition.id));
    if (!state.selectedTeamRosterCompetitionId && rosterCompetitions.length) state.selectedTeamRosterCompetitionId = String(rosterCompetitions[0].id);
    const selectedCompetition = competitions.find((x) => String(x.id) === String(state.selectedTeamRosterCompetitionId));
    const visibleRows = selectedCompetition ? (grouped.get(String(selectedCompetition.id)) || []) : [];

    $("#team-detail").innerHTML = `
      <div class="team-detail-header">
        ${teamLogoMarkup(team, "team-detail-logo")}
        <div><span class="eyebrow">FICHA DEL EQUIPO</span><h2>${escapeHtml(team.name)}</h2><p>${escapeHtml(team.short_name || "Sin nombre corto")}</p><div class="color-pair"><span class="color-dot" style="background:${escapeHtml(team.primary_color || "#1f2937")}"></span><span class="color-dot" style="background:${escapeHtml(team.secondary_color || "#ffffff")}"></span></div></div>
        <div class="detail-actions"><button class="secondary" data-edit-team-detail="${escapeHtml(team.id)}">Editar equipo</button><button id="team-create-roster" ${!canWrite() ? "disabled" : ""}>Crear roster</button><button class="danger" data-delete="team" data-id="${escapeHtml(team.id)}" data-name="${escapeHtml(team.name)}" ${!canWrite() ? "disabled" : ""}>Eliminar equipo</button></div>
      </div>
      <div class="roster-browser">
        <aside class="roster-list-panel">
          <div class="panel-head"><div><span class="eyebrow">ROSTERS</span><h3>Temporadas y competiciones</h3></div><span class="count">${rosterCompetitions.length}</span></div>
          <div class="roster-card-list">${rosterCompetitions.length ? rosterCompetitions.map((competition) => {
            const members = grouped.get(String(competition.id)) || [];
            return `<button type="button" class="roster-card ${String(state.selectedTeamRosterCompetitionId) === String(competition.id) ? "selected" : ""}" data-open-team-roster="${escapeHtml(competition.id)}"><div><strong>${escapeHtml(competition.name)}</strong><span>${escapeHtml(competitionSeason(competition))}</span></div><span class="pill">${members.length} jugadores</span></button>`;
          }).join("") : '<div class="empty-state">Este equipo todavía no tiene rosters. Pulsa «Crear roster».</div>'}</div>
        </aside>
        <section class="roster-members-panel">
          ${selectedCompetition ? `
            <div class="panel-head"><div><span class="eyebrow">${escapeHtml(competitionSeason(selectedCompetition))}</span><h3>${escapeHtml(selectedCompetition.name)}</h3></div><div class="detail-actions"><button class="secondary" id="team-add-existing" ${!canWrite() ? "disabled" : ""}>Añadir jugador</button><button class="secondary" id="team-import-roster" ${!canWrite() ? "disabled" : ""}>Importación masiva</button><button id="team-create-player" ${!canWrite() ? "disabled" : ""}>Crear y añadir</button></div></div>
            <div id="roster-import-panel" hidden></div>
            ${visibleRows.length ? `<table class="data-table"><thead><tr><th>Jugador</th><th>Dorsal</th><th>Capitán</th><th></th></tr></thead><tbody>${visibleRows.map((row) => {
              const player = row.player || {};
              return `<tr><td><div class="roster-row-player"><span class="player-avatar-small">${escapeHtml(initials(playerName(player)))}</span><div><span class="row-title">${escapeHtml(playerName(player))}</span><span class="row-subtitle">${escapeHtml(positionLabel(player.position))}</span>${coachBadge(player)}</div></div></td><td><span class="shirt-number">${escapeHtml(row.shirt_number ?? "—")}</span></td><td>${row.captain ? '<span class="captain-mark">C</span>' : "—"}</td><td><div class="table-actions"><button data-roster-edit="${escapeHtml(row.id)}" ${!canWrite() ? "disabled" : ""}>Editar</button><button data-roster-remove="${escapeHtml(row.id)}" ${!canWrite() ? "disabled" : ""}>Quitar</button></div></td></tr>`;
            }).join("")}</tbody></table>` : '<div class="empty-state">Roster creado. Añade ahora jugadores existentes o crea uno nuevo.</div>'}
          ` : '<div class="empty-state detail-empty">Selecciona un roster para ver sus jugadores.</div>'}
        </section>
      </div>`;
    $("[data-edit-team-detail]")?.addEventListener("click", () => openForm("team", team));
    $("#team-import-roster")?.addEventListener("click", () => openRosterImport(team, selectedCompetition));
    $("#team-create-roster")?.addEventListener("click", () => openRosterShellForm(team));
    $$('[data-open-team-roster]').forEach((button) => button.addEventListener("click", () => {
      state.selectedTeamRosterCompetitionId = button.dataset.openTeamRoster;
      renderTeamDetail(team, rows);
    }));
    $("#team-add-existing")?.addEventListener("click", () => openRosterForm("rosterExisting", { team_id: team.id, competition_id: state.selectedTeamRosterCompetitionId }));
    $("#team-create-player")?.addEventListener("click", () => openRosterForm("rosterNew", { team_id: team.id, competition_id: state.selectedTeamRosterCompetitionId }));
    $$('[data-roster-edit]').forEach((button) => button.addEventListener("click", () => {
      const row = rows.find((item) => String(item.id) === String(button.dataset.rosterEdit));
      openRosterForm("rosterEdit", row);
    }));
    $$('[data-roster-remove]').forEach((button) => button.addEventListener("click", () => removeRoster(button.dataset.rosterRemove)));
    bindDeleteButtons($("#team-detail"));
  }

  function openRosterShellForm(team) {
    const used = new Set((state.cache.teamRosters?.[String(team.id)] || []).map((row) => String(row.competition_id)));
    const options = [["", "Selecciona una competición"], ...(state.cache.competitions || []).filter((x) => !used.has(String(x.id))).map((x) => [x.id, `${x.name} · ${competitionSeason(x)}`])];
    openConfiguredForm("rosterShell", {
      title: "Crear roster",
      fields: [{ name: "competition_id", label: "Temporada / competición", type: "select", options, required: true, full: true }],
    }, null);
    state.modal.team = team;
  }

  async function loadPlayers(force = false) {
    if (force) {
      delete state.cache.players;
      delete state.cache.playerRosters;
    }
    await ensureSportsCache();
    renderPlayers();
    if (state.selectedPlayerId && (state.cache.players || []).some((x) => x.id === state.selectedPlayerId)) {
      await openPlayerDetail(state.selectedPlayerId, force);
    }
  }

  function renderPlayers() {
    const players = state.cache.players || [];
    $("#player-count").textContent = players.length;
    $("#players-list").innerHTML = players.length ? `<table class="data-table"><thead><tr><th>Jugador</th><th>Nombre mostrado</th><th>Posición</th></tr></thead><tbody>${players.map((player) => `<tr class="clickable ${state.selectedPlayerId === player.id ? "selected" : ""}" data-player-detail="${escapeHtml(player.id)}"><td><div class="roster-row-player"><span class="player-avatar-small">${escapeHtml(initials(playerName(player)))}</span><span class="row-title">${escapeHtml([player.first_name, player.last_name].filter(Boolean).join(" ") || player.display_name)}</span></div></td><td>${escapeHtml(player.display_name || "—")}</td><td><span class="pill">${escapeHtml(positionLabel(player.position))}</span>${coachBadge(player)}</td></tr>`).join("")}</tbody></table>` : '<div class="empty-state">Todavía no hay jugadores.</div>';
    $$('[data-player-detail]').forEach((row) => row.addEventListener("click", () => openPlayerDetail(row.dataset.playerDetail)));
  }

  async function openPlayerDetail(playerId, force = false) {
    state.selectedPlayerId = playerId;
    renderPlayers();
    const player = (state.cache.players || []).find((x) => String(x.id) === String(playerId));
    if (!player) return;
    $("#player-detail").innerHTML = '<div class="empty-state detail-empty">Cargando participaciones…</div>';
    state.cache.playerRosters ||= {};
    if (force || !state.cache.playerRosters[playerId]) state.cache.playerRosters[playerId] = await api(`/api/players/${encodeURIComponent(playerId)}/rosters`);
    renderPlayerDetail(player, state.cache.playerRosters[playerId]);
  }

  function renderPlayerDetail(player, rows) {
    $("#player-detail").innerHTML = `
      <div class="player-detail-header">
        <div class="player-detail-avatar">${escapeHtml(initials(playerName(player)))}</div>
        <div><span class="eyebrow">JUGADOR</span><h2>${escapeHtml(playerName(player))}</h2><p>${escapeHtml(positionLabel(player.position))}</p>${coachBadge(player)}</div>
        <div class="detail-actions"><button class="secondary" id="player-edit" ${!canWrite() ? "disabled" : ""}>Editar</button><button id="player-add-roster" ${!canWrite() ? "disabled" : ""}>Añadir a roster</button><button class="danger" data-delete="player" data-id="${escapeHtml(player.id)}" data-name="${escapeHtml(playerName(player))}" ${!canWrite() ? "disabled" : ""}>Eliminar jugador</button></div>
      </div>
      <div class="panel-head" style="margin-top:18px"><div><span class="eyebrow">PARTICIPACIONES</span><h3>${(rows || []).length} rosters activos</h3></div></div>
      <div class="player-rosters">${(rows || []).length ? rows.map((row) => {
        const team = row.team || {};
        return `<article class="membership-card">${team.logo_url ? `<img class="membership-logo" src="${escapeHtml(team.logo_url)}" alt="">` : `<div class="membership-logo logo-placeholder">${escapeHtml((team.short_name || team.name || "?").slice(0,3))}</div>`}<div><span class="row-title">${escapeHtml(team.name || "Equipo")}</span><span class="row-subtitle">${escapeHtml(row.competition?.name || "Competición")} · ${escapeHtml(competitionSeason(row.competition || {}))}</span></div><div><span class="shirt-number">${escapeHtml(row.shirt_number ?? "—")}</span>${row.captain ? '<span class="captain-mark"> C</span>' : ""}</div></article>`;
      }).join("") : '<div class="empty-state">Este jugador todavía no pertenece a ningún roster activo.</div>'}</div>
    `;
    $("#player-edit")?.addEventListener("click", () => openForm("player", player));
    $("#player-add-roster")?.addEventListener("click", () => openRosterForm("playerRoster", { player_id: player.id }));
    bindDeleteButtons($("#player-detail"));
  }

  async function removeRoster(rosterId) {
    if (!canWrite()) return;
    if (!window.confirm("¿Quitar este jugador del roster? El histórico no se eliminará.")) return;
    try {
      await api(`/api/rosters/${encodeURIComponent(rosterId)}`, { method: "DELETE" });
      clearRosterCache();
      if (state.view === "teams") await openTeamDetail(state.selectedTeamId, true);
      if (state.view === "players") await openPlayerDetail(state.selectedPlayerId, true);
      showToast("Jugador retirado del roster");
    } catch (error) { showToast(error.message, true); }
  }

  function clearRosterCache() {
    delete state.cache.teamRosters;
    delete state.cache.playerRosters;
  }

  async function loadMatches(force = false) {
    if (!force && state.cache.matches) return renderMatches();
    const [matches, competitions, teams, members] = await Promise.all([
      api("/api/matches"),
      state.cache.competitions ? Promise.resolve(state.cache.competitions) : api("/api/competitions"),
      state.cache.teams ? Promise.resolve(state.cache.teams) : api("/api/teams"),
      state.cache.members ? Promise.resolve(state.cache.members) : api("/api/members"),
    ]);
    state.cache.matches = matches;
    state.cache.competitions = competitions;
    state.cache.teams = teams;
    state.cache.members = members;
    renderMatches();
  }

  function renderMatches() {
    const matches = state.cache.matches || [];
    $("#matches-list").innerHTML = matches.length ? `<table class="data-table"><thead><tr><th>Fecha</th><th>Partido</th><th>Competición</th><th>Uso</th><th>Realizador</th><th>Estado</th><th></th></tr></thead><tbody>${matches.map((match) => `<tr><td>${formatDate(match.time_confirmed === false && match.scheduled_date ? match.scheduled_date + "T12:00:00" : match.match_date, match.time_confirmed !== false) + (match.time_confirmed === false ? " · " + tr("Hora pendiente") : "")}</td><td><span class="row-title">${escapeHtml(match.home_team?.name || "Local")} — ${escapeHtml(match.away_team?.name || "Visitante")}</span><span class="row-subtitle">${escapeHtml(match.venue || "Sin pabellón")}</span></td><td>${escapeHtml(match.competition?.name || "—")}</td><td><span class="pill ${match.broadcast_enabled === false ? "amber" : "green"}">${match.broadcast_enabled === false ? "Solo registro" : "Live"}</span></td><td>${escapeHtml(match.broadcast_enabled === false ? "No aplica" : (match.assigned_operator?.display_name || match.assigned_operator?.email || "Sin asignar"))}</td><td><span class="pill ${match.status === "finished" ? "green" : match.status === "cancelled" ? "red" : ""}">${escapeHtml(statusLabels[match.status] || match.status || "—")}${match.status === "finished" ? ` · ${match.home_score ?? 0}-${match.away_score ?? 0}` : ""}</span></td><td><div class="table-actions"><button class="secondary" data-match-events="${escapeHtml(match.id)}">Acta</button><button data-edit="match" data-id="${escapeHtml(match.id)}">Editar</button><button class="danger" data-delete="match" data-id="${escapeHtml(match.id)}" data-name="${escapeHtml(`${match.home_team?.name || "Local"} — ${match.away_team?.name || "Visitante"}`)}">Eliminar</button></div></td></tr>`).join("")}</tbody></table>` : '<div class="empty-state">Todavía no hay partidos programados.</div>';
    bindEntityActionButtons();
    $$('[data-match-events]').forEach((button) => button.addEventListener("click", () => openMatchEvents(button.dataset.matchEvents)));
  }

  function matchEventPlayerOptions(side, selected = "") {
    const context = state.matchEventContext || {};
    const rows = side === "away" ? (context.away_roster || []) : (context.home_roster || []);
    return `<option value="">Selecciona jugador</option>${rows.filter((row) => String(row.member_type || "player") !== "coach").map((row) => {
      const player = row.player || {};
      const name = player.display_name || [player.first_name, player.last_name].filter(Boolean).join(" ") || "Jugador";
      return `<option value="${escapeHtml(row.player_id || player.id || "")}" ${String(selected) === String(row.player_id || player.id || "") ? "selected" : ""}>#${escapeHtml(row.shirt_number ?? "—")} · ${escapeHtml(name)}</option>`;
    }).join("")}`;
  }

  function refreshMatchEventPlayerControls() {
    const side = $("#match-event-team")?.value || "home";
    const currentPlayer = $("#match-event-player")?.value || "";
    const currentAssistant = $("#match-event-assistant")?.value || "";
    $("#match-event-player").innerHTML = matchEventPlayerOptions(side, currentPlayer);
    $("#match-event-assistant").innerHTML = `<option value="">Sin asistencia</option>${matchEventPlayerOptions(side, currentAssistant).replace('<option value="">Selecciona jugador</option>', '')}`;
  }

  function renderMatchEvents() {
    const context = state.matchEventContext || {};
    const match = context.match || {};
    $("#match-events-title").textContent = `${match.home_team?.name || "Local"} — ${match.away_team?.name || "Visitante"}`;
    const events = context.events || [];
    $("#match-events-list").innerHTML = events.length ? `<table class="data-table"><thead><tr><th>Tiempo</th><th>Equipo</th><th>Evento</th><th>Jugador</th><th></th></tr></thead><tbody>${events.map((event) => {
      const type = event.event_type === "goal" ? "Gol" : event.event_type === "assist" ? "Asistencia" : event.event_type === "penalty" ? `Expulsión ${event.penalty_type || "2"}` : event.event_type;
      return `<tr><td>${escapeHtml(event.match_time || "—")}</td><td>${escapeHtml(event.team?.short_name || event.team?.name || "—")}</td><td>${escapeHtml(type)}</td><td>${escapeHtml(event.player?.display_name || [event.player?.first_name, event.player?.last_name].filter(Boolean).join(" ") || "—")}</td><td><div class="table-actions">${event.event_type !== "assist" ? `<button class="danger" data-delete-match-event="${escapeHtml(event.id)}">Eliminar</button>` : ""}</div></td></tr>`;
    }).join("")}</tbody></table>` : '<div class="empty-state">Todavía no hay eventos en el acta.</div>';
    $$('[data-delete-match-event]').forEach((button) => button.addEventListener("click", async () => {
      if (!confirm("¿Eliminar este evento del acta?")) return;
      try { state.matchEventContext = await api(`/api/matches/${state.selectedMatchEventId}/events/${button.dataset.deleteMatchEvent}`, { method: "DELETE" }); renderMatchEvents(); delete state.cache.matches; await loadMatches(true); }
      catch (error) { showToast(error.message, true); }
    }));
    refreshMatchEventPlayerControls();
  }

  async function openMatchEvents(matchId) {
    state.selectedMatchEventId = matchId;
    state.pendingMatchEventImport = null;
    try {
      state.matchEventContext = await api(`/api/matches/${matchId}/events`);
      $("#match-events-backdrop").hidden = false;
      $("#match-events-backdrop").setAttribute("aria-hidden", "false");
      $("#match-events-import-preview").hidden = true;
      $("#match-events-import-actions").hidden = true;
      renderMatchEvents();
    } catch (error) { showToast(error.message, true); }
  }

  function closeMatchEvents() {
    $("#match-events-backdrop").hidden = true;
    $("#match-events-backdrop").setAttribute("aria-hidden", "true");
    state.selectedMatchEventId = ""; state.matchEventContext = null; state.pendingMatchEventImport = null;
  }

  function syncMatchEventType() {
    const isPenalty = $("#match-event-type").value === "penalty";
    $("#match-event-assistant-wrap").hidden = isPenalty;
    $("#match-event-penalty-wrap").hidden = !isPenalty;
  }

  async function submitMatchEvent(event) {
    event.preventDefault();
    if (!state.selectedMatchEventId) return;
    const data = {
      event_type: $("#match-event-type").value, team: $("#match-event-team").value, match_time: $("#match-event-time").value.trim(),
      player_id: $("#match-event-player").value, assistant_id: $("#match-event-assistant").value || null,
      penalty_type: $("#match-event-penalty").value, notes: $("#match-event-notes").value.trim(),
    };
    try {
      const result = await api(`/api/matches/${state.selectedMatchEventId}/events`, { method: "POST", body: JSON.stringify({ data }) });
      state.matchEventContext = result.context; renderMatchEvents(); delete state.cache.matches; await loadMatches(true);
      $("#match-event-time").value = ""; $("#match-event-notes").value = "";
      showToast("Evento añadido al acta");
    } catch (error) { showToast(error.message, true); }
  }

  async function downloadMatchEventTemplate() {
    if (!state.selectedMatchEventId) return;
    const status = $("#match-events-template-status");
    if (status) status.textContent = "Generando plantilla…";
    try {
      const result = await api(`/api/matches/${state.selectedMatchEventId}/events/template/download`, { method: "POST" });
      if (status) status.textContent = `Guardada en ${result.path}`;
      showToast("Plantilla de acta guardada en Descargas");
    } catch (error) {
      if (status) status.textContent = error.message;
      showToast(error.message, true);
    }
  }

  async function finalizeMatchEventAct() {
    if (!state.selectedMatchEventId) return;
    if (!confirm("¿Finalizar el acta? El resultado se recalculará con los goles registrados y el partido pasará a Finalizado.")) return;
    try {
      const result = await api(`/api/matches/${state.selectedMatchEventId}/events/finalize`, { method: "POST" });
      state.matchEventContext = result.context;
      renderMatchEvents();
      delete state.cache.matches;
      await loadMatches(true);
      showToast(`Acta finalizada · ${result.match?.home_score ?? 0}-${result.match?.away_score ?? 0}`);
    } catch (error) { showToast(error.message, true); }
  }

  async function previewMatchEventImport(file) {
    if (!state.selectedMatchEventId || !file) return;
    const form = new FormData(); form.append("file", file);
    try {
      const result = await api(`/api/matches/${state.selectedMatchEventId}/events/import-preview`, { method: "POST", body: form });
      state.pendingMatchEventImport = result;
      const validRows = (result.rows || []).filter((row) => row.valid);
      $("#match-events-import-preview").hidden = false;
      $("#match-events-import-preview").innerHTML = `<strong>${result.valid || 0} eventos válidos</strong> · ${result.errors || 0} filas con error${result.errors ? `<br>${(result.rows || []).filter((row) => !row.valid).slice(0,6).map((row) => `Fila ${row.row_number}: ${escapeHtml(row.error)}`).join("<br>")}` : ""}`;
      $("#match-events-import-actions").hidden = validRows.length < 1 || Number(result.errors || 0) > 0;
    } catch (error) { showToast(error.message, true); }
  }

  async function confirmMatchEventImport() {
    const rows = (state.pendingMatchEventImport?.rows || []).filter((row) => row.valid).map((row) => row.data);
    if (!rows.length) return;
    try {
      const result = await api(`/api/matches/${state.selectedMatchEventId}/events/import-confirm`, { method: "POST", body: JSON.stringify({ rows }) });
      state.matchEventContext = result.context; state.pendingMatchEventImport = null; renderMatchEvents();
      $("#match-events-import-preview").hidden = true; $("#match-events-import-actions").hidden = true;
      delete state.cache.matches; await loadMatches(true); showToast(`${result.created} eventos importados${result.auto_finalized ? " · acta finalizada" : ""}`);
    } catch (error) { showToast(error.message, true); }
  }

  async function saveSportMode() {
    if (!state.session.permissions?.can_set_sport_mode) return showToast("Sólo el propietario puede cambiar el deporte", true);
    try {
      const session = await api("/api/workspace/sport-mode", { method: "PATCH", body: JSON.stringify({ sport_mode: $("#settings-sport-mode").value }) });
      renderSession(session);
      $("#period-strip-segments").value = session.workspace?.sport_mode === "handball" ? 2 : 3;
      $("#period-strip-segments").disabled = session.workspace?.sport_mode === "handball";
      updateVisualPreview();
      showToast("Modo de deporte actualizado");
    } catch (error) { showToast(error.message, true); }
  }

  async function loadMembers(force = false) {
    if (!force && state.cache.members) return renderMembers();
    state.cache.members = await api("/api/members");
    renderMembers();
  }

  function renderMembers() {
    const members = state.cache.members || [];
    $("#members-list").innerHTML = members.length ? `<table class="data-table"><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Desde</th><th></th></tr></thead><tbody>${members.map((member) => {
      const profile = member.profile || {};
      const name = profile.display_name || profile.email || member.user_id;
      const isOwner = member.role === "owner";
      return `<tr><td><span class="row-title">${escapeHtml(name)}</span><span class="row-subtitle">${escapeHtml(profile.email || member.user_id)}</span></td><td>${escapeHtml(roleLabels[member.role] || member.role)}</td><td><span class="pill ${member.status === "active" ? "green" : "amber"}">${escapeHtml(statusLabels[member.status] || member.status)}</span></td><td>${formatDate(member.joined_at)}</td><td><div class="table-actions">${isOwner ? '<span class="pill">Propietario</span>' : `<button data-edit="member" data-id="${escapeHtml(member.user_id)}">Editar</button><button class="danger" data-delete="member" data-id="${escapeHtml(member.user_id)}" data-name="${escapeHtml(name)}">Eliminar</button>`}</div></td></tr>`;
    }).join("")}</tbody></table>` : '<div class="empty-state">No hay miembros en el espacio.</div>';
    bindEntityActionButtons();
  }

  function themeAppearance(theme) {
    const config = theme?.config || {};
    return config.appearance || config;
  }

  const ELEMENT_LABELS = {scoreboard: "Marcador", bottom_bar: "Goles y avisos", player_profile: "Ficha de jugador", prematch: "Previa", intermission: "Descanso", lineups_home: "Alineación local", lineups_away: "Alineación visitante", top_scorers: "Goleadores", standings: "Clasificación", penalties: "Penaltis"};
  const ELEMENT_FONTS = ["default", "Arial", "Verdana", "Georgia", "Trebuchet MS", "Courier New"];
  function mergedAppearance(input = {}) {
    const result = JSON.parse(JSON.stringify(DEFAULT_APPEARANCE));
    Object.entries(PALETTE_FIELDS).forEach(([section]) => Object.assign(result[section], input?.[section] || {}));
    result.elements = Object.fromEntries(Object.keys(ELEMENT_LABELS).map((key) => [key, {scale: 1, font: "default", ...(input.elements?.[key] || {})}]));
    const segments = state.session?.workspace?.sport_mode === "handball" ? 2 : Math.max(1, Math.min(12, Number(input.period_strip?.segments || 3)));
    const labels = Array.from({length: segments}, (_, index) => String(input.period_strip?.labels?.[index] || index + 1).slice(0, 8));
    result.period_strip = {show_number: Boolean(input.period_strip?.show_number), enabled: Boolean(input.period_strip?.enabled), segments, labels, active_color: /^#[0-9a-f]{6}$/i.test(input.period_strip?.active_color || "") ? input.period_strip.active_color : "#8cff00", text_color: /^#[0-9a-f]{6}$/i.test(input.period_strip?.text_color || "") ? input.period_strip.text_color : "#102000"};
    result.goal_celebration = {delay_seconds: Math.max(0, Math.min(30, Number(input.goal_celebration?.delay_seconds ?? 4))), duration_seconds: Math.max(1, Math.min(30, Number(input.goal_celebration?.duration_seconds || 6)))};
    return result;
  }

  async function loadThemes(force = false) {
    if (force) delete state.cache.themes;
    if (!state.cache.themes || !state.cache.competitions) {
      const [themes, competitions] = await Promise.all([
        state.cache.themes ? Promise.resolve(state.cache.themes) : api("/api/themes"),
        state.cache.competitions ? Promise.resolve(state.cache.competitions) : api("/api/competitions"),
      ]);
      state.cache.themes = themes;
      state.cache.competitions = competitions;
    }
    renderIdentityCompetitionOptions();
    renderThemes();
  }

  function renderIdentityCompetitionOptions() {
    const select = $("#identity-competition");
    const current = select.value;
    const competitionMode = state.session.workspace?.visual_identity_mode === "competition";
    select.innerHTML = `<option value="">Identidad general</option>${competitionMode ? (state.cache.competitions || []).map((x) => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.name)}</option>`).join("") : ""}`;
    if ([...select.options].some((x) => x.value === current)) select.value = current;
  }

  function renderThemes() {
    const themes = state.cache.themes || [];
    const competitions = Object.fromEntries((state.cache.competitions || []).map((item) => [item.id, item.name]));
    $("#themes-list").innerHTML = themes.length ? themes.map((theme) => {
      const appearance = mergedAppearance(themeAppearance(theme));
      const swatches = [appearance.scoreboard.background, appearance.scoreboard.name_box, appearance.bottom_bar.body, appearance.panels.accent];
      return `<article class="theme-card ${theme.published ? "published" : ""}"><div class="theme-card-head"><div><span class="eyebrow">${theme.competition_id ? escapeHtml(competitions[theme.competition_id] || "COMPETICIÓN") : "IDENTIDAD GENERAL"}</span><h3>${escapeHtml(theme.name)}</h3></div><span class="pill ${theme.published ? "green" : ""}">${theme.published ? "Publicada" : `v${theme.version}`}</span></div><div class="theme-swatches">${swatches.map((color) => `<span style="background:${escapeHtml(color)}"></span>`).join("")}</div><div class="details"><div><dt>Bloqueada</dt><dd>${booleanLabel(theme.locked)}</dd></div><div><dt>Actualizada</dt><dd>${formatDate(theme.updated_at)}</dd></div></div><div class="theme-card-actions"><button class="secondary" data-load-theme="${escapeHtml(theme.id)}">Usar como base</button>${!theme.published && canWrite() ? `<button data-publish-theme="${escapeHtml(theme.id)}">Publicar</button>` : ""}<button class="danger" data-delete="theme" data-id="${escapeHtml(theme.id)}" data-name="${escapeHtml(theme.name)}" ${!canWrite() ? "disabled" : ""}>Eliminar</button></div></article>`;
    }).join("") : '<div class="empty-state">Todavía no hay identidades guardadas. Configura y guarda la primera versión.</div>';
    bindDeleteButtons($("#themes-list"));
    $$('[data-load-theme]').forEach((button) => button.addEventListener("click", () => {
      const theme = themes.find((x) => String(x.id) === String(button.dataset.loadTheme));
      loadThemeIntoEditor(theme);
    }));
    $$('[data-publish-theme]').forEach((button) => button.addEventListener("click", async () => {
      try {
        button.disabled = true;
        await api(`/api/themes/${button.dataset.publishTheme}/publish`, { method: "POST" });
        delete state.cache.themes;
        await loadThemes(true);
        showToast("Identidad publicada y disponible para SecretariatPro");
      } catch (error) { showToast(error.message, true); }
      finally { button.disabled = false; }
    }));
  }

  function renderPaletteFields() {
    $("#element-controls").innerHTML = Object.entries(ELEMENT_LABELS).map(([key, label]) => `<label>${label} · tamaño (%)<input type="number" min="50" max="150" step="1" required value="100" data-element-scale="${key}"></label><label>${label} · tipografía<select data-element-font="${key}">${ELEMENT_FONTS.map(font => `<option value="${font}">${font === "default" ? "Original del diseño" : font}</option>`).join("")}</select></label>`).join("");
    $$("[data-element-scale], [data-element-font]").forEach(field => field.addEventListener("input", updateVisualPreview));
    [$("#period-clock-number"), $("#period-strip-enabled"), $("#period-strip-segments"), $("#period-strip-labels"), $("#period-strip-active-color"), $("#period-strip-text-color"), $("#goal-celebration-delay"), $("#goal-celebration-duration")].forEach(field => field?.addEventListener("input", updateVisualPreview));
    Object.entries(PALETTE_FIELDS).forEach(([section, fields]) => {
      const host = $(`[data-palette-section="${section}"]`);
      host.innerHTML = fields.map(([key, label]) => {
        const value = DEFAULT_APPEARANCE[section][key];
        const name = `${section}.${key}`;
        return `<label class="color-control"><span>${escapeHtml(label)}</span><input type="color" data-color-picker="${escapeHtml(name)}" value="${escapeHtml(value)}"><input type="text" name="${escapeHtml(name)}" data-color-text="${escapeHtml(name)}" value="${escapeHtml(value)}" pattern="#[0-9A-Fa-f]{6}" maxlength="7" required></label>`;
      }).join("");
    });
    $$('[data-color-picker]').forEach((picker) => picker.addEventListener("input", () => {
      const text = $(`[data-color-text="${picker.dataset.colorPicker}"]`);
      text.value = picker.value.toUpperCase();
      updateVisualPreview();
    }));
    $$('[data-color-text]').forEach((input) => input.addEventListener("input", () => {
      const value = input.value.trim();
      if (/^#[0-9a-f]{6}$/i.test(value)) {
        $(`[data-color-picker="${input.dataset.colorText}"]`).value = value;
        updateVisualPreview();
      }
    }));
    updateVisualPreview();
  }

  function identityFormAppearance() {
    const result = {};
    Object.entries(PALETTE_FIELDS).forEach(([section, fields]) => {
      result[section] = {};
      fields.forEach(([key]) => {
        result[section][key] = $(`[name="${section}.${key}"]`).value;
      });
    });
    result.elements = Object.fromEntries(Object.keys(ELEMENT_LABELS).map(key => [key, {
      scale: Math.max(.5, Math.min(1.5, Number($(`[data-element-scale="${key}"]`).value) / 100 || 1)),
      font: $(`[data-element-font="${key}"]`).value
    }]));
    const segments = Math.max(1, Math.min(12, Number($("#period-strip-segments").value || 3)));
    const entered = $("#period-strip-labels").value.split(",").map(value => value.trim()).filter(Boolean);
    result.period_strip = {show_number: $("#period-clock-number").checked, enabled: $("#period-strip-enabled").checked, active_color: $("#period-strip-active-color").value, text_color: $("#period-strip-text-color").value, segments, labels: Array.from({length:segments}, (_, index) => (entered[index] || String(index + 1)).slice(0, 8))};
    result.goal_celebration = {delay_seconds: Math.max(0, Math.min(30, Number($("#goal-celebration-delay").value || 0))), duration_seconds: Math.max(1, Math.min(30, Number($("#goal-celebration-duration").value || 6)))};
    return mergedAppearance(result);
  }

  function updateVisualPreview() {
    if (!$("#visual-preview")) return;
    const appearance = identityFormAppearance();
    [["scoreboard", ".preview-scoreboard"], ["bottom_bar", ".preview-bottom"], ["intermission", ".preview-panel"]].forEach(([key, selector]) => {
      const el = $(selector); const config = appearance.elements[key];
      el.style.scale = String(config.scale);
      el.style.fontFamily = config.font === "default" ? "" : `"${config.font}"`;
    });
    const style = $("#visual-preview").style;
    style.setProperty("--sb-bg", appearance.scoreboard.background);
    style.setProperty("--sb-name", appearance.scoreboard.name_box);
    style.setProperty("--sb-text", appearance.scoreboard.text);
    style.setProperty("--bb-body", appearance.bottom_bar.body);
    style.setProperty("--bb-middle", appearance.bottom_bar.middle);
    style.setProperty("--bb-text", appearance.bottom_bar.text);
    style.setProperty("--bb-secondary", appearance.bottom_bar.secondary_text);
    style.setProperty("--panel-bg", appearance.panels.background);
    style.setProperty("--panel-surface", appearance.panels.surface);
    style.setProperty("--panel-accent", appearance.panels.accent);
    style.setProperty("--panel-text", appearance.panels.text);
    $(".preview-clock > span").textContent = appearance.period_strip.show_number ? "2 · 12:34" : "12:34";
    const period = $("#preview-period-strip");
    if (period) {
      period.hidden = !appearance.period_strip.enabled;
      period.parentElement.classList.toggle("has-period-strip", appearance.period_strip.enabled);
      period.style.setProperty("--period-active-color", appearance.period_strip.active_color);
      period.style.setProperty("--period-text-color", appearance.period_strip.text_color);
      period.innerHTML = appearance.period_strip.labels.map((label, index) => `<i class="${index === 0 ? "active" : ""}">${escapeHtml(label)}</i>`).join("");
    }
  }

  function loadThemeIntoEditor(theme = null) {
    const form = $("#identity-form");
    const appearance = mergedAppearance(themeAppearance(theme || {}));
    form.elements.name.value = theme ? theme.name : "Nueva personalización";
    form.elements.competition_id.value = theme?.competition_id || "";
    form.elements.locked.value = "true";
    Object.entries(appearance.elements).forEach(([key, config]) => {
      $(`[data-element-scale="${key}"]`).value = Math.round(config.scale * 100);
      $(`[data-element-font="${key}"]`).value = config.font;
    });
    $("#period-clock-number").checked = appearance.period_strip.show_number;
    $("#period-strip-enabled").checked = appearance.period_strip.enabled;
    $("#period-strip-segments").value = appearance.period_strip.segments;
    $("#period-strip-segments").disabled = state.session?.workspace?.sport_mode === "handball";
    $("#period-strip-labels").value = appearance.period_strip.labels.join(", ");
    $("#period-strip-active-color").value = appearance.period_strip.active_color;
    $("#period-strip-text-color").value = appearance.period_strip.text_color;
    $("#goal-celebration-delay").value = appearance.goal_celebration.delay_seconds;
    $("#goal-celebration-duration").value = appearance.goal_celebration.duration_seconds;
    form.elements.published.value = "false";
    Object.entries(PALETTE_FIELDS).forEach(([section, fields]) => fields.forEach(([key]) => {
      const name = `${section}.${key}`;
      const value = appearance[section][key];
      $(`[name="${name}"]`).value = value;
      $(`[data-color-picker="${name}"]`).value = value;
    }));
    $("#identity-editor-state").textContent = theme ? `Editando copia de ${theme.name}` : "Nueva personalización";
    $("#identity-message").textContent = "";
    updateVisualPreview();
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveIdentity(event) {
    event.preventDefault();
    if (!canWrite()) return;
    const form = event.currentTarget;
    const button = $("#identity-save");
    button.disabled = true;
    $("#identity-message").textContent = "";
    try {
      const data = {
        name: form.elements.name.value.trim(),
        competition_id: form.elements.competition_id.value || null,
        locked: form.elements.locked.value === "true",
        published: form.elements.published.value === "true",
        config: { appearance: identityFormAppearance() },
      };
      await api("/api/themes", { method: "POST", body: JSON.stringify({ data }) });
      delete state.cache.themes;
      await loadThemes(true);
      $("#identity-editor-state").textContent = data.published ? "Publicada" : "Borrador guardado";
      showToast(data.published ? "Identidad publicada" : "Borrador visual guardado");
    } catch (error) { $("#identity-message").textContent = error.message; }
    finally { button.disabled = !canWrite(); }
  }

  function workspaceSportMode() {
    return state.session?.workspace?.sport_mode === "handball" ? "handball" : "floorball";
  }

  function isCoachOnly(person) { return person?.position === "coach" || (person?.is_coach && !person?.position); }
  function coachBadge(person) { return person?.is_coach || person?.position === "coach" ? `<span class="pill coach-tag">${escapeHtml(tr("Entrenador"))}</span>` : ""; }
  function playerPositionOptions() {
    const positions = workspaceSportMode() === "handball"
      ? [["goalkeeper", "Portero"], ["left_back", "Lateral izquierdo"], ["center_back", "Central"], ["right_back", "Lateral derecho"], ["pivot", "Pivote"], ["left_wing", "Extremo izquierdo"], ["right_wing", "Extremo derecho"]]
      : [["goalkeeper", "Portero"], ["defender", "Defensa"], ["midfielder", "Medio"], ["forward", "Delantero"]];
    return [["", "Sin posición"], ...positions];
  }


  const forms = {
    season: {
      title: "Nueva temporada", endpoint: "/api/seasons",
      fields: [{ name: "name", label: "Nombre", required: true, placeholder: "2026–2027", full: true }],
    },
    competition: {
      title: "Competición", endpoint: "/api/competitions", cache: "competitions",
      fields: () => [
        { name: "name", label: "Nombre", required: true, full: true },
        { name: "category", label: "Categoría" },
        { name: "season_id", label: "Temporada", type: "select", options: [["", "Sin temporada"], ...(state.cache.seasons || []).map((x) => [x.id, x.name])] },
        { name: "points_win", label: "Puntos por victoria", type: "number", value: 2 },
        { name: "points_draw", label: "Puntos por empate", type: "number", value: 1 },
        { name: "points_loss", label: "Puntos por derrota", type: "number", value: 0 },
        { name: "logo_url", label: "Logo de la liga", type: "logo", assetKind: "league-logos", full: true },
        { name: "active", label: "Estado", type: "select", options: [[true, "Activa"], [false, "Inactiva"]], value: true },
      ],
    },
    team: {
      title: "Equipo", endpoint: "/api/teams", cache: "teams",
      fields: [
        { name: "name", label: "Nombre", required: true, full: true },
        { name: "short_name", label: "Nombre corto", required: true },
        { name: "primary_color", label: "Color principal", type: "colorPair", value: "#1f2937" },
        { name: "secondary_color", label: "Color secundario", type: "colorPair", value: "#ffffff" },
        { name: "logo_url", label: "Logo principal", type: "logo", assetKind: "team-logos", full: true },
        { name: "alternate_logo_url", label: "Logo alternativo", type: "logo", assetKind: "team-logos", full: true },
      ],
    },
    player: {
      title: "Jugador", endpoint: "/api/players", cache: "players",
      fields: () => [
        { name: "first_name", label: "Nombre", required: true },
        { name: "last_name", label: "Apellidos", required: true },
        { name: "display_name", label: "Nombre mostrado", full: true },
        { name: "birth_date", label: "Fecha de nacimiento", type: "date" },
        { name: "nationality", label: "Nacionalidad" },
        { name: "is_coach", label: "Entrenador", type: "checkbox", value: false, help: "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega." },
        { name: "position", label: "Posición", type: "select", options: playerPositionOptions() },
      ],
    },
    match: {
      title: "Partido", endpoint: "/api/matches", cache: "matches",
      fields: () => {
        const competitions = (state.cache.competitions || []).map((x) => [x.id, x.name]);
        const teams = (state.cache.teams || []).map((x) => [x.id, x.name]);
        const members = (state.cache.members || []).filter((x) => x.status === "active").map((x) => [x.user_id, x.profile?.display_name || x.profile?.email || x.user_id]);
        return [
          { name: "competition_id", label: "Competición", type: "select", options: [["", "Selecciona"], ...competitions], required: true, full: true },
          { name: "home_team_id", label: "Equipo local", type: "select", options: [["", "Selecciona"], ...teams], required: true },
          { name: "away_team_id", label: "Equipo visitante", type: "select", options: [["", "Selecciona"], ...teams], required: true },
          { name: "match_date", label: "Fecha y hora", type: "datetime-local", required: true },
          { name: "time_confirmed", label: "Hora confirmada", type: "select", options: [[true, "Sí"], [false, "No"]], value: true },
          { name: "venue", label: "Pabellón" },
          { name: "assigned_to", label: "Realizador", type: "select", options: [["", "Sin asignar"], ...members], full: true },
          { name: "broadcast_enabled", label: "Uso del partido", type: "select", options: [[true, "Retransmitir / operar en Live"], [false, "Solo registro administrativo (no Live)"]], value: true, full: true },
          { name: "status", label: "Estado", type: "select", options: [["scheduled", "Programado"], ["live", "En directo"], ["finished", "Finalizado"], ["postponed", "Aplazado"], ["cancelled", "Cancelado"]], value: "scheduled" },
          { name: "home_score", label: "Resultado local", type: "number", value: 0 },
          { name: "away_score", label: "Resultado visitante", type: "number", value: 0 },
        ];
      },
    },
    member: {
      title: "Invitar usuario", endpoint: "/api/members", direct: true,
      fields: [
        { name: "email", label: "Correo de la invitación", type: "email", required: true, full: true },
        { name: "role", label: "Rol", type: "select", options: [["producer", "Realizador"], ["competition_manager", "Gestor de competiciones"]], full: true },
      ],
    },
    memberEdit: {
      title: "Editar miembro", endpoint: "/api/members", cache: "members",
      fields: [
        { name: "role", label: "Rol", type: "select", options: [["producer", "Realizador"], ["competition_manager", "Gestor de competiciones"]], full: true },
        { name: "status", label: "Estado", type: "select", options: [["invited", "Invitación pendiente"], ["active", "Activo"], ["suspended", "Suspendido"]], full: true },
      ],
    },
  };

  function rosterFormConfig(type, preset = {}) {
    const competitionOptions = [["", "Selecciona"], ...(state.cache.competitions || []).map((x) => [x.id, `${x.name} · ${competitionSeason(x)}`])];
    const teamOptions = [["", "Selecciona"], ...(state.cache.teams || []).map((x) => [x.id, x.name])];
    const playerOptions = [["", "Selecciona"], ...(state.cache.players || []).map((x) => [x.id, playerName(x)])];
    const shared = [
      { name: "competition_id", label: "Competición / temporada", type: "select", options: competitionOptions, required: true, full: true, value: preset.competition_id || "" },
      { name: "shirt_number", label: "Dorsal", type: "number", min: 0, max: 999, required: false },
      { name: "captain", label: "Capitanía", type: "select", options: [[false, "No"], [true, "Sí"]], value: preset.captain || false },
    ];
    if (type === "rosterExisting") return {
      title: "Añadir jugador al roster", endpoint: "/api/rosters",
      fields: [{ name: "player_id", label: "Jugador existente", type: "select", options: playerOptions, required: true, full: true }, ...shared],
      transform: (data) => ({ ...data, team_id: preset.team_id, active: true, member_type: isCoachOnly((state.cache.players || []).find(p => p.id === data.player_id)) ? "coach" : "player" }),
      validate: (data) => validateRosterClient(data),
    };
    if (type === "rosterNew") return {
      title: "Crear jugador y añadirlo", endpoint: "/api/rosters/with-player",
      fields: [
        { name: "first_name", label: "Nombre", required: true },
        { name: "last_name", label: "Apellidos", required: true },
        { name: "display_name", label: "Nombre mostrado", full: true },
        { name: "birth_date", label: "Fecha de nacimiento", type: "date" },
        { name: "nationality", label: "Nacionalidad" },
        { name: "is_coach", label: "Entrenador", type: "checkbox", value: false, help: "Marca Entrenador para añadir la etiqueta. Conserva la posición si esa persona también juega." },
        { name: "position", label: "Posición", type: "select", options: playerPositionOptions() },
        ...shared,
      ],
      transform: (data) => ({ player: { first_name: data.first_name, last_name: data.last_name, display_name: data.display_name, position: data.position, birth_date: data.birth_date, nationality: data.nationality, is_coach: data.is_coach }, roster: { competition_id: data.competition_id, team_id: preset.team_id, shirt_number: data.shirt_number, captain: (data.is_coach && !data.position) ? false : data.captain, active: true, member_type: (data.is_coach && !data.position) ? "coach" : "player" } }),
    };
    if (type === "playerRoster") return {
      title: "Añadir jugador a un roster", endpoint: "/api/rosters",
      fields: [{ name: "team_id", label: "Equipo", type: "select", options: teamOptions, required: true, full: true }, ...shared],
      transform: (data) => ({ ...data, player_id: preset.player_id, active: true, member_type: isCoachOnly((state.cache.players || []).find(p => p.id === preset.player_id)) ? "coach" : "player" }),
      validate: (data) => validateRosterClient(data),
    };
    return {
      title: "Editar dorsal y capitanía", endpoint: "/api/rosters", record: preset,
      fields: [
        { name: "shirt_number", label: "Dorsal", type: "number", min: 0, max: 999, required: false, value: preset.shirt_number },
        { name: "captain", label: "Capitanía", type: "select", options: [[false, "No"], [true, "Sí"]], value: preset.captain },
      ],
      transform: (data) => ({ ...preset, shirt_number: data.shirt_number, captain: data.captain }),
      validate: (data) => validateRosterClient(data, preset.id),
    };
  }

  function validateRosterClient(data, excludeId = "") {
    const roster = data.roster || data;
    const allRows = Object.values(state.cache.teamRosters || {}).flat();
    const duplicatePlayer = allRows.find((row) => String(row.id) !== String(excludeId) && row.active !== false && String(row.team_id) === String(roster.team_id) && String(row.competition_id) === String(roster.competition_id) && String(row.player_id) === String(roster.player_id));
    if (duplicatePlayer) throw new Error("Este jugador ya pertenece a ese roster");
    const duplicateNumber = roster.member_type !== "coach" && roster.shirt_number != null && roster.shirt_number !== "" && allRows.find((row) => String(row.id) !== String(excludeId) && row.active !== false && String(row.team_id) === String(roster.team_id) && String(row.competition_id) === String(roster.competition_id) && String(row.shirt_number) === String(roster.shirt_number));
    if (duplicateNumber) throw new Error(`El dorsal ${roster.shirt_number} ya está asignado en ese roster`);
  }

  async function openRosterForm(type, preset) {
    if (!canWrite()) return showToast("Tu cuenta no tiene permisos de gestión", true);
    await ensureSportsCache();
    const config = rosterFormConfig(type, preset);
    openConfiguredForm(type, config, config.record || null);
  }

  function normalizeInputValue(type, value) {
    if (type === "datetime-local" && value) {
      const date = new Date(value);
      if (!Number.isNaN(date.getTime())) {
        const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
        return local.toISOString().slice(0, 16);
      }
    }
    return value ?? "";
  }

  function fieldHtml(field, value) {
    const full = field.full ? " full" : "";
    const required = field.required ? " required" : "";
    const current = value ?? field.value ?? "";
    if (field.type === "checkbox") {
      return `<label class="coach-checkbox"><input type="checkbox" name="${escapeHtml(field.name)}" ${current === true ? "checked" : ""}>${escapeHtml(field.label)}<small>${escapeHtml(tr(field.help || ""))}</small></label>`;
    }
    if (field.type === "select") {
      return `<label class="${full.trim()}">${escapeHtml(field.label)}<select name="${escapeHtml(field.name)}"${required}>${(field.options || []).map(([optionValue, label]) => `<option value="${escapeHtml(String(optionValue))}" ${String(current) === String(optionValue) ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}</select></label>`;
    }
    if (field.type === "colorPair") {
      return `<label>${escapeHtml(field.label)}<div class="color-control"><input type="color" data-modal-color="${escapeHtml(field.name)}" value="${escapeHtml(current)}"><input type="text" name="${escapeHtml(field.name)}" value="${escapeHtml(current)}" pattern="#[0-9A-Fa-f]{6}" maxlength="7" required></div></label>`;
    }
    if (field.type === "logo") {
      return `<div class="logo-field"><label>${escapeHtml(field.label)}</label><div class="logo-field-main"><input name="${escapeHtml(field.name)}" type="text" value="${escapeHtml(current)}" placeholder="https://… o selecciona un archivo local"><button class="logo-file-button" type="button" data-logo-select="${escapeHtml(field.name)}">Elegir archivo local</button><input type="file" data-logo-file="${escapeHtml(field.name)}" data-asset-kind="${escapeHtml(field.assetKind || "logos")}" accept="image/png,image/jpeg,image/webp,image/svg+xml" hidden></div><div class="logo-preview" data-logo-preview="${escapeHtml(field.name)}">${current ? `<img src="${escapeHtml(current)}" alt="">` : '<span class="logo-placeholder">LOGO</span>'}</div><div class="logo-hint">Se aceptan enlaces de internet o archivos PNG, JPG, WEBP y SVG. El archivo local se subirá al espacio.</div></div>`;
    }
    const bounds = `${field.min !== undefined ? ` min="${field.min}"` : ""}${field.max !== undefined ? ` max="${field.max}"` : ""}`;
    return `<label class="${full.trim()}">${escapeHtml(field.label)}<input name="${escapeHtml(field.name)}" type="${escapeHtml(field.type || "text")}" value="${escapeHtml(normalizeInputValue(field.type, current))}" placeholder="${escapeHtml(field.placeholder || "")}"${required}${bounds}></label>`;
  }

  async function openForm(type, record = null) {
    if (!canWrite()) return showToast("Tu cuenta está en modo consulta o no tiene permisos de gestión", true);
    if (["competition", "match"].includes(type)) await loadCompetitions();
    if (type === "match") await loadMatches();
    const config = forms[type];
    if (!config) return;
    openConfiguredForm(type, config, record);
  }

  function openConfiguredForm(type, config, record = null) {
    const fields = typeof config.fields === "function" ? config.fields() : config.fields;
    state.modal = { type, config, record, fields, files: {} };
    $("#modal-eyebrow").textContent = record ? "EDITAR" : "NUEVO";
    $("#modal-title").textContent = config.title;
    $("#modal-fields").innerHTML = fields.map((field) => fieldHtml(field, record?.[field.name])).join("");
    $("#modal-message").textContent = "";
    $("#modal-save").disabled = false;
    const backdrop = $("#modal-backdrop");
    backdrop.hidden = false;
    backdrop.setAttribute("aria-hidden", "false");
    bindModalSpecialFields();
    $("#modal-fields input, #modal-fields select")?.focus();
  }

  function bindModalSpecialFields() {
    $$('[data-modal-color]').forEach((picker) => picker.addEventListener("input", () => {
      const input = $(`[name="${picker.dataset.modalColor}"]`, $("#modal-fields"));
      input.value = picker.value.toUpperCase();
    }));
    $$('[data-logo-select]').forEach((button) => button.addEventListener("click", () => $(`[data-logo-file="${button.dataset.logoSelect}"]`).click()));
    $$('[data-logo-file]').forEach((input) => input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      state.modal.files[input.dataset.logoFile] = { file, assetKind: input.dataset.assetKind };
      const preview = $(`[data-logo-preview="${input.dataset.logoFile}"]`);
      const objectUrl = URL.createObjectURL(file);
      preview.innerHTML = `<img src="${objectUrl}" alt="Previsualización">`;
      $(`[name="${input.dataset.logoFile}"]`, $("#modal-fields")).value = file.name;
    }));
    $$('[data-logo-preview]').forEach((preview) => {
      const name = preview.dataset.logoPreview;
      const input = $(`[name="${name}"]`, $("#modal-fields"));
      input?.addEventListener("input", () => {
        const value = input.value.trim();
        if (/^https?:\/\//i.test(value) || value.startsWith("data:")) preview.innerHTML = `<img src="${escapeHtml(value)}" alt="Previsualización">`;
      });
    });
  }

  function closeModal() {
    const backdrop = $("#modal-backdrop");
    if (backdrop) {
      backdrop.hidden = true;
      backdrop.setAttribute("hidden", "");
      backdrop.setAttribute("aria-hidden", "true");
    }
    state.modal = null;
  }

  function parseForm(form, fields) {
    const formData = new FormData(form);
    const data = {};
    fields.forEach((field) => {
      let value = formData.get(field.name);
      if (field.type === "checkbox") value = form.elements[field.name].checked;
      if (field.type === "number") value = value === "" ? null : Number(value);
      if (field.type === "select") {
        const option = (field.options || []).find(([raw]) => String(raw) === String(value));
        if (option && typeof option[0] === "boolean") value = option[0];
      }
      if (field.type === "datetime-local" && value) value = new Date(value).toISOString();
      data[field.name] = value === "" ? null : value;
      if (field.name === "match_date" && formData.get(field.name)) data.scheduled_date = String(formData.get(field.name)).slice(0,10);
    });
    return data;
  }

  async function uploadModalFiles(data) {
    for (const [name, item] of Object.entries(state.modal?.files || {})) {
      const body = new FormData();
      body.append("file", item.file);
      const result = await api(`/api/assets/upload?asset_kind=${encodeURIComponent(item.assetKind || "logos")}`, { method: "POST", body, timeout: 45000 });
      data[name] = result.url;
    }
    return data;
  }

  async function submitModal(event) {
    event.preventDefault();
    if (!state.modal) return;
    const { type, config, record, fields } = state.modal;
    const button = $("#modal-save");
    button.disabled = true;
    $("#modal-message").textContent = "";
    try {
      let data = parseForm(event.currentTarget, fields);
      if (type === "rosterShell") {
        if (!data.competition_id) throw new Error("Selecciona una competición");
        const team = state.modal.team;
        const group = await api(`/api/teams/${encodeURIComponent(team.id)}/roster-groups/${encodeURIComponent(data.competition_id)}`, {method:"POST"});
        state.cache.rosterGroups = [...(state.cache.rosterGroups || []).filter(g => g.id !== group.id), group];
        state.selectedTeamRosterCompetitionId = String(data.competition_id);
        closeModal();
        renderTeamDetail(team, state.cache.teamRosters?.[String(team.id)] || []);
        showToast("Roster preparado. Ya puedes añadir jugadores");
        return;
      }
      data = await uploadModalFiles(data);
      if (config.transform) data = config.transform(data);
      if (config.validate) config.validate(data);
      let endpoint = config.endpoint;
      let method = "POST";
      if (record) {
        endpoint += `/${record.id || record.user_id}`;
        method = "PATCH";
      }
      const body = config.direct ? JSON.stringify(data) : JSON.stringify({ data });
      const result = await api(endpoint, { method, body, timeout: 45000 });
      const successMessage = type === "member"
        ? (result.invited ? "Invitación enviada por correo" : result.already_pending ? "La invitación ya estaba pendiente" : "El usuario ya tenía cuenta y se ha añadido")
        : "Datos guardados correctamente";
      closeModal();
      clearRelevantCache(type);
      try {
        await loadView(state.view, true);
      } catch (refreshError) {
        // The write has already succeeded. A transient read timeout while
        // refreshing must not make the operator repeat an invitation.
        console.warn("No se pudo refrescar la vista después de guardar", refreshError);
      }
      showToast(successMessage);
    } catch (error) {
      const message = $("#modal-message");
      if (message) message.textContent = error.message;
      else showToast(error.message, true);
    }
    finally { button.disabled = false; }
  }

  function clearRelevantCache(type) {
    const map = {
      season: ["seasons", "competitions", "dashboard"],
      competition: ["competitions", "dashboard", "matches", "themes", "teamRosters", "playerRosters"],
      team: ["teams", "dashboard", "matches", "teamRosters", "playerRosters"],
      player: ["players", "dashboard", "teamRosters", "playerRosters"],
      match: ["matches", "dashboard"],
      member: ["members", "dashboard", "matches"],
      memberEdit: ["members", "dashboard", "matches"],
      rosterExisting: ["teamRosters", "playerRosters"],
      rosterNew: ["players", "teamRosters", "playerRosters", "dashboard"],
      playerRoster: ["teamRosters", "playerRosters"],
      rosterEdit: ["teamRosters", "playerRosters"],
    };
    (map[type] || []).forEach((key) => delete state.cache[key]);
  }

  function bindEditButtons(root = document) {
    $$('[data-edit]', root).forEach((button) => {
      button.disabled = !canWrite();
      button.onclick = async () => {
        const type = button.dataset.edit;
        const id = button.dataset.id;
        const cacheKey = type === "member" ? "members" : (type === "match" ? "matches" : `${type}s`);
        const list = state.cache[cacheKey] || [];
        const record = list.find((item) => String(item.id || item.user_id) === String(id));
        await openForm(type === "member" ? "memberEdit" : type, record);
      };
    });
  }

  const deleteEndpoint = {
    season: "/api/seasons", competition: "/api/competitions", team: "/api/teams",
    player: "/api/players", match: "/api/matches", member: "/api/members", theme: "/api/themes",
  };
  const deleteNoun = {
    season: "la temporada", competition: "la competición", team: "el equipo",
    player: "el jugador", match: "el partido", member: "el usuario", theme: "la personalización",
  };

  async function deleteEntity(type, id, name = "") {
    if (!canWrite()) return showToast("Tu cuenta no tiene permisos de gestión", true);
    const noun = deleteNoun[type] || "el elemento";
    const extra = type === "member"
      ? "Se retirará su acceso al espacio, pero no se eliminará su cuenta de SecretariatPro."
      : type === "match"
        ? "Se eliminarán también sus convocatorias y eventos. Esta acción no se puede deshacer."
        : "Si contiene histórico protegido, el Manager impedirá el borrado y te indicará qué debes resolver.";
    if (!window.confirm(`¿Eliminar ${noun}${name ? ` «${name}»` : ""}?

${extra}`)) return;
    const endpoint = deleteEndpoint[type];
    if (!endpoint) return showToast("Este tipo de elemento no se puede eliminar", true);
    try {
      await api(`${endpoint}/${encodeURIComponent(id)}`, { method: "DELETE", timeout: 45000 });
      if (type === "team") {
        state.selectedTeamId = "";
        state.selectedTeamRosterCompetitionId = "";
        $("#team-detail").innerHTML = '<div class="empty-state detail-empty">Selecciona un equipo para consultar su ficha y sus rosters.</div>';
      }
      if (type === "player") {
        state.selectedPlayerId = "";
        $("#player-detail").innerHTML = '<div class="empty-state detail-empty">Selecciona un jugador para consultar sus equipos, competiciones y dorsales.</div>';
      }
      clearRelevantCache(type === "theme" ? "competition" : type);
      if (type === "theme") delete state.cache.themes;
      state.cache.dashboard = null;
      await loadView(state.view, true);
      showToast(`${name || "Elemento"} eliminado correctamente`);
    } catch (error) { showToast(error.message, true); }
  }

  function bindDeleteButtons(root = document) {
    $$('[data-delete]', root).forEach((button) => {
      button.disabled = !canWrite();
      button.onclick = () => deleteEntity(button.dataset.delete, button.dataset.id, button.dataset.name || "");
    });
  }

  function bindEntityActionButtons(root = document) {
    bindEditButtons(root);
    bindDeleteButtons(root);
  }

  function openAccount() {
    renderAccountContent();
    $("#account-backdrop").hidden = false;
    $("#account-backdrop").setAttribute("aria-hidden", "false");
  }
  function closeAccount() {
    const backdrop = $("#account-backdrop");
    if (backdrop) { backdrop.hidden = true; backdrop.setAttribute("aria-hidden", "true"); }
  }
  function renderAccountContent() {
    const profile = state.session.profile || {};
    const workspace = state.session.workspace || {};
    if (!$("#account-avatar")) return;
    $("#account-avatar").innerHTML = avatarHtml(profile);
    $("#account-name-label").textContent = profile.display_name || "Usuario";
    $("#account-email-label").textContent = profile.email || "—";
    $("#account-workspace-label").textContent = workspace.name ? `Espacio activo: ${workspace.name}` : "Sin espacio activo";
    $("#account-display-name").value = profile.display_name || "";
    $("#account-avatar-remove").disabled = !profile.avatar_url;
  }

  async function saveAccountProfile(event) {
    event.preventDefault();
    const message = $("#account-profile-message");
    message.textContent = "";
    try {
      const result = await api("/api/account/profile", { method: "PATCH", body: JSON.stringify({ display_name: $("#account-display-name").value.trim() }) });
      renderSession(result.state);
      message.textContent = "Nombre actualizado";
      message.style.color = "var(--accent)";
    } catch (error) { message.textContent = error.message; message.style.color = ""; }
  }

  async function saveAccountPassword(event) {
    event.preventDefault();
    const message = $("#account-password-message");
    message.textContent = "";
    const newPassword = $("#account-password").value;
    const confirmPassword = $("#account-password-confirm").value;
    try {
      const result = await api("/api/account/password", { method: "POST", body: JSON.stringify({ new_password: newPassword, confirm_password: confirmPassword }) });
      message.textContent = result.message || "Contraseña actualizada";
      message.style.color = "var(--accent)";
      event.currentTarget.reset();
    } catch (error) { message.textContent = error.message; message.style.color = ""; }
  }

  async function uploadAccountAvatar(file) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const result = await api("/api/account/avatar", { method: "POST", body, timeout: 45000 });
      renderSession(result.state);
      showToast("Foto de perfil actualizada");
    } catch (error) { showToast(error.message, true); }
  }

  async function removeAccountAvatar() {
    try {
      const result = await api("/api/account/avatar", { method: "DELETE" });
      renderSession(result.state);
      showToast("Foto de perfil eliminada");
    } catch (error) { showToast(error.message, true); }
  }

  function openRosterImport(team, competition) {
    const panel = $("#roster-import-panel");
    panel.hidden = false;
    const endpoint = `/api/teams/${encodeURIComponent(team.id)}/rosters/${encodeURIComponent(competition.id)}/import`;
    const help = "Importa directamente en este roster. Los perfiles idénticos se reutilizan. Puedes incluir dorsal y capitán; el equipo y la competición serán los seleccionados aquí.";
    panel.innerHTML = `<article class="panel"><h3>${escapeHtml(team.name)} · ${escapeHtml(competition.name)}</h3><p>${escapeHtml(tr(help))}</p><div class="roster-import-tools"><a class="secondary" href="/api/import/roster-template.xlsx" download="SecretariatPro_roster.xlsx">${tr("Descargar plantilla Excel")}</a><input type="file" accept=".xlsx,.xlsm,.csv" data-roster-file></div><div data-roster-analysis></div><div class="detail-actions"><button data-roster-confirm hidden>${tr("Confirmar importación")}</button><button class="secondary" data-roster-cancel>${tr("Cancelar")}</button></div><div data-roster-report></div></article>`;
    let pending = null;
    const input = $("[data-roster-file]", panel), confirm = $("[data-roster-confirm]", panel), cancel = $("[data-roster-cancel]", panel);
    const analysis = $("[data-roster-analysis]", panel);
    input.addEventListener("change", async () => {
      pending = null; confirm.hidden = true;
      const file = input.files[0]; if (!file) return;
      input.disabled = true; cancel.disabled = true;
      analysis.textContent = tr("Preparando plantilla…");
      const body = new FormData(); body.append("file", file);
      try {
        const data = await api(`${endpoint}/analyze`, {method:"POST", body, timeout:45000});
        analysis.innerHTML = (data.sheets || []).map(sheet => `<h4>${escapeHtml(sheet.sheet)}</h4>${renderPreviewTable(sheet.preview || [])}`).join("");
        if (data.importable_rows) { pending = file; confirm.hidden = false; }
        else analysis.textContent = tr("Sin jugadores reconocibles.");
      } catch(error) { analysis.textContent = error.message; }
      finally { input.disabled = false; cancel.disabled = false; }
    });
    cancel.addEventListener("click", () => { panel.hidden = true; panel.replaceChildren(); });
    confirm.addEventListener("click", async () => {
      if (!pending || confirm.disabled) return;
      confirm.disabled = true; cancel.disabled = true; input.disabled = true;
      const body = new FormData(); body.append("file", pending);
      try {
        const report = await api(`${endpoint}/commit`, {method:"POST", body, timeout:180000});
        renderImportReport(report, $("[data-roster-report]", panel));
        pending = null; confirm.hidden = true; state.cache = {};
        // Keep the report visible; refresh the roster when the user closes it.
        cancel.textContent = tr("Cerrar");
        cancel.addEventListener("click", () => loadTeams(true).catch(error => showToast(error.message, true)), {once:true});
      } catch(error) { showToast(error.message, true); }
      finally { confirm.disabled = false; cancel.disabled = false; input.disabled = false; }
    });
    translateManagerUI(panel);
  }

  function resetPendingImport() {
    state.importVersion = (state.importVersion || 0) + 1;
    state.pendingImportFile = null;
    state.pendingImportAnalysis = null;
    $("#import-confirmation").hidden = true;
    $("#import-report").hidden = true;
    $("#import-report").innerHTML = "";
  }

  function importScopeQuery() {
    const season = $("#import-season").value, competition = $("#import-competition").value;
    if (!season || !competition) throw new Error(tr("Selecciona temporada y competición"));
    return new URLSearchParams({season_id:season, competition_id:competition, timezone_name:Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Madrid"});
  }
  function syncImportCompetitions() {
    const previous = $("#import-competition").value;
    const items = (state.cache.competitions || []).filter(c => String(c.season_id || "") === $("#import-season").value);
    $("#import-competition").innerHTML = '<option value="">' + tr("Selecciona") + '</option>' + items.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join("");
    if (items.some(c => c.id === previous)) $("#import-competition").value = previous;
    else if (items.length === 1) $("#import-competition").value = items[0].id;
  }
  function syncImportHelp() {
    const matches = $("#import-kind").value === "matches";
    $("#import-mode-help").textContent = tr(matches ? "Fecha, hora opcional, instalación, local y visitante. Los equipos deben existir." : "Incluye Equipo, Dorsal y los datos personales. Entrenador admite Sí o No.");
  }
  async function loadImportScope() {
    await ensureSportsCache();
    const previous = $("#import-season").value;
    $("#import-season").innerHTML = '<option value="">' + tr("Selecciona") + '</option>' + (state.cache.seasons || []).map(s => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.name)}</option>`).join("");
    if ((state.cache.seasons || []).some(s => s.id === previous)) $("#import-season").value = previous;
    else {
      const current = (state.cache.competitions || []).find(c => c.id === state.selectedTeamRosterCompetitionId);
      $("#import-season").value = current?.season_id || state.cache.seasons?.[0]?.id || "";
    }
    syncImportCompetitions(); syncImportHelp();
  }
  async function analyseImport(file) {
    resetPendingImport(); state.pendingImportFile = file;
    const version = state.importVersion = (state.importVersion || 0) + 1;
    const result = $("#import-result"); result.hidden = false;
    $("#import-result-title").textContent = file.name;
    $("#import-analysis").textContent = tr("Cargando…");
    try {
      const kind = $("#import-kind").value, scope = importScopeQuery().toString();
      const body = new FormData(); body.append("file", file);
      const data = await api(`/api/import/scoped/${kind}/analyze?${scope}`, {method:"POST", body, timeout:45000});
      if (version !== state.importVersion) return;
      state.pendingImportAnalysis = {...data, scope, kind};
      $("#import-total").textContent = String(data.total_rows);
      $("#import-analysis").innerHTML = renderPreviewTable(data.preview || []) + (data.errors || []).map(e => `<p class="notice">${escapeHtml(e)}</p>`).join("")
        + (kind === "people" ? (data.missing_teams || []).map(name => `<p class="notice">${escapeHtml(name)} <button type="button" data-import-create-team="${escapeHtml(encodeURIComponent(name))}">${tr("Crear equipo")}</button></p>`).join("") : "")
        + (data.missing_rosters || []).map(g => `<p class="notice">${escapeHtml(g.name)} · ${tr("Sin roster en esta competición")} <button type="button" data-import-create-roster="${escapeHtml(g.team_id)}">${tr("Crear roster")}</button></p>`).join("");
      $("#import-confirmation").hidden = !data.ready;
      $("#confirm-import").disabled = !data.ready || !canWrite();
      $("#import-confirmation-text").textContent = tr("Confirma para guardar los datos en Supabase.");
      $$('[data-import-create-team], [data-import-create-roster]', $("#import-analysis")).forEach(button => button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          if (button.dataset.importCreateTeam) await api("/api/teams", {method:"POST",body:JSON.stringify({data:{name:decodeURIComponent(button.dataset.importCreateTeam)}})});
          else await api(`/api/teams/${encodeURIComponent(button.dataset.importCreateRoster)}/roster-groups/${encodeURIComponent(new URLSearchParams(scope).get("competition_id"))}`, {method:"POST"});
          delete state.cache.teams; delete state.cache.rosterGroups;
          await analyseImport(file);
        } catch(error) { showToast(error.message,true);button.disabled=false; }
      }));
    } catch(error) {
      if (version !== state.importVersion) return;
      $("#import-analysis").textContent = error.message;
    }
  }

  function renderImportReport(report = {}, target = null) {
    const totals = report.totals || {};
    const sections = report.sections || {};
    const errors = report.errors || [];
    const box = target || $("#import-report");
    box.className = "import-report";
    box.hidden = false;
    box.innerHTML = `
      <div class="import-report-summary">
        <article><span>Creados</span><strong>${Number(totals.created || 0)}</strong></article>
        <article><span>Actualizados</span><strong>${Number(totals.updated || 0)}</strong></article>
        <article><span>Sin cambios</span><strong>${Number(totals.skipped || 0)}</strong></article>
        <article><span>Errores</span><strong>${Number(totals.failed || 0)}</strong></article>
      </div>
      <div class="import-report-sections">${Object.entries(sections).map(([name, item]) => `<div class="import-report-row"><strong>${escapeHtml(item.label || name)}</strong><span>${Number(item.created || 0)} creados · ${Number(item.updated || 0)} actualizados · ${Number(item.skipped || 0)} omitidos · ${Number(item.failed || 0)} errores</span></div>`).join("")}</div>
      ${errors.length ? `<div class="import-errors"><strong>Filas que requieren revisión</strong><ul>${errors.slice(0, 30).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>${errors.length > 30 ? `<small>Se muestran 30 de ${errors.length} errores.</small>` : ""}</div>` : ""}
    `;
  }

  async function confirmImport() {
    const file = state.pendingImportFile;
    const analysis = state.pendingImportAnalysis;
    if (!file || !analysis) return showToast("Selecciona y analiza primero un archivo", true);
    const button = $("#confirm-import");
    const cancel = $("#cancel-import");
    button.disabled = true;
    cancel.disabled = true;
    button.textContent = "Importando…";
    const body = new FormData();
    body.append("file", file);
    try {
      if (analysis.scope !== importScopeQuery().toString() || analysis.kind !== $("#import-kind").value) throw new Error(tr("Vuelve a analizar el archivo"));
      const report = await api(`/api/import/scoped/${analysis.kind}/commit?${analysis.scope}`, { method: "POST", body, timeout: 180000 });
      if (report.blocked) { await analyseImport(file); return; }
      $("#import-confirmation").hidden = true;
      renderImportReport(report);
      state.pendingImportFile = null;
      state.pendingImportAnalysis = null;
      state.cache = {};
      const failed = Number(report.totals?.failed || 0);
      showToast(failed ? `Importación completada con ${failed} filas pendientes de revisión` : "Importación confirmada y guardada", failed > 0);
    } catch (error) {
      showToast(error.message, true);
      $("#import-report").hidden = false;
      $("#import-report").innerHTML = `<div class="notice">${escapeHtml(error.message)}</div>`;
    } finally {
      button.disabled = false;
      cancel.disabled = false;
      button.textContent = "Confirmar importación";
    }
  }

  async function downloadPlayerTemplate() {
    const button = $("#download-player-template");
    const status = $("#template-download-status");
    const original = button.textContent;
    button.disabled = true;
    button.textContent = tr("Preparando plantilla…");
    status.textContent = tr("Generando el archivo Excel…");
    try {
      const result = await api(`/api/import/scoped/${$("#import-kind").value}/template/download`, { method: "POST", timeout: 30000 });
      status.textContent = `${tr("Plantilla guardada en")}: ${result.path}`;
      showToast(`${tr("Plantilla Excel guardada")}: ${result.filename}`);
    } catch (error) {
      status.textContent = error.message;
      showToast(error.message, true);
      try {
        const response = await fetch(`/api/import/scoped/${$("#import-kind").value}/template.xlsx`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Error ${response.status}`);
        const blob = await response.blob();
        const href = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = href;
        anchor.download = `SecretariatPro_${$("#import-kind").value}.xlsx`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(href), 1000);
      } catch (_) {
        // The direct local-save route already displayed the useful error.
      }
    } finally {
      button.disabled = false;
      button.textContent = "Descargar plantilla Excel";
      translateManagerUI(button);
    }
  }

  function renderPreviewTable(rows) {
    const headers = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    return `<div class="preview-scroll"><table class="data-table"><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((header) => `<td>${escapeHtml(row[header] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  async function bootstrap() {
    try {
      const health = await api("/api/health", { timeout: 4000 });
      $("#login-diagnostic").textContent = `Motor local preparado · ${health.version}`;
      const session = await api("/api/state", { timeout: 5000 });
      renderSession(session);
      if (session.connected) await loadView("dashboard", true);
    } catch (error) {
      $("#login-diagnostic").textContent = `No se puede comunicar con el motor local: ${error.message}`;
      setLoginMessage("Reinicia SecretariatPro Manager. El motor local no está respondiendo.");
    }
  }

  function setSidebarState(open, { persist = true } = {}) {
    const shell = $("#manager-shell");
    const compact = window.matchMedia("(max-width: 980px)").matches;
    if (!shell) return;
    if (compact) {
      shell.classList.toggle("sidebar-open", Boolean(open));
      shell.classList.remove("sidebar-collapsed");
    } else {
      shell.classList.remove("sidebar-open");
      shell.classList.toggle("sidebar-collapsed", !open);
      if (persist) localStorage.setItem("secretariatpro.manager.sidebar", open ? "open" : "collapsed");
    }
    $("#sidebar-toggle")?.setAttribute("aria-expanded", String(Boolean(open)));
  }

  function initialiseSidebar() {
    const compact = window.matchMedia("(max-width: 980px)").matches;
    const saved = localStorage.getItem("secretariatpro.manager.sidebar") || "open";
    setSidebarState(compact ? false : saved !== "collapsed", { persist: false });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initializePreferences();
    initialiseSidebar();
    systemThemeQuery.addEventListener?.("change", () => { if (state.preferences.theme === "system") applyTheme("system", false); });
    $("#sidebar-toggle")?.addEventListener("click", () => {
      const shell = $("#manager-shell");
      const compact = window.matchMedia("(max-width: 980px)").matches;
      const currentlyOpen = compact ? shell.classList.contains("sidebar-open") : !shell.classList.contains("sidebar-collapsed");
      setSidebarState(!currentlyOpen);
    });
    $("#sidebar-scrim")?.addEventListener("click", () => setSidebarState(false, { persist: false }));
    window.addEventListener("resize", () => initialiseSidebar());
    closeModal();
    closeAccount();
    renderPaletteFields();

    $("#login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      setLoginMessage("");
      setLoginBusy(true);
      try {
        const session = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: $("#login-email").value.trim(), password: $("#login-password").value }),
          timeout: 30000,
        });
        renderSession(session);
        $("#login-password").value = "";
        state.cache = {};
        switchView("dashboard");
      } catch (error) { setLoginMessage(error.message || "No se pudo iniciar sesión"); }
      finally { setLoginBusy(false); }
    });

    $("#forgot-password").addEventListener("click", async () => {
      const email = $("#login-email").value.trim();
      if (!email) return setLoginMessage("Escribe primero el correo de tu cuenta");
      setLoginMessage("");
      try {
        const result = await api("/api/auth/reset-password", { method: "POST", body: JSON.stringify({ email }) });
        setLoginMessage(result.message || "Correo solicitado", true);
      } catch (error) { setLoginMessage(error.message); }
    });

    $("#logout-button").addEventListener("click", async () => {
      try { renderSession(await api("/api/auth/logout", { method: "POST" })); }
      catch (error) { showToast(error.message, true); }
      state.cache = {};
      resetPendingImport();
    });

    $("#workspace-select").addEventListener("change", async (event) => {
      try {
        const session = await api("/api/workspaces/activate", { method: "POST", body: JSON.stringify({ workspace_id: event.target.value }) });
        state.cache = {};
        state.selectedTeamId = "";
        state.selectedPlayerId = "";
        resetPendingImport();
        renderSession(session);
        await loadView(state.view, true);
      } catch (error) { showToast(error.message, true); }
    });

    $$('[data-view]').forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
    $$('[data-view-jump]').forEach((button) => button.addEventListener("click", () => switchView(button.dataset.viewJump)));
    $$('[data-action="refresh"]').forEach((button) => button.addEventListener("click", async () => {
      state.cache = {};
      await loadView(state.view, true);
      showToast("Datos actualizados");
    }));
    $$('[data-create]').forEach((button) => button.addEventListener("click", () => openForm(button.dataset.create)));

    $("#modal-close").addEventListener("click", closeModal);
    $("#modal-cancel").addEventListener("click", closeModal);
    $("#modal-backdrop").addEventListener("click", (event) => { if (event.target.id === "modal-backdrop") closeModal(); });
    $("#entity-form").addEventListener("submit", submitModal);

    $("#profile-button").addEventListener("click", openAccount);
    $("#open-profile-portal").addEventListener("click", openProfilePortal);
    $("#account-close").addEventListener("click", closeAccount);
    $("#account-backdrop").addEventListener("click", (event) => { if (event.target.id === "account-backdrop") closeAccount(); });
    $("#account-profile-form").addEventListener("submit", saveAccountProfile);
    $("#account-password-form").addEventListener("submit", saveAccountPassword);
    $("#account-avatar-select").addEventListener("click", () => $("#account-avatar-file").click());
    $("#account-avatar-file").addEventListener("change", () => uploadAccountAvatar($("#account-avatar-file").files?.[0]));
    $("#account-avatar-remove").addEventListener("click", removeAccountAvatar);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") { closeModal(); closeAccount(); closeMatchEvents(); }
    });

    $("#identity-new").addEventListener("click", () => loadThemeIntoEditor(null));
    $("#identity-form").addEventListener("submit", saveIdentity);
    $("#identity-form").addEventListener("reset", () => setTimeout(() => loadThemeIntoEditor(null), 0));

    $("#match-events-close").addEventListener("click", closeMatchEvents);
    $("#match-events-backdrop").addEventListener("click", (event) => { if (event.target.id === "match-events-backdrop") closeMatchEvents(); });
    $("#match-event-form").addEventListener("submit", submitMatchEvent);
    $("#match-event-type").addEventListener("change", syncMatchEventType);
    $("#match-event-team").addEventListener("change", refreshMatchEventPlayerControls);
    $("#match-events-template").addEventListener("click", downloadMatchEventTemplate);
    $("#match-events-finalize").addEventListener("click", finalizeMatchEventAct);
    $("#match-events-import").addEventListener("click", () => $("#match-events-file").click());
    $("#match-events-file").addEventListener("change", () => { const file = $("#match-events-file").files?.[0]; if (file) previewMatchEventImport(file); });
    $("#match-events-import-cancel").addEventListener("click", () => { state.pendingMatchEventImport = null; $("#match-events-import-preview").hidden = true; $("#match-events-import-actions").hidden = true; });
    $("#match-events-import-confirm").addEventListener("click", confirmMatchEventImport);
    $("#save-sport-mode").addEventListener("click", saveSportMode);

    $("#settings-language").addEventListener("change", (event) => {
      applyLanguage(event.target.value);
      showToast(tr("Idioma actualizado"));
    });
    $("#settings-theme").addEventListener("change", (event) => {
      applyTheme(event.target.value);
      showToast(tr("Tema actualizado"));
    });
    $("#settings-reset").addEventListener("click", () => {
      applyTheme("system");
      applyLanguage(systemLanguage());
      showToast("Preferencias restablecidas");
    });
    $("#download-player-template").addEventListener("click", downloadPlayerTemplate);

    ["#import-kind", "#import-season", "#import-competition"].forEach(selector => $(selector).addEventListener("change", () => {
      if (selector === "#import-season") syncImportCompetitions();
      syncImportHelp(); state.importVersion = (state.importVersion || 0) + 1;
      const file = state.pendingImportFile;
      resetPendingImport(); if (file) analyseImport(file);
    }));
    const fileInput = $("#import-file");
    $("#select-import-file").addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => { if (fileInput.files[0]) analyseImport(fileInput.files[0]); });
    const dropzone = $("#dropzone");
    ["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.add("dragover"); }));
    ["dragleave", "drop"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.remove("dragover"); }));
    dropzone.addEventListener("drop", (event) => { const file = event.dataTransfer.files[0]; if (file) analyseImport(file); });
    $("#confirm-import").addEventListener("click", confirmImport);
    $("#cancel-import").addEventListener("click", () => {
      resetPendingImport();
      $("#import-result").hidden = true;
      fileInput.value = "";
      showToast("Importación cancelada");
    });

    bootstrap();
  });
})();
