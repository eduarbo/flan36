// Read back the actual exported GLB, registered print materials and visible halves.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require(process.env.FLAN36_PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),url=process.env.FLAN36_VIEWER_URL||'file://'+path.join(root,'docs/offline.html');
const out=path.join(root,'build/frame-orientation',url.startsWith('http')?'public':'viewer');fs.mkdirSync(out,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function glb(bytes){
 const length=bytes.readUInt32LE(12),doc=JSON.parse(bytes.toString('utf8',20,20+length)),bin=bytes.subarray(28+length);
 const access=id=>{const a=doc.accessors[id],v=doc.bufferViews[a.bufferView],size=a.componentType===5126||a.componentType===5125?4:2,n=a.type==='VEC3'?3:1,stride=v.byteStride||size*n,start=(v.byteOffset||0)+(a.byteOffset||0);assert([5126,5125,5123].includes(a.componentType));return Array.from({length:a.count},(_,i)=>Array.from({length:n},(_,j)=>{const p=start+i*stride+j*size;return a.componentType===5126?bin.readFloatLE(p):size===4?bin.readUInt32LE(p):bin.readUInt16LE(p);}));};
 const moments=(side,role)=>{
  const node=doc.nodes.find(n=>n.extras?.group==='lid'&&n.extras?.side===side&&n.extras?.frame_style==='gameboy');assert(node,side);
  const p=doc.meshes[node.mesh].primitives[role],verts=access(p.attributes.POSITION),ids=access(p.indices).flat();let area=0,mx=0,mz=0;
  for(let i=0;i<ids.length;i+=3){const t=ids.slice(i,i+3).map(k=>verts[k]);if(t.some(v=>Math.abs(v[1]-13.59)>.0001))continue;const [a,b,c]=t,w=Math.abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))/2;area+=w;mx+=w*(a[0]+b[0]+c[0])/3;mz+=w*(a[2]+b[2]+c[2])/3;}
  assert(area>0);return {area,x:mx/area,z:mz/area};
 };
 const roles=[];for(const role of [1,2,3]){const l=moments('left',role),r=moments('right',role);assert(Math.abs(r.x-l.x+86)<.001);assert(Math.abs(r.z-l.z)<.001);assert(Math.abs(r.area-l.area)<.01);roles.push({role,left:l,right:r});}
 return roles;
}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.FLAN36_BROWSER});const errors=[];
 try{
  const p=await browser.newPage({viewport:{width:1500,height:1050}});p.on('pageerror',e=>errors.push(e.message));
  await p.goto(url+(url.includes('?')?'&':'?')+'diagnostics');await p.waitForFunction(()=>window.flan36,null,{timeout:120000});
  await p.click('#part-lid');await p.click('#frame-target [data-side=both]');const before=await p.evaluate(()=>window.flan36.snapshot());
  await p.click('[data-style=gameboy]');await p.click('#theme-colors');await p.evaluate(()=>window.flan36.idle());
  const after=await p.evaluate(()=>window.flan36.snapshot());assert.deepEqual(after.camera,before.camera);assert.deepEqual(after.view,before.view);
  for(const side of ['left','right'])assert.equal(after.configuration.frames[side].style,'gameboy');
  await p.selectOption('#view','top');await p.click('#fit');await p.click('#collapse-detail');
  // Collapsing the inspector resizes and clears the WebGL drawing buffer. Let
  // ResizeObserver and the requested render finish before reading its pixels.
  await p.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));
  assert.equal(await p.locator('#error').isVisible(),false);
  await p.screenshot({path:path.join(out,'both-gameboy.png')});
  await p.click('#nav-files');
  async function download(id,name){const waiting=p.waitForEvent('download',{timeout:120000});await p.click(id);const d=await waiting;await d.saveAs(path.join(out,name));return fs.readFileSync(path.join(out,name));}
  const roles=glb(await download('#glb','assembly.glb'));
  require('esbuild').buildSync({stdin:{contents:"export {unzipSync} from 'three/addons/libs/fflate.module.js';",resolveDir:__dirname},bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'zip.cjs')});
  const files=require(path.join(out,'zip.cjs')).unzipSync(await download('#print-kit','kit.zip')),manifest=JSON.parse(Buffer.from(files['manifest.json']));
  assert.deepEqual(manifest.configuration,after.configuration);let materialCount=0;
  for(const part of manifest.parts){assert.equal(sha(files['STL/'+part.id+'.stl']),sha(fs.readFileSync(path.join(root,part.source))));for(const m of part.material_parts||[]){if(!part.id.includes('-frame-'))continue;assert.equal(sha(files[`Materials/${part.id}/${m.role}.stl`]),sha(fs.readFileSync(path.join(root,m.source))));materialCount++;}}
  assert.equal(materialCount,8);assert.deepEqual(errors,[]);
  const report={url,passed:true,exported_glb_roles:roles,registered_frame_materials:materialCount,camera_preserved:true,errors,viewer_sha256:sha(fs.readFileSync(path.join(root,url.startsWith('http')?'docs/index.html':'docs/offline.html')))};
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
