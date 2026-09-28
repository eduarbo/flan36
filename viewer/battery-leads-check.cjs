// Exact battery/connected-lead profile switching in isolated headless Chromium.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),zlib=require('node:zlib'),crypto=require('node:crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/slim-flush/battery-viewer');fs.mkdirSync(out,{recursive:true});
const html=fs.readFileSync(path.join(root,'docs/index.html'),'utf8');
const scene=JSON.parse(zlib.gunzipSync(Buffer.from(html.match(/<script id="scene-data" type="application\/octet-stream">([\s\S]*?)<\/script>/)[1],'base64')));
const expectedCount=scene.parts.length;
const url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/index.html');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:960},acceptDownloads:true}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));if(url.startsWith('file:'))await context.route(/^https?:/,r=>r.abort());
  await page.goto(url);await page.waitForFunction(n=>document.querySelector('#status').textContent.includes(`${n} visible components`),expectedCount,{timeout:60000});
  const cases=[{name:'adafruit',profiles:{left:'adafruit-1570',right:'adafruit-1570'}},{name:'301230',profiles:{left:'301230',right:'301230'}},{name:'mixed',profiles:{left:'301230',right:'adafruit-1570'}}];
  const checked=[];
  for(const c of cases){
   if(c.name==='mixed'){
    const cfg=structuredClone(scene.catalog.default_configuration);cfg.batteries=c.profiles;
    await page.click('#nav-files');await page.locator('#load-config').setInputFiles({name:'mixed.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(cfg))});
    assert.equal(await page.locator('#config-status').getAttribute('data-error'),'false');
   }else{
    await page.click('#part-battery');await page.click(`[data-battery="${c.profiles.left}"]`);
   }
   await page.click('#nav-files');const pending=page.waitForEvent('download');await page.click('#glb');const download=await pending;
   const filename=path.join(out,c.name+'.glb');await download.saveAs(filename);const bytes=fs.readFileSync(filename),jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
   const geometryBytes=node=>{const primitive=gltf.meshes[node.mesh].primitives[0],a=gltf.accessors[primitive.attributes.POSITION],v=gltf.bufferViews[a.bufferView];const at=20+jsonLength+8+(v.byteOffset||0)+(a.byteOffset||0);return bytes.subarray(at,at+a.count*12);};
   for(const side of ['left','right']){
    assert.equal(gltf.nodes.filter(n=>n.extras?.part_id===`${side}-display-socket`&&n.extras?.group==='connectors').length,1,'Battery selection must retain J2');
    const battery=gltf.nodes.find(n=>n.extras?.side===side&&n.extras?.group==='battery');assert.equal(battery.extras.battery_profile,c.profiles[side]);
    const leads=gltf.nodes.filter(n=>n.extras?.side===side&&Number.isInteger(n.extras?.battery_lead_index));assert.equal(leads.length,2);
    for(const lead of leads){
     assert.equal(lead.extras.battery_profile,c.profiles[side]);const native=scene.batteryLeadProfiles[`${side}-${c.profiles[side]}`].find(w=>w.index===lead.extras.battery_lead_index);
     assert.deepEqual(geometryBytes(lead),Buffer.from(scene.geometries[native.geometry].positions,'base64'));
     const primitive=gltf.meshes[lead.mesh].primitives[0],color=gltf.materials[primitive.material].pbrMetallicRoughness.baseColorFactor;
     for(const [i,at] of [1,3,5].entries()){const srgb=parseInt(native.color.slice(at,at+2),16)/255,linear=srgb<=.04045?srgb/12.92:Math.pow((srgb+.055)/1.055,2.4);assert.ok(Math.abs(color[i]-linear)<1e-5,'Lead color must match native contact orientation');}
    }
   }
   assert.equal(gltf.nodes.filter(n=>n.mesh!==undefined).length,expectedCount);checked.push(c);
  }
  const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({viewer_sha256:sha(html),checker_sha256:sha(fs.readFileSync(__filename)),checked,exact_native_lead_meshes:true,exact_native_lead_colors:true,physical_polarity_verified:false,stable_component_count:expectedCount,runtime_errors:errors},null,2)+'\n');
  console.log('PASS: both battery profiles and mixed halves export their exact native connected leads; all scene components preserved');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
