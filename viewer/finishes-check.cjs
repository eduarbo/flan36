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
const probes={flan:[[123,60,3,'Custard'],[123,64,1,'Saucer']],tape:[[115.4,58.25,3,'Reel'],[128,13,2,'Diagonal stripe'],[123,62.2,1,'Slat']],orbit:[[122.8,60.4,3,'Ivory disc'],[124,64,2,'Crescent']],manga:[[132,65,2,'Corner'],[116,59.9,1,'Dot 1'],[121,59.9,1,'Dot 2'],[116,64.1,1,'Dot 3'],[121,64.1,1,'Dot 4']],talavera:[[123,60.4,2,'Concave center'],[118,57.7,3,'Teardrop']],gameboy:[[117,58,1,'D-pad'],[130.1,56.3,2,'A']],nes:[[130.5,58.7,2,'A']],snes:[[127.8,62.55,2,'B']],phone:[[116,59.2,1,'Key']],walkman:[[129,57.9,3,'Play']],ipod:[[123,60.4,3,'Center']]};
function triangleSet(g){const ids=Array.from(g.index.array),t=[];for(let i=0;i<ids.length;i+=3)t.push(ids.slice(i,i+3).join(','));return t.sort();}
const roof=scene.measurements.cover_top_mm;
const r4=JSON.parse(fs.readFileSync(path.join(root,'design/proposals/frame-master-r4/master.json')));
// Check the actual three approved thickness domains, including shared boundaries.
// The former uniform 0.4 mm test incorrectly rejected the through-color collar.
function materialFloor(style,side,x,z){
 if(finishes.styles[style].approved_master!=='R4')return roof-.4;
 const localX=side==='left'?x-111:49-x,localY=z-11,epsilon=1e-4;
 const inside=(b,e)=>localX>=b[0]-e&&localX<=b[2]+e&&localY>=b[1]-e&&localY<=b[3]+e;
 const collar=inside(r4.common.relief_bounds_mm,epsilon)&&!inside(r4.common.header_cover_bounds_mm,-epsilon);
 return collar?r4.common.relief_top_z_mm:roof-.4;
}
function assertMaterialPoint(style,side,x,y,z){assert.ok(y>=materialFloor(style,side,x,z)-1e-4&&y<=roof+1e-4,`${side} ${style}: color must stay within its approved thickness domain`);}
// Negative controls reject excess material below the ordinary face and pin cover.
for(const side of ['left','right']){
 const x=local=>side==='left'?111+local:49-local;
 assert.throws(()=>assertMaterialPoint('talavera',side,x(2),13,61));
 assert.throws(()=>assertMaterialPoint('talavera',side,x(12),13,51));
 assertMaterialPoint('talavera',side,x(4.3),12.725,31);
 assert.throws(()=>assertMaterialPoint('talavera',side,x(4.3),12.5,31));
}
Object.assign(probes,{
 talavera:[[123,59.6,2,'R4 star'],[119.5,56.5,3,'R4 petal']],
 gameboy:[[117.4,57.45,1,'R4 D-pad'],[130.2,55.7,2,'R4 A']],
 snes:[[127.5,62.1,2,'R4 B']],phone:[[116.8,57.75,1,'R4 Key00']],
 ipod:[[123,59.6,3,'R4 center'],[126,59.6,0,'R4 wheel void'],[127.5,59.6,2,'R4 wheel']]
});
function topRole(g,x,z){const p=g.attributes.position;for(const group of g.groups)for(let i=group.start;i<group.start+group.count;i+=3){const a=[0,1,2].map(j=>g.index.getX(i+j));if(a.some(n=>Math.abs(p.getY(n)-roof)>.001))continue;const sides=a.map((v,j)=>{const w=a[(j+1)%3];return (p.getX(w)-p.getX(v))*(z-p.getZ(v))-(p.getZ(w)-p.getZ(v))*(x-p.getX(v));});if(sides.every(n=>n>=-1e-5)||sides.every(n=>n<=1e-5))return group.materialIndex;}return null;}
const checked=[];
for(const style of Object.keys(scene.catalog.frame_styles))for(const side of ['left','right']){
 const id=`mechanical/revI/${side}-frame-${style}.stl`,source=geometryFor(id),f=make(style,side),g=f.geometry;
 assert.deepEqual(g.attributes.position.array,source.attributes.position.array);assert.deepEqual(g.attributes.normal.array,source.attributes.normal.array);assert.deepEqual(triangleSet(g),triangleSet(source));
 assert.equal(g.groups.length,finishes.styles[style]?4:1);let offset=0;
 for(const group of g.groups){assert.equal(group.start,offset);offset+=group.count;if(group.materialIndex){for(let i=group.start;i<offset;i+=3){const ids=[0,1,2].map(j=>g.index.getX(i+j));const p=g.attributes.position;for(const n of ids)assertMaterialPoint(style,side,p.getX(n),p.getY(n),p.getZ(n));assertMaterialPoint(style,side,...['getX','getY','getZ'].map(axis=>ids.reduce((sum,n)=>sum+p[axis](n),0)/3));}}}assert.equal(offset,g.index.count);
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
  const expected=role;
  assert.equal(topRole(g,side==='right'?160-x:x,z),expected,`${side} ${style}: ${label}`);
 }
 const override=make(style,side,'#abcdef');assert.equal(override.material[0].color,'#abcdef');assert.equal(override.geometry,g,'Reuse geometry across body changes');
 checked.push({side,style,triangles:g.index.count/3,groups:g.groups.length,feature_probes:(probes[style]||[]).length});
}
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={viewer_sha256:sha(path.join(root,'docs/index.html')),scene_sha256:sha(path.join(root,'build/viewer-scene.json')),checker_sha256:sha(__filename),original_vertices_normals_and_triangles:true,flush_feature_probes:true,approved_thickness_domains_and_negative_controls:true,exact_native_material_volumes:true,no_raised_relief:true,max_material_groups:4,geometry_cached:true,checked};
fs.writeFileSync(path.join(out,'geometry.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
