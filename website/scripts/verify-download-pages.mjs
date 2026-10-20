import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const root = new URL('../', import.meta.url);
const releases = JSON.parse(await readFile(new URL('src/lib/downloads.json', root), 'utf8'));
const redirects = (await readFile(new URL('dist/_redirects', root), 'utf8')).trim().split('\n');
assert.equal(redirects.length, releases.length);
assert.equal(new Set(redirects.map((line) => line.split(' ')[0])).size, releases.length);
for (const release of releases) {
  assert.ok(redirects.includes(`${release.path} ${release.url} 302`));
}

for (const page of ['descargas', 'en/downloads']) {
  const dom = new JSDOM(await readFile(new URL(`dist/${page}/index.html`, root), 'utf8'));
  const document = dom.window.document;
  try {
    assert.equal(document.querySelectorAll('[data-download-card]').length, 2);
    const legacy = document.querySelector('details#legacy');
    assert.ok(legacy);
    assert.match(legacy.querySelector('summary').textContent, /Legacy/);
    assert.equal(legacy.querySelectorAll('[data-platform], [data-download-card]').length, 0);
    for (const release of releases) {
      const links = [...document.querySelectorAll('a[href]')].filter((link) => link.getAttribute('href') === release.path);
      assert.equal(links.length, 1, `${page}: ${release.path}`);
      const link = links[0];
      if (release.channel === 'current') {
        assert.ok(link.closest(`[data-download-card]#${release.product}`));
        assert.equal(link.dataset.platform, release.platform);
        assert.match(link.dataset.meta, /^Beta 11 ·/);
      } else {
        assert.ok(legacy.contains(link));
        assert.match(link.textContent, /Legacy/);
      }
    }
  } finally {
    dom.window.close();
  }
}
console.log('ES/EN downloads verified: current installers, Legacy and direct routes.');
