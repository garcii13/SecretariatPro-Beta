const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {document: {addEventListener() {}}};
vm.runInNewContext(fs.readFileSync('script.js', 'utf8') + '\nglobalThis.presentation = OverlayPresentation;', context);
const p = context.presentation;

test('goal word follows all six Live languages', () => {
  for (const [language, word] of Object.entries({es:'GOL',en:'GOAL',sv:'MÅL',cs:'GÓL',fi:'MAALI',de:'TOR',unknown:'GOAL'})) assert.equal(p.goalWord(language), word);
});
test('both flags share one capped visible width and fit vertically without distortion', () => {
  for (const ratios of [[1.5,2], [1,2], [0.7,1.5], [3,4], [1.6,1.666]]) {
    const width = p.flagWidth(94, ratios);
    assert.ok(width <= 141);
    for (const ratio of ratios) assert.ok(width / ratio <= 94);
  }
  assert.equal(p.flagWidth(94,[1.5,2]),141);
  assert.equal(p.flagWidth(94,[1,2]),94);
});
test('published flags reach every team graphic while club assets stay intact', () => {
  const source = {team1:{id:'h',logo:'home-crest'},team2:{id:'a',logo:'away-crest'},bottombar:{team_key:'team2',team_logo:'away-crest'},statistics:{lineups:{team1_logo:'home-crest',team2_logo:'away-crest'},top_scorers:{team1:{team_logo:'home-crest'},team2:{team_logo:'away-crest'}},player_profile:{team_key:'team1',team_logo:'home-crest'}}};
  const original = JSON.stringify(source);
  const result = p.withFlags(source,{international:true,flags:{h:'home-flag',a:'away-flag'}});
  assert.equal(result.team1.logo,'home-flag');
  assert.equal(result.team2.logo,'away-flag');
  assert.equal(result.bottombar.team_logo,'away-flag');
  assert.equal(result.statistics.player_profile.team_logo,'home-flag');
  assert.equal(result.statistics.lineups.team2_logo,'away-flag');
  assert.equal(result.statistics.top_scorers.team1.team_logo,'home-flag');
  assert.equal(JSON.stringify(source),original);
  assert.equal(p.withFlags(source,{international:false}),source);
  assert.equal(p.withFlags(source,{international:true,flags:{}}).team1.logo,'home-crest');
});


test('goal phases seek server timing and keep the overlay through the handoff', () => {
  const intro=p.goalPhase({phase:'GOAL_INTRO',generation:4,started_at:100,duration_seconds:2.2},true,100.8);
  assert.equal(intro.overlay,true);assert.equal(intro.reveal,false);
  assert.ok(Math.abs(intro.elapsed-.8)<.0001);
  const reveal=p.goalPhase({phase:'GOAL_REVEAL',generation:4,started_at:102.2,duration_seconds:.64},true,102.4);
  assert.equal(reveal.overlay,true);assert.equal(reveal.reveal,true);
  assert.ok(Math.abs(reveal.elapsed-.2)<.0001);
  assert.equal(p.goalPhase({phase:'GOAL_REVEAL',started_at:100},true,110).elapsed,.64);
  assert.equal(p.goalPhase({phase:'GOAL_BOTTOM'},true).overlay,false);
  assert.equal(p.goalPhase({phase:'GOAL_REVEAL'},false).overlay,false);
  assert.equal(p.goalPhase(null,true).overlay,false);
});

function goalRenderer() {
  const source=fs.readFileSync('script.js','utf8');
  const block=source.slice(source.indexOf('      const goal = OverlayPresentation.goalPhase'),source.indexOf('      const stateTeamColor',source.indexOf('      const goal = OverlayPresentation.goalPhase')));
  const classes=new Set(),properties={},reveals=[];
  let reflows=0;
  const bottomBar={dataset:{},classList:{contains:k=>classes.has(k),remove:(...keys)=>keys.forEach(k=>classes.delete(k)),toggle:(k,on)=>on?classes.add(k):classes.delete(k)},style:{setProperty:(k,v)=>properties[k]=v},get offsetWidth(){reflows++;return 1080;}};
  const c={OverlayPresentation:p,bottomBar,bar:{status:'show'},data:{broadcast_flow:{}},safeGet:()=>({dataset:{}}),overlayLanguage:'es',setTextIfChanged(){},motion:{setVisible(){},revealDetails:(...args)=>reveals.push(args)}};
  vm.runInNewContext(`globalThis.render = () => {${block}};`,c);
  return {c,classes,reveals,reflows:()=>reflows};
}
test('cancelling during the goal intro keeps its curtain during the outro', () => {
  const f=goalRenderer();
  f.c.data.broadcast_flow={phase:'GOAL_INTRO',generation:1};f.c.render();
  assert.equal(f.classes.has('goal-intro'),true);
  f.c.bar.status='hide';f.c.data.broadcast_flow={phase:'BUILDING',generation:2};f.c.render();
  assert.equal(f.classes.has('goal-intro'),true);
  assert.equal(f.reveals.length,0);
});
test('a new goal restarts the ceremony and reveal hands over exactly once', () => {
  const f=goalRenderer();
  f.c.data.broadcast_flow={phase:'GOAL_INTRO',generation:1};f.c.render();
  f.c.data.broadcast_flow={phase:'GOAL_INTRO',generation:2};f.c.render();
  assert.equal(f.reflows(),1);
  f.c.data.broadcast_flow={phase:'GOAL_REVEAL',generation:2};f.c.render();f.c.render();
  assert.equal(f.classes.has('goal-reveal'),true);assert.equal(f.reveals.length,1);
  f.c.data.broadcast_flow={phase:'GOAL_BOTTOM',generation:2};f.c.render();
  assert.equal(f.classes.has('goal-intro'),false);assert.equal(f.reveals.length,1);
});
