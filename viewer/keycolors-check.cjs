// SPDX-License-Identifier: GPL-3.0-or-later
// Disposable, focused acceptance checks. Run after rebuilding the viewer.
// FLAN36_VIEWER_URL / FLAN36_ROOT / FLAN36_PLAYWRIGHT_MODULE /
// FLAN36_BROWSER / FLAN36_KEYCOLORS_OUT are optional overrides.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=process.env.FLAN36_ROOT||path.resolve(__dirname,'..');
const out=process.env.FLAN36_KEYCOLORS_OUT||path.join(root,'build/keycolors');
const url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/offline.html');
const clone=x=>JSON.parse(JSON.stringify(x));
const colorMap=c=>Object.fromEntries(Object.entries(c.keycaps).map(([side,keys])=>[side,Object.fromEntries(Object.entries(keys).map(([ref,k])=>[ref,k.color]))]));
const geometry=c=>({keycaps:Object.fromEntries(Object.entries(c.keycaps).map(([side,keys])=>[side,Object.fromEntries(Object.entries(keys).map(([ref,k])=>[ref,{variant:k.variant,rotation_deg:k.rotation_deg}]))])),frames:Object.fromEntries(Object.entries(c.frames).map(([s,f])=>[s,f.style])),cases:Object.fromEntries(Object.entries(c.cases).map(([s,v])=>[s,{style:v.style,cover:v.cover}])),batteries:c.batteries});
const checks=[],runtimeErrors=[];
let step='launch',browser;
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 browser=await chromium.launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:960},acceptDownloads:true});
 const p=await context.newPage();p.on('pageerror',e=>runtimeErrors.push(e.message));
 async function openDetails(selector){
  const target=p.locator(selector);
  // XPath returns ancestors in document order: open outer details before inner.
  for(const detail of await target.locator('xpath=ancestor::details').all()){
   if(await detail.getAttribute('open')!==null)continue;
   const summary=detail.locator(':scope > summary');await summary.focus();await summary.press('Enter');
   assert(await detail.getAttribute('open')!==null,'Could not open details containing '+selector);
  }
 }
 async function activate(selector){await openDetails(selector);const e=p.locator(selector);await e.focus();await e.press('Enter');}
 async function ready(){await p.waitForFunction(()=>{try{return Object.values(localStorage).some(v=>{try{return JSON.parse(v)?.schema==='flan36-config-1';}catch{return false;}});}catch{return false;}},null,{timeout:60000});await p.waitForFunction(()=>document.querySelectorAll('[data-cap-key]').length===36,null,{timeout:60000});}
 async function saved(){await p.evaluate(()=>new Promise(requestAnimationFrame));await p.evaluate(()=>window.flan36.idle());return p.evaluate(()=>{for(const value of Object.values(localStorage)){try{const c=JSON.parse(value);if(c?.schema==='flan36-config-1')return c;}catch{}}throw Error('No persisted Flan36 configuration');});}
 async function library(){await p.evaluate(()=>new Promise(requestAnimationFrame));await p.evaluate(()=>window.flan36.idle());return p.evaluate(()=>{for(const value of Object.values(localStorage)){try{const c=JSON.parse(value);if(c?.schema==='flan36-keycap-palettes-1')return c;}catch{}}return null;});}
 async function caps(){await activate('#part-keycaps');}
 async function libraryOpen(){await caps();await openDetails('#cap-palette-name');}
 async function download(selector,filename){const pending=p.waitForEvent('download');await activate(selector);const d=await pending,file=path.join(out,filename);await d.saveAs(file);assert.equal(await d.failure(),null);return fs.readFileSync(file);}
 async function configDownload(filename){await activate('#nav-files');return JSON.parse((await download('#save-config',filename)).toString());}
 async function importConfig(c,name='configuration.json'){await activate('#nav-files');await p.locator('#load-config').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(c))});await p.waitForFunction(()=>document.querySelector('#load-config').value==='');}
 // The self-contained page exceeds Chromium's response-body cache. Read the
 // same source directly instead of relying on the inspector retaining 47 MiB.
 const viewerBytes=url.startsWith('file:')?fs.readFileSync(new URL(url)):Buffer.from(await(await fetch(url)).arrayBuffer());
 const viewerSha=crypto.createHash('sha256').update(viewerBytes).digest('hex');
 await p.goto(url+(url.includes('?')?'&':'?')+'diagnostics');await p.waitForFunction(()=>document.querySelector('#status').textContent.includes('visible components'));await p.evaluate(()=>document.querySelector('#default-config').click());await ready();
 const scene=await p.evaluate(async()=>{const bytes=Uint8Array.from(atob(document.querySelector('#scene-data').textContent),c=>c.charCodeAt(0));return JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());});
 const layout=scene.catalog.layout;
 assert.deepEqual(Object.keys(layout).sort(),['left','right']);
 assert.equal(Object.values(layout).flat().length,36);
 const initial=await configDownload('initial.json');
 assert.equal(Object.values(colorMap(initial)).flatMap(Object.values).length,36);
 assert(Object.values(colorMap(initial)).flatMap(Object.values).every(c=>/^#[0-9a-f]{6}$/i.test(c)));
 checks.push('36 normalized key colors in exported configuration');

 // Expected sets derive directly from layout metadata, independently of the UI resolver.
 function wanted(side,mode,value){return Object.entries(layout).flatMap(([s,keys])=>keys.filter(k=>(side==='both'||s===side)&&(mode==='all'||mode==='row'&&k.row===value||mode==='column'&&k.row!==3&&k.col===value||mode==='key'&&k.ref===value)).map(k=>[s,k.ref]));}
 async function select(side,mode,value){await caps();await activate(`#cap-side [data-side="${side}"]`);await p.selectOption('#cap-mode',mode);if(mode==='row')await p.selectOption('#cap-row',String(value));if(mode==='column')await p.selectOption('#cap-column',String(value));if(mode==='key')await activate(`[data-cap-side="${side}"][data-cap-key="${value}"]`);}
 async function paint(side,mode,value,color){
  step=`paint ${side}/${mode}/${value??''}`;const before=await saved(),expected=clone(before),targets=wanted(side,mode,value);
  await select(side,mode,value);
  const selected=await p.locator('[data-cap-key][aria-pressed="true"]').evaluateAll(es=>es.map(e=>[e.dataset.capSide,e.dataset.capKey]));
  assert.deepEqual(selected.map(x=>x.join(':')).sort(),targets.map(x=>x.join(':')).sort(),step+' selected set');
  assert((await p.locator('#cap-selection').textContent()).startsWith(String(targets.length)+' '),step+' count');
  await p.locator('#cap-color').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));},color);
  for(const [s,ref] of targets)expected.keycaps[s][ref].color=color;
  assert.deepEqual(await saved(),expected,step+' must change only intended colors');checks.push(step);return expected;
 }
 await paint('both','all',null,'#19334f');
 await paint('left','all',null,'#c54e68');
 await paint('right','all',null,'#57a383');
 for(const [side,row,color] of [['both',0,'#a153cc'],['left',1,'#d4b56a'],['right',2,'#325dcc'],['both',3,'#dc804b']])await paint(side,'row',row,color);
 for(const [side,col,color] of [['both',1,'#db3377'],['left',3,'#3377dd'],['right',5,'#77dd33']])await paint(side,'column',col,color);
 for(const [side,color] of [['left','#992211'],['right','#119922']])await paint(side,'key',layout[side].find(k=>k.row===1).ref,color);
 const painted=await saved();
 assert(layout.left.filter(k=>k.row===3).every(k=>painted.keycaps.left[k.ref].color==='#dc804b'));
 assert(layout.right.filter(k=>k.row===3).every(k=>painted.keycaps.right[k.ref].color==='#dc804b'));
 checks.push('columns exclude every thumb on both halves');
 const mapPaint=await p.locator('[data-cap-key]').evaluateAll(es=>es.map(e=>({side:e.dataset.capSide,key:e.dataset.capKey,rgb:getComputedStyle(e).backgroundColor})));
 for(const item of mapPaint){const hex=painted.keycaps[item.side][item.key].color;assert.equal(item.rgb,`rgb(${[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)).join(', ')})`,'Selected map keys must show their actual color');}
 checks.push('selected key map displays actual colors');

 step='geometry preset preserves all colors';await caps();
 const currentGeometry=geometry(painted).keycaps;
 const preset=Object.keys(scene.presets).find(id=>JSON.stringify(geometry({...painted,keycaps:scene.presets[id].keycaps}).keycaps)!==JSON.stringify(currentGeometry));
 assert(preset,'Need a geometrically different available preset');
 await activate(`#key-presets [data-preset="${preset}"]`);const sculpted=await saved();
 assert.deepEqual(colorMap(sculpted),colorMap(painted));
 assert.notDeepEqual(geometry(sculpted).keycaps,currentGeometry);
 assert.deepEqual(geometry(sculpted).keycaps,geometry({...sculpted,keycaps:scene.presets[preset].keycaps}).keycaps);
 checks.push(step);

 step='global themes color caps and preserve every selected geometry';await activate('#nav-themes');
 await activate('#theme-target [data-side="both"]');
 const themeIds=await p.locator('[data-theme]').evaluateAll(es=>es.map(e=>e.dataset.theme));assert(themeIds.length>=2);
 await activate(`[data-theme="${themeIds[0]}"]`);const themed=await saved();
 assert.deepEqual(geometry(themed),geometry(sculpted));assert.notDeepEqual(colorMap(themed),colorMap(sculpted));
 assert(Object.values(colorMap(themed)).flatMap(Object.values).every(c=>/^#[0-9a-f]{6}$/i.test(c)));
 await activate('#theme-target [data-side="left"]');await activate(`[data-theme="${themeIds[1]}"]`);const halfTheme=await saved();
 assert.deepEqual(geometry(halfTheme),geometry(sculpted));assert.deepEqual(halfTheme.keycaps.right,themed.keycaps.right);assert.notDeepEqual(colorMap(halfTheme).left,colorMap(themed).left);checks.push(step);

 const beforeDedicated=await paint('right','all',null,'#032649');
 step='dedicated cap palette honors half and preserves geometry';await caps();await activate('#cap-side [data-side="right"]');
 const capPalette=await p.locator('[data-cap-palette]').first().getAttribute('data-cap-palette');assert(capPalette);
 await activate(`[data-cap-palette="${capPalette}"]`);const dedicated=await saved();
 assert.deepEqual(geometry(dedicated),geometry(beforeDedicated));assert.deepEqual(dedicated.keycaps.left,beforeDedicated.keycaps.left);assert.notDeepEqual(colorMap(dedicated).right,colorMap(beforeDedicated).right);checks.push(step);

 step='save custom palette and reload';await paint('left','key',layout.left.find(k=>k.row===0).ref,'#1a2b3c');
 const personal=await saved();await libraryOpen();await p.fill('#cap-palette-name','Acceptance palette');await activate('#save-cap-palette');
 const savedLibrary=await library();assert.equal(savedLibrary.palettes.length,1);assert.equal(savedLibrary.palettes[0].name,'Acceptance palette');assert.deepEqual(savedLibrary.palettes[0].colors,colorMap(personal));
 await p.reload();await ready();assert.deepEqual(await saved(),personal);assert.deepEqual(await library(),savedLibrary);await libraryOpen();assert.equal(await p.locator('[data-custom-cap-palette]').count(),1);checks.push(step);
 await paint('both','all',null,'#aabbcc');await libraryOpen();await activate('#cap-side [data-side="both"]');await activate('[data-custom-cap-palette="0"]');assert.deepEqual(await saved(),personal);checks.push('custom palette restores all 36 colors without geometry changes');

 step='palette export and valid import';await libraryOpen();const exported=JSON.parse((await download('#export-cap-palettes','personal-palettes.json')).toString());assert.deepEqual(exported,savedLibrary);
 const imported=clone(exported);imported.palettes[0].name='Imported palette';
 for(const side of ['left','right'])for(const ref of Object.keys(imported.palettes[0].colors[side]))imported.palettes[0].colors[side][ref]=side==='left'?'#aa3377':'#33aa77';
 await libraryOpen();await p.locator('#cap-palette-file').setInputFiles({name:'valid-palettes.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))});await p.waitForFunction(()=>document.querySelector('#cap-palette-file').value==='');
 assert.deepEqual(await saved(),personal,'Importing a palette must not apply it');
 assert.equal((await library()).palettes.length,2);assert.equal(await p.locator('[data-custom-cap-palette]').count(),2);
 await activate('[data-custom-cap-palette="1"]');const appliedImported=await saved();assert.deepEqual(colorMap(appliedImported),imported.palettes[0].colors);assert.deepEqual(geometry(appliedImported),geometry(personal));checks.push(step);

 step='invalid palette import is atomic across collection and keyboard';const priorLibrary=await library(),badPalette=clone(imported);
 badPalette.palettes.unshift(clone(imported.palettes[0]));badPalette.palettes[1].colors.right[layout.right[0].ref]='#nothex';
 await libraryOpen();await p.locator('#cap-palette-file').setInputFiles({name:'invalid-palettes.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(badPalette))});await p.waitForFunction(()=>document.querySelector('#cap-palette-file').value==='');
 assert.equal(await p.locator('#config-status').getAttribute('data-error'),'true');assert.deepEqual(await library(),priorLibrary);assert.equal(await p.locator('[data-custom-cap-palette]').count(),2);assert.deepEqual(await saved(),appliedImported);checks.push(step);

 step='36 distinct colors survive configuration import/export';const distinct=clone(appliedImported);let sequence=0;
 for(const side of ['left','right'])for(const k of layout[side])distinct.keycaps[side][k.ref].color='#'+(0x234567+sequence++*0x030207).toString(16).padStart(6,'0');
 assert.equal(new Set(Object.values(colorMap(distinct)).flatMap(Object.values)).size,36);
 await importConfig(distinct);assert.deepEqual(await saved(),distinct);assert.deepEqual(await configDownload('distinct-colors.json'),distinct);checks.push(step);
 step='invalid keycap color import is atomic';const badConfig=clone(distinct);badConfig.keycaps.right[layout.right[0].ref].color='red';await importConfig(badConfig,'bad-key-color.json');
 assert.equal(await p.locator('#config-status').getAttribute('data-error'),'true');assert.deepEqual(await saved(),distinct);assert.deepEqual(await configDownload('after-invalid-config.json'),distinct);checks.push(step);

 step='GLB contains exact 36 configured colors';await activate('#nav-files');const bytes=await download('#glb','distinct-colors.glb');
 assert.equal(bytes.toString('ascii',0,4),'glTF');assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);assert.equal(bytes.readUInt32LE(16),0x4e4f534a);
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));const assembly=gltf.nodes.find(n=>n.extras?.configuration);assert(assembly);assert.deepEqual(assembly.extras.configuration,distinct);
 const nodes=gltf.nodes.filter(n=>n.extras?.group==='keycaps');assert.equal(nodes.length,36);const seen=new Set();
 const linear=h=>{const v=parseInt(h,16)/255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4);};
 for(const n of nodes){const {side,key}=n.extras,id=side+':'+key;assert(!seen.has(id));seen.add(id);assert(distinct.keycaps[side]?.[key],id);const chosen=distinct.keycaps[side][key],expected=[1,3,5].map(i=>linear(chosen.color.slice(i,i+2)));assert.equal(n.extras.variant,chosen.variant);assert.equal(n.extras.cap_rotation_deg,chosen.rotation_deg);for(const primitive of gltf.meshes[n.mesh].primitives){const actual=gltf.materials[primitive.material].pbrMetallicRoughness.baseColorFactor;assert(actual,id+' missing material color');expected.forEach((v,i)=>assert(Math.abs(actual[i]-v)<1e-5,id+' RGB channel '+i));assert.equal(actual[3],1);}}
 assert.deepEqual([...seen].sort(),Object.entries(layout).flatMap(([s,ks])=>ks.map(k=>s+':'+k.ref)).sort());checks.push(step);

 step='final reload matches exported configuration and palette collection';await p.reload();await ready();assert.deepEqual(await saved(),distinct);assert.deepEqual(await library(),priorLibrary);checks.push(step);
 assert.deepEqual(runtimeErrors,[]);
 const report={target:process.env.FLAN36_VIEWER_URL?'provided URL':'local generated viewer',viewer_sha256:viewerSha,checks,keycaps:36,distinct_glb_colors:36,glb_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),runtime_errors:runtimeErrors};
 fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));await context.close();
})().catch(error=>{console.error('Failed at:',step);console.error(error);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
