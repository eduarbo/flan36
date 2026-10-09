// SPDX-License-Identifier: GPL-3.0-or-later
// Real pixels and interactive state across layout transitions, without resetting.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const pw=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),engine=process.env.FLAN36_ENGINE||'chromium';
const out=path.join(root,'build/mobile-redesign');fs.mkdirSync(out,{recursive:true});
const target=process.env.FLAN36_VIEWER_URL||pathToFileURL(path.join(root,'docs/offline.html')).href;
const result={engine,target:target.startsWith('file:')?'offline':target,checks:[],errors:[],physical_phone_tested:false};
const settle=p=>p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
const snapshot=p=>p.evaluate(()=>window.flan36.snapshot());
function preserved(a,b){const {halfHeight:aa,...ac}=a.camera,{halfHeight:bb,...bc}=b.camera;assert.deepEqual(bc,ac,'Orbit, pan and zoom preserved');for(const k of ['configuration','view','selected','hidden','undo','redo'])assert.deepEqual(b[k],a[k],k+' preserved');assert.ok(Number.isFinite(bb)&&bb>0);}
async function framed(p){
 await p.locator('#canvas').scrollIntoViewIfNeeded();await settle(p);
 const r=await p.locator('#canvas').boundingBox();
 const png=(await p.screenshot({clip:{x:Math.ceil(r.x)+1,y:Math.ceil(r.y)+1,width:Math.floor(r.width)-2,height:Math.floor(r.height)-2},style:'.stage-label,#leader-lines{visibility:hidden!important}.view-controls{box-shadow:none!important}'})).toString('base64');
 fs.writeFileSync(path.join(out,engine+'-canvas.png'),Buffer.from(png,'base64'));
 const bounds=await p.evaluate(async png=>{const i=new Image();i.src='data:image/png;base64,'+png;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const x=c.getContext('2d');x.drawImage(i,0,0);const {data}=x.getImageData(0,0,c.width,c.height),bg=[...data.slice(0,3)];let x0=c.width,y0=c.height,x1=0,y1=0;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const n=(y*c.width+x)*4;if(bg.reduce((s,v,j)=>s+Math.abs(v-data[n+j]),0)>40){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}}return {x0,y0,x1,y1,w:c.width,h:c.height};},png);
 assert.ok(bounds.x1>bounds.x0&&bounds.y1>bounds.y0&&bounds.x0>5&&bounds.y0>5&&bounds.x1<bounds.w-6&&bounds.y1<bounds.h-6,'Rendered model fits: '+JSON.stringify(bounds));
 return bounds;
}
async function layout(p,label,hasModel=true){
 await settle(p);await p.waitForTimeout(100);
 const boxes=await p.evaluate(()=>{const c=document.querySelector('#canvas').getBoundingClientRect(),t=document.querySelector('.view-controls').getBoundingClientRect();const nav=[...document.querySelectorAll('.app-nav button')].map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height,visible:r.top>=0&&r.bottom<=innerHeight&&e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))};});return {width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,canvasHeight:c.height,overlap:c.bottom-t.top,nav};});
 assert.equal(boxes.overflow,false,label+' horizontal overflow');assert.ok(boxes.nav.every(r=>r.visible&&r.width>=44&&r.height>=36),label+' persistent navigation reachable');
 if(hasModel){assert.ok(boxes.canvasHeight>=100,label+' usable preview');assert.ok(boxes.overlap<=1,label+' tools do not cover model');boxes.pixels=await framed(p);}
 result.checks.push({label,...boxes});
}
(async()=>{const b=await pw[engine].launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});result.browser=await b.version();try{
 const c=await b.newContext({viewport:{width:1440,height:960},hasTouch:true,deviceScaleFactor:1});const p=await c.newPage();p.on('pageerror',e=>result.errors.push(e.message));
 await p.goto(target+(target.includes('?')?'&':'?')+'diagnostics');await p.waitForFunction(()=>window.flan36,null,{timeout:90000});
 const initial=await snapshot(p);
 for(const [w,h] of [[1440,960],[390,690],[320,568],[430,820],[844,390],[768,1024],[1024,768]]){
  console.log(w+'x'+h);const before=await snapshot(p);await p.setViewportSize({width:w,height:h});await settle(p);preserved(before,await snapshot(p));
  for(const mode of ['customize','inspect','files','about']){
   const a=await snapshot(p);await p.click('#nav-'+mode);await settle(p);preserved(a,await snapshot(p));
   assert.equal(await p.locator('body').getAttribute('data-mode'),mode);assert.equal(await p.locator('.app-nav [aria-current=page]').getAttribute('id'),'nav-'+mode);
   assert.equal(await p.locator('#inspector').evaluate(e=>e.scrollTop),0,'New section starts at its heading');
   assert.equal(await p.locator('.directory').isVisible(),mode==='inspect');
   assert.equal(await p.locator('.customize-nav').isVisible(),mode==='customize');
   if(mode==='files'||mode==='about')assert.equal(await p.locator('#config-status').isVisible(),false,'No customization instruction in '+mode);
   await layout(p,`${w}x${h} ${mode}`,!['files','about'].includes(mode)||w>1000||(w>700&&w>h));
   await p.screenshot({path:path.join(out,`${engine}-${w}-${mode}.png`)});
  }
  await p.click('#credits');assert.ok(await p.locator('#licenses').isVisible());assert.equal(await p.locator('#licenses details[open]').count(),0,'License texts start collapsed');
  await p.locator('#licenses details summary').first().click();await p.locator('#licenses .dialog-body').evaluate(e=>e.scrollTop=e.scrollHeight);await settle(p);
  assert.ok(await p.locator('#close-credits').evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}),'Close stays accessible with long license');
  await p.keyboard.press('Escape');assert.equal(await p.locator('#licenses').isVisible(),false);assert.equal(await p.evaluate(()=>document.activeElement.id),'credits');
  await p.locator('#licenses details').first().evaluate(e=>e.open=false);
  await p.click('#credits');await p.screenshot({path:path.join(out,`${engine}-${w}-licenses.png`)});await p.click('#close-credits');
  await p.click('#nav-customize');const a=await snapshot(p);await p.click('#view-options');await p.screenshot({path:path.join(out,`${engine}-${w}-view.png`)});await p.click('#close-view');preserved(a,await snapshot(p));
 }
 // All editor categories, including touch-accessible advanced inputs.
 await p.setViewportSize({width:390,height:690});await p.click('#nav-customize');
 for(const panel of ['cases','frames','keycaps','themes','battery']){
  await p.click(`[data-panel=${panel}]`);assert.ok(await p.locator('#panel-'+panel).isVisible());await p.screenshot({path:path.join(out,`${engine}-editor-${panel}.png`)});
 }
 for(const [panel,disclosure,detail] of [['cases','#panel-cases .option-group','case-colors'],['frames','#panel-frames .option-group','theme-palette'],['keycaps','#cap-colors','cap-map'],['keycaps','#key-details','apply-keys']]){
  await p.click(`[data-panel=${panel}]`);const d=p.locator(disclosure).first();if(!await d.evaluate(e=>e.open))await d.locator('summary').first().click();await p.locator('#'+detail).scrollIntoViewIfNeeded();await p.screenshot({path:path.join(out,`${engine}-expanded-${detail}.png`)});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await d.locator('summary').first().click();
 }
 await p.click('#edit-cases');await p.locator('#panel-cases .option-group summary').first().click();await p.locator('#case-target [data-side=left]').click();
 const base=await snapshot(p);await p.locator('#case-colors .hex-input').first().fill('#223344');
 await p.setViewportSize({width:390,height:400});await settle(p);assert.equal(await p.locator('#canvas').isVisible(),false,'Editor makes room at keyboard height');assert.ok(await p.locator('#case-colors .hex-input').first().evaluate(e=>{const r=e.getBoundingClientRect();return r.height>=44;}));await p.locator('#case-colors .hex-input').first().blur();await p.setViewportSize({width:390,height:690});await p.click('#toggle-preview');await settle(p);assert.ok(await p.locator('#canvas').isVisible());await p.evaluate(()=>window.flan36.idle());const edited=await snapshot(p);
 assert.equal(edited.configuration.cases.left.base_color,'#223344');assert.equal(edited.configuration.cases.right.base_color,base.configuration.cases.right.base_color);
 // Saved choices and view survive every destination, including hidden mobile canvas.
 for(const mode of ['files','about','inspect','customize']){await p.click('#nav-'+mode);await settle(p);preserved(edited,await snapshot(p));}
 await p.click('#undo');await p.evaluate(()=>window.flan36.idle());assert.deepEqual((await snapshot(p)).configuration,base.configuration);await p.click('#redo');await p.evaluate(()=>window.flan36.idle());assert.deepEqual((await snapshot(p)).configuration,edited.configuration);await p.click('#undo');await p.evaluate(()=>window.flan36.idle());
 await p.click('#nav-inspect');
 for(const group of ['base','plate','lid','keycaps','switches','pcb','battery','mcu','display','connectors','supports','fasteners']){
  await p.locator('#part-'+group).tap();assert.equal(await p.locator('body').getAttribute('data-mode'),'inspect');assert.ok(await p.locator('#selection').isVisible());
  const eye=p.locator('#layer-'+group);await eye.scrollIntoViewIfNeeded();const r=await eye.boundingBox();assert.ok(r.width>=44&&r.height>=44);await eye.uncheck();assert.equal((await snapshot(p)).view.layers[group],false);await eye.check();
 }
 await p.click('#part-base');const selected=await snapshot(p);await p.click('#view-options');await p.keyboard.press('Escape');assert.equal(await p.locator('#view-dialog').isVisible(),false);preserved(selected,await snapshot(p));assert.equal(await p.evaluate(()=>document.activeElement.id),'view-options');
 await p.click('#part-keycaps');await p.locator('#inspector').evaluate(e=>e.scrollTop=0);await p.waitForFunction(()=>!document.querySelector('#part-link').hasAttribute('hidden'));await p.click('#toggle-preview');await p.waitForFunction(()=>document.querySelector('#part-link').hasAttribute('hidden'));await p.click('#toggle-preview');
 await p.locator('#inspector').evaluate(e=>e.scrollTop=e.scrollHeight);await p.waitForFunction(()=>document.querySelector('#part-link').hasAttribute('hidden'));
 await p.click('#part-base');await p.click('#isolate-selection');const solo=await snapshot(p);assert.ok(solo.visible.length<initial.visible.length);await p.click('#show-all');assert.equal((await snapshot(p)).visible.length,initial.visible.length);await p.click('#edit-selection');assert.ok(await p.locator('#panel-cases').isVisible());
 await p.click('#nav-inspect');await p.click('#part-keycaps');await p.click('#nav-files');assert.equal(await p.locator('#selection').isVisible(),false);await p.click('#nav-about');assert.equal(await p.locator('#selection').isVisible(),false);await p.click('#nav-inspect');await p.click('#clear-selection');assert.equal(await p.locator('.part-item[aria-expanded=true]').count(),0);
 await p.click('#nav-customize');await p.click('#complete');
 if(engine==='chromium'){
  const client=await c.newCDPSession(p),r=await p.locator('#canvas').boundingBox(),x=r.x+r.width/2,y=r.y+r.height/2;
  for(const points of [[{x,y,id:1}],[{x:x-25,y,id:1},{x:x+25,y,id:2}]]){await client.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:points});await client.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:points.map((a,i)=>({...a,x:a.x+(i?40:-30),y:a.y+15}))});await client.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});}
  assert.equal((await snapshot(p)).selected,null,'Gestures do not select');
 }
 await p.click('#fit');await layout(p,'fit after gestures');const r=await p.locator('#canvas').boundingBox();await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.wheel(0,-200);await settle(p);const zoomed=await snapshot(p);
 await p.setViewportSize({width:844,height:390});await settle(p);preserved(zoomed,await snapshot(p));
 assert.deepEqual(result.errors,[]);result.passed=true;result.interactions=['navigation preserves view and design','independent section scroll','five editors','12 component eyes','solo and restore','edit selected part','one-half color edit','undo redo','long license close and focus','Escape preserves selection in view dialog','clear removes active row','selection lines clip with inspector scroll','view dialog','touch orbit and pinch','responsive pan/zoom','short keyboard viewport and explicit preview restore'];
 }finally{await b.close();fs.writeFileSync(path.join(out,`${engine}-responsive.json`),JSON.stringify(result,null,2)+'\n');}
 console.log(JSON.stringify({engine,passed:result.passed,checks:result.checks.length,errors:result.errors}));
})().catch(e=>{console.error(e);process.exitCode=1;});
