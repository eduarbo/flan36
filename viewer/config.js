// SPDX-License-Identifier: GPL-3.0-or-later
import {framePalette} from './finishes.js';
export const copy=x=>JSON.parse(JSON.stringify(x));
export function polygon(hull,key,turn){const a=(-key.angle-turn)*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return hull.map(([x,y])=>[key.x+x*c-y*s,key.y+x*s+y*c]);}
export function gap(a,b){
 const xs=p=>p.map(v=>v[0]),ys=p=>p.map(v=>v[1]);
 let result=Math.max(Math.min(...xs(b))-Math.max(...xs(a)),Math.min(...xs(a))-Math.max(...xs(b)),Math.min(...ys(b))-Math.max(...ys(a)),Math.min(...ys(a))-Math.max(...ys(b)));
 if(result>=.2)return result;
 for(const p of [a,b])for(let i=0;i<p.length;i++){
   const [x,y]=p[i],[xx,yy]=p[(i+1)%p.length],l=Math.hypot(xx-x,yy-y);if(l<1e-8)continue;
   const nx=-(yy-y)/l,ny=(xx-x)/l,aa=a.map(([u,v])=>u*nx+v*ny),bb=b.map(([u,v])=>u*nx+v*ny);
   result=Math.max(result,Math.min(...bb)-Math.max(...aa),Math.min(...aa)-Math.max(...bb));
 }
 return result;
}
export const retiredFrames=(config,c)=>['left','right'].filter(side=>Object.hasOwn(c.retired_frame_styles||{},config?.frames?.[side]?.style));
export function normalize(config,c){const result=copy(config);result.schema="flan36-config-1";for(const [side,keys] of Object.entries(c.layout))for(const key of keys)result.keycaps[side][key.ref].color??=key.row===3?'#45967b':'#e9dfc6';if(!('cases' in result))result.cases=Object.fromEntries(['left','right'].map(side=>[side,{style:'solid',cover:true}]));for(const side of ['left','right']){const cs=result.cases[side],style=c.case_styles[cs.style];cs.base_color??=style.base_color;cs.plate_color??=style.plate_color;cs.match_frame??=false;const f=result.frames[side];if(Object.hasOwn(c.retired_frame_styles||{},f.style))f.style=c.retired_frame_styles[f.style];const p=framePalette(f.style,f.color,f.accents);f.accents=Object.fromEntries(['detail','accent','secondary'].map(k=>[k,p[k]]));}return result;}
export function check(config,c){
 const record=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 if(!record(config))return {errors:['Choose a configuration object.']};
 const errors=[],variants=new Map(c.variants.map(v=>[v.id,v]));let minimum=Infinity;
 if(!['flan36-config-1','filo36-config-1'].includes(config?.schema)||config?.revision!=='I')return {errors:['Unsupported configuration format or revision.']};
 if(Object.keys(record(config.keycaps)?config.keycaps:{}).sort().join()!=='left,right'||Object.keys(record(config.frames)?config.frames:{}).sort().join()!=='left,right')return {errors:['Both halves are required.']};
 if(Object.keys(record(config.batteries)?config.batteries:{}).sort().join()!=='left,right')return {errors:['Select a battery for each half.']};
 if('cases' in config){if(Object.keys(record(config.cases)?config.cases:{}).sort().join()!=='left,right')return {errors:['Select a case for each half.']};for(const choice of Object.values(config.cases))if(!record(choice)||typeof choice.style!=='string'||!Object.hasOwn(c.case_styles,choice.style)||typeof choice?.cover!=='boolean')return {errors:['Invalid case or display cover option.']};}
 const color=v=>typeof v==='string'&&/^#[0-9a-f]{6}$/i.test(v);
 for(const side of ['left','right']){const cs=config.cases?.[side]||{},f=config.frames[side];if(!record(f))return {errors:['Invalid frame.']};if(['base_color','plate_color'].some(k=>k in cs&&!color(cs[k])))return {errors:['Invalid case color.']};if('match_frame' in cs&&typeof cs.match_frame!=='boolean')return {errors:['Invalid color link.']};if('accents' in f&&(!f.accents||typeof f.accents!=='object'||Array.isArray(f.accents)||Object.entries(f.accents).some(([k,v])=>!['detail','accent','secondary'].includes(k)||!color(v))))return {errors:['Invalid frame accent color.']};if(cs.match_frame&&cs.style==='level'&&cs.plate_color?.toLowerCase()!==String(f.color||'').toLowerCase())return {errors:['Linked Level shell and frame colors must match.']};if(cs.match_frame&&cs.base_color?.toLowerCase()!==String(f.color||'').toLowerCase())return {errors:['Linked rim and frame colors must match.']};}
 for(const [side,keys] of Object.entries(c.layout)){
   if(typeof config.batteries[side]!=='string'||!Object.hasOwn(c.battery_profiles,config.batteries[side]))errors.push('Unknown battery profile.');
   if(Object.keys(record(config.keycaps[side])?config.keycaps[side]:{}).sort().join()!==keys.map(k=>k.ref).sort().join())return {errors:['Missing keys or unknown positions.']};
   const f=config.frames[side];if(typeof f.style!=='string'||(!Object.hasOwn(c.frame_styles,f.style)&&!Object.hasOwn(c.retired_frame_styles||{},f.style))||!color(f.color))errors.push('Invalid frame or color.');
   const shapes=[];
   for(const k of keys){
     const x=config.keycaps[side][k.ref];if(!record(x))return {errors:['Invalid keycap choice.']};const v=variants.get(x.variant);
     if(x&&'color' in x&&(typeof x.color!=='string'||!/^#[0-9a-f]{6}$/i.test(x.color)))return {errors:['Invalid keycap color.']};
     if(!v||!v.rotations_deg.includes(x?.rotation_deg)||!v.qualified_reference_positions.length){errors.push(`${side} ${k.ref}: unqualified variant or orientation.`);continue;}
     const p=polygon(v.hull_xy_mm,k,x.rotation_deg);shapes.push([k.ref,p]);const d=gap(p,c.frame_envelopes[side]);minimum=Math.min(minimum,d);
     if(d<c.minimum_clearance_mm-1e-7)errors.push(`${side} ${k.ref}: violates the frame clearance.`);
   }
   for(let i=0;i<shapes.length;i++)for(let j=i+1;j<shapes.length;j++){
     const d=gap(shapes[i][1],shapes[j][1]);minimum=Math.min(minimum,d);
     if(d<c.minimum_clearance_mm-1e-7)errors.push(`${side} ${shapes[i][0]}/${shapes[j][0]}: insufficient keycap clearance.`);
   }
 }
 return {errors,minimum};
}
