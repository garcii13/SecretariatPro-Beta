const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('manager_app/app.js','utf8');
const piece = (start,end) => source.slice(source.indexOf(start),source.indexOf(end));

test('international identity survives editing and legacy themes remain clubs', () => {
  const c = {DEFAULT_APPEARANCE:{scoreboard:{},bottom_bar:{},panels:{}},PALETTE_FIELDS:{scoreboard:[],bottom_bar:[],panels:[]},ELEMENT_LABELS:{scoreboard:'Marcador'},state:{session:{workspace:{}}}};
  vm.runInNewContext(piece('  function mergedAppearance(', '  async function loadThemes('),c);
  const flags = {h:'https://assets.test/es.svg',a:'https://assets.test/fi.png'};
  const identity = c.mergedAppearance({team_identity:{international:true,flags}}).team_identity;
  assert.equal(identity.international,true);
  assert.equal(JSON.stringify(identity.flags),JSON.stringify(flags));
  assert.equal(c.mergedAppearance({}).team_identity.international,false);
  assert.equal(c.mergedAppearance({team_identity:{international:'false'}}).team_identity.international,false);
});

test('flag upload sends the original image and persists URLs; retries preserve completed uploads', async () => {
  const file1 = {name:'es.svg',bytes:'original svg'}, file2 = {name:'fi.png',bytes:'original png'};
  const requests = [];
  let failed = false;
  const c = {identityFlagFiles:{h:file1,a:file2}, identityFlags:{}, FormData:class {append(key,value){this[key]=value;}},api:async (url,options) => {
    requests.push({url,options});
    if (options.body.file === file2 && !failed) {failed=true;throw Error('offline');}
    return {url:'https://assets.test/'+options.body.file.name};
  }};
  vm.runInNewContext(piece('  async function uploadIdentityFlags(', '  function renderIdentityCompetitionOptions('),c);
  await assert.rejects(c.uploadIdentityFlags(),/offline/);
  assert.equal(c.identityFlags.h,'https://assets.test/es.svg');
  assert.equal(c.identityFlagFiles.h,undefined);
  await c.uploadIdentityFlags();
  assert.equal(requests.length,3);
  assert.equal(requests[0].options.body.file,file1);
  assert.equal(requests[2].options.body.file,file2);
  assert.equal(c.identityFlags.a,'https://assets.test/fi.png');
  assert.equal(Object.keys(c.identityFlagFiles).length,0);
  assert.ok(requests.every(r => r.url === '/api/assets/upload?asset_kind=team-flags'));
});

test('saving waits for flag uploads before publishing the theme', async () => {
  const events = [],nodes={};
  const c={canWrite:()=>true, $:id=>nodes[id] ||= {}, state:{cache:{}},
    uploadIdentityFlags:async()=>events.push('upload'),identityFormAppearance:()=>({team_identity:{international:true,flags:{h:'https://assets.test/es.svg'}}}),
    api:async (url,options)=>{events.push('save');const data=JSON.parse(options.body).data;assert.equal(data.config.appearance.team_identity.flags.h,'https://assets.test/es.svg');},
    loadThemes:async()=>events.push('refresh'),showToast:()=>{}};
  vm.runInNewContext(piece('  async function saveIdentity(', '  function workspaceSportMode('),c);
  const elements=Object.fromEntries(Object.entries({name:'World Cup',competition_id:'cup',locked:'true',published:'true'}).map(([k,v])=>[k,{value:v}]));
  await c.saveIdentity({preventDefault(){},currentTarget:{elements}});
  assert.deepEqual(events,['upload','save','refresh']);
  assert.equal(nodes['#identity-save'].disabled,false);
});
