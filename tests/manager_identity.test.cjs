const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('manager_app/app.js','utf8');
const piece = (start,end) => source.slice(source.indexOf(start),source.indexOf(end));

test('Manager flag preview uses both minimum dimensions and matches the broadcast frame', () => {
  const overlay = {document:{addEventListener(){}}};
  vm.runInNewContext(fs.readFileSync('script.js','utf8')+'\nglobalThis.presentation=OverlayPresentation;',overlay);
  const code = piece('    const syncPreviewFlagWidth = () => {','    $$(".preview-scoreboard .preview-logo").forEach');
  for (const dimensions of [[],[[0,0]],[[200,100],[100,200]],[[150,100],[200,100]],[[100,100],[300,100]],[[50,100],[100,200]]]) {
    let width;
    const images = dimensions.map(([naturalWidth,naturalHeight])=>({naturalWidth,naturalHeight}));
    const context = {$$:()=>images,$:()=>({style:{setProperty:(key,value)=>{assert.equal(key,'--preview-flag-width');width=parseFloat(value);}}})};
    vm.runInNewContext(code+'\nsyncPreviewFlagWidth();',context);
    const expected = overlay.presentation.flagWidth(64,images.map(img=>({width:img.naturalWidth,height:img.naturalHeight})));
    assert.equal(width,expected);
  }
});

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

test('team flag upload preserves originals and completed URLs across a retry', async () => {
  const flag = {name:'es.svg',bytes:'original svg'}, crest = {name:'club.png',bytes:'original crest'};
  const requests = [];
  let failed = false;
  const c = {state:{modal:{files:{flag_url:{file:flag,assetKind:'team-flags'},logo_url:{file:crest,assetKind:'team-logos'}}}}, FormData:class {append(key,value){this[key]=value;}},api:async (url,options) => {
    requests.push({url,options});
    if (options.body.file === crest && !failed) {failed=true;throw Error('offline');}
    return {url:'https://assets.test/'+options.body.file.name};
  }};
  vm.runInNewContext(piece('  async function uploadModalFiles(', '  async function submitModal('),c);
  await assert.rejects(c.uploadModalFiles({}),/offline/);
  assert.equal(c.state.modal.files.flag_url.url,'https://assets.test/es.svg');
  const saved = await c.uploadModalFiles({});
  assert.equal(requests.length,3);
  assert.equal(requests[0].options.body.file,flag);
  assert.equal(requests[0].url,'/api/assets/upload?asset_kind=team-flags');
  assert.equal(requests[2].options.body.file,crest);
  assert.equal(saved.flag_url,'https://assets.test/es.svg');
  assert.equal(saved.logo_url,'https://assets.test/club.png');
});

test('competition preview uses competition metadata and team flags independently of visual themes', () => {
  let selected='international';
  const c={state:{cache:{competitions:[{id:'international',is_international:true},{id:'clubs',is_international:false}],teams:[{id:'home',flag_url:'https://assets.test/es.svg',logo_url:'crest'}]}},$:()=>({get value(){return selected;}})};
  vm.runInNewContext(piece('  function previewCompetitionIdentity(', '  function renderIdentityCompetitionOptions('),c);
  assert.equal(c.previewCompetitionIdentity().international,true);
  assert.equal(c.previewCompetitionIdentity().flags.home,'https://assets.test/es.svg');
  selected='clubs';assert.equal(c.previewCompetitionIdentity().international,false);
  selected='unknown';assert.equal(c.previewCompetitionIdentity().international,false);
});

test('visual publication saves the palette without authoring competition identity', async () => {
  const events = [],nodes={};
  const c={canWrite:()=>true, $:id=>nodes[id] ||= {}, state:{cache:{}},
    identityFormAppearance:()=>({scoreboard:{background:'#112233'}}),
    api:async (url,options)=>{events.push('save');const data=JSON.parse(options.body).data;assert.equal(data.config.appearance.team_identity,undefined);assert.equal(data.config.appearance.scoreboard.background,'#112233');},
    loadThemes:async()=>events.push('refresh'),showToast:()=>{}};
  vm.runInNewContext(piece('  async function saveIdentity(', '  function workspaceSportMode('),c);
  const elements=Object.fromEntries(Object.entries({name:'World Cup',competition_id:'cup',locked:'true',published:'true'}).map(([k,v])=>[k,{value:v}]));
  await c.saveIdentity({preventDefault(){},currentTarget:{elements}});
  assert.deepEqual(events,['save','refresh']);
  assert.equal(nodes['#identity-save'].disabled,false);
});
