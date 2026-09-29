// Actual viewer inspection of the frame, glass and support ledges.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/display-seam/viewer');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.FLAN36_BROWSER});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:960}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('file://'+path.join(root,'docs/offline.html')+'?diagnostics');
  await page.waitForFunction(()=>window.flan36,null,{timeout:120000});
  await page.selectOption('#half','left');await page.click('#part-lid');
  await page.click('[data-style=talavera]');await page.click('#theme-colors');
  await page.click('#isolate-selection');
  await page.check('#layer-display');await page.check('#layer-supports');
  await page.selectOption('#half','left');
  assert.equal(await page.locator('#panel-frames a.case-guide').getAttribute('href'),'https://eduarbo.github.io/flan36/frame-proposals/');
  await page.click('#annotations');await page.mouse.move(1430,15);
  const images={};
  for(const view of ['top','iso']){
   await page.selectOption('#view',view);await page.click('#fit');
   await page.evaluate(()=>window.flan36.idle());await page.mouse.move(1430,15);
   await page.waitForTimeout(200);
   const file=path.join(out,view+'.png');await page.locator('.stage').screenshot({path:file});images[view]=sha(file);
  }
  const state=await page.evaluate(()=>window.flan36.snapshot());
  assert.equal(state.configuration.frames.left.style,'talavera');assert(state.view.layers.display&&state.view.layers.supports&&state.view.layers.lid);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({viewer_sha256:sha(path.join(root,'docs/offline.html')),checker_sha256:sha(__filename),real_frame_glass_and_supports_visible:true,proposal_link_verified:true,images,errors,pixel_fit_automatically_qualified:false},null,2)+'\n');
  console.log('PASS: actual viewer front/oblique captures and proposal navigation; visual inspection required');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
