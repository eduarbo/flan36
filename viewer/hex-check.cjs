// SPDX-License-Identifier: GPL-3.0-or-later
// Run against generated HTML with an isolated disposable browser profile.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/hex-check');
const url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/offline.html');
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.FLAN36_BROWSER});
 const context=await browser.newContext({viewport:{width:1440,height:960},permissions:['clipboard-read','clipboard-write']});
 const page=await context.newPage(),errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(url+(url.includes('?')?'&':'?')+'diagnostics');await page.waitForSelector('#case-base_color-hex',{timeout:60000});
  await page.evaluate(()=>document.querySelector('#default-config').click());
  const saved=async()=>{await page.evaluate(()=>new Promise(requestAnimationFrame));await page.evaluate(()=>window.flan36.idle());return page.evaluate(()=>{for(const v of Object.values(localStorage)){try{const c=JSON.parse(v);if(c.schema==='flan36-config-1')return c;}catch{}}});};
  const initial=await saved(),geometry=c=>Object.fromEntries(Object.entries(c.keycaps).map(([s,ks])=>[s,Object.fromEntries(Object.entries(ks).map(([k,v])=>[k,[v.variant,v.rotation_deg]]))]));
  const hex=page.locator('#case-base_color-hex');
  await page.locator('#case-link-colors').check();
  await hex.fill(' A1b2C3 ');assert.equal((await saved()).cases.left.base_color,'#a1b2c3');assert.equal((await saved()).frames.right.color,'#a1b2c3');
  await hex.fill('#abc');await hex.press('Enter');assert.equal((await saved()).cases.left.base_color,'#aabbcc');
  const valid=await saved();await hex.fill('oops');await hex.press('Enter');assert.equal(await hex.getAttribute('aria-invalid'),'true');assert.deepEqual(await saved(),valid);await hex.press('Escape');assert.equal(await hex.inputValue(),'#aabbcc');checks.push('3/6 digits, optional #, trim, invalid atomicity and Escape');
  await page.locator('#case-base_color').evaluate(e=>{e.value='#765432';e.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(await hex.inputValue(),'#765432');
  await page.getByRole('button',{name:'Copy Base / color rim HEX',exact:true}).click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),'#765432');
  await page.locator('#case-plate_color-hex').focus();await page.keyboard.press(process.platform==='darwin'?'Meta+V':'Control+V');assert.equal((await saved()).cases.left.plate_color,'#765432');checks.push('native picker sync, Copy, real clipboard paste to another part');
  await page.locator('#case-target [data-side="left"]').click();await hex.fill('bb1122');await page.locator('#case-target [data-side="both"]').click();assert.equal(await hex.inputValue(),'');assert.equal(await hex.getAttribute('placeholder'),'Mixed');assert.equal(await page.getByRole('button',{name:'Copy Base / color rim HEX',exact:true}).isEnabled(),false);checks.push('mixed halves stay explicit and cannot copy a misleading value');
  await page.locator('#part-lid').click();await page.locator('[data-style="gameboy"]').click();
  for(const [id,value] of [['frame-color','#abcdef'],['frame-detail','#445566'],['frame-accent','#c0ffee'],['frame-secondary','#123abc']]){await page.locator('#'+id+'-hex').fill(value);assert.equal(await page.locator('#'+id).inputValue(),value);}
  assert.equal((await saved()).cases.left.base_color,'#abcdef');checks.push('frame body and all three accent HEX fields, linked rim');
  await page.locator('#part-keycaps').click();await page.locator('#cap-mode').selectOption('all');await page.locator('#cap-color-hex').fill('abc123');assert(Object.values((await saved()).keycaps).flatMap(Object.values).every(k=>k.color==='#abc123'));
  await page.locator('#cap-mode').selectOption('row');await page.locator('#cap-row').selectOption('1');await page.locator('#cap-color-hex').fill('112233');
  const row=await saved();for(const ks of Object.values(row.keycaps))for(const [ref,k] of Object.entries(ks))assert.equal(k.color,ref[1]==='1'?'#112233':'#abc123');
  await page.locator('#cap-mode').selectOption('key');await page.locator('[data-cap-side="left"][data-cap-key="K11"]').click();await page.locator('#cap-color-hex').fill('fedcba');const single=await saved();assert.equal(single.keycaps.left.K11.color,'#fedcba');assert.equal(single.keycaps.right.K11.color,'#112233');assert.deepEqual(geometry(single),geometry(initial));checks.push('HEX follows all/row/individual targets and preserves cap geometry');
  await page.reload();await page.waitForSelector('#case-base_color-hex',{timeout:60000});assert.deepEqual(await saved(),single);checks.push('reload preserves configuration');
  await page.locator('#part-lid').click();await page.locator('#frame-color-hex').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'desktop.png')});
  await page.setViewportSize({width:390,height:844});await page.locator('#part-keycaps').click();await page.locator('#cap-color-hex').scrollIntoViewIfNeeded();
  const bounds=await page.locator('#cap-color-hex').boundingBox();assert(bounds.x>=0&&bounds.x+bounds.width<=390);await page.locator('#cap-color-hex').fill('badbad');assert.equal(await page.locator('#cap-color').inputValue(),'#badbad');await page.screenshot({path:path.join(out,'mobile.png')});checks.push('390px mobile HEX input and editing');
  assert.deepEqual(errors,[]);const bytes=url.startsWith('file:')?fs.readFileSync(new URL(url)):Buffer.from(await(await fetch(url)).arrayBuffer());
  const report={checker_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),viewer_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),checks,runtime_errors:errors};fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
