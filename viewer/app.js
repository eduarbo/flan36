// SPDX-License-Identifier: GPL-3.0-or-later
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';

import {copy,check,normalize} from './config.js';
import {printKit} from './printing.js';
import {createAppearance,setColor,savedKey} from './appearance.js';
import {restoreConfiguration} from './storage.js';
import {enhanceColorInput} from './color-input.js';
import {createKeycapColors} from './keycap-colors.js';
import {createExplorer,partInfo} from './explorer.js';
import {createPreviewRenderer} from './previews.js';
import {createFrameFinishes,framePalette,finishes} from './finishes.js';

async function start(){
const $=id=>document.getElementById(id);
const compressed=Uint8Array.from(atob($('scene-data').textContent),c=>c.charCodeAt(0));
const data=JSON.parse(await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
for(const node of document.querySelectorAll('[data-measurement]'))node.textContent=String(data.measurements[node.dataset.measurement]);
const catalog=data.catalog;let configuration=normalize(catalog.default_configuration,catalog);
let restored=false,storageMessage='';try{const saved=restoreConfiguration(localStorage,catalog);if(saved.configuration){configuration=saved.configuration;restored=true;}storageMessage=saved.message;}catch(e){storageMessage='Device storage unavailable; use JSON to restore.';}
const variants=new Map(catalog.variants.map(v=>[v.id,v]));
const labels={base:'Bases',plate:'Plates',lid:'Frames / covers',keycaps:'Keycaps',switches:'Switches',pcb:'PCB',battery:'Batteries',mcu:'Controllers',display:'Displays',connectors:'Connectors',supports:'Supports',fasteners:'Fasteners / feet'};
const state={half:'both',layers:Object.fromEntries(Object.keys(labels).map(k=>[k,true])),explode:0,view:'iso'};
const directions={iso:[.35,1.6,1.75],top:[0,1,.0001],front:[0,0,1],back:[0,0,-1],right:[1,0,0],left:[-1,0,0],bottom:[0,-1,.0001]};
const scene=new THREE.Scene();scene.background=new THREE.Color('#edf0e9');
const camera=new THREE.OrthographicCamera(-180,180,100,-100,.1,3000);
const canvas=$('canvas');
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});}
catch(error){$('error').hidden=false;$('error').textContent='WebGL 2 could not start. Use a current Safari, Chrome or Firefox browser, or download the STEP files from the guide.';throw error;}
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.outputColorSpace=THREE.SRGBColorSpace;
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=false;controls.minZoom=.2;controls.maxZoom=14;
controls.minPolarAngle=0;controls.maxPolarAngle=Math.PI;
controls.touches.ONE=THREE.TOUCH.ROTATE;controls.touches.TWO=THREE.TOUCH.DOLLY_PAN;
scene.add(new THREE.HemisphereLight('#ffffff','#9cafa0',2));
for(const [pos,power] of [[[20,250,160],2.4],[[-220,100,-180],1.1],[[360,30,20],.7]]){
  const light=new THREE.DirectionalLight('#ffffff',power);light.position.fromArray(pos);scene.add(light);
}

function decode(text,Type){const bytes=Uint8Array.from(atob(text),c=>c.charCodeAt(0));return new Type(bytes.buffer);}
const geometries=new Map();
function geometryFor(id){
  if(!id)return undefined;
  if(geometries.has(id))return geometries.get(id);
  const g=data.geometries[id];if(!g)throw Error('Geometry unavailable: '+id);
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(decode(g.positions,Float32Array),3));
  geometry.setAttribute('normal',new THREE.BufferAttribute(decode(g.normals,Float32Array),3));
  geometry.setIndex(new THREE.BufferAttribute(decode(g.indices,Uint32Array),1));
  if(g.groups)for(const group of g.groups)geometry.addGroup(group.start,group.count,group.materialIndex);
  geometry.computeBoundingBox();geometries.set(id,geometry);return geometry;
}
const materials=new Map();
function material(color){
  if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.78,metalness:0}));
  return materials.get(color);
}
const frameFinish=createFrameFinishes(geometryFor,material);
const objects=[];const hiddenObjects=new Set();
const matchesPart=(o,ref)=>ref&&o.userData.group===ref.group&&(!ref.side||o.userData.side===ref.side)&&(!ref.key||o.userData.key===ref.key)&&(ref.objectIndex===undefined||o.userData.objectIndex===ref.objectIndex);
for(const part of data.parts){
  let geometry=geometryFor(part.geometry),mat=part.materials?part.materials.map(material):material(part.color);
  if(part.primitive){
    const p=part.primitive;
    if(p.kind==='cylinder')geometry=new THREE.CylinderGeometry(p.radius,p.radius,p.height,32);
    else if(p.kind==='box')geometry=new THREE.BoxGeometry(...p.size);
    else{
      geometry=new THREE.PlaneGeometry(p.size[0],p.size[2]);geometry.rotateX(-Math.PI/2);
      const art=document.createElement('canvas');art.width=128;art.height=300;
      const ctx=art.getContext('2d');ctx.fillStyle=part.color;ctx.fillRect(0,0,128,300);
      ctx.fillStyle='#294234';ctx.textAlign='center';ctx.font='23px monospace';
      p.text.split(' / ').forEach((text,i)=>ctx.fillText(text,64,65+i*87));
      const texture=new THREE.CanvasTexture(art);texture.colorSpace=THREE.SRGBColorSpace;
      mat=new THREE.MeshBasicMaterial({map:texture});
    }
  }
  const mesh=new THREE.Mesh(geometry,mat);mesh.name=part.name;
  mesh.position.fromArray(part.position);mesh.rotation.y=THREE.MathUtils.degToRad(part.angle_deg);
  mesh.userData={objectIndex:objects.length,group:part.group,side:part.side,base:[...part.position],explode:part.explode_mm,key:part.key_ref};
  if(part.part_id)mesh.userData.part_id=part.part_id;
  if(Number.isInteger(part.battery_lead_index))mesh.userData.battery_lead_index=part.battery_lead_index;
  if(part.name.includes('Electronics cover'))mesh.userData.frame_style=configuration.frames[part.side].style;
  objects.push(mesh);scene.add(mesh);
}
// Runtime scene uses x=CAD x, y=CAD z, z=CAD y; right-hand meshes are not mirrored again.
let explorer,appearance,keycapColors,renderFrame=0;
function render(){if(renderFrame)return;renderFrame=requestAnimationFrame(()=>{renderFrame=0;explorer?.update();renderer.render(scene,camera);});}
let orbiting=false;
controls.addEventListener('start',()=>{orbiting=true;explorer?.motion(true);});controls.addEventListener('end',()=>{orbiting=false;explorer?.motion(false);});
controls.addEventListener('change',()=>{
  if(orbiting&&state.view!=='iso'&&camera.position.clone().sub(controls.target).normalize().distanceTo(new THREE.Vector3(...directions[state.view]).normalize())>.001){
    state.view='iso';$('view').value='iso';for(const button of document.querySelectorAll('[data-view]'))button.setAttribute('aria-pressed',String(button.dataset.view==='iso'));
  }
  if(!orbiting)explorer?.cameraChanged();
  render();
});
let halfHeight=100;
function resize(){
  const {width,height}=canvas.getBoundingClientRect();
  renderer.setSize(width,height,false);const aspect=width/height;
  camera.left=-halfHeight*aspect;camera.right=halfHeight*aspect;camera.top=halfHeight;camera.bottom=-halfHeight;
  camera.updateProjectionMatrix();explorer?.layoutChanged();render();
}
new ResizeObserver(()=>fit()).observe(canvas);

function visibleBounds(){
  const box=new THREE.Box3();for(const o of objects)if(o.visible)box.union(new THREE.Box3().setFromObject(o));
  if(box.isEmpty())box.set(new THREE.Vector3(0,0,0),new THREE.Vector3(300,20,98));
  return box;
}
function fit(direction){
  const box=visibleBounds(),center=box.getCenter(new THREE.Vector3());
  const d=direction?new THREE.Vector3(...direction):camera.position.clone().sub(controls.target);
  camera.position.copy(center).add(d.normalize().multiplyScalar(500));controls.target.copy(center);
  camera.zoom=1;controls.update();camera.updateMatrixWorld();
  const right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0),up=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1);
  let w=0,h=0;
  for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
    const v=new THREE.Vector3(x,y,z).sub(center);w=Math.max(w,Math.abs(v.dot(right)));h=Math.max(h,Math.abs(v.dot(up)));
  }
  const aspect=canvas.clientWidth/canvas.clientHeight;halfHeight=Math.max(h,w/aspect,10)*1.13;resize();
}
function sync(){
  explorer?.invalidate();
  for(const o of objects){
    o.visible=o.userData.installed!==false&&!hiddenObjects.has(o.userData.objectIndex)&&state.layers[o.userData.group]&&(state.half==='both'||state.half===o.userData.side);
    o.position.fromArray(o.userData.base);o.position.y+=o.userData.explode*state.explode;
  }
  $('half').value=state.half;$('view').value=state.view;$('explode').value=Math.round(state.explode*100);
  $('explosion').textContent=Math.round(state.explode*100)+' %';
  for(const key of Object.keys(labels)){
    const nodes=objects.filter(o=>o.userData.group===key&&o.userData.installed!==false),shown=nodes.filter(o=>state.layers[key]&&!hiddenObjects.has(o.userData.objectIndex)).length,input=$('layer-'+key);
    input.disabled=nodes.length===0;input.checked=shown>0;input.indeterminate=shown>0&&shown<nodes.length;input.parentElement.title=nodes.length?(shown?'Hide ':'Show ')+labels[key]:'No covers installed. Pick a frame to reinstall them.';
  }
  refreshPartVisibility();
  const count=objects.filter(o=>o.visible).length;
  $('status').textContent=`Rev${data.revision} · ${count} visible components${state.explode?' · Exploded view':''}`;
  for(const button of document.querySelectorAll('[data-view]'))button.setAttribute('aria-pressed',String(button.dataset.view===state.view));
  const isComplete=state.half==='both'&&state.explode===0&&Object.values(state.layers).every(Boolean)&&hiddenObjects.size===0;
  $('complete').setAttribute('aria-pressed',String(isComplete));
  $('inside').setAttribute('aria-pressed',String(!state.layers.base&&!state.layers.lid&&state.layers.pcb));
  $('stack').setAttribute('aria-pressed',String(!state.layers.base&&!state.layers.pcb&&state.layers.mcu));
  render();
}
function reset(){
  hiddenObjects.clear();state.half='both';state.explode=0;state.view='iso';
  for(const key of Object.keys(labels))state.layers[key]=true;
  sync();fit(directions.iso);
}
function setCollapsed(value){
  document.querySelector('main').classList.toggle('detail-collapsed',value);$('collapse-detail').setAttribute('aria-expanded',String(!value));$('collapse-detail').textContent=value?'›':'‹';explorer?.layoutChanged();
}
function openPanel(id,section=id){
  setCollapsed(false);
  for(const name of ['cases','frames','themes','keycaps','battery','files','about'])$('panel-'+name).hidden=id!==name;
  for(const button of document.querySelectorAll('.part-item'))button.setAttribute('aria-expanded',String(button.dataset.group===section));
  for(const name of ['themes','files','about'])$('nav-'+name).setAttribute('aria-expanded',String(name===section));
  $('inspector').scrollTop=0;appearance?.sync();keycapColors?.sync();
}
$('collapse-detail').onclick=()=>setCollapsed($('collapse-detail').getAttribute('aria-expanded')==='true');
for(const name of ['themes','files','about'])$('nav-'+name).onclick=()=>{if(name!=='files')explorer?.clear();openPanel(name);};
$('layers').replaceChildren();
for(const [id,label] of Object.entries(labels)){
  const row=document.createElement('div');row.className='part-row';row.dataset.group=id;
  const button=document.createElement('button');button.type='button';button.className='part-item';button.dataset.group=id;button.id='part-'+id;button.setAttribute('aria-expanded',String(id==='lid'));button.setAttribute('aria-controls','inspector');button.title=partInfo[id].name;button.setAttribute('aria-label',partInfo[id].name);
  const item=objects.find(o=>o.userData.group===id),color='#'+(Array.isArray(item.material)?item.material[0]:item.material).color.getHexString();
  const dot=document.createElement('span');dot.className='part-anchor';dot.dataset.group=id;dot.style.setProperty('--part-color',color);
  const name=document.createElement('span');name.className='part-name';name.textContent=partInfo[id].short;button.append(dot,name);
  const ref=()=>({group:id,side:state.half==='both'?null:state.half});
  row.onpointerenter=e=>{if(e.pointerType!=='touch')explorer.highlight(ref());};row.onpointerleave=()=>explorer.highlight(null);
  row.onfocusin=()=>explorer.highlight(ref());row.onfocusout=e=>{if(!row.contains(e.relatedTarget))explorer.highlight(null);};
  button.onclick=()=>explorer.select(ref());
  const visibility=document.createElement('label');visibility.className='visibility';visibility.title='Show / hide '+label;
  const input=document.createElement('input');input.type='checkbox';input.id='layer-'+id;input.checked=true;input.setAttribute('aria-label','Show '+label);
  input.addEventListener('change',()=>{state.layers[id]=input.checked;if(input.checked)for(const o of objects)if(o.userData.group===id)hiddenObjects.delete(o.userData.objectIndex);sync();});
  const eye=document.createElement('span');eye.className='eye';eye.innerHTML='<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.7"/><path class="eye-slash" d="m3 3 18 18"/></svg>';eye.setAttribute('aria-hidden','true');visibility.append(input,eye);
  row.append(button,visibility);$('layers').append(row);
}
$('half').addEventListener('change',e=>{state.half=e.target.value;sync();fit();});
function chooseView(view){state.view=view;sync();fit(directions[view]);}
$('view').addEventListener('change',e=>chooseView(e.target.value));
for(const button of document.querySelectorAll('[data-view]'))button.onclick=()=>chooseView(button.dataset.view);
$('explode').addEventListener('input',e=>{state.explode=Number(e.target.value)/100;sync();fit();});
$('complete').onclick=reset;$('reset').onclick=()=>{reset();$('view-feedback').textContent='View and layers reset. Your parts are unchanged.';};$('fit').onclick=()=>{fit();$('view-feedback').textContent=objects.some(o=>o.visible)?'Visible parts centered and fitted.':'Nothing visible. Show a layer or choose Assembled.';};
$('inside').onclick=()=>{reset();for(const k of ['base','plate','lid','keycaps','switches','fasteners'])state.layers[k]=false;sync();fit();};
$('stack').onclick=()=>{reset();state.half='left';state.explode=.55;for(const k of Object.keys(labels))state.layers[k]=['battery','mcu','display','supports','connectors'].includes(k);sync();fit();};
$('credits').onclick=()=>$('licenses').showModal();$('close-credits').onclick=()=>$('licenses').close();
canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();$('error').hidden=false;$('error').textContent='Graphics context lost. Reload the page to restore the viewer.';});
$('print-kit').onclick=async()=>{const b=$('print-kit');b.disabled=true;try{const {bytes,manifest}=await printKit(configuration,data.printing,{half:$('print-half').value,scope:$('print-scope').value,progress:(i,n)=>b.textContent=`Preparing ${i} / ${n}…`});const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'})),a=document.createElement('a');a.href=url;a.download=`Flan36-${manifest.half}-${manifest.scope}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);$('print-status').textContent=`${manifest.parts.length} printed parts exported. See the included joining instructions.`;}catch(e){$('print-status').textContent='Export failed: '+e.message;}finally{b.disabled=false;b.textContent='Download print kit';}};
$('glb').onclick=async()=>{
  const button=$('glb');button.disabled=true;button.textContent='Preparing GLB…';
  try{
    const assembly=new THREE.Group();assembly.name=`Flan36 rev${data.revision} · nominal`;assembly.scale.setScalar(.001);
    for(const object of objects){if(object.userData.installed===false)continue;const clone=object.clone();clone.visible=true;clone.position.fromArray(object.userData.base);assembly.add(clone);}
    assembly.userData={configuration:copy(configuration),units:'metres',source:'https://github.com/eduarbo/flan36',limitations:data.limits,
      attribution:'Flan36 / Eduardo Ruiz, derived from Piantor by beekeeb (GPL-3.0); KLP Lame keycaps by braindefender (CC-BY-SA-4.0), unchanged meshes, placed and coloured. Choc models by keyswitch-kicad-library contributors (MIT); reset and power switch geometry by KiCad (CC-BY-SA-4.0 with library exception).',
      licenses:['https://www.gnu.org/licenses/gpl-3.0.html','https://creativecommons.org/licenses/by-sa/4.0/'],
      component_sources:'https://github.com/eduarbo/flan36/blob/main/components/sources.json',
      component_licenses:'https://github.com/eduarbo/flan36/blob/main/components/README.md',
      keycap_source:'https://github.com/braindefender/KLP-Lame-Keycaps/tree/4a67a824232d3054c61599ea047c56a340faaba2'};
    const buffer=await new GLTFExporter().parseAsync(assembly,{binary:true,onlyVisible:true});
    const url=URL.createObjectURL(new Blob([buffer],{type:'model/gltf-binary'}));const link=document.createElement('a');
    link.href=url;link.download=`Flan36-rev${data.revision}-assembled.glb`;link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
    button.textContent='GLB downloaded';
  }catch(error){button.textContent='Export failed; use STEP files';console.error(error);}
  finally{button.disabled=false;}
};
const message=(text,error=false)=>{$('config-status').textContent=text;$('config-status').dataset.error=String(error);};
const targetKeys=()=>Object.entries(catalog.layout).flatMap(([side,keys])=>keys.filter(k=>{
  const t=$('key-target').value;
  return t==='all'||t==='thumbs'&&k.row===3||t===`row-${k.row}`||t===`${side}:${k.ref}`;
}).map(k=>[side,k]));
for(const [value,label] of [['all','All keys'],['row-0','Top row'],['row-1','Home row'],['row-2','Bottom row'],['thumbs','Thumbs']])$('key-target').add(new Option(label,value));
for(const [side,keys] of Object.entries(catalog.layout))for(const k of keys)$('key-target').add(new Option(`${side==='left'?'Left':'Right'} ${k.ref}`,`${side}:${k.ref}`));
for(const v of catalog.variants)$('key-variant').add(new Option(v.label+(v.status==='unqualified'?' · no qualified position':''),v.id));
$('key-variant').value='choc_stem_choc_size_normal';
function candidate(id,turn){const cfg=copy(configuration);for(const [side,k] of targetKeys())cfg.keycaps[side][k.ref]={...cfg.keycaps[side][k.ref],variant:id,rotation_deg:turn};return cfg;}
function updateChoices(){
  const v=variants.get($('key-variant').value),old=Number($('key-rotation').value);
  $('key-rotation').replaceChildren(...v.rotations_deg.map(a=>new Option(a+'°',String(a))));
  if(v.rotations_deg.includes(old))$('key-rotation').value=String(old);
  const turn=Number($('key-rotation').value);
  for(const option of $('key-variant').options){
    const item=variants.get(option.value),rotation=item.rotations_deg.includes(turn)?turn:item.rotations_deg[0];
    // Fast reference-position gate, then exact combination check on Apply.
    option.disabled=!targetKeys().every(([side,k])=>item.qualified_reference_positions.some(p=>p.side===side&&p.key===k.ref&&p.rotation_deg===rotation));
  }
  const result=check(candidate(v.id,turn),catalog);$('apply-keys').disabled=result.errors.length>0;
  $('key-fit').textContent=result.errors.length?result.errors[0]:`Conservative clearance ≥ ${result.minimum.toFixed(2)} mm. Physical seating and travel untested.`;
}
function applyConfiguration(next){
  const result=check(next,catalog);if(result.errors.length)throw Error(result.errors[0]);
  next=normalize(next,catalog);
  for(const o of objects){
    const {side,key,group}=o.userData;
    if(group==='base'||group==='plate'){const style=next.cases[side].style;o.geometry=geometryFor(`mechanical/revI/${side}-case-${style}-${group}.stl`);o.material=material(next.cases[side][group+'_color']);o.userData.case_style=style;}
    if(group==='lid')o.userData.installed=next.cases[side].cover;
    if(group==='keycaps'){
      const choice=next.keycaps[side][key],v=variants.get(choice.variant),k=catalog.layout[side].find(k=>k.ref===key);
      o.material=material(choice.color);o.userData.color=choice.color;o.geometry=geometryFor(v.path);o.rotation.y=THREE.MathUtils.degToRad(k.angle+choice.rotation_deg);o.userData.base[1]=v.seating_z_mm;
      o.userData.variant=v.id;o.userData.cap_rotation_deg=choice.rotation_deg;
    }
    if(group==='lid'&&o.userData.frame_style!==undefined){
      const f=next.frames[side],finish=frameFinish(f.style,side,f.color,f.accents);o.geometry=finish.geometry;o.material=finish.material;o.userData.frame_style=f.style;o.userData.frame_palette=finish.palette;
    }
  }
  for(const o of objects)if(o.userData.group==='battery'){const id=next.batteries[o.userData.side];o.geometry=geometryFor(`mechanical/revI/${o.userData.side}-battery-${id}.stl`);o.userData.battery_profile=id;}
  for(const o of objects)if(Number.isInteger(o.userData.battery_lead_index)){const id=next.batteries[o.userData.side],wire=data.batteryLeadProfiles[`${o.userData.side}-${id}`].find(p=>p.index===o.userData.battery_lead_index);o.geometry=geometryFor(wire.geometry);o.material=material(wire.color);o.userData.battery_profile=id;}
  configuration=copy(next);sync();updateChoices();syncConfigurationUI();try{localStorage.setItem(savedKey,JSON.stringify(configuration));message('Saved on this device.');}catch(e){message('Configuration applied. Device storage unavailable; save JSON to keep it.');}
}
function chooseKeyTarget(){
  const target=targetKeys();if(target.length===1){const [side,k]=target[0],choice=configuration.keycaps[side][k.ref];$('key-variant').value=choice.variant;updateChoices();$('key-rotation').value=String(choice.rotation_deg);}
  updateChoices();
}
$('key-target').onchange=chooseKeyTarget;$('key-variant').onchange=updateChoices;$('key-rotation').onchange=updateChoices;
$('apply-keys').onclick=()=>{try{applyConfiguration(candidate($('key-variant').value,Number($('key-rotation').value)));}catch(e){message(e.message,true);}};
let frameSide='both',caseSide='both';
const preview=createPreviewRenderer(renderer,geometryFor);
function card(id,label,src){
  const button=document.createElement('button');button.type='button';button.className='preview-card';button.dataset.choice=id;button.setAttribute('aria-pressed','false');
  const img=document.createElement('img');img.src=src;img.alt='';img.width=220;img.height=220;const text=document.createElement('span');text.textContent=label;button.append(img,text);button.setAttribute('aria-label',label);return button;
}
function frameTargets(){return frameSide==='both'?['left','right']:[frameSide];}
function setFrameSide(side){frameSide=side;syncConfigurationUI();}
function applyFrame(change){
  const cfg=copy(configuration);for(const side of frameTargets()){if(change.style&&!cfg.cases[side].match_frame){const f=cfg.frames[side],p=framePalette(f.style);if(f.color===p.body&&Object.entries(f.accents).every(([k,v])=>v===p[k])){const np=framePalette(change.style);f.color=np.body;f.accents=Object.fromEntries(['detail','accent','secondary'].map(k=>[k,np[k]]));}}Object.assign(cfg.frames[side],change);if(cfg.cases[side].match_frame){cfg.cases[side].base_color=cfg.frames[side].color;if(cfg.cases[side].style==='level')cfg.cases[side].plate_color=cfg.frames[side].color;}if(change.style)cfg.cases[side].cover=true;}
  try{
    applyConfiguration(cfg);
    // A new style must be visible even when coming from the internal stack study.
    if(change.style){for(const o of objects)if(o.userData.group==='lid'&&frameTargets().includes(o.userData.side))hiddenObjects.delete(o.userData.objectIndex);const needsFit=state.explode>0||!state.layers.lid||frameSide==='both'&&state.half!=='both'||state.half!=='both'&&!frameTargets().includes(state.half);
      if(needsFit){for(const k of Object.keys(state.layers))state.layers[k]=true;state.explode=0;state.half=frameSide;sync();fit();}else sync();}
  }catch(e){message(e.message,true);}
}
function caseTargets(){return caseSide==='both'?['left','right']:[caseSide];}
for(const [id,spec] of Object.entries(catalog.case_styles)){
  const entries=['base','plate'].map(group=>({path:`mechanical/revI/left-case-${id}-${group}.stl`,material:material(spec[group+'_color'])}));
  // Every thumbnail uses that style's exported parts, with the same camera.
  const button=card(id,spec.label,preview.image(entries,[.15,.8,1],{width:360,height:250}));button.dataset.case=id;button.title=spec.description;
  const img=button.querySelector('img');img.width=360;img.height=250;img.alt=spec.description;
  button.onclick=()=>{const cfg=copy(configuration);for(const side of caseTargets()){const cs=cfg.cases[side],old=catalog.case_styles[cs.style];if(!cs.match_frame&&cs.base_color===old.base_color&&cs.plate_color===old.plate_color){cs.base_color=spec.base_color;cs.plate_color=spec.plate_color;}cs.style=id;if(cs.match_frame&&id==='level')cs.plate_color=cfg.frames[side].color;}applyConfiguration(cfg);for(const o of objects)if(['base','plate'].includes(o.userData.group)&&caseTargets().includes(o.userData.side))hiddenObjects.delete(o.userData.objectIndex);state.layers.base=state.layers.plate=true;state.half=caseSide;sync();fit();};
  $('case-grid').append(button);
}
for(const button of $('case-target').children)button.onclick=()=>{caseSide=button.dataset.side;syncConfigurationUI();};
$('case-cover').onchange=e=>{const cfg=copy(configuration);for(const side of caseTargets())cfg.cases[side].cover=e.target.checked;applyConfiguration(cfg);};
for(const id of ['cartridge','arcade','mecha','kintsugi','handheld','tv','cyberpunk','smooth','bevel','facet']){
  const finish=frameFinish(id,'left'),button=card(id,catalog.frame_styles[id],preview.image([finish],[0,1,.16],{width:220,height:360,up:[0,0,-1]}));button.dataset.style=id;
  const img=button.querySelector('img');img.width=220;img.height=360;img.alt=catalog.frame_styles[id]+' frame in its original palette';
  button.onclick=()=>applyFrame({style:id});$('frame-grid').append(button);
}
for(const button of $('frame-target').children)button.onclick=()=>setFrameSide(button.dataset.side);
for(const [color,label] of [['#304d4e','Deep teal'],['#ded8c6','Linen'],['#ad7656','Clay'],['#363b3b','Graphite']]){
  const button=document.createElement('button');button.type='button';button.dataset.color=color;button.title=label;button.setAttribute('aria-label',label);button.setAttribute('aria-pressed','false');button.style.setProperty('--swatch',color);button.onclick=()=>applyFrame({color});$('swatches').append(button);
}
const frameHex=enhanceColorInput($('frame-color'));
$('frame-color').oninput=e=>applyConfiguration(setColor(configuration,frameTargets(),'frame','body',e.target.value));
$('theme-colors').onclick=()=>{const cfg=copy(configuration);for(const side of frameTargets()){const p=framePalette(cfg.frames[side].style);cfg.frames[side].color=p.body;cfg.frames[side].accents=Object.fromEntries(['detail','accent','secondary'].map(k=>[k,p[k]]));if(cfg.cases[side].match_frame){cfg.cases[side].base_color=p.body;if(cfg.cases[side].style==='level')cfg.cases[side].plate_color=p.body;}}applyConfiguration(cfg);};
for(const [id,label] of [['default','Original'],['normal-sculpted','Sculpted Normal'],['saddle-sculpted','Sculpted Saddle']]){
  const entries=['K01','K11','K21'].map((key,i)=>({path:variants.get(data.presets[id].keycaps.left[key].variant).path,rotation:data.presets[id].keycaps.left[key].rotation_deg,center:[(i-1)*20,0,0]}));
  const button=card(id,label,preview.image(entries,[.5,1,2]));button.dataset.preset=id;
  button.onclick=()=>{const cfg=copy(configuration);for(const [side,keys] of Object.entries(cfg.keycaps))for(const ref of Object.keys(keys))cfg.keycaps[side][ref]={...data.presets[id].keycaps[side][ref],color:keys[ref].color};try{applyConfiguration(cfg);}catch(e){message(e.message,true);}};$('key-presets').append(button);
}
preview.finish();
for(const [id,spec] of Object.entries(catalog.battery_profiles)){const b=document.createElement('button');b.type='button';b.dataset.battery=id;b.textContent=spec.label;b.title=`${spec.width} × ${spec.length} × ${spec.height} mm`;b.onclick=()=>{const c=copy(configuration);for(const side of ['left','right'])c.batteries[side]=id;applyConfiguration(c);};$('battery-options').append(b);}
function syncConfigurationUI(){
  const cases=caseTargets().map(side=>configuration.cases[side]),caseStyles=new Set(cases.map(c=>c.style));
  $('case-current').textContent=caseStyles.size===1?catalog.case_styles[cases[0].style].label:'Mixed cases';
  for(const b of $('case-grid').children)b.setAttribute('aria-pressed',String(caseStyles.size===1&&caseStyles.has(b.dataset.case)));
  for(const b of $('case-target').children)b.setAttribute('aria-pressed',String(b.dataset.side===caseSide));
  $('case-cover').checked=cases.every(c=>c.cover);$('case-cover').indeterminate=cases.some(c=>c.cover)&&!cases.every(c=>c.cover);
  $('cover-state').textContent=cases.every(c=>c.cover)?'Covered':cases.every(c=>!c.cover)?'Exposed stack':'Mixed covers';
  for(const b of document.querySelectorAll('[data-battery]'))b.setAttribute('aria-pressed',String(['left','right'].every(side=>configuration.batteries[side]===b.dataset.battery)));
  const frames=frameTargets().map(side=>configuration.frames[side]),styles=new Set(frames.map(f=>f.style)),colors=new Set(frames.map(f=>f.color.toLowerCase()));
  for(const button of $('frame-target').children)button.setAttribute('aria-pressed',String(button.dataset.side===frameSide));
  for(const button of $('frame-grid').children)button.setAttribute('aria-pressed',String(styles.size===1&&styles.has(button.dataset.style)));
  $('frame-current').textContent=styles.size===1?catalog.frame_styles[frames[0].style]:'Mixed styles';
  $('color-current').textContent=colors.size===1?[...colors][0]:'Mixed colors';
  for(const button of $('swatches').children)button.setAttribute('aria-pressed',String(colors.size===1&&colors.has(button.dataset.color)));
  // The color input has no mixed state: its visible companion explicitly names it.
  $('frame-color').value=frames[0].color;$('frame-color').setAttribute('aria-label',colors.size===1?'Custom frame color':'Custom frame color; mixed colors, changing this applies to both halves');
  frameHex.sync(frames.map(f=>f.color));
  appearance?.sync();keycapColors?.sync();
  for(const button of $('key-presets').children){const preset=data.presets[button.dataset.preset];const same=Object.entries(configuration.keycaps).every(([side,keys])=>Object.entries(keys).every(([ref,c])=>c.variant===preset.keycaps[side][ref].variant&&c.rotation_deg===preset.keycaps[side][ref].rotation_deg));button.setAttribute('aria-pressed',String(same));}
}
function refreshPartVisibility(){
  for(const b of document.querySelectorAll('[data-solo-object]'))b.disabled=objects[Number(b.dataset.soloObject)].userData.installed===false;
  const installed=explorer?.selected&&objects.some(o=>o.userData.installed!==false&&matchesPart(o,explorer.selected));
  $('toggle-selection').disabled=$('isolate-selection').disabled=!installed;
  for(const input of document.querySelectorAll('[data-object-visibility]')){const o=objects[Number(input.dataset.objectVisibility)];input.checked=o.visible;input.disabled=o.userData.installed===false;}
  if(explorer?.selected){const visible=objects.some(o=>o.visible&&matchesPart(o,explorer.selected));$('toggle-selection').textContent=visible?'Hide':'Show';}
}
function populatePartVisibility(ref){
  const list=$('part-visibility-list');list.replaceChildren();const matching=objects.filter(o=>o.userData.group===ref.group);
  $('individual-count').textContent=String(matching.length);
  for(const o of matching){
    const row=document.createElement('div');row.className='individual-row';
    const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.dataset.objectVisibility=String(o.userData.objectIndex);input.checked=o.visible;input.disabled=o.userData.installed===false;
    const text=document.createElement('span');text.textContent=o.userData.side.charAt(0).toUpperCase()+o.userData.side.slice(1)+' · '+(o.userData.key||o.name.replace(/^(left|right)[ -·]*/i,''));
    input.setAttribute('aria-label','Show '+text.textContent);label.append(input,text);
    const current={group:o.userData.group,side:o.userData.side,key:o.userData.key,objectIndex:o.userData.objectIndex};
    input.onchange=()=>{if(input.checked){hiddenObjects.delete(o.userData.objectIndex);state.layers[o.userData.group]=true;if(state.half!==o.userData.side)state.half='both';}else hiddenObjects.add(o.userData.objectIndex);sync();};
    row.onpointerenter=e=>{if(e.pointerType!=='touch')explorer.highlight(current);};row.onpointerleave=()=>explorer.highlight(null);
    row.onfocusin=()=>explorer.highlight(current);row.onfocusout=e=>{if(!row.contains(e.relatedTarget))explorer.highlight(null);};
    const solo=document.createElement('button');solo.textContent='Solo';solo.title='Isolate '+text.textContent;solo.dataset.soloObject=String(o.userData.objectIndex);solo.disabled=o.userData.installed===false;solo.onclick=()=>isolate(current);
    row.append(label,solo);list.append(row);
  }
  const visible=objects.some(o=>o.visible&&matchesPart(o,ref));$('toggle-selection').textContent=visible?'Hide':'Show';
  refreshPartVisibility();
}
function isolate(ref){
  hiddenObjects.clear();state.half='both';for(const key of Object.keys(labels))state.layers[key]=true;
  for(const o of objects)if(!matchesPart(o,ref))hiddenObjects.add(o.userData.objectIndex);
  sync();fit();$('view-feedback').textContent='Showing only this selection. Show all restores the assembly.';
}
$('isolate-selection').onclick=()=>{if(explorer.selected)isolate(explorer.selected);};
$('toggle-selection').onclick=()=>{
  const ref=explorer.selected;if(!ref)return;const hide=objects.some(o=>o.visible&&matchesPart(o,ref));
  for(const o of objects)if(matchesPart(o,ref)){if(hide)hiddenObjects.add(o.userData.objectIndex);else{hiddenObjects.delete(o.userData.objectIndex);state.layers[o.userData.group]=true;}}
  if(!hide&&ref.side&&state.half!==ref.side)state.half='both';sync();
};
$('show-all').onclick=()=>{hiddenObjects.clear();state.half='both';for(const key of Object.keys(labels))state.layers[key]=true;sync();fit();$('view-feedback').textContent='All parts visible.';};
explorer=createExplorer({scene,camera,canvas,objects,requestRender:render,
  onSelect(ref){
    $('selection').hidden=false;$('selection').classList.toggle('compact',['lid','keycaps'].includes(ref.group));$('selection-meta').textContent=(ref.side?ref.side+' half':'Both halves')+(ref.key?' / '+ref.key:'');
    populatePartVisibility(ref);
    $('selection-title').textContent=partInfo[ref.group].name;$('selection-info').textContent=partInfo[ref.group].info;
    if(ref.group==='lid'){setFrameSide(ref.side||'both');openPanel('frames','lid');}
    else if(ref.group==='keycaps'){openPanel('keycaps','keycaps');$('key-details').open=true;if(ref.key)$('key-target').value=ref.side+':'+ref.key;else $('key-target').value='all';chooseKeyTarget();keycapColors?.focus(ref.side,ref.key);}
    else if(['base','plate'].includes(ref.group)){caseSide=ref.side||'both';syncConfigurationUI();openPanel('cases',ref.group);}
    else if(ref.group==='battery')openPanel('battery','battery');
    else openPanel('none',ref.group);
  },onClear(){$('selection').hidden=true;}
});
$('load-trigger').onclick=()=>$('load-config').click();
function downloadJSON(){const url=URL.createObjectURL(new Blob([JSON.stringify(configuration,null,2)+'\n'],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='Flan36-config.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
$('save-config').onclick=downloadJSON;
$('load-config').onchange=async e=>{try{const f=e.target.files[0];if(f){if(f.size>100000)throw Error('File too large. Choose a configuration JSON.');applyConfiguration(JSON.parse(await f.text()));}}catch(error){message(error.message,true);}finally{e.target.value='';}};
$('default-config').onclick=()=>applyConfiguration(catalog.default_configuration);
appearance=createAppearance({$,get:()=>configuration,apply:applyConfiguration,targets:kind=>kind==='case'?caseTargets():frameTargets(),preview,frameFinish,material,resize,catalog,geometryFor});
keycapColors=createKeycapColors({$,catalog,get:()=>configuration,apply:applyConfiguration,message});
applyConfiguration(configuration);
if(storageMessage)message(storageMessage,true);else if(restored)message('Restored your saved configuration.');
if(keycapColors.initialWarning)message(keycapColors.initialWarning,true);


resize();reset();openPanel('cases','base');

}
start().catch(error=>{document.getElementById('error').hidden=false;document.getElementById('error').textContent='Could not open the viewer: '+error.message;console.error(error);});
