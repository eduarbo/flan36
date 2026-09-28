// SPDX-License-Identifier: GPL-3.0-or-later
// Repeatable before/after measurements on the same browser, viewport and CPU throttle.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process'),{pathToFileURL}=require('node:url');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/viewer-sidebar');fs.mkdirSync(out,{recursive:true});
const baseline=process.argv.includes('--baseline'),smoke=process.argv.includes('--smoke'),revision='8b4edc1d8230a5ad4d35b5e4a9b0f66d912f689a';
assert.ok(!(baseline&&smoke),'--smoke measures only the current viewer');
const file=baseline?path.join(out,'baseline.html'):path.join(root,'docs/index.html');
if(baseline)fs.writeFileSync(file,execFileSync('git',['show',revision+':docs/index.html'],{cwd:root,maxBuffer:50*1024*1024}));
const scene=baseline?null:JSON.parse(fs.readFileSync(path.join(root,'build/viewer-scene.json')));
const expectedCount=baseline?168:scene.parts.length;
const percentile=(arr,p)=>[...arr].sort((a,b)=>a-b)[Math.min(arr.length-1,Math.floor(arr.length*p))]||0;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:800},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const cdp=await page.context().newCDPSession(page);await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
  await page.addInitScript(()=>{
   window.frameSamples=[];window.longTasks=[];window.measuring=false;let last=0;
   function frame(t){if(window.measuring&&last)window.frameSamples.push(t-last);last=t;requestAnimationFrame(frame);}requestAnimationFrame(frame);
   new PerformanceObserver(list=>{if(window.measuring)window.longTasks.push(...list.getEntries().map(e=>e.duration));}).observe({type:'longtask',buffered:false});
  });
  const start=Date.now();await page.goto(pathToFileURL(file).href);await page.waitForFunction(n=>document.querySelector('#status').textContent.includes(`${n} visible components`),expectedCount,{timeout:60000});
  const ready=Date.now()-start;await page.waitForTimeout(250);
  const results={baseline,baseline_revision:revision,smoke,measurement_only:smoke,browser:await browser.version(),viewport:[1200,800],cpu_throttle:4,ready_ms:ready,scene_objects:expectedCount,physical_phone_tested:false,checker_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex')};
  async function drag(){
   const rect=await page.locator('#canvas').boundingBox();await page.mouse.move(rect.x+rect.width*.45,rect.y+rect.height*.46);await page.mouse.down();
   await page.evaluate(()=>{window.frameSamples=[];window.longTasks=[];window.measuring=true;});
   const begin=Date.now();
   for(let i=0;i<60;i++){await page.mouse.move(rect.x+rect.width*(.45+i*.003),rect.y+rect.height*(.46+Math.sin(i/12)*.07));await page.waitForTimeout(12);}
   await page.mouse.up();await page.waitForTimeout(40);
   const samples=await page.evaluate(()=>{window.measuring=false;return{frames:window.frameSamples,longTasks:window.longTasks}});
   return{elapsed_ms:Date.now()-begin,frame_count:samples.frames.length,p50_frame_ms:percentile(samples.frames,.5),p95_frame_ms:percentile(samples.frames,.95),long_tasks:samples.longTasks.length,long_task_ms:samples.longTasks.reduce((a,b)=>a+b,0)};
  }
  results.viewer_sha256=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  if(!baseline){await page.locator('#part-lid').click();await page.waitForTimeout(120);}
  results.link_state=baseline?'all floating labels':'selected frame linked to sidebar';
  results.orbit=await drag();await page.locator('#reset').click();
  const timings=[];
  const styles=baseline?['handheld','tv','cyberpunk','smooth','bevel','facet']:Object.keys(scene.catalog.frame_styles);
  for(const style of styles)timings.push(await page.evaluate(async style=>{const start=performance.now();document.querySelector(`[data-style=${style}]`).click();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-start},style));
  results.frame_choice={styles,p50_ms:percentile(timings,.5),p95_ms:percentile(timings,.95),samples_ms:timings};
  if(!baseline){await page.locator('#part-base').click();const cases=[];for(const style of ['solid','rim','terrace'])cases.push(await page.evaluate(async style=>{const start=performance.now();document.querySelector(`[data-case=${style}]`).click();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return performance.now()-start},style));results.case_choice={p50_ms:percentile(cases,.5),p95_ms:percentile(cases,.95),samples_ms:cases};}
  if(baseline){await page.locator('#annotations').click();await page.locator('#reset').click();results.orbit_without_labels=await drag();}
  assert.deepEqual(errors,[]);results.runtime_errors=errors;
  fs.writeFileSync(path.join(out,baseline?'baseline-performance.json':'performance.json'),JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results,null,2));
  if(!baseline&&!smoke&&fs.existsSync(path.join(out,'baseline-performance.json'))){const old=JSON.parse(fs.readFileSync(path.join(out,'baseline-performance.json')));assert.ok(results.orbit.p95_frame_ms<old.orbit.p95_frame_ms*.65,'Orbit p95 must improve by at least 35% under the same throttle');assert.ok(results.orbit.long_task_ms<old.orbit.long_task_ms*.35,'Long task time must fall by at least 65%');}
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
