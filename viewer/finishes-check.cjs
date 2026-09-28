// SPDX-License-Identifier: GPL-3.0-or-later
// Verify exact native flush material volumes and their viewer/GLB groups.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/viewer-multicolor');fs.mkdirSync(out,{recursive:true});
require('esbuild').buildSync({entryPoints:[path.join(__dirname,'finishes.js')],bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'finishes.cjs')});
const {createFrameFinishes,finishes}=require(path.join(out,'finishes.cjs')),THREE=require('three');
const scene=JSON.parse(fs.readFileSync(path.join(root,'build/viewer-scene.json')));
const decode=(s,Type)=>{const b=Buffer.from(s,'base64');return new Type(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));};
const geometryFor=p=>{const s=scene.geometries[p],g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(decode(s.positions,Float32Array),3));g.setAttribute('normal',new THREE.BufferAttribute(decode(s.normals,Float32Array),3));g.setIndex(new THREE.BufferAttribute(decode(s.indices,Uint32Array),1));for(const group of s.groups||[])g.addGroup(group.start,group.count,group.materialIndex);g.computeBoundingBox();return g;};
const make=createFrameFinishes(geometryFor,color=>({color}));
const probes={handheld:[[117,55,1,'D-pad'],[129.3,53.5,2,'Button A'],[125.7,56.1,2,'Button B'],[119.5,64,3,'Speaker']],tv:[[114.5,30,1,'CRT bezel'],[120,17.5,1,'Upper bezel'],[128.9,55.1,2,'Tuning knob'],[117,54.3,3,'Speaker']],cyberpunk:[[113.8,54,1,'Vent'],[131.5,52.2,2,'Trace'],[122,64,3,'Panel'],[128.1,61,3,'Node']]};
function triangleSet(g){const ids=Array.from(g.index.array),t=[];for(let i=0;i<ids.length;i+=3)t.push(ids.slice(i,i+3).join(','));return t.sort();}
const roof=scene.measurements.cover_top_mm;
function topRole(g,x,z){const p=g.attributes.position;for(const group of g.groups)for(let i=group.start;i<group.start+group.count;i+=3){const a=[0,1,2].map(j=>g.index.getX(i+j));if(a.some(n=>Math.abs(p.getY(n)-roof)>.001))continue;const sides=a.map((v,j)=>{const w=a[(j+1)%3];return (p.getX(w)-p.getX(v))*(z-p.getZ(v))-(p.getZ(w)-p.getZ(v))*(x-p.getX(v));});if(sides.every(n=>n>=-1e-5)||sides.every(n=>n<=1e-5))return group.materialIndex;}return null;}
const checked=[];
for(const style of Object.keys(scene.catalog.frame_styles))for(const side of ['left','right']){
 const id=`mechanical/revI/${side}-frame-${style}.stl`,source=geometryFor(id),f=make(style,side),g=f.geometry;
 assert.deepEqual(g.attributes.position.array,source.attributes.position.array);assert.deepEqual(g.attributes.normal.array,source.attributes.normal.array);assert.deepEqual(triangleSet(g),triangleSet(source));
 assert.equal(g.groups.length,finishes.styles[style]?4:1);let offset=0;
 for(const group of g.groups){assert.equal(group.start,offset);offset+=group.count;if(group.materialIndex){for(let i=group.start;i<offset;i+=3){const ids=[0,1,2].map(j=>g.index.getX(i+j));assert.ok(ids.every(n=>g.attributes.position.getY(n)>=roof-.4-1e-4&&g.attributes.position.getY(n)<=roof+1e-4),'Inlays remain inside the 0.4 mm roof band');}}}assert.equal(offset,g.index.count);
 assert.ok(g.boundingBox.max.y<=roof+1e-4,'No decoration rises above frame top');
 if(finishes.styles[style]){
  assert.deepEqual(g.groups,source.groups);
  let vertex=0;
  for(const [i,part] of scene.geometries[id].material_parts.entries()){
   const child=geometryFor(part.path),group=g.groups[i];
   assert.equal(group.materialIndex,finishes.roles.indexOf(part.role));
   assert.deepEqual(Array.from(g.attributes.position.array.slice(vertex*3,(vertex+child.attributes.position.count)*3)),Array.from(child.attributes.position.array));
   assert.deepEqual(Array.from(g.index.array.slice(group.start,group.start+group.count)),Array.from(child.index.array,v=>v+vertex));
   vertex+=child.attributes.position.count;
  }
 }
 for(const [x,z,role,label] of probes[style]||[]){
  // The Level PCB undercut leaves .665 mm here. Keep solid body material;
  // a .4 mm inlay would violate the retained .8 mm backing requirement.
  const expected=label==='Upper bezel'&&Math.abs(roof-13.39)<.001?0:role;
  assert.equal(topRole(g,side==='right'?160-x:x,z),expected,`${side} ${style}: ${label}`);
 }
 const override=make(style,side,'#abcdef');assert.equal(override.material[0].color,'#abcdef');assert.equal(override.geometry,g,'Reuse geometry across body changes');
 checked.push({side,style,triangles:g.index.count/3,groups:g.groups.length,feature_probes:(probes[style]||[]).length});
}
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={viewer_sha256:sha(path.join(root,'docs/index.html')),scene_sha256:sha(path.join(root,'build/viewer-scene.json')),checker_sha256:sha(__filename),original_vertices_normals_and_triangles:true,flush_feature_probes:true,exact_native_material_volumes:true,no_raised_relief:true,max_material_groups:4,geometry_cached:true,checked};
fs.writeFileSync(path.join(out,'geometry.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
