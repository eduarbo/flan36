// SPDX-License-Identifier: GPL-3.0-or-later
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {Script} from 'node:vm';
import {build} from 'esbuild';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.dirname(here);
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const scene=JSON.parse(fs.readFileSync(path.join(root,'build/viewer-scene.json'),'utf8'));
for(const item of scene.sources)if(hash(item.path)!==item.sha256)throw Error(`Stale input: ${item.path}`);
const bundle=await build({entryPoints:[path.join(here,'app.js')],bundle:true,write:false,minify:true,
  format:'iife',target:['es2020'],legalComments:'inline'});
const license=fs.readFileSync(path.join(here,'node_modules/three/LICENSE'),'utf8');
fs.writeFileSync(path.join(root,'LICENSES/Three-MIT.txt'),license);
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const licenses=['LICENSE','LICENSES/CC-BY-SA-4.0.txt','LICENSES/Three-MIT.txt','LICENSES/fflate-MIT.txt','components/sources/KiSwitch-MIT.txt'].map(p=>`<h3>${p}</h3><pre>${escape(fs.readFileSync(path.join(root,p),'utf8'))}</pre>`).join('');
const credits=`<p>Flan36: Eduardo Ruiz. CAD derived from Piantor (beekeeb, GPL-3.0). KLP Lamé by braindefender, CC-BY-SA-4.0, commit 4a67a824232d3054c61599ea047c56a340faaba2; unchanged meshes, placed and colored. KiSwitch Choc v1: MIT; KiCad component models: CC-BY-SA-4.0 with library exception. See the component guide for per-file provenance. Three.js 0.180.0: MIT. Source code and full notices: <a href="https://github.com/eduarbo/flan36">github.com/eduarbo/flan36</a>.</p>`;
const template=fs.readFileSync(path.join(here,'template.html'),'utf8');
const html=template.replace('/*__STYLE__*/',()=>fs.readFileSync(path.join(here,'style.css'),'utf8'))
  .replace('<!--__LICENSES__-->',()=>credits+licenses)
  .replace('/*__DATA__*/',()=>gzipSync(Buffer.from(JSON.stringify(scene)),{level:9}).toString('base64'))
  .replace('/*__APP__*/',()=>bundle.outputFiles[0].text.replaceAll('</script','<\\/script'))
  .replaceAll('\r\n','\n');
new Script([...html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)[1]);
fs.writeFileSync(path.join(root,'docs/index.html'),html);
fs.writeFileSync(path.join(root,'docs/.nojekyll'),'');
const sources=[...scene.sources,...['viewer/app.js','viewer/config.js','viewer/storage.js','viewer/keycap-colors.js','viewer/color-input.js','design/keycap-themes.json','viewer/appearance.js','viewer/printing.js','design/themes.json','viewer/explorer.js','viewer/previews.js','viewer/finishes.js','design/frame-finishes.json','design/frame-extensions.json','viewer/style.css','viewer/template.html','viewer/build.mjs','viewer/package-lock.json'].map(p=>({path:p,sha256:hash(p)}))];
const receipt={revision:scene.revision,units:'mm',objects:scene.parts.length,unique_meshes:Object.keys(scene.geometries).length,
  keycaps:scene.parts.filter(p=>p.group==='keycaps').length,geometry_changed:false,
  sources,viewer_sha256:hash('docs/index.html'),measurements:scene.measurements,
  offline:'All geometry, scripts, styles and license notices embedded; external links only open on explicit click.',
  limitations:scene.limits};
fs.writeFileSync(path.join(root,`validation/rev${scene.revision}-viewer.json`),JSON.stringify(receipt,null,2)+'\n');
console.log(`Self-contained viewer: ${(Buffer.byteLength(html)/1048576).toFixed(2)} MiB; ${scene.parts.length} objects.`);
