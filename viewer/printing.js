// SPDX-License-Identifier: GPL-3.0-or-later
import {zipSync,strToU8} from 'three/addons/libs/fflate.module.js';
import {framePalette,finishes} from './finishes.js';
const utf8=x=>strToU8(typeof x==='string'?x:JSON.stringify(x,null,2)+'\n');
const decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const xml=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
export function selectedParts(config,registry,half='both',scope='shells'){
 const parts=[];for(const side of ['left','right']){if(half!=='both'&&side!==half)continue;const cs=config.cases[side],f=config.frames[side];for(const group of ['base','plate'])parts.push({...registry.assets[`${side}-case-${cs.style}-${group}`],side,colors:{body:cs[group+'_color']}});if(cs.cover)parts.push({...registry.assets[`${side}-frame-${f.style}`],side,style:f.style,colors:framePalette(f.style,f.color,f.accents)});if(scope==='complete')for(const id of registry.supports)parts.push({...registry.assets[`${side}-${id}`],side,colors:{body:'#78908a'}});}return parts;
}
function stlMesh(encoded){
 const bytes=decode(encoded);if(bytes.length<84)throw Error('Expected a binary STL.');
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),n=view.getUint32(80,true);
 if(!n||bytes.length!==84+50*n)throw Error('Expected a nonempty binary STL.');
 const vertexIds=new Map(),points=[],triangles=[],minimum=[Infinity,Infinity,Infinity];
 for(let t=0;t<n;t++){
  const ids=[];
  for(let j=0;j<3;j++){
   const p=[0,1,2].map(a=>view.getFloat32(84+t*50+12+j*12+a*4,true));
   if(!p.every(Number.isFinite))throw Error('Invalid STL coordinate.');
   p.forEach((v,a)=>minimum[a]=Math.min(minimum[a],v));
   const key=p.join(',');if(!vertexIds.has(key)){vertexIds.set(key,points.length);points.push(p);}ids.push(vertexIds.get(key));
  }
  triangles.push(ids);
 }
 return {points,triangles,minimum};
}
export function mesh3MF(part){
 if(part.style&&finishes.styles[part.style]&&!part.material_parts?.length)throw Error('Native flush materials unavailable: '+part.id);
 const inputs=part.material_parts?.length?part.material_parts:[{role:'body',path:part.path,sha256:part.sha256,stl:part.stl}];
 const seen=new Set(),materials=inputs.map((source,i)=>{
  const roleIndex=finishes.roles.indexOf(source.role);
  if(roleIndex<0||seen.has(source.role))throw Error('Invalid native material role: '+source.role);
  seen.add(source.role);return {...source,object_id:i+2,roleIndex,...stlMesh(source.stl)};
 });
 if(!seen.has('body'))throw Error('Frame body material unavailable.');
 const minimum=[0,1,2].map(a=>Math.min(...materials.map(p=>p.minimum[a])));
 // One shared transform for all material bodies: never drop inlays individually
 // onto the bed, which would destroy their mating registration.
 const shift=minimum.map((v,i)=>(i===2?0:10)-v),colors=finishes.roles.map(role=>part.colors[role]||part.colors.body);
 const objects=materials.map(p=>{
  const vertices=p.points.map(v=>`<vertex x="${v[0]+shift[0]}" y="${v[1]+shift[1]}" z="${v[2]+shift[2]}"/>`).join('');
  const faces=p.triangles.map(a=>`<triangle v1="${a[0]}" v2="${a[1]}" v3="${a[2]}"/>`).join('');
  return `<object id="${p.object_id}" type="model" name="${xml(part.id+'-'+p.role)}" pid="1" pindex="${p.roleIndex}"><mesh><vertices>${vertices}</vertices><triangles>${faces}</triangles></mesh></object>`;
 }).join('');
 const assemblyId=materials.length+2,assembly=`<object id="${assemblyId}" type="model" name="${xml(part.id)}"><components>${materials.map(p=>`<component objectid="${p.object_id}"/>`).join('')}</components></object>`;
 const model=`<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Application">Flan36</metadata><metadata name="Title">${xml(part.id)}</metadata><metadata name="Description">Native material volumes registered as one co-print assembly. Prototype geometry; verify process before slicing.</metadata><resources><basematerials id="1">${colors.map((c,i)=>`<base name="${finishes.roles[i]}" displaycolor="${c.toUpperCase()}FF"/>`).join('')}</basematerials>${objects}${assembly}</resources><build><item objectid="${assemblyId}"/></build></model>`;
 const settings=`<?xml version="1.0"?><config><object id="${assemblyId}"><metadata key="name" value="${xml(part.id)}"/>${materials.map(p=>`<part id="${p.object_id}" subtype="normal_part"><metadata key="name" value="${xml(p.role)}"/><metadata key="extruder" value="${p.roleIndex+1}"/></part>`).join('')}</object></config>`;
 const files={'[Content_Types].xml':utf8('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>'),'_rels/.rels':utf8('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'),'3D/3dmodel.model':utf8(model),'Metadata/model_settings.config':utf8(settings)};
 const material_parts=materials.map(p=>({role:p.role,object_id:p.object_id,source:p.path,source_sha256:p.sha256,color:colors[p.roleIndex],triangles:p.triangles.length}));
 return {bytes:zipSync(files,{level:6}),translation_mm:shift,triangles:materials.reduce((n,p)=>n+p.triangles.length,0),material_parts,
  role_triangles:finishes.roles.map((role,i)=>({role,count:materials.filter(p=>p.role===role).reduce((n,p)=>n+p.triangles.length,0),color:colors[i]}))};
}
export async function printKit(config,registry,{half='both',scope='shells',progress=()=>{}}={}){
 const selected=selectedParts(config,registry,half,scope),files={},records=[];
 for(const [i,p] of selected.entries()){progress(i+1,selected.length);await new Promise(requestAnimationFrame);const colored=mesh3MF(p);files[`STL/${p.id}.stl`]=decode(p.stl);files[`3MF/${p.id}.3mf`]=colored.bytes;for(const m of p.material_parts||[])files[`Materials/${p.id}/${m.role}.stl`]=decode(m.stl);records.push({id:p.id,side:p.side,quantity:1,source:p.path,source_sha256:p.sha256,colors:p.colors,translation_3mf_mm:colored.translation_mm,triangles:colored.triangles,role_triangles:colored.role_triangles,material_parts:colored.material_parts});}
 const manifest={schema:2,revision:'I',units:'mm',status:'Prototype geometry; physical fit and joining untested',half,scope,parts:records,configuration:config,joining:registry.joining,source:'https://github.com/eduarbo/flan36',license:'GPL-3.0-or-later',excludes:'Commercial electronics, cells, hardware, feet and KLP keycaps. View visibility and exploded offsets do not affect this kit.'};
 files['manifest.json']=utf8(manifest);files['Flan36-config.json']=utf8(config);files['READ-ME.txt']=utf8(`FLAN36 / PRINT KIT / mm\n\nSTL: exact native CAD exports in assembly coordinates.\n3MF: exact native material volumes as one registered assembly. A single shared\ntranslation places the body on Z=0 and preserves the recessed inlay positions.\nMaterials/: native role STLs in assembly coordinates for manual multipart import.\nOne file per physical part. No printer profile, G-code or verified print process.\n\nJOINING\nEach half: 3 M2x6 and 2 M2x4 screws; tap 1.7 mm pilot holes to M2.\nInstalled frame: 3 captive 2x3 mm magnets and 3 ferromagnetic 2x4 mm pins.\nCapture inserts during printing; inspect cavities and plan insertion pauses.\nNo clips are modeled. Complete printed set includes 3 washers per half.\n\nDecorated frames contain closed body/detail/accent/secondary material volumes.\nThese are co-printed regions, not separate fitted inserts. Import each 3MF as one\nassembly. For manual STL import, import all Materials/ files for a frame together\nas parts of one object and preserve their relative positions. The STL/ frame is\na complete single-color fallback.\n\nAdd filaments in body/detail/accent/secondary order using manifest HEX colors.\nVerify each material assignment and every sliced layer. Automatic slicer palette\nimport and printer-specific process settings are not qualified. Choose your actual\nfilaments and process before slicing.\n\nhttps://github.com/eduarbo/flan36/blob/main/docs/customize.md\nGPL-3.0-or-later; see repository LICENSE.\n`);
 return {bytes:zipSync(files,{level:6}),manifest};
}
