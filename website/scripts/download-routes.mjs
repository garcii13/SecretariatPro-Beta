import { readFile, writeFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const releases = JSON.parse(await readFile(new URL('src/lib/downloads.json', root), 'utf8'));
// A direct attachment redirect avoids proxy timeouts for the large installers.
// Never accept an arbitrary upstream URL or put credentials into this file.
const rules = releases.map(({ path, url }) => {
  if (!/^https:\/\/github\.com\/garcii13\/SecretariatPro-Beta\/releases\/download\//.test(url)) {
    throw new Error('Download URL must be a published SecretariatPro release');
  }
  return `${path} ${url} 302`;
});
await writeFile(new URL('public/_redirects', root), rules.join('\n') + '\n');
