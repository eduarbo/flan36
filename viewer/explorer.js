// SPDX-License-Identifier: GPL-3.0-or-later
import * as THREE from 'three';

export const partInfo={
  lid:{name:'Display frame',short:'Frame',info:'Magnetic frame with captive steel targets and vertical release. Pick a design below; PCB and battery remain mechanically secured.'},
  keycaps:{name:'KLP Lamé keycaps',short:'Caps',info:'Original Choc-stem meshes. Choose a shape preset; color all keys, rows, columns or individual keys.'},
  display:{name:'nice!view display',short:'Display',info:'14 × 36 × 2.9 mm nominal nice!view. Illustrative screen content; flush frame details. The 6.09 mm connector stack is a dimensional candidate pending a physical fit test.'},
  base:{name:'Printed base',short:'Base',info:'Key-aligned local curves and a shared contour. Pick a real case variant below; native parts are editable in FreeCAD.'},
  plate:{name:'Switch plate',short:'Plate',info:'Holds the 36 Piantor switch positions and angles. Nominal plate height: 7.6 mm.'},
  switches:{name:'Choc switches',short:'Switch',info:'Licensed KiSwitch Choc v1 housings, pins and stems. Generic model; seating, travel and printed keycap stems need physical fit tests.'},
  pcb:{name:'PCB',short:'PCB',info:'Custom wireless board outline. Zero geometric DRC violations, but routing remains unfinished; this is not a manufacturing file.'},
  battery:{name:'LiPo battery',short:'Battery',info:'Adafruit 1570 and 301230 nominal profiles share the insulated case floor and captured cage. Choose a profile below. Verify actual pack, leads and insulation.'},
  mcu:{name:'nice!nano v2 controller',short:'MCU',info:'Nominal v2 reconstruction with separate PCB, ENIG pads, mid-mount USB-C, ICs and passives. Community outline dimensions; package detail inferred from official photos.'},
  supports:{name:'Insulating supports',short:'Mounts',info:'Cradle, display sled and controller supports. Retention is a nominal CAD proposal.'},
  connectors:{name:'Connectors & controls',short:'Ports',info:'Sockets, battery connector, reset and power-switch references. Final supplied dimensions and cabling remain open.'},
  fasteners:{name:'Fasteners & feet',short:'Feet',info:'Five internal M2 structural screws per half, three captive magnet stations and steel frame targets. Printed threads and magnetic holding force need coupons.'}
};

export function createExplorer({scene,camera,canvas,objects,onSelect,onClear,requestRender}){
  const $=id=>document.getElementById(id),main=canvas.closest('main'),path=$('part-link'),dot=$('part-link-dot'),svg=$('leader-lines');
  const ray=new THREE.Raycaster(),pointer=new THREE.Vector2(),overlay=new THREE.Group(),bounds=new Map(),highlights=new Map();
  scene.add(overlay);
  const glow=new THREE.MeshBasicMaterial({color:'#75bd86',transparent:true,opacity:.33,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2});
  const xray=new THREE.MeshBasicMaterial({color:'#39a9a4',transparent:true,opacity:.38,depthTest:false,depthWrite:false});
  const match=(o,ref)=>o.userData.installed!==false&&ref&&o.userData.group===ref.group&&(!ref.side||o.userData.side===ref.side)&&(!ref.key||o.userData.key===ref.key)&&(ref.objectIndex===undefined||o.userData.objectIndex===ref.objectIndex);
  const key=ref=>ref?[ref.group,ref.side||'',ref.key||'',ref.objectIndex??''].join(':'):'';
  const refOf=o=>({group:o.userData.group,side:o.userData.side,key:o.userData.key,objectIndex:o.userData.objectIndex});
  let selected=null,hovered=null,enabled=true,moving=false,down=null,pointers=new Set(),pickTimer=0,anchorTimer=0,anchor=null;
  let revision=0,boxRevision=-1,highlightStamp='',activeKey='',layoutDirty=true,layout;
  function refreshBounds(){
    if(boxRevision===revision)return;
    scene.updateMatrixWorld(true);
    for(const o of objects){if(!o.geometry.boundingBox)o.geometry.computeBoundingBox();bounds.set(o,o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld));}
    boxRevision=revision;
  }
  // Near-first bounding boxes stop triangle work once the closest hit is known.
  // Exported/displayed meshes are unchanged; there is no approximate hit mesh.
  function cast(){
    refreshBounds();const candidates=[],point=new THREE.Vector3();
    for(const o of objects)if(o.visible&&ray.ray.intersectBox(bounds.get(o),point))candidates.push({object:o,near:ray.ray.origin.distanceTo(point)});
    candidates.sort((a,b)=>a.near-b.near);let closest=null;
    for(const {object,near} of candidates){if(closest&&near>closest.distance+.001)break;const found=ray.intersectObject(object,false)[0];if(found&&(!closest||found.distance<closest.distance))closest=found;}
    return closest;
  }
  function hit(event){
    const rect=canvas.getBoundingClientRect();pointer.set((event.clientX-rect.left)/rect.width*2-1,1-(event.clientY-rect.top)/rect.height*2);camera.updateMatrixWorld();ray.setFromCamera(pointer,camera);return cast();
  }
  function surface(ref){
    if(!ref)return null;refreshBounds();camera.updateMatrixWorld();
    const list=objects.filter(o=>o.visible&&match(o,ref)).slice(0,3);
    for(const o of list){
      const box=bounds.get(o),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
      // One active component only, after input settles. Never searched during orbit.
      for(const point of [center,new THREE.Vector3(box.min.x+size.x*.08,box.max.y,center.z),new THREE.Vector3(box.max.x-size.x*.08,box.max.y,center.z)]){
        const projected=point.clone().project(camera);if(Math.abs(projected.x)>1||Math.abs(projected.y)>1||Math.abs(projected.z)>1)continue;
        ray.setFromCamera(new THREE.Vector2(projected.x,projected.y),camera);const found=cast();
        if(found&&match(found.object,ref))return{point:found.point.clone(),object:found.object};
      }
    }
    return null;
  }
  function scheduleAnchor(){
    clearTimeout(anchorTimer);anchor=null;path.setAttribute('hidden','');dot.setAttribute('hidden','');
    if(enabled&&!moving&&(hovered||selected))anchorTimer=setTimeout(()=>{anchorTimer=0;if(!moving){anchor=surface(hovered||selected);if(!anchor&&hovered){refreshBounds();const o=objects.find(o=>match(o,hovered));if(o)anchor={point:bounds.get(o).getCenter(new THREE.Vector3()),object:o};}requestRender();}},70);
  }
  function setHover(ref,hitPoint){
    if(key(ref)===key(hovered))return;hovered=ref;
    if(hitPoint){clearTimeout(anchorTimer);anchor=hitPoint;}else scheduleAnchor();
    requestRender();
  }
  function select(ref,hitPoint){selected=ref;hovered=null;onSelect(ref);if(hitPoint){clearTimeout(anchorTimer);anchor=hitPoint;}else scheduleAnchor();requestRender();}
  function clear(){selected=null;hovered=null;anchor=null;clearTimeout(anchorTimer);onClear();requestRender();}
  canvas.addEventListener('pointerdown',e=>{pointers.add(e.pointerId);clearTimeout(pickTimer);hovered=null;down=pointers.size===1?{id:e.pointerId,x:e.clientX,y:e.clientY,moved:false}:null;});
  canvas.addEventListener('pointermove',e=>{
    if(down&&Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)down.moved=true;
    clearTimeout(pickTimer);if(pointers.size||e.pointerType==='touch'||moving)return;
    const event={clientX:e.clientX,clientY:e.clientY};
    pickTimer=setTimeout(()=>{const found=hit(event);setHover(found?refOf(found.object):null,found?{point:found.point.clone(),object:found.object}:null);canvas.style.cursor=found?'pointer':'';},55);
  });
  canvas.addEventListener('pointerup',e=>{const tap=down&&down.id===e.pointerId&&!down.moved&&pointers.size===1;pointers.delete(e.pointerId);down=null;if(tap){const found=hit(e);if(found)select(refOf(found.object),{point:found.point.clone(),object:found.object});else clear();}});
  canvas.addEventListener('pointercancel',e=>{pointers.delete(e.pointerId);down=null;clearTimeout(pickTimer);});
  canvas.addEventListener('pointerleave',()=>{clearTimeout(pickTimer);setHover(null);canvas.style.cursor='';});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('licenses').open)clear();});
  $('clear-selection').onclick=clear;
  $('annotations').onclick=()=>{enabled=!enabled;$('annotations').setAttribute('aria-pressed',String(enabled));scheduleAnchor();$('view-feedback').textContent=!enabled?'Part links hidden.':!(hovered||selected)?'Part links on. Hover or select a visible component.':'Part links on. The line appears when the selected surface is visible.';requestRender();};
  new ResizeObserver(()=>{layoutDirty=true;requestRender();}).observe(main);
  function update(){
    // Keep selected frame and keycap palettes visible; hover still highlights its surface.
    const active=hovered||selected,highlighted=hovered||(['lid','keycaps'].includes(selected?.group)?null:selected),stamp=key(active)+':'+key(highlighted)+':'+revision;
    if(stamp!==highlightStamp){
      highlightStamp=stamp;for(const mesh of highlights.values())mesh.visible=false;
      for(const o of objects)if((o.visible||hovered)&&match(o,highlighted)){
        let mesh=highlights.get(o);if(!mesh){mesh=new THREE.Mesh(o.geometry,glow);highlights.set(o,mesh);overlay.add(mesh);}
        mesh.material=hovered?xray:glow;mesh.renderOrder=hovered?1000:0;mesh.geometry=o.geometry;mesh.position.copy(o.position);mesh.rotation.copy(o.rotation);mesh.scale.copy(o.scale);mesh.visible=true;
      }
      if(selected)$('selection-visibility').textContent=objects.some(o=>o.visible&&match(o,selected))?'':selected.group==='lid'&&!objects.some(o=>match(o,selected))?'Display covers are not installed. Choose a frame to reinstall them.':'This layer is hidden. Use its eye in the directory to show it.';
    }
    if(activeKey!==key(active)){
      activeKey=key(active);for(const row of document.querySelectorAll('.part-row'))row.classList.toggle('is-highlighted',active?.group===row.dataset.group);
    }
    path.setAttribute('hidden','');dot.setAttribute('hidden','');
    if(!enabled||moving||!active||!anchor||(!anchor.object.visible&&!hovered))return;
    if(layoutDirty){
      const r=main.getBoundingClientRect(),stage=canvas.getBoundingClientRect();layout={r,stage,targets:new Map()};
      for(const e of document.querySelectorAll('.part-anchor')){const b=e.getBoundingClientRect();layout.targets.set(e.dataset.group,{x:b.x+b.width/2-r.x,y:b.y+b.height/2-r.y});}
      svg.setAttribute('viewBox',`0 0 ${r.width} ${r.height}`);layoutDirty=false;
    }
    const p=anchor.point.clone().project(camera);if(Math.abs(p.x)>1||Math.abs(p.y)>1||Math.abs(p.z)>1)return;
    const {r,stage}=layout,to=layout.targets.get(active.group);if(!to)return;
    const x=stage.x-r.x+(p.x+1)*stage.width/2,y=stage.y-r.y+(1-p.y)*stage.height/2;
    const edge=x<stage.width/2?8:stage.width-8;
    const elbow=stage.width===r.width?`L ${edge} ${y.toFixed(1)} L ${edge} ${(stage.bottom-r.y-2).toFixed(1)} L ${to.x.toFixed(1)} ${(stage.bottom-r.y-2).toFixed(1)}`:`L ${(stage.right-r.x-8).toFixed(1)} ${y.toFixed(1)} L ${(stage.right-r.x-8).toFixed(1)} ${to.y.toFixed(1)}`;
    path.setAttribute('d',`M ${x.toFixed(1)} ${y.toFixed(1)} ${elbow} L ${to.x.toFixed(1)} ${to.y.toFixed(1)}`);path.dataset.group=active.group;path.dataset.side=anchor.object.userData.side;path.dataset.endX=to.x;path.dataset.endY=to.y;
    dot.setAttribute('cx',x.toFixed(1));dot.setAttribute('cy',y.toFixed(1));path.removeAttribute('hidden');dot.removeAttribute('hidden');
  }
  return {update,highlight:ref=>setHover(ref),select,clear,
    invalidate(){revision++;scheduleAnchor();},
    layoutChanged(){layoutDirty=true;path.setAttribute('hidden','');dot.setAttribute('hidden','');requestRender();},
    cameraChanged(){scheduleAnchor();},
    motion(value){moving=value;clearTimeout(pickTimer);if(value){clearTimeout(anchorTimer);anchor=null;path.setAttribute('hidden','');dot.setAttribute('hidden','');}else scheduleAnchor();requestRender();},
    get selected(){return selected;}
  };
}
