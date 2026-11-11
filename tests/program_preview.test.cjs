const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function fixture() {
  const source = fs.readFileSync('webapp/app.js', 'utf8');
  const pending = [], labels = [{textContent: ''}], timers = new Map();
  const images = {};
  for (const id of ['#program-video', '#production-program-video']) {
    images[id] = { dataset: {}, src: '', classList: {add() {}, remove() {}}, removeAttribute() { this.src = ''; } };
  }
  let serial = 0;
  const context = { document: {visibilityState: 'visible'}, AbortController, Date,
    $: id => images[id], $$: () => labels,
    api: (url, options) => new Promise(resolve => pending.push({url, options, resolve})),
    setTimeout: callback => {timers.set(++serial, callback); return serial;},
    clearTimeout: id => timers.delete(id) };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('let programStatusTimer'), source.indexOf('function handleDocumentVisibility')), context);
  return {context, pending, labels, images, timers};
}

const flush = () => new Promise(resolve => setImmediate(resolve));

test('hiding the monitor releases image streams, aborts status polling and cancels retries', async () => {
  const f = fixture();
  f.context.activateProgramMonitor('live');
  assert.match(f.images['#program-video'].src, /program-stream/);
  f.images['#program-video'].onerror();
  assert.equal(f.timers.size, 1);
  f.context.document.visibilityState = 'hidden';
  f.context.activateProgramMonitor('live');
  assert.equal(f.images['#program-video'].src, '');
  assert.equal(f.images['#production-program-video'].src, '');
  assert.equal(f.timers.size, 0);
  assert.equal(f.pending[0].options.signal.aborted, true);
  f.pending[0].resolve({fps: 60, paused: false});
  await flush();
  assert.equal(f.timers.size, 0);
  assert.equal(f.labels[0].textContent, '');
});

test('view changes share one status poll and stale responses cannot overwrite a pause', async () => {
  const f = fixture();
  f.context.activateProgramMonitor('live');
  f.context.activateProgramMonitor('production');
  assert.equal(f.images['#program-video'].src, '');
  assert.match(f.images['#production-program-video'].src, /program-stream/);
  f.pending[1].resolve({fps: 0, paused: true});
  await flush();
  assert.match(f.labels[0].textContent, /⏸/);
  f.pending[0].resolve({fps: 60, paused: false});
  await flush();
  assert.match(f.labels[0].textContent, /⏸/);
  assert.equal(f.timers.size, 1);
});
