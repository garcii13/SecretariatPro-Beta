const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function fixture(fetch) {
  const visible = new Set();
  const image = { classList: { add: x => visible.add(x), remove: x => visible.delete(x) },
    removeAttribute() { this.src = ''; }, decode: async () => {} };
  const empty = { hidden: false }, status = { textContent: '' }, errors = [];
  let ready = 0, revoked = 0;
  const context = { window: {}, fetch, AbortController, setTimeout, clearTimeout,
    URL: { createObjectURL: blob => `blob:${blob.name}`, revokeObjectURL: () => revoked++ } };
  vm.runInNewContext(fs.readFileSync('webapp/ocr_preview.js', 'utf8'), context);
  const controller = new context.window.OCRPreviewController({image, empty, status,
    onReady: () => ready++, onError: message => errors.push(message)});
  return {controller, image, empty, status, errors, visible, ready: () => ready, revoked: () => revoked};
}
const response = name => ({ok: true, blob: async () => ({type: 'image/jpeg', name})});

test('preview displays the server permission error instead of hiding it', async () => {
  const f = fixture(async () => ({ok: false, status: 503, json: async () => ({detail: 'macOS denegó el permiso de captura'})}));
  assert.equal(await f.controller.load('/preview', 'Ventana'), false);
  assert.equal(f.status.textContent, 'macOS denegó el permiso de captura');
  assert.equal(f.visible.size, 0);
  assert.equal(f.empty.hidden, false);
  assert.equal(f.errors.length, 1);
});
test('decoded preview becomes visible and enables ROI layout', async () => {
  const f = fixture(async () => response('camera'));
  assert.equal(await f.controller.load('/camera', 'Cámara'), true);
  assert.equal(f.image.src, 'blob:camera');
  assert.ok(f.visible.has('is-visible'));
  assert.equal(f.empty.hidden, true);
  assert.equal(f.ready(), 1);
  f.controller.reset();
  assert.equal(f.revoked(), 1);
  assert.equal(f.visible.size, 0);
});
test('late old source cannot replace the new preview or its status', async () => {
  let finishOld;
  const f = fixture(url => url === '/old' ? new Promise(resolve => { finishOld = resolve; }) : Promise.resolve(response('new')));
  const old = f.controller.load('/old', 'Vieja');
  assert.equal(await f.controller.load('/new', 'Nueva'), true);
  finishOld(response('old'));
  assert.equal(await old, false);
  assert.equal(f.image.src, 'blob:new');
  assert.equal(f.status.textContent, 'Nueva');
  assert.equal(f.errors.length, 0);
});
test('source change clears preview even if an old request ignores cancellation', async () => {
  let finish;
  const f = fixture(() => new Promise(resolve => { finish = resolve; }));
  const pending = f.controller.load('/old', 'Vieja');
  f.controller.reset('Otra fuente seleccionada');
  finish(response('old'));
  assert.equal(await pending, false);
  assert.equal(f.status.textContent, 'Otra fuente seleccionada');
  assert.equal(f.visible.size, 0);
  assert.equal(f.ready(), 0);
});

test('status refresh preserves preview errors and an unsaved source selection', () => {
  const source = fs.readFileSync('webapp/app.js', 'utf8');
  const render = source.slice(source.indexOf('function renderOCR('), source.indexOf('\nfunction renderEvents('));
  const nodes = new Map();
  const $ = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {textContent: '', value: '', options: []});
    return nodes.get(selector);
  };
  $('#ocr-current-window').textContent = 'macOS denegó el permiso';
  $('#ocr-window').value = 'camera:1';
  $('#ocr-window').options = [{value: 'window:5'}, {value: 'camera:1'}];
  const context = {$, app: {ocrDirty: true, snapshot: {}}, previewController: {}, document: {activeElement: null},
    ocrSourceKey: c => `${c.source_type}:${c.source_id}`, updateOCRPerspectiveHelp() {}, updateOCRReadingMeta() {}, drawOCRRegions() {}};
  vm.runInNewContext(render, context);
  context.renderOCR({source_type: 'window', source_id: '5', source_label: 'Anterior'}, {running: true, error: 'Sin imagen'});
  assert.equal($('#ocr-current-window').textContent, 'macOS denegó el permiso');
  assert.equal($('#ocr-window').value, 'camera:1');
  assert.equal($('#ocr-runtime-copy').textContent, 'OCR con incidencia');
  assert.equal($('#ocr-runtime-dot').className, 'is-error');
});
