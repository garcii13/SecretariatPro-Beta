import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';
import { setTimeout as delay } from 'node:timers/promises';
const root = new URL('../../', import.meta.url);
export const source = name => readFileSync(new URL(name, root), 'utf8');
export function fixture() {
  const player = { number: '9', first_name: 'Ana', last_name: 'García', captain: true, position: 'forward' };
  return {
    animation: { status: 'show' },
    overlay_settings: { language: 'es', score_control: { mode: 'manual' }, appearance: {
      scoreboard: { background: '#25334a', name_box: '#344867', text: '#eff6ff' },
      bottom_bar: { body: '#1c2a40', middle: '#304563', text: '#ffffff', secondary_text: '#bbcddd' },
      panels: { background: '#101d30', surface: '#24374f', accent: '#89abcd', text: '#f1f8ff' },
      period_strip: { enabled: true, show_number: true, segments: 3, labels: ['I','II','III'] },
      elements: { scoreboard: { scale: .9, font: 'Verdana' }, bottom_bar: { scale: 1.1, font: 'Georgia' } },
    } },
    team1: { id: 'home', name: 'Madrid', logo: '/home.svg', stripe_color: '#c42635', text_color: '#ffffff' },
    team2: { id: 'away', name: 'Berlin', logo: '/away.svg', stripe_color: '#185ba8', alternate_text_color: '#ffff00' },
    match: { logo: '/league.svg', league_name: 'Liga', period: 2, sport_mode: 'floorball' },
    bottombar: { status: 'show', team_key: 'team2', team_logo: '/away.svg', team_color: '#185ba8', scorer_number: '9', scorer_last_name: 'García', scorer_match_goals: 2, assistant_number: '12', assistant_last_name: 'Ruiz', graphic_scores: { team1_score: 3, team2_score: 2 } },
    broadcast_flow: { phase: 'GOAL_BOTTOM', generation: 1 },
    powerplay: { team1: { penalties: [{ status: true, id: 'p1', player_number: '14', remaining_seconds: 85 }, { status: true, id: 'p2', player_number: '4', remaining_seconds: 45 }] }, team2: {} },
    empty_net: { team1: true, team2: false },
    penalty_shootout: { status: true, team1: ['goal','miss','goal'], team2: ['miss','goal'] },
    intermission: { status: true, events: [{ type: 'goal', side: 'home', score: '3–2', minute: '15:20', number: '9', last_name: 'García', assistant_number: '12', assistant_last_name: 'Ruiz', powerplay_goal: true }, { type: 'penalty', side: 'away', minute: '15:30', number: '4', last_name: 'Müller', penalty_type: '2' }] },
    prematch: { status: true, venue: 'Palacio', kickoff: '19:30h', team1: { position: 1, points: 24, wins: '8 · 0 · 1', goals_for: 50, goals_against: 21 }, team2: { position: 2, points: 21, wins: '7 · 0 · 2', goals_for: 43, goals_against: 24 } },
    statistics: {
      lineups: { title: 'ALINEACIONES', team1_status: true, team2_status: true, team1_name: 'Madrid', team2_name: 'Berlin', team1_logo: '/home.svg', team2_logo: '/away.svg', team1_color: '#c42635', team2_color: '#185ba8', competition_name: 'Liga', competition_logo: '/league.svg', team1_players: [player], team2_players: [{ ...player, last_name: 'Müller' }], team1_coaches: [{ first_name: 'Luis', last_name: 'Pérez' }], team2_coaches: [], team1_starters: { forward_left: player, goalkeeper: player }, team2_starters: { centre: player } },
      top_scorers: { status: true, competition_name: 'Liga', competition_logo: '/league.svg', team1: { team_name: 'Madrid', team_logo: '/home.svg', player_name: 'García', goals: 18, assists: 7, points: 25 }, team2: { team_name: 'Berlin', team_logo: '/away.svg', player_name: 'Müller', goals: 16, assists: 8, points: 24 } },
      standings: { status: true, competition_name: 'Liga', rows: [{ position: 1, team_name: 'Madrid', played: 9, goal_difference: 29, points: 24 }, { position: 2, team_name: 'Berlin', played: 9, goal_difference: 19, points: 21 }] },
      player_profile: { status: true, team_key: 'team1', team_logo: '/home.svg', team_color: '#c42635', number: '9', name: 'Ana García', birth_date: '2000-01-02', nationality: 'ES', position: 'forward', played: 9, goals: 18, assists: 7 },
    },
  };
}
export async function harness({ legacy = false, state = fixture(), reduced = true, search = '', captureMotion = false } = {}) {
  const errors = [], requests = [], intervals = [];
  const console = new VirtualConsole();
  console.on('error', (...args) => errors.push(args));
  console.on('jsdomError', error => errors.push(error));
  const dom = new JSDOM(source(legacy ? 'overlay.html' : 'overlay-studio.html'), {
    url: `http://localhost:8765/overlay.html${search}`, runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: console,
  });
  const w = dom.window;
  let rendererMotion;
  if (captureMotion) {
    let constructor;
    Object.defineProperty(w,'SPBroadcastMotion',{
      get: () => constructor,
      set: Base => { constructor = class extends Base { constructor(...args) { super(...args); rendererMotion = this; } }; },
      configurable: true,
    });
  }
  let current = structuredClone(state), score = ['3','2','15:20'], reduce = reduced;
  const preferenceListeners = [];
  w.matchMedia = query => ({ get matches() { return query.includes('reduced-motion') ? reduce : false; }, addEventListener: (_, callback) => preferenceListeners.push(callback) });
  w.setInterval = (callback, ms) => { intervals.push({ callback, ms }); return intervals.length; };
  w.fetch = async path => {
    requests.push(String(path));
    let value;
    if (String(path).includes('/api/settings')) value = current.overlay_settings;
    else if (String(path).includes('Home Score.txt')) value = score[0];
    else if (String(path).includes('Away Score.txt')) value = score[1];
    else if (String(path).includes('Time.txt')) value = score[2];
    else value = current;
    const saved = structuredClone(value);
    return { ok: true, json: async () => saved, text: async () => String(saved) };
  };
  if (legacy) {
    w.eval(source('overlay_motion.js'));
    w.eval(source('script.js'));
    w.startSecretariatOverlay();
  } else w.eval(source('overlay_studio/studio.js'));
  const flush = async () => { await delay(35); };
  await flush();
  return { w, errors, requests, intervals, flush, close: () => w.close(),
    get motion() { return rendererMotion; },
    get state() { return current; },
    async update(next, nextScore) { current = structuredClone(next); if (nextScore) score = nextScore; intervals.filter(i => i.ms === 250).forEach(i => i.callback()); await flush(); },
    async reduce(value) { reduce = value; preferenceListeners.forEach(fn => fn()); await flush(); },
  };
}
