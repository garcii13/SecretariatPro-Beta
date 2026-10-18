import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../../', import.meta.url));
const inputs = ['script.js','styles.css','overlay_cinematic.css','overlay-studio.html',
  'broadcast_renderer/package.json','broadcast_renderer/package-lock.json','broadcast_renderer/tsconfig.json',
  'broadcast_renderer/vite.config.ts','broadcast_renderer/scripts/manifest.mjs'];
function walk(folder) {
  for (const entry of readdirSync(path.join(root,folder),{withFileTypes:true})) {
    const name = `${folder}/${entry.name}`;
    if (entry.isDirectory()) walk(name); else inputs.push(name);
  }
}
walk('broadcast_renderer/src');
const dependencyRoot = path.join(root,'broadcast_renderer/node_modules');
const svelteLicense = readFileSync(path.join(dependencyRoot,'svelte/LICENSE.md'),'utf8');
const gsapBanner = readFileSync(path.join(dependencyRoot,'gsap/gsap-core.js'),'utf8').match(/\/\*![\s\S]*?\*\//)[0];
const cssBanner = readFileSync(path.join(dependencyRoot,'gsap/CSSPlugin.js'),'utf8').match(/\/\*![\s\S]*?\*\//)[0];
writeFileSync(path.join(root,'overlay_studio/THIRD_PARTY_NOTICES.txt'),`Svelte\n\n${svelteLicense}\n\nGSAP\n\n${gsapBanner}\n\n${cssBanner}\n`);
const sha = name => createHash('sha256').update(readFileSync(path.join(root,name))).digest('hex');
const sources = Object.fromEntries(inputs.sort().map(name => [name,sha(name)]));
const assets = Object.fromEntries(['studio.js','studio.css','THIRD_PARTY_NOTICES.txt'].map(name => [name,sha(`overlay_studio/${name}`)]));
writeFileSync(path.join(root,'overlay_studio/manifest.json'),JSON.stringify({ renderer:'svelte-svg-gsap',sources,assets },null,2)+'\n');
