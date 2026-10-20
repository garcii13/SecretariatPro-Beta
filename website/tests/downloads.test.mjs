import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { detectInstaller } from '../src/lib/download-platform.mjs';

const releases = JSON.parse(await readFile(new URL('../src/lib/downloads.json', import.meta.url)));
test('only explicit compatible OS and architecture signals select an installer', async () => {
  const cases = [
    [{ userAgent: 'Windows NT 10.0; Win64; x64' }, 'windows-x64'],
    [{ userAgent: 'Windows NT 10.0; Win32' }, null],
    [{ userAgent: 'Windows NT 10.0; ARM64' }, null],
    [{ userAgent: 'Intel Mac OS X 10_15_7', platform: 'MacIntel' }, null],
    [{ userAgent: 'Macintosh', userAgentData: { platform: 'macOS', architecture: 'arm' } }, 'macos-arm64'],
    [{ userAgent: 'Macintosh', userAgentData: { platform: 'macOS', architecture: 'x86', bitness: '64' } }, 'macos-x86_64'],
    [{ userAgent: 'Macintosh', platform: 'MacIntel', maxTouchPoints: 5 }, null],
    [{ userAgent: 'iPhone; CPU iPhone OS 18 like Mac OS X' }, null],
    [{ userAgent: 'Linux x86_64' }, null],
    [{ userAgent: 'Windows', userAgentData: { async getHighEntropyValues() { return { platform: 'Windows', architecture: 'x86', bitness: '64' }; } } }, 'windows-x64'],
    [{ userAgent: 'Macintosh', userAgentData: { async getHighEntropyValues() { throw new Error('Denied'); } } }, null]
  ];
  for (const [navigator, expected] of cases) assert.equal(await detectInstaller(navigator), expected, JSON.stringify(navigator));
});

test('catalog covers both products and three platforms with pinned release files and hashes', () => {
  assert.equal(releases.length, 12);
  assert.equal(new Set(releases.map((r) => r.path)).size, 12);
  for (const r of releases) {
    assert.match(r.url, /^https:\/\/github.com\/garcii13\/SecretariatPro-Beta\/releases\/download\//);
    assert.ok(r.url.endsWith(r.file)); assert.match(r.sha256, /^[a-f0-9]{64}$/);
    assert.ok(r.bytes > 10_000_000); assert.ok(['live', 'manager'].includes(r.product));
    assert.ok(['current', 'legacy'].includes(r.channel));
    assert.ok(r.file.includes(r.version));
    assert.ok(r.url.includes(`/${r.product}-v${r.version}/`));
  }
  for (const product of ['live', 'manager']) {
    const current = releases.filter((r) => r.product === product && r.channel === 'current');
    const legacy = releases.filter((r) => r.product === product && r.channel === 'legacy');
    assert.equal(current.length, 3); assert.equal(legacy.length, 3);
    assert.deepEqual(new Set(current.map((r) => r.platform)), new Set(['windows-x64', 'macos-arm64', 'macos-x86_64']));
    for (const r of current) {
      assert.equal(r.version, '1.0.0-beta.11');
      assert.equal(r.path, `/download/${product}/${r.platform}`);
    }
    for (const r of legacy) {
      assert.equal(r.path, `/download/legacy/${product}/${r.version}/${r.platform}`);
      assert.notEqual(r.version, '1.0.0-beta.11');
    }
  }
});

test('download enhancement preserves a manual choice made before detection finishes', async (t) => {
  const dom = new JSDOM(`<div data-downloads data-lang="es"><p data-detection-status></p>
    <article data-download-card><div data-download-picker hidden><select><option value=""></option><option value="windows-x64">Windows</option><option value="macos-arm64">Mac</option></select>
    <a data-download-main hidden></a><p data-download-meta></p></div>
    ${releases.filter((r) => r.product === 'live' && r.channel === 'current').map((r) => `<a data-platform="${r.platform}" href="${r.path}" data-meta="${r.version}">Download</a>`).join('')}</article></div>`, {
    url: 'https://example.invalid/descargas', runScripts: 'outside-only'
  });
  t.after(() => dom.window.close());
  let finish;
  Object.defineProperty(dom.window.navigator, 'userAgentData', { value: { getHighEntropyValues: () => new Promise((resolve) => { finish = resolve; }) } });
  const output = await build({ entryPoints: [new URL('../src/scripts/downloads.ts', import.meta.url).pathname], bundle: true, write: false, format: 'iife' });
  dom.window.eval(output.outputFiles[0].text);
  const select = dom.window.document.querySelector('select'); select.value = 'macos-arm64';
  select.dispatchEvent(new dom.window.Event('change'));
  finish({ platform: 'Windows', architecture: 'x86', bitness: '64' });
  await new Promise((resolve) => setTimeout(resolve, 10));
  const link = dom.window.document.querySelector('[data-download-main]');
  assert.equal(link.pathname, '/download/live/macos-arm64'); assert.equal(link.hidden, false);
  assert.equal(dom.window.document.querySelector('[data-download-meta]').textContent, '1.0.0-beta.11');
  assert.equal(dom.window.document.querySelectorAll('a[data-platform][href]').length, 3);
  select.value = ''; select.dispatchEvent(new dom.window.Event('change'));
  assert.equal(link.hasAttribute('href'), false); assert.equal(link.hidden, true);
});
