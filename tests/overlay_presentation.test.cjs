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
