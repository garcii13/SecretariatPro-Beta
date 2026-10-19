import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fixture, harness, source } from './harness.mjs';
import { JSDOM } from 'jsdom';

const panels = ['scoreboard-wrapper','bottom-bar','player-profile-bar','prematch-modal','intermission-modal','lineups-team1-modal','lineups-team2-modal','top-scorers-modal','standings-modal','penalties-modal'];
const byId = (h, id) => h.w.document.getElementById(id);
function snapshot(h, ids) {
  return ids.map(id => {
    const el = byId(h,id);
    assert.ok(el, `Missing ${id}`);
    return { id, text: el.value ?? el.textContent, src: el.getAttribute('src') || null, hidden: el.hidden };
  });
}

test('the compiled Svelte presentation retains every baseline display ID exactly once', async () => {
  const h = await harness();
  try {
    assert.equal(h.w.secretariatStudioReady, true);
    const legacy = new JSDOM(source('overlay.html'));
    for (const node of legacy.window.document.querySelectorAll('[id]')) assert.equal(h.w.document.querySelectorAll(`[id="${node.id}"]`).length, 1, node.id);
    assert.equal(h.intervals.filter(i => i.ms === 250).length, 1);
    h.w.document.dispatchEvent(new h.w.Event('DOMContentLoaded'));
    h.w.startSecretariatOverlay();
    assert.equal(h.intervals.filter(i => i.ms === 250).length, 1, 'startup is idempotent');
    legacy.window.close();
    assert.deepEqual(h.errors, []);
  } finally { h.close(); }
});

test('live content, dynamic islands, all languages and sport formations match the reference renderer', async () => {
  const old = await harness({ legacy: true }), studio = await harness();
  try {
    const legacy = new JSDOM(source('overlay.html'));
    const ids = [...legacy.window.document.querySelectorAll('[id]')].filter(el => !el.children.length).map(el => el.id);
    legacy.window.close();
    for (const language of ['es','en','sv','cs','fi','de']) {
      const state = fixture(); state.overlay_settings.language = language;
      for (const sport of ['floorball','handball']) {
        state.match.sport_mode = sport;
        await old.update(state); await studio.update(state);
        assert.deepEqual(snapshot(studio,ids), snapshot(old,ids), `${language}/${sport}`);
        for (const id of panels) assert.equal(byId(studio,id).dataset.spMotion, 'on', id);
        assert.equal(byId(studio,'lineups-team1-starting').dataset.sportMode, sport);
        assert.equal(studio.w.document.querySelectorAll('#penalties-team1-attempts .penalty-attempt').length, 5);
        assert.equal(studio.w.document.querySelectorAll('#team1-status-stack .sp-status-item').length, 3);
      }
    }
    assert.deepEqual(old.errors, []); assert.deepEqual(studio.errors, []);
  } finally { old.close(); studio.close(); }
});

test('Manager palette, fonts, scales, periods and TXT scoring remain live after publication', async () => {
  const h = await harness();
  try {
    const state = fixture();
    state.overlay_settings.appearance.scoreboard.background = '#eeeeee';
    state.overlay_settings.appearance.bottom_bar = {body:'#25375a',middle:'#436a8c',text:'#ffeedd',secondary_text:'#aaccee'};
    state.overlay_settings.appearance.elements.scoreboard = { scale: 1.25, font: 'Georgia' };
    state.match.period = 3;
    await h.update(state, ['4','2','18:34']);
    assert.equal(h.w.document.documentElement.style.getPropertyValue('--overlay-score-bg'), '#eeeeee');
    const surface = byId(h,'bottom-bar').style;
    assert.equal(surface.getPropertyValue('--bottom-body-color'),'#25375a');
    assert.equal(surface.getPropertyValue('--bottom-middle-color'),'#436a8c');
    assert.equal(surface.getPropertyValue('--bottom-text-color'),'#ffeedd');
    assert.equal(surface.getPropertyValue('--bottom-secondary-color'),'#aaccee');
    assert.match(byId(h,'secretariat-overlay-elements').textContent, /scale: 1.25/);
    assert.match(byId(h,'secretariat-overlay-elements').textContent, /Georgia/);
    assert.equal(h.w.document.querySelector('.team1-score').value, '4');
    assert.equal(byId(h,'match-time').textContent, '18:34');
    assert.equal(byId(h,'period-strip').querySelectorAll('.active').length, 3);
    assert.equal(byId(h,'bottom-current-score').textContent, '3–2', 'goal snapshot stays separate from live OCR/manual scores');
    assert.deepEqual(h.errors, []);
  } finally { h.close(); }
});

test('international flags fill equal minimum-dimension frames in both renderers and club crests stay intact', async () => {
  for (const legacy of [true,false]) {
    const h = await harness({legacy});
    try {
      for (const name of ['styles.css','overlay_cinematic.css',...(!legacy ? ['overlay_studio/studio.css'] : [])]) {
        const style=h.w.document.createElement('style');style.textContent=source(name);h.w.document.head.append(style);
      }
      const state = fixture();
      state.overlay_settings.appearance.team_identity = { international: true, flags: { home: '/home-flag.svg', away: '/away-flag.svg' } };
      const sizes={home:{width:200,height:100},away:{width:100,height:200}};
      for (const [id,key] of [['team1-logo','home'],['team2-logo','away']]) {
        Object.defineProperty(byId(h,id),'naturalWidth',{get:()=>sizes[key].width});
        Object.defineProperty(byId(h,id),'naturalHeight',{get:()=>sizes[key].height});
      }
      await h.update(state);
      assert.equal(byId(h,'scoreboard').style.getPropertyValue('--logo-width'), '94px');
      for (const id of ['team1-logo','team2-logo']) {
        const img=byId(h,id),css=h.w.getComputedStyle(img),box=h.w.getComputedStyle(img.parentElement);
        assert.equal(img.dataset.nationalFlag,'true');
        assert.equal(css.objectFit,'cover');assert.equal(css.objectPosition,'center');
        assert.equal(css.width,'100%');assert.equal(css.height,'100%');
        assert.equal(box.height,'94px');assert.equal(box.padding,'0px');assert.equal(box.overflow,'hidden');
      }
      assert.equal(h.w.getComputedStyle(byId(h,'scoreboard')).gap,'0px');
      assert.equal(byId(h,'team1-logo').getAttribute('src'), '/home-flag.svg');
      assert.equal(byId(h,'team2-logo').getAttribute('src'), '/away-flag.svg');
      assert.equal(byId(h,'bottom-team-logo').getAttribute('src'), '/away-flag.svg');
      assert.equal(state.team1.logo, '/home.svg');
      sizes.home={width:300,height:100};sizes.away={width:400,height:100};
      byId(h,'team2-logo').dispatchEvent(new h.w.Event('load'));
      assert.equal(byId(h,'scoreboard').style.getPropertyValue('--logo-width'),'141px');
      delete state.overlay_settings.appearance.team_identity.flags.home;
      await h.update(state);
      assert.equal(byId(h,'team1-logo').getAttribute('src'),'/home.svg');
      assert.equal(h.w.getComputedStyle(byId(h,'team1-logo')).objectFit,'contain');
      await h.update(fixture());
      assert.equal(byId(h,'team1-logo').getAttribute('src'), '/home.svg');
      assert.equal(byId(h,'scoreboard').style.getPropertyValue('--logo-width'), '');
      assert.deepEqual(h.errors, []);
    } finally { h.close(); }
  }
});

test('Manager edits international mode on the competition and keeps each team flag separate from both crests', () => {
  const dom = new JSDOM(source('manager_app/index.html'), {runScripts:'outside-only'});
  try {
    const text=source('manager_app/app.js');
    const piece=(start,end)=>text.slice(text.indexOf(start),text.indexOf(end));
    dom.window.eval(`const state={cache:{seasons:[]}};
      const tr=value=>value;const escapeHtml=value=>String(value??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
      ${piece('  const forms = {','  function rosterFormConfig(')}
      ${piece('  function normalizeInputValue(','  async function openForm(')}
      ${piece('  function parseForm(','  async function uploadModalFiles(')}
      globalThis.managerFields={forms,fieldHtml,parseForm};`);
    const {forms,fieldHtml,parseForm}=dom.window.managerFields;
    const form=dom.window.document.createElement('form');
    const competitionFields=forms.competition.fields();
    form.innerHTML=competitionFields.map(field=>fieldHtml(field)).join('');
    const toggle=form.elements.namedItem('is_international');
    assert.ok(toggle);assert.match(form.textContent,/Particularidades de la competición/);
    toggle.checked=true;assert.equal(parseForm(form,competitionFields).is_international,true);
    toggle.checked=false;assert.equal(parseForm(form,competitionFields).is_international,false);
    assert.equal(dom.window.document.querySelector('#identity-international'),null);
    assert.ok(dom.window.document.querySelector('#identity-preview-competition'));
    form.innerHTML=forms.team.fields.map(field=>fieldHtml(field)).join('');
    for(const [key,value] of Object.entries({logo_url:'crest',alternate_logo_url:'alternate',flag_url:'https://assets.test/flag.svg'})) form.elements.namedItem(key).value=value;
    const payload=parseForm(form,forms.team.fields);
    assert.equal(payload.logo_url,'crest');assert.equal(payload.alternate_logo_url,'alternate');
    assert.equal(payload.flag_url,'https://assets.test/flag.svg');
    assert.equal(form.querySelector('[data-logo-file="flag_url"]').dataset.assetKind,'team-flags');
  } finally {dom.window.close();}
});

test('queue previews preserve the cue endpoint and every panel clears on hide-all', async () => {
  const h = await harness({ search: '?cue=demo%2F123' });
  try {
    assert.ok(h.requests.some(path => path === '/api/graphics/preview/demo%2F123'));
    const state = fixture();
    state.animation.status = 'hide'; state.bottombar.status = 'hide';
    for (const key of ['prematch','intermission','penalty_shootout']) state[key].status = false;
    state.statistics.lineups.team1_status = state.statistics.lineups.team2_status = false;
    for (const key of ['player_profile','top_scorers','standings']) state.statistics[key].status = false;
    await h.update(state);
    for (const id of panels) assert.equal(byId(h,id).dataset.spMotion,'off',id);
    assert.deepEqual(h.errors, []);
  } finally { h.close(); }
});

test('powerplays retain both teams, multiple penalties, paused clocks, warning state and FIFO removal alongside EMPTY NET', async () => {
  const state = fixture();
  state.powerplay.team2 = { penalties: [{ status: true, id: 'a1', serving_player_number: '22', remaining_seconds: 120 }] };
  const h = await harness({ state });
  try {
    const home = byId(h,'team1-status-stack'), away = byId(h,'team2-status-stack');
    const first = home.querySelector('[data-sp-status-key="penalty:p1"]');
    const second = home.querySelector('[data-sp-status-key="penalty:p2"]');
    assert.equal(first.querySelector('.sp-status-number').textContent,'#14');
    assert.equal(first.querySelector('.sp-status-timer').textContent,'1:25');
    assert.equal(away.querySelector('.sp-status-number').textContent,'#22');
    assert.equal(away.querySelector('.sp-status-timer').textContent,'2:00');
    assert.ok(home.querySelector('[data-sp-status-key="empty-net"]'));
    for (const time of ['15:20','15:20','15:21']) {
      await h.update(state,['3','2',time]);
      assert.equal(first.querySelector('.sp-status-timer').textContent,'1:25','browser never invents penalty elapsed time');
      assert.equal(home.querySelector('[data-sp-status-key="penalty:p1"]'),first,'clock ticks retain the existing node/animation');
    }
    state.powerplay.team1.penalties[1].remaining_seconds = 9;
    await h.update(state);
    assert.ok(second.classList.contains('sp-status-item--ending'));
    assert.equal(second.querySelector('.sp-status-timer').textContent,'0:09');
    state.powerplay.team1.penalties.shift();
    await h.update(state);
    assert.equal(home.children[0],second,'next penalty takes the first queue position');
    assert.equal(home.children[1].dataset.spStatusKey,'empty-net');
    assert.equal(home.dataset.spCount,'2');
    state.powerplay.team1 = {}; state.empty_net.team1=false; state.powerplay.team2={};
    await h.update(state);
    assert.equal(home.children.length,0); assert.equal(away.children.length,0);
    assert.deepEqual(h.errors,[]);
  } finally { h.close(); }
});

test('powerplay queue changes during an exit use the latest order, and a returning penalty cancels removal', async () => {
  const state = fixture(), h = await harness({ state, reduced:false, captureMotion:true });
  try {
    const stack = byId(h,'team1-status-stack');
    const first = stack.querySelector('[data-sp-status-key="penalty:p1"]');
    const saved = structuredClone(state.powerplay.team1.penalties[0]);
    state.powerplay.team1.penalties.shift(); await h.update(state);
    const outgoing = h.motion.statuses.get(first).tween;
    state.powerplay.team1.penalties.push({status:true,id:'p3',player_number:'7',remaining_seconds:120});
    await h.update(state);
    outgoing.progress(1);
    assert.deepEqual([...stack.children].map(node=>node.dataset.spStatusKey),['penalty:p2','penalty:p3','empty-net']);
    state.powerplay.team1.penalties.unshift(saved); await h.update(state);
    const returning = stack.querySelector('[data-sp-status-key="penalty:p1"]');
    state.powerplay.team1.penalties.shift(); await h.update(state);
    const cancelled = h.motion.statuses.get(returning).tween;
    cancelled.progress(.4);
    state.powerplay.team1.penalties.unshift(saved); await h.update(state);
    cancelled.progress(1);
    assert.ok(returning.isConnected);
    assert.equal(returning.dataset.spExiting,'0');
    assert.equal(stack.children[0],returning);
    assert.deepEqual(h.errors,[]);
  } finally { h.motion?.settle();h.close(); }
});

test('startup fallback preserves queue preview parameters and never redirects a healthy renderer', async () => {
  const { runInNewContext } = await import('node:vm');
  const inline = source('overlay-studio.html').match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  for (const ready of [false,true]) {
    let listener, result;
    const context = { URL, window: { secretariatStudioReady: ready }, document: { addEventListener: (_,fn)=>listener=fn },
      location: { href: 'http://localhost:8765/overlay.html?cue=a%2Fb&v=17', search: '?cue=a%2Fb&v=17', replace: url=>result=url } };
    runInNewContext(inline,context); listener();
    if (ready) assert.equal(result,undefined);
    else { assert.equal(result.searchParams.get('cue'),'a/b'); assert.equal(result.searchParams.get('v'),'17'); assert.equal(result.searchParams.get('renderer'),'legacy'); }
  }
});

test('prematch and intermission show complete team names while the scoreboard keeps abbreviations, including older saved matches', async () => {
  const state=fixture();
  state.team1.name='TRC';state.team1.full_name='Club Deportivo Unión de Tres Cantos';
  state.team2.name='ESC';state.team2.full_name='Club Unihockey San Lorenzo de El Escorial';
  const h=await harness({state});
  try {
    const check=(home,away)=>{
      for(const panel of ['prematch','intermission']) {
        assert.equal(byId(h,`${panel}-team1-name`).textContent,home);
        assert.equal(byId(h,`${panel}-team2-name`).textContent,away);
      }
      assert.equal(h.w.document.querySelector('.team1-name').value,'TRC');
      assert.equal(h.w.document.querySelector('.team2-name').value,'ESC');
    };
    check(state.team1.full_name,state.team2.full_name);
    state.team1.full_name='Club Deportivo Tres Cantos Femenino';
    await h.update(state);check(state.team1.full_name,state.team2.full_name);
    delete state.team1.full_name;delete state.team2.full_name;
    state.statistics.lineups.team1_name='Tres Cantos Completo';state.statistics.lineups.team2_name='El Escorial Completo';
    await h.update(state);check('Tres Cantos Completo','El Escorial Completo');
    state.statistics.lineups.team1_name='';state.statistics.lineups.team2_name='';
    await h.update(state);check('TRC','ESC');
    assert.deepEqual(h.errors,[]);
  } finally {h.close();}
});
