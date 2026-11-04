const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context={};vm.runInNewContext(fs.readFileSync('manager_app/federation-i18n.js','utf8'),context);
const {messages,format,languages}=context.SPFederationI18n;
const slots=value=>(value.match(/\{[A-Za-z]+\}/g)||[]).sort();
test('all six SecretariatPro languages cover federation text and retain template parameters',()=>{
 assert.deepEqual(Array.from(languages),['es','en','sv','cs','fi','de']);
 for(const language of languages) {
  assert.deepEqual(Object.keys(messages[language]).sort(),Object.keys(messages.es).sort());
  for(const key of Object.keys(messages.es)) {
   assert(messages[language][key].trim(),`${language}: ${key}`);
   assert.deepEqual(slots(messages[language][key]),slots(key),`${language}: ${key}`);
  }
 }
});
test('federation names and external IDs are data, not translatable labels',()=>{
 for(const language of languages) {
  const name='Svenska Innebandyförbundet · Německý tým <test>';
  assert(format(language,'Espacio de destino: {workspace}',{workspace:name}).endsWith(name));
  const sentence=format(language,'{kind} · {id}: {message}',{kind:{message:'Jugador'},id:'spelar-ID-č-99',message:{message:'Fecha de nacimiento no válida en el catálogo federativo.'}});
  assert(sentence.includes('spelar-ID-č-99'));
  assert(sentence.includes(messages[language]['Fecha de nacimiento no válida en el catálogo federativo.']));
 }
});
test('static federation wizard has translations in all supported languages',()=>{
 const html=fs.readFileSync('manager_app/index.html','utf8').split('<section class="view" id="view-federations">')[1].split('</section>')[0];
 const visible=html.split(/<[^>]+>/).map(s=>s.trim().replace(/\s+/g,' ')).filter(Boolean);
 for(const text of visible)for(const language of languages)assert(messages[language][text],`${language}: ${text}`);
 assert(html.includes('placeholder="Pega aquí tu invitación"'));
 assert(messages.de['Pega aquí tu invitación']);
});
test('switching language renders nested status and dates without changing sporting data',()=>{
 const params={competition:'Tävling 2026/27',state:{message:'Actualización parcial'},cached:12,pending:0,receipt:{message:'Sin entregas confirmadas'}};
 const key='{competition} · {state} · {cached} registros · {pending} envíos pendientes · {receipt}.';
 const original=JSON.stringify(params);
 const outputs=languages.map(language=>format(language,key,params));
 assert.equal(new Set(outputs).size,6);assert.equal(JSON.stringify(params),original);
 assert(outputs.every(s=>s.startsWith('Tävling 2026/27 · ')));
 assert.equal(format('es',key,params),outputs[0]);
 assert(format('fi','Última actualización: {date}',{date:{date:1793790000}}).startsWith('Päivitetty viimeksi:'));
});
