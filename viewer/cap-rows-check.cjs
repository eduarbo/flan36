// Directional regression against exported vertices, plus literal configuration persistence.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),THREE=require(path.join(root,'viewer/node_modules/three'));
const out=process.env.FLAN36_CAP_ROWS_OUT||path.join(root,'build/cap-row-fix/browser');
const url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/offline.html');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),clone=x=>JSON.parse(JSON.stringify(x));
const html=fs.readFileSync(path.join(root,'docs/offline.html'));
const packed=html.toString().match(/<script id="scene-data" type="application\/octet-stream">([\s\S]*?)<\/script>/)[1];
const scene=JSON.parse(require('node:zlib').gunzipSync(Buffer.from(packed,'base64')));
for(const [alias,id] of Object.entries(scene.geometryAliases||{}))scene.geometries[alias]=scene.geometries[id];
const geometry=c=>Object.fromEntries(Object.entries(c.keycaps).map(([s,keys])=>[s,Object.fromEntries(Object.entries(keys).map(([k,v])=>[k,{variant:v.variant,rotation_deg:v.rotation_deg}]))]));
const colors=c=>Object.fromEntries(Object.entries(c.keycaps).map(([s,keys])=>[s,Object.fromEntries(Object.entries(keys).map(([k,v])=>[k,v.color]))]));
const rest=c=>{const x=clone(c);delete x.keycaps;return x;};
const errors=[];let browser;
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 browser=await chromium.launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});
 const context=await browser.newContext({viewport:{width:1440,height:960},acceptDownloads:true});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
 async function activate(selector){const e=p.locator(selector);for(const d of await e.locator('xpath=ancestor::details').all())if(await d.getAttribute('open')===null){await d.locator(':scope > summary').focus();await p.keyboard.press('Enter');}await e.focus();await p.keyboard.press('Enter');}
 async function ready(){await p.waitForFunction(()=>document.querySelectorAll('[data-preset]').length===3&&localStorage.getItem('flan36.configuration.v1'),null,{timeout:60000});}
 const saved=async()=>{await p.evaluate(()=>window.flan36.idle());return p.evaluate(()=>JSON.parse(localStorage.getItem('flan36.configuration.v1')));};
 async function download(selector,name){await activate('#nav-files');const event=p.waitForEvent('download');await activate(selector);const d=await event,file=path.join(out,name);await d.saveAs(file);assert.equal(await d.failure(),null);return fs.readFileSync(file);}
 async function imported(c){await activate('#nav-files');await p.locator('#load-config').setInputFiles({name:'caps.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(c))});await p.waitForFunction(()=>document.querySelector('#load-config').value==='');assert.equal(await p.locator('#config-status').getAttribute('data-error'),'false');}
 await p.goto(url+(url.includes('?')?'&':'?')+'diagnostics');await p.waitForFunction(()=>document.querySelector('#status').textContent.includes('visible components'));await p.evaluate(()=>document.querySelector('#default-config').click());await ready();
 assert.equal(await p.evaluate(async()=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(document.querySelector('#scene-data').textContent)))).map(x=>x.toString(16).padStart(2,'0')).join('')),hash(Buffer.from(packed)));
 const initial=await saved(),legacy=clone(initial);
 for(const [side,keys] of Object.entries(legacy.keycaps))for(const [ref,choice] of Object.entries(keys)){
   const k=scene.catalog.layout[side].find(k=>k.ref===ref);
   Object.assign(choice,scene.presets['normal-sculpted'].keycaps[side][ref]);
   if(k.row===0||k.row===2)choice.rotation_deg=(choice.rotation_deg+180)%360;
   choice.color='#'+((k.row+1)*0x123456+(side==='left'?k.col:17)).toString(16).padStart(6,'0');
 }
 // A flat manual exception must survive the repair, unlike reapplying a whole preset.
 legacy.keycaps.left.K02.variant='choc_stem_choc_size_normal';
 legacy.batteries.left='301230';legacy.cases.right.style='rim';legacy.frames.right.style='tv';
 await imported(legacy);const normalized=await saved();
 await p.reload();await ready();assert.deepEqual(await saved(),normalized,'No inferred migration of literal manual choices');
 await activate('#part-keycaps');assert.equal(await p.locator('#fix-cap-rows').textContent(),'Fix top/bottom slopes (19)');
 await p.selectOption('#half','left');await p.selectOption('#view','left');await p.mouse.move(10,10);await p.keyboard.press('Escape');
 await p.locator('#canvas').screenshot({path:path.join(out,'before.png'),style:'.stage-label,#leader-lines{opacity:0!important}'});
 await p.setViewportSize({width:390,height:844});
 await p.locator('#fix-cap-rows').scrollIntoViewIfNeeded();
 const repairBounds=await p.locator('#fix-cap-rows').boundingBox();
 assert(repairBounds.x>=0&&repairBounds.x+repairBounds.width<=390,'Repair control fits mobile width');
 await p.locator('#fix-cap-rows').click();const fixed=await saved(),expected=clone(normalized);
 await p.setViewportSize({width:1440,height:960});
 for(const [side,keys] of Object.entries(scene.catalog.layout))for(const k of keys)if((k.row===0||k.row===2)&&expected.keycaps[side][k.ref].variant.endsWith('_tilted'))expected.keycaps[side][k.ref].rotation_deg=(expected.keycaps[side][k.ref].rotation_deg+180)%360;
 assert.deepEqual(fixed,expected,'Repair changes only nineteen targeted rotations');
 await p.mouse.move(10,10);await p.keyboard.press('Escape');
 await p.locator('#canvas').screenshot({path:path.join(out,'after.png'),style:'.stage-label,#leader-lines{opacity:0!important}'});
 assert(await p.locator('#fix-cap-rows').isHidden());await p.reload();await ready();assert.deepEqual(await saved(),fixed);
 const exported=JSON.parse(await download('#save-config','repaired.json'));assert.deepEqual(exported,fixed);await imported(exported);assert.deepEqual(await saved(),fixed);
 const presets={};
 for(const id of ['normal-sculpted','saddle-sculpted']){
   await activate('#part-keycaps');await activate(`[data-preset="${id}"]`);const config=await saved();
   assert.deepEqual(geometry(config),geometry(scene.presets[id]));assert.deepEqual(colors(config),colors(fixed));assert.deepEqual(rest(config),rest(fixed));
   const glb=await download('#glb',id+'.glb'),length=glb.readUInt32LE(12),gltf=JSON.parse(glb.toString('utf8',20,20+length));
   assert.deepEqual(gltf.nodes.find(n=>n.name==='Flan36 revI · nominal').extras.configuration,config);
   const measurements=[];
   for(const node of gltf.nodes.filter(n=>n.extras?.group==='keycaps')){
     const side=node.extras.side,ref=node.extras.key,key=scene.catalog.layout[side].find(k=>k.ref===ref);
     if(![0,2].includes(key.row))continue;
     const a=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION],v=gltf.bufferViews[a.bufferView];
     assert.equal(a.componentType,5126);assert(!v.byteStride||v.byteStride===12);
     const start=20+length+8+(v.byteOffset||0)+(a.byteOffset||0),bytes=glb.subarray(start,start+a.count*12);
     const variant=scene.catalog.variants.find(v=>v.id===config.keycaps[side][ref].variant);
     assert.deepEqual(bytes,Buffer.from(scene.geometries[variant.path].positions,'base64'));
     const matrix=node.matrix?new THREE.Matrix4().fromArray(node.matrix):new THREE.Matrix4().compose(new THREE.Vector3(...(node.translation||[0,0,0])),new THREE.Quaternion(...(node.rotation||[0,0,0,1])),new THREE.Vector3(...(node.scale||[1,1,1])));
     let outer=-Infinity,inner=-Infinity;
     const direction=key.row===0?-1:1,centerX=key.x+(side==='right'?161:0);
     for(let at=0;at<bytes.length;at+=12){const p=new THREE.Vector3(bytes.readFloatLE(at),bytes.readFloatLE(at+4),bytes.readFloatLE(at+8)).applyMatrix4(matrix);if(Math.abs(p.x-centerX)>=4)continue;const distance=(p.z-key.y)*direction;if(distance>4)outer=Math.max(outer,p.y);if(distance< -4)inner=Math.max(inner,p.y);}
     assert(outer-inner>2.5,`${id}/${side}/${ref}: wrong actual GLB surface direction ${outer-inner}`);
     measurements.push({side,key:ref,outer_above_inner_mm:outer-inner});
   }
   assert.equal(measurements.length,20);presets[id]=measurements;
   await activate('#part-keycaps');await p.locator('#key-presets').screenshot({path:path.join(out,'presets.png')});
   await p.selectOption('#view','left');await p.selectOption('#half','left');await p.mouse.move(10,10);await p.keyboard.press('Escape');
   await p.locator('#canvas').screenshot({path:path.join(out,id+'-side.png'),style:'.stage-label,#leader-lines{opacity:0!important}'});
   await p.selectOption('#half','both');await p.selectOption('#view','iso');
   await p.reload();await ready();assert.deepEqual(await saved(),config,'Preset orientation survives reload');
 }
 assert.deepEqual(errors,[]);
 const result={passed:true,viewer_sha256:hash(html),checker_sha256:hash(fs.readFileSync(__filename)),target:url.startsWith('file:')?'local':'public',actual_glb_surface_measurements:presets,legacy_manual_state_preserved:true,repair_changes_only_19_rotations:true,mobile_repair:true,repair_idempotent:true,colors_and_other_components_preserved:true,json_roundtrip:true,reload:true,runtime_errors:errors};
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');console.log('PASS: 40 GLB surface directions, explicit repair, preserved custom choices, JSON and reload');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();});
