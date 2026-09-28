// Regression: recessed color volumes retain their native height in one 3MF.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve(__dirname,'../build/slim-flush/viewer-tests');fs.mkdirSync(out,{recursive:true});
require('esbuild').buildSync({stdin:{contents:"export * from './printing.js'; export {unzipSync,strFromU8} from 'three/addons/libs/fflate.module.js';",resolveDir:__dirname},bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'printing.cjs')});
const {mesh3MF,selectedParts,unzipSync,strFromU8}=require(path.join(out,'printing.cjs'));
function box(x,y,z,w,l,h){
 const p=[[x,y,z],[x+w,y,z],[x+w,y+l,z],[x,y+l,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+l,z+h],[x,y+l,z+h]],f=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],b=Buffer.alloc(84+50*f.length);b.writeUInt32LE(f.length,80);
 for(const [i,t] of f.entries())for(let j=0;j<3;j++)for(let a=0;a<3;a++)b.writeFloatLE(p[t[j]][a],84+50*i+12+12*j+4*a);
 return b.toString('base64');
}
const body=box(100,-40,6.3,20,30,8.1),inlay=box(101,-39,14.4,2,3,.4);
const part={id:'left-frame-handheld',side:'left',style:'handheld',path:'whole.stl',stl:body,colors:{body:'#abcdef',detail:'#123456',accent:'#ff0000',secondary:'#00ff00'},material_parts:[{role:'body',path:'body.stl',stl:body},{role:'detail',path:'detail.stl',stl:inlay}]};
const result=mesh3MF(part),zip=unzipSync(result.bytes),xml=strFromU8(zip['3D/3dmodel.model']);
assert.equal(result.material_parts.length,2);assert.deepEqual(result.translation_mm.map(v=>Math.round(v*1e5)/1e5),[-90,50,-6.3]);
assert.match(strFromU8(zip['[Content_Types].xml']),/<Default Extension="config" ContentType="application\/xml"\/>/);
assert.match(xml,/<basematerials id="1">/);assert.doesNotMatch(xml,/paint_color|colorgroup/);
const objects=[...xml.matchAll(/<object\b([^>]*)>([\s\S]*?)<\/object>/g)];assert.equal(objects.length,3);
assert.match(objects[0][1],/pindex="0"/);assert.match(objects[1][1],/pindex="1"/);
const points=objects.slice(0,2).map(m=>[...m[2].matchAll(/<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"\/>/g)].map(v=>v.slice(1).map(Number)));
assert.ok(Math.abs(Math.min(...points[0].map(v=>v[2])))<1e-6);
assert.ok(Math.abs(Math.min(...points[1].map(v=>v[2]))-8.1)<1e-6,'Inlay must retain its height, not fall independently onto the bed');
assert.match(objects[2][2],/<component objectid="2"\/><component objectid="3"\/>/);assert.match(xml,/<build><item objectid="4"\/><\/build>/);
assert.equal(result.triangles,24);assert.equal(result.role_triangles.find(r=>r.role==='detail').color,'#123456');
assert.throws(()=>mesh3MF({...part,material_parts:undefined}),/Native flush materials unavailable/);
assert.throws(()=>mesh3MF({...part,material_parts:[part.material_parts[0],part.material_parts[0]]}),/Invalid native material role/);
const plain=mesh3MF({...part,style:'smooth',material_parts:undefined});assert.equal(plain.material_parts.length,1);
const registry={assets:{},supports:['cradle']},configuration={cases:{},frames:{}};
for(const side of ['left','right']){
 configuration.cases[side]={style:'rim',cover:side==='left',base_color:'#112233',plate_color:'#445566'};
 configuration.frames[side]={style:'handheld',color:'#abcdef',accents:{detail:'#123456',accent:'#ff0000',secondary:'#00ff00'}};
 for(const id of [`${side}-case-rim-base`,`${side}-case-rim-plate`,`${side}-frame-handheld`,`${side}-cradle`])registry.assets[id]={...part,id};
}
assert.deepEqual(selectedParts(configuration,registry,'both','complete').map(p=>p.id),['left-case-rim-base','left-case-rim-plate','left-frame-handheld','left-cradle','right-case-rim-base','right-case-rim-plate','right-cradle']);
assert.deepEqual(selectedParts(configuration,registry,'left','shells').map(p=>p.id),['left-case-rim-base','left-case-rim-plate','left-frame-handheld']);
console.log('PASS: native material objects, one shared 3MF placement, exact HEX roles, missing-material rejection, fallback and print scopes');
