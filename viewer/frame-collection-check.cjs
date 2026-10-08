// Actual frame thumbnails, transitions, migrations and registered native print volumes.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/frame-collection/acceptance');fs.mkdirSync(out,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(path.join(root,p))),spec=read('design/frame-finishes.json'),scene=read('build/viewer-scene.json'),catalog=scene.catalog,selection=read('design/frame-selection.json'),themes=read('design/themes.json').themes,styles=Object.keys(catalog.frame_styles),fallback=catalog.default_frame_style;
assert.deepEqual(styles,selection.viewer.installed_styles);assert.equal(fallback,'talavera');assert.deepEqual(catalog.pending_frame_styles,[]);
require('esbuild').buildSync({stdin:{contents:"export * from './printing.js';export * from './config.js';export * from './storage.js';export {unzipSync,strFromU8} from 'three/addons/libs/fflate.module.js';",resolveDir:__dirname},bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'printing.cjs')});
const {mesh3MF,unzipSync,strFromU8,normalize,check,restoreConfiguration}=require(path.join(out,'printing.cjs')),materials=[];
for(const side of ['left','right'])for(const style of styles){
 const id=`${side}-frame-${style}`,part=scene.printing.assets[id];assert(part,id);assert.equal(part.material_parts.length,4);
 for(const m of part.material_parts)assert.equal(sha(Buffer.from(m.stl,'base64')),sha(fs.readFileSync(path.join(root,m.path))),id+' '+m.role);
 const p={...part,id,style,colors:spec.styles[style].colors},result=mesh3MF(p),xml=strFromU8(unzipSync(result.bytes)['3D/3dmodel.model']);
 assert.equal((xml.match(/<object /g)||[]).length,5);assert.equal((xml.match(/<component /g)||[]).length,4);assert.equal((xml.match(/<item /g)||[]).length,1);assert.doesNotMatch(xml,/paint_color|colorgroup/);
 for(const [i,role] of spec.roles.entries())assert.match(xml,new RegExp(`name="${role}" displaycolor="${p.colors[role].toUpperCase()}FF"`));
 fs.writeFileSync(path.join(out,id+'.3mf'),result.bytes);materials.push({id,material_parts:4,sha256:sha(result.bytes)});
}
for(const side of ['left','right'])for(const old of selection.viewer.retired_styles)assert(!scene.printing.assets[`${side}-frame-${old}`]);
// The active catalog must exclude rejected shapes in both render and print data.
const retired=selection.viewer.retired_styles,fixtures=[];
for(const old of retired){
 assert.equal(catalog.retired_frame_styles[old],fallback);
 for(const key of Object.keys(scene.geometries))assert(!key.includes('-frame-'+old+'.')&&!key.includes('-frame-'+old+'-'),key);
 for(const accents of [undefined,{detail:'#2468ac'},{detail:'#2468ac',accent:'#654321',secondary:'#abcdef'}]){
  const input=structuredClone(catalog.default_configuration);
  for(const side of ['left','right']){input.frames[side].style=old;if(accents)input.frames[side].accents=structuredClone(accents);else delete input.frames[side].accents;}
  input.keycaps.left.K30.color='#123456';input.batteries.right='301230';input.cases.right.cover=false;
  const expected=structuredClone(input),palette=spec.styles[spec.retired_styles.includes(old)?'flan':old].colors;
  for(const side of ['left','right']){expected.frames[side].style=fallback;expected.frames[side].accents=Object.fromEntries(['detail','accent','secondary'].map(role=>[role,accents?.[role]||palette[role]]));}
  assert.deepEqual(check(input,catalog).errors,[]);assert.deepEqual(normalize(input,catalog),expected);
  for(const key of ['flan36.configuration.v1','filo36.configuration.v1']){
   const raw=JSON.stringify(input),values=new Map([[key,raw]]),saved=restoreConfiguration({getItem:k=>values.get(k)??null},catalog);
   assert.deepEqual(saved.configuration,expected);assert.equal(values.get(key),raw);assert.match(saved.message,/Talavera/);
  }
  fixtures.push({input,expected});
 }
}
// Materialized active exports remain exact inputs to the historical native CAD reader.
const py=require('child_process').spawnSync('python3',['-c',"import sys,json;sys.path.insert(0,'tools');from keycap_config import check,normalize;xs=json.load(sys.stdin);assert all(not check(x)[0] for x in xs);print(json.dumps([normalize(x) for x in xs]))"],{cwd:root,input:JSON.stringify(fixtures.map(f=>f.expected)),encoding:'utf8',maxBuffer:5e6});
assert.equal(py.status,0,py.stderr);assert.deepEqual(JSON.parse(py.stdout),fixtures.map(f=>f.expected));
for(const preset of Object.values(scene.presets))for(const frame of Object.values(preset.frames))assert(styles.includes(frame.style));
const report={styles,viewer_sha256:sha(fs.readFileSync(path.join(root,'docs/offline.html'))),native_3mf:materials,checks:{},runtime_errors:[]};
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.FLAN36_BROWSER});
 try{
  const ctx=await browser.newContext({viewport:{width:1440,height:960}}),p=await ctx.newPage();p.on('pageerror',e=>report.runtime_errors.push(e.message));
  const url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/offline.html');
  const open=async(page)=>{if(page!==p)page.on('pageerror',e=>report.runtime_errors.push(e.message));await page.goto(url+(url.includes('?')?'&':'?')+'diagnostics');await page.waitForFunction(()=>window.flan36,null,{timeout:120000});};
  const snap=()=>p.evaluate(()=>window.flan36.snapshot()),idle=()=>p.evaluate(()=>window.flan36.idle());
  await open(p);const initial=await snap();assert.deepEqual(initial.configuration,catalog.default_configuration);
  await p.click('#part-lid');assert.deepEqual(await p.locator('[data-style]').evaluateAll(es=>es.map(e=>e.dataset.style)),styles);
  const images=await p.locator('[data-style] img').evaluateAll(es=>es.map(e=>e.src));assert.equal(new Set(images).size,styles.length,'Each frame has a distinct rendered preview');
  assert(images.every(s=>s.startsWith('data:image/')));report.checks.distinct_actual_previews=styles.length;
  await p.selectOption('#view','front');await p.mouse.move(400,400);await p.mouse.wheel(0,-300);await p.waitForTimeout(80);
  for(const style of styles){const before=await snap();await p.click(`[data-style=${style}]`);await idle();const after=await snap();assert.deepEqual(after.camera,before.camera);assert.deepEqual(after.view,before.view);assert.deepEqual(after.hidden,before.hidden);assert.equal(after.configuration.frames.left.style,style);assert.equal(after.configuration.frames.right.style,style);}
  report.checks.frame_changes_preserve_inspection=styles.length;
  await p.click('#nav-themes');await p.click('#theme-target [data-side=both]');
  for(const theme of themes){const before=await snap();await p.click(`[data-theme="${theme.id}"]`);await idle();const after=await snap();assert.deepEqual(after.camera,before.camera);assert.deepEqual(after.configuration.frames.left.style,before.configuration.frames.left.style);for(const side of ['left','right'])for(const k of catalog.layout[side]){const expected=k.row===3?theme.keycaps.thumbs[k.col]:theme.keycaps.pattern==='rows'?theme.keycaps.colors[k.row]:theme.keycaps.base;assert.equal(after.configuration.keycaps[side][k.ref].color,expected);}}
  report.checks.themes_without_pinky_accents=themes.length;
  await p.click('#nav-files');await p.click('#default-config');await idle();assert.deepEqual((await snap()).configuration,catalog.default_configuration);report.checks.approved_reset_default=true;
  // Exercise the real file-import route for every withdrawn ID, with implicit accents.
  for(const fixture of fixtures.filter((_,i)=>i%3===0)){
   const before=await snap();await p.setInputFiles('#load-config',{name:'old.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture.input))});
   await p.waitForFunction(()=>document.getElementById('config-status').textContent.includes('Retired frames replaced with Talavera'));
   await idle();const after=await snap();assert.deepEqual(after.configuration,fixture.expected);assert.deepEqual(after.camera,before.camera);assert.deepEqual(after.view,before.view);assert.deepEqual(after.hidden,before.hidden);
  }
  report.checks.all_retired_imports_preserve_view_and_implicit_colors=retired.length;
  report.checks.storage_keys_and_color_fixtures=fixtures.length*2;
  report.checks.native_reader_export_parity=fixtures.length;
  await p.click('#part-keycaps');
  for(const id of await p.locator('[data-preset]').evaluateAll(es=>es.map(e=>e.dataset.preset))){await p.click(`[data-preset="${id}"]`);await idle();for(const f of Object.values((await snap()).configuration.frames))assert(styles.includes(f.style));}
  report.checks.presets_cannot_restore_retired_frames=true;
  // Seed an actual old device configuration in a separate disposable profile.
  const cx=await browser.newContext({viewport:{width:1200,height:850}});const old=structuredClone(catalog.default_configuration);old.frames.left.style='tape';old.frames.right.style='orbit';old.keycaps.left.K30.color='#123456';old.batteries.right='301230';old.cases.right.cover=false;const raw=JSON.stringify(old);
  await cx.addInitScript(raw=>{if(!sessionStorage.seeded){localStorage.setItem('flan36.configuration.v1',raw);sessionStorage.seeded='yes';}},raw);
  const q=await cx.newPage();await open(q);const migrated=await q.evaluate(()=>window.flan36.snapshot().configuration);assert.equal(migrated.frames.left.style,fallback);assert.equal(migrated.frames.right.style,fallback);const expected=structuredClone(old);expected.frames.left.style=expected.frames.right.style=fallback;assert.deepEqual(migrated,expected);assert.match(await q.locator('#config-status').textContent(),/Retired frames/);assert.equal(await q.evaluate(()=>localStorage.getItem('flan36.configuration.v1')),raw);
  await q.click('[data-case=rim]');await q.evaluate(()=>window.flan36.idle());const saved=await q.evaluate(()=>({raw:localStorage.getItem('flan36.configuration.v1'),recovery:Object.keys(localStorage).filter(k=>k.startsWith('flan36.recovery.')).map(k=>JSON.parse(localStorage.getItem(k)))}));assert(saved.recovery.some(r=>r.raw===raw));assert.notEqual(saved.raw,raw);await q.reload();await q.waitForFunction(()=>window.flan36);assert.equal((await q.evaluate(()=>window.flan36.snapshot().configuration)).frames.right.style,fallback);await cx.close();report.checks.exact_old_configuration_preserved_on_migration=true;
  // Current frame IDs must survive an artwork update with custom selections intact.
  const savedCurrent=structuredClone(catalog.default_configuration);savedCurrent.frames.left.style='talavera';savedCurrent.frames.right.style='phone';savedCurrent.frames.left.color='#123456';savedCurrent.cases.left.base_color=savedCurrent.cases.left.plate_color='#123456';savedCurrent.frames.left.accents.detail='#654321';savedCurrent.keycaps.right.K31.color='#abc123';savedCurrent.batteries.right='301230';savedCurrent.cases.right.cover=false;
  const preserved=await browser.newContext({viewport:{width:1200,height:850}});await preserved.addInitScript(raw=>localStorage.setItem('flan36.configuration.v1',raw),JSON.stringify(savedCurrent));const currentPage=await preserved.newPage();await open(currentPage);assert.deepEqual(await currentPage.evaluate(()=>window.flan36.snapshot().configuration),savedCurrent);await preserved.close();report.checks.current_custom_configuration_preserved=true;
  await p.selectOption('#view','iso');await p.click('#fit');await p.click('#nav-themes');await p.screenshot({path:path.join(out,'themes.png')});
  await p.click('#part-lid');await p.screenshot({path:path.join(out,'frame-explorer.png')});await p.setViewportSize({width:390,height:844});await p.click('[data-style=phone]');await idle();assert.equal((await snap()).configuration.frames.left.style,'phone');await p.screenshot({path:path.join(out,'mobile.png')});report.checks.mobile_gallery=true;
  assert.deepEqual(report.runtime_errors,[]);report.passed=true;await ctx.close();
 }finally{await browser.close();fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify({styles:styles.length,checks:report.checks,passed:report.passed}));
})().catch(e=>{console.error(e);process.exitCode=1;});
