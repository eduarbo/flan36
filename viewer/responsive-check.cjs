// SPDX-License-Identifier: GPL-3.0-or-later
// Real pixels and interactive state across layout transitions, without resetting.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const pw=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),engine=process.env.FLAN36_ENGINE||'chromium';
const out=path.join(root,'build/responsive-review');fs.mkdirSync(out,{recursive:true});
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
async function layout(p,label){
 console.log(label);
 await settle(p);await p.waitForTimeout(150);const boxes=await p.evaluate(()=>{const c=document.querySelector('#canvas').getBoundingClientRect(),t=document.querySelector('.view-controls').getBoundingClientRect();return {width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,canvasHeight:c.height,overlap:c.bottom-t.top,toolbarRight:t.right};});
 assert.equal(boxes.overflow,false,label+' horizontal overflow');assert.ok(boxes.canvasHeight>=(boxes.height<500?160:180),label+' usable canvas');assert.ok(boxes.overlap<=1,label+' toolbar does not cover model');assert.ok(boxes.toolbarRight<=boxes.width,label+' toolbar contained');
 const pixels=await framed(p);result.checks.push({label,...boxes,pixels});
}
(async()=>{const b=await pw[engine].launch({headless:true,...(process.env.FLAN36_BROWSER?{executablePath:process.env.FLAN36_BROWSER}:{})});result.browser=await b.version();try{
 const c=await b.newContext({viewport:{width:1440,height:960},hasTouch:true,deviceScaleFactor:1});
 const p=await c.newPage();p.on('pageerror',e=>result.errors.push(e.message));
 await p.goto(target+(target.includes('?')?'&':'?')+'diagnostics');await p.waitForFunction(()=>window.flan36,null,{timeout:90000});await layout(p,'desktop initial');
 const initial=await snapshot(p);
 for(const [w,h] of [[390,690],[320,568],[844,390],[768,1024],[1024,768],[1440,960],[390,844]]){
  const a=await snapshot(p);await p.setViewportSize({width:w,height:h});await layout(p,`${w}x${h} transition`);preserved(a,await snapshot(p));
 }
 await p.screenshot({path:path.join(out,`${engine}-mobile.png`),fullPage:true});
 for(const action of ['collapse','expand']){const a=await snapshot(p);await p.click('#collapse-detail');await layout(p,action+' details');preserved(a,await snapshot(p));}
 for(const action of ['open','close']){const a=await snapshot(p);await p.locator('.view-settings summary').click();await layout(p,action+' view settings');preserved(a,await snapshot(p));}
 // Primary actions must be in view in short landscape, without test auto-scroll.
 await p.setViewportSize({width:844,height:390});await p.evaluate(()=>scrollTo(0,0));await settle(p);
 const hits=await p.locator('.toolbar-primary button').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return r.top>=0&&r.bottom<=innerHeight&&r.height>=44&&e.contains(hit);}));assert.ok(hits.every(Boolean),'Landscape primary actions are visible touch targets');
 await p.locator('.view-settings summary').click();await layout(p,'landscape expanded settings');
 assert.ok(await p.evaluate(()=>document.querySelector('.stage').getBoundingClientRect().bottom>=document.querySelector('#view-feedback').getBoundingClientRect().bottom),'Expanded tools stay inside stage');
 await p.locator('.view-settings summary').click();await p.setViewportSize({width:390,height:844});
 console.log('Touch components');
 // Each component and its independent visibility target remains reachable by touch.
 for(const group of ['base','plate','lid','keycaps','switches','pcb','battery','mcu','display','connectors','supports','fasteners']){
  const button=p.locator('#part-'+group);await button.scrollIntoViewIfNeeded();await button.tap();
  const target=p.locator('#layer-'+group),r=await target.boundingBox();assert.ok(r.width>=44&&r.height>=44,group+' eye target');
  await target.uncheck();assert.equal((await snapshot(p)).view.layers[group],false);await target.check();
 }
 console.log('Selection line clipping');
 // A visible line must hide when its anchor is clipped, then return.
 await p.locator('#part-keycaps').scrollIntoViewIfNeeded();await p.locator('#part-keycaps').tap();
 await p.locator('#canvas').scrollIntoViewIfNeeded();
 await p.waitForFunction(()=>!document.querySelector('#part-link').hasAttribute('hidden'));
 await p.locator('#layers').evaluate(e=>e.scrollLeft=e.scrollWidth);
 await p.waitForFunction(()=>document.querySelector('#part-link').hasAttribute('hidden'));
 await p.locator('#layers').evaluate(e=>e.scrollLeft=0);
 await p.waitForFunction(()=>!document.querySelector('#part-link').hasAttribute('hidden'));
 // Vertical scroll in the compact, collapsed directory has a different clip owner.
 await p.setViewportSize({width:844,height:390});await p.click('#collapse-detail');await p.evaluate(()=>scrollTo(0,0));
 await p.locator('.directory').evaluate(e=>e.scrollTop=0);
 await p.waitForFunction(()=>!document.querySelector('#part-link').hasAttribute('hidden'));
 await p.locator('.directory').evaluate(e=>e.scrollTop=e.scrollHeight);
 await p.waitForFunction(()=>document.querySelector('#part-link').hasAttribute('hidden'));
 await p.locator('.directory').evaluate(e=>e.scrollTop=0);
 await p.waitForFunction(()=>!document.querySelector('#part-link').hasAttribute('hidden'));
 await p.click('#collapse-detail');await p.setViewportSize({width:390,height:844});await p.click('#clear-selection');
 console.log('Return after editing');
 // Color editing can return to the model without altering view or history.
 await p.click('#part-base');await p.locator('#case-colors .hex-input').first().scrollIntoViewIfNeeded();await p.locator('#case-colors .hex-input').first().fill('#223344');await p.evaluate(()=>window.flan36.idle());
 await p.waitForFunction(()=>!document.querySelector('#back-to-model').hidden);const edited=await snapshot(p);
 await p.click('#back-to-model');await settle(p);preserved(edited,await snapshot(p));
 assert.ok(await p.locator('#canvas').evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}),'Back to model brings preview into view');
 await p.click('#undo');await p.evaluate(()=>window.flan36.idle());await p.click('#clear-selection');
 await p.click('#complete');await layout(p,'touch navigation return');
 // Touch drag and pinch must orbit/zoom, never select a component accidentally.
 if(engine==='chromium'){
  const client=await c.newCDPSession(p),r=await p.locator('#canvas').boundingBox(),x=r.x+r.width/2,y=r.y+r.height/2;
  for(const points of [[{x,y,id:1}],[{x:x-25,y,id:1},{x:x+25,y,id:2}]]){
   await client.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:points});
   await client.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:points.map((a,i)=>({...a,x:a.x+(i?40:-30),y:a.y+15}))});
   await client.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  }
  assert.equal((await snapshot(p)).selected,null,'Touch gestures do not select');
 }
 await p.click('#fit');await layout(p,'fit after gestures');
 // Intentional zoom and pan survive projection changes too.
 const r=await p.locator('#canvas').boundingBox();await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.wheel(0,-200);await settle(p);const zoomed=await snapshot(p);
 await p.setViewportSize({width:844,height:390});await settle(p);preserved(zoomed,await snapshot(p));
 await p.setViewportSize({width:1440,height:960});await p.click('#complete');await layout(p,'return desktop');
 assert.deepEqual((await snapshot(p)).configuration,initial.configuration);
 await p.screenshot({path:path.join(out,`${engine}-desktop.png`)});
 assert.deepEqual(result.errors,[]);result.passed=true;
 }finally{await b.close();fs.writeFileSync(path.join(out,`responsive-${engine}.json`),JSON.stringify(result,null,2)+'\n');}console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
