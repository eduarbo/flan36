// Reproduce the September 2026 general audit in disposable browser contexts.
// Writes only ignored build/general-review artifacts; never uses a user profile.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/general-review');
fs.mkdirSync(out,{recursive:true});
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const html=fs.readFileSync(path.join(root,'docs/index.html'));
const catalog=JSON.parse(fs.readFileSync(path.join(root,'keycaps/catalog.json')));
require(path.join(root,'viewer/node_modules/esbuild')).buildSync({stdin:{contents:"export {check,normalize} from './config.js';",resolveDir:path.join(root,'viewer')},bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'config.cjs')});
const {check,normalize}=require(path.join(out,'config.cjs'));
const base=normalize(catalog.default_configuration,catalog),slot='flan36.configuration.v1';
const report={snapshot:require('node:child_process').execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),viewer_sha256:hash(html),html_bytes:html.length,scope:'Review only; deliberately malformed inputs stay in disposable profiles.',observations:{}};
const clone=x=>structuredClone(x);
const legacy=clone(base);delete legacy.cases;
report.observations.legacy_without_cases={errors:check(legacy,catalog).errors,result:normalize(legacy,catalog).cases};
const bad=clone(base);bad.frames.right.style='constructor';bad.cases.left.base_color='#ff0000';bad.cases.left.match_frame=false;
report.observations.prototype_style={errors:check(bad,catalog).errors};
const target=pathToFileURL(path.join(root,'docs/index.html')).href;
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});
 try{
  const context=await browser.newContext({viewport:{width:1280,height:900},acceptDownloads:true});
  await context.route(/^https?:/,r=>r.abort());
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  async function ready(p){await p.waitForFunction(()=>/182 visible components/.test(document.querySelector('#status').textContent),null,{timeout:90000});}
  async function load(p,c){await p.locator('#load-config').setInputFiles({name:'audit.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(c))});}
  async function stored(p){return p.evaluate(slot=>JSON.parse(localStorage.getItem(slot)),slot);}
  const started=Date.now();await page.goto(target);await ready(page);
  const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');
  report.observations.load={local_readiness_ms:Date.now()-started,metrics:(await cdp.send('Performance.getMetrics')).metrics.filter(x=>['JSHeapUsedSize','JSHeapTotalSize','Documents','Nodes'].includes(x.name))};
  // A rejected import must not partially recolor a render/export.
  await load(page,bad);
  report.observations.prototype_style.ui_message=await page.locator('#config-status').textContent();
  report.observations.prototype_style.saved_config_unchanged=JSON.stringify(await stored(page))===JSON.stringify(base);
  await page.click('#nav-files');const dl=page.waitForEvent('download');await page.click('#glb');
  const download=await dl;const glbPath=path.join(out,'rejected-import.glb');await download.saveAs(glbPath);
  const bytes=fs.readFileSync(glbPath),gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const left=gltf.nodes.find(n=>n.extras?.side==='left'&&n.extras?.group==='base');
  report.observations.prototype_style.exported_left_base_color=gltf.materials[gltf.meshes[left.mesh].primitives[0].material].pbrMetallicRoughness.baseColorFactor;
  report.observations.prototype_style.exported_config_color=gltf.nodes.find(n=>n.extras?.configuration).extras.configuration.cases.left.base_color;
  await load(page,base);
  // Two ordinary tabs editing different parts silently replace each other's state.
  const second=await context.newPage();await second.goto(target);await ready(second);
  const painted=clone(base);painted.keycaps.left.K01.color='#123456';await load(page,painted);
  await second.click('#part-lid');await second.click('[data-style=tv]');
  report.observations.concurrent_tabs={first_tab_edit:'#123456',stored_after_second_tab_edit:(await stored(page)).keycaps.left.K01.color,expected_if_preserved:'#123456'};
  await second.close();await load(page,base);
  // Half=left scopes the view; the Battery selector also changes the hidden half.
  await page.selectOption('#half','left');await page.click('#part-battery');
  await page.click('[data-battery="301230"]');
  report.observations.battery_half={view:await page.locator('#half').inputValue(),selection:await page.locator('#selection-meta').textContent(),batteries:(await stored(page)).batteries};
  // Preserving an unsupported file gives the user a recovery path; load must not erase it.
  const unsupported=clone(base);unsupported.revision='H';unsupported.keycaps.left.K01.color='#654321';
  await page.evaluate(({slot,value})=>localStorage.setItem(slot,JSON.stringify(value)),{slot,value:unsupported});
  await page.reload();await ready(page);
  report.observations.rejected_saved_config={message:await page.locator('#config-status').textContent(),before_revision:'H',before_color:'#654321',after_revision:(await stored(page)).revision,after_color:(await stored(page)).keycaps.left.K01.color};
  report.runtime_errors=errors;await context.close();
 }finally{await browser.close();}
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
