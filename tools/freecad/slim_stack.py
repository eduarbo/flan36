"""Reversible nominal electronics fit update; no vendor CAD is embedded.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,math,hashlib
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parents[2]
GENERATOR_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
J1={'left':{'at':[125.45,57.2,270],'pads':[[125.45,57.2],[125.45,59.2]]},'right':{'at':[34.55,59.2,90],'pads':[[34.55,59.2],[34.55,57.2]]}}
RESET={'left':[119.0,59.5],'right':[41.0,59.5]}
def reset_access_shape(side):
 return Part.makeCylinder(1.4,1.7,A.Vector(RESET[side][0],-RESET[side][1],-.1))

def ph_transform(side):
 oldx=118 if side=='left' else 42;newx=117.2 if side=='left' else 42.8
 return A.Placement(A.Vector(newx,-58.2,0),A.Rotation(A.Vector(0,0,1),90 if side=='left' else -90)).multiply(A.Placement(A.Vector(-oldx,52.87,0),A.Rotation()))

def ph_plug_pieces(side):
 cx=118 if side=='left' else 42;tr=ph_transform(side)
 shapes=[Part.makeBox(4.2,4.85,3.9,A.Vector(cx-2.1,-59.72,5.85)),Part.makeBox(5.8,2,4.5,A.Vector(cx-2.9,-54.87,5.55))]
 for shape in shapes:shape.Placement=tr.multiply(shape.Placement)
 return shapes

def key_reserves(side):
 """Conservative transformed bounds of each licensed Choc source sub-mesh."""
 data=json.loads((ROOT/'components/switches.json').read_text());result={}
 for key in json.loads((ROOT/'design/layout.json').read_text())['halves'][side]:
  tr=A.Placement(A.Vector(key['x'],-key['y'],5.4),A.Rotation(A.Vector(0,0,1),key['angle']));shapes=[]
  for item in [*data['choc-body'],*data['choc-stem']]:
   x,y,z,X,Y,Z=item['bounds_mm'];shape=Part.makeBox(X-x,Y-y,Z-z,A.Vector(x,y,z));shape.Placement=tr.multiply(shape.Placement);shapes.append(shape)
  result['switch-bound-'+key['ref']]=Part.makeCompound(shapes)
 return result

def bounds(shape):
 b=shape.optimalBoundingBox(False,False);return [round(getattr(b,k),6) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def overlap(a,b):
 def possible(x,y):return all(min(getattr(x,k+'Max'),getattr(y,k+'Max'))>max(getattr(x,k+'Min'),getattr(y,k+'Min')) for k in 'XYZ')
 if not possible(a.optimalBoundingBox(False,False),b.optimalBoundingBox(False,False)):return 0.
 aa,bb=a.Solids,b.Solids
 if not aa or not bb:return a.common(b).Volume
 pairs=[(i,j) for i,x in enumerate(aa) for j,y in enumerate(bb) if possible(x.optimalBoundingBox(False,False),y.optimalBoundingBox(False,False))]
 if not pairs:return 0.
 ai=sorted({i for i,j in pairs});bi=sorted({j for i,j in pairs})
 sa=aa[ai[0]] if len(ai)==1 else Part.makeCompound([aa[i] for i in ai]);sb=bb[bi[0]] if len(bi)==1 else Part.makeCompound([bb[i] for i in bi])
 return sa.common(sb).Volume

def visible(obj,value):
 if obj.ViewObject is not None:obj.ViewObject.Visibility=value

def wire_shape(route,right=False):
 def vec(x,y,z):return A.Vector(160-x if right else x,-y,z)
 x,y,z=route['cell_end'];cy=route['return_center_y'];rr=route['return_radius'];sz=route['storage_z']
 start=vec(x,y,z);bs=vec(x,cy,z);be=vec(x,cy,sz)
 edges=[Part.makeLine(start,bs),Part.Arc(bs,vec(x,cy+rr,z+rr),be).toShape()]
 p=route['control_points'];last=p[0];r=1.5
 for j,b in enumerate(p[1:-1],1):
  a,c=p[j-1],p[j+1];u=[b[t]-a[t] for t in [0,1]];v=[c[t]-b[t] for t in [0,1]]
  lu,lv=math.hypot(*u),math.hypot(*v);u=[q/lu for q in u];v=[q/lv for q in v]
  s=[b[t]-u[t]*r for t in [0,1]];e=[b[t]+v[t]*r for t in [0,1]]
  turn=math.atan2(u[0]*v[1]-u[1]*v[0],sum(i*k for i,k in zip(u,v)));sign=1 if turn>0 else -1
  center=[s[0]-u[1]*r*sign,s[1]+u[0]*r*sign];angle=math.atan2(s[1]-center[1],s[0]-center[0])
  mid=[center[0]+r*math.cos(angle+turn/2),center[1]+r*math.sin(angle+turn/2)]
  edges.extend([Part.makeLine(vec(*last,sz),vec(*s,sz)),Part.Arc(vec(*s,sz),vec(*mid,sz),vec(*e,sz)).toShape()]);last=e
 edges.append(Part.makeLine(vec(*last,sz),vec(*p[-1],sz)));spine=Part.Wire(edges)
 assert abs(spine.Length-105)<1e-5,spine.Length
 circle=Part.Wire([Part.makeCircle(.3,start,bs-start)]);shape=spine.makePipeShell([circle],True,False)
 assert shape.isValid() and len(shape.Solids)==1
 return shape

def apply(doc):
 receipt=doc.getObject('SlimStackReceipt')
 if receipt:
  previous=json.loads(receipt.RecipeJSON)
  if previous.get('generator_sha256')!=GENERATOR_SHA256 or previous.get('wire_spec_sha256')!=hashlib.sha256((ROOT/'design/revI-wire-study.json').read_bytes()).hexdigest():raise ValueError('Slim recipe changed: regenerate from preserved pre-slim source; refusing a second reset flip.')
  return previous
 params=doc.getObject('Parameters')
 for alias,value in [('DisplayBottom',12.4),('FrameTop',14.8),('BatteryShiftY',1.2)]:
  if abs(getattr(params,alias).Value-value)>1e-8:params.set(params.getCellFromAlias(alias),f'{value} mm')
 spec=json.loads((ROOT/'design/revI-wire-study.json').read_text())
 report={'schema':'flan36-slim-stack-1','generator_sha256':GENERATOR_SHA256,'wire_spec_sha256':hashlib.sha256((ROOT/'design/revI-wire-study.json').read_bytes()).hexdigest(),'target_frame_top_mm':14.8,'display_pcb_bottom_mm':12.4,'mcu_pcb_bottom_mm':8.8,'battery_shift_y_mm':1.2,'battery_rotation_deg':0,'nominal_only':True,'physical_acceptance':False,'net_mapping':{'left':{'lead0':'GND','lead1':'BAT_PLUS'},'right':{'lead0':'BAT_PLUS','lead1':'GND'}},'polarity_status':'Footprint pad net mapping preserved; purchased battery polarity must be verified, never inferred from wire color.','halves':{}}
 for side,prefix in [('left','L_'),('right','R_')]:
  history=doc.getObject(prefix+'Construction');assembly=doc.getObject(prefix+'Half')
  def add(typ,name):
   o=doc.addObject(typ,prefix+'Slim'+name);history.addObject(o);return o
  def feature(name,shape,color):
   o=add('Part::Feature',name);o.Shape=shape
   if o.ViewObject is not None:o.ViewObject.ShapeColor=tuple(float(channel) for channel in color)
   return o
  def part(ident):return next(o for o in doc.Objects if getattr(o,'PartID',None)==side+'-'+ident)
  def replace(old,new):
   for prop in ['PartID','DisplayName','ViewerGroup','PrototypePrintable','Layer','ModelStatus']:
    if hasattr(old,prop):
     new.addProperty(old.getTypeIdOfProperty(prop),prop,'Flan36');setattr(new,prop,getattr(old,prop));old.removeProperty(prop)
   new.Label=old.Label;assembly.addObject(new);visible(old,False);visible(new,True)
  slot=doc.getObject(prefix+'BatteryOpening');slot.Width=34.4;slot.setExpression('Placement.Base.y',None);slot.Placement.Base.y=-47.6
  notch=feature('RearLeadNotchTool',Part.makeBox(2.2,1.8,2.2,A.Vector(117.65 if side=='left' else 160-119.85,-49.4,3.6)),(.5,.5,.5));pcb=part('pcb');newpcb=add('Part::Cut','PCBLeadNotch');newpcb.Base=pcb;newpcb.Tool=notch;replace(pcb,newpcb);visible(notch,False)
  exit_tool=doc.getObject(prefix+'KeeperCableTool');exit_tool.Length=2.2;exit_tool.Height=2.0;exit_tool.Placement.Base.z=3.8;exit_tool.Placement.Base.x=117.65 if side=='left' else 160-119.85
  tool=doc.getObject(prefix+'SledCableTunnelTool');tool.Length=12.2;tool.Width=6.2;tool.Height=3.2;tool.Placement.Base=A.Vector(116.5 if side=='left' else 160-128.7,-54,5.2)
  cross=doc.getObject(prefix+'SledCableCrossingTool');cross.Height=3.2;cross.Placement.Base.z=5.2
  doc.getObject(prefix+'HeaderReliefTool').Height=7.25
  bridge=doc.getObject(prefix+'RiserBridge');bridge.setExpression('Placement.Base.y','-40.2 mm - Parameters.MCUShiftY')
  cx=118.0 if side=='left' else 42.0;cy=61.12
  header=Part.makeBox(5.9,7.6,4.8,A.Vector(cx-2.95,-cy-1.35,5.4));header.Placement=ph_transform(side).multiply(header.Placement)
  pieces=ph_plug_pieces(side);plug=pieces[0].fuse(pieces[1]);header=header.cut(plug)
  ho=feature('PHHeader',header,(.86,.84,.75));po=feature('PHPlug',plug,(.95,.94,.86));pins=[]
  for n,(px,py) in enumerate(J1[side]['pads']):pins.append(feature('PHPin'+str(n),Part.makeBox(.5,.5,3.4,A.Vector(px-.25,-py-.25,2.0)),(.7,.72,.7)))
  conn=add('Part::Compound','JST');conn.Links=[ho,po,*pins];conn.addProperty('App::PropertyLinkList','VisualParts','Flan36');conn.VisualParts=conn.Links
  conn.addProperty('App::PropertyString','SourceStatus','Flan36');conn.SourceStatus='Original nominal reconstruction: JST PH side-entry mated reserve9.6 ×4.8 mm; terminal engagement inferred.'
  old=part('jst');replace(old,conn);conn.Label='JST PH · side-entry header + mated PHR-2'
  for o in conn.Links:visible(o,False)
  housing=feature('DisplaySocketHousing',Part.makeBox(13.2,3,5,A.Vector(116.2 if side=='left' else 30.6,-52.3,5.4)),(.055,.06,.065))
  socketpins=feature('DisplaySocketPins',Part.makeCompound([Part.makeCylinder(.3,8.4,A.Vector(x if side=='left' else 160-x,-50.8,2)) for x in [117.72,120.26,122.8,125.34,127.88]]),(.72,.74,.76))
  socket=add('Part::Compound','DisplaySocket');socket.Links=[housing,socketpins];socket.addProperty('App::PropertyLinkList','VisualParts','Flan36');socket.VisualParts=socket.Links
  for prop,value in [('PartID',side+'-display-socket'),('DisplayName','nice!view socket · nominal reserve'),('ViewerGroup','connectors'),('Layer','connectors'),('ModelStatus','Nominal 13.2 ×3 ×5 mm housing reserve; 5 mm supplier height, XY/contact geometry unqualified')]:socket.addProperty('App::PropertyString',prop,'Flan36');setattr(socket,prop,value)
  socket.addProperty('App::PropertyBool','PrototypePrintable','Flan36');socket.PrototypePrintable=False;socket.Label='J2 · retained nice!view socket';assembly.addObject(socket)
  for o in socket.Links:visible(o,False)
  visible(socket,True)
  male=feature('DisplayMaleSpacer',Part.makeBox(13.2,3,2,A.Vector(116.2 if side=='left' else 30.6,-52.3,0)),(.055,.06,.065));male.setExpression('Placement.Base.z','Parameters.DisplayBottom - 2 mm')
  contacts=feature('DisplayMaleContacts',Part.makeCompound([Part.makeCylinder(.3,3,A.Vector(x if side=='left' else 160-x,-50.8,0)) for x in [117.72,120.26,122.8,125.34,127.88]]),(.72,.74,.76));contacts.setExpression('Placement.Base.z','Parameters.DisplayBottom - 2 mm')
  display=part('display');display.Links=[*display.Links,male,contacts];display.VisualParts=[*display.VisualParts,male,contacts]
  if hasattr(display,'VisualFaceColors'):
   colors=json.loads(display.VisualFaceColors)+[(.055,.06,.065)]*len(male.Shape.Faces)+[(.72,.74,.76)]*len(contacts.Shape.Faces);display.VisualFaceColors=json.dumps(colors)
   if display.ViewObject is not None:display.ViewObject.DiffuseColor=[tuple(float(channel) for channel in color) for color in colors]
  visible(male,False);visible(contacts,False)
  olds=part('display-sled');news=add('Part::Cut','DisplayHeaderClearance');news.Base=olds;news.Tool=doc.getObject(prefix+'HeaderReliefTool');replace(olds,news)
  reset=part('reset');oldx=123 if side=='left' else 37;newx=RESET[side][0]
  transform=A.Placement(A.Vector(newx,-59.5,3.8),A.Rotation(A.Vector(1,0,0),180)).multiply(A.Placement(A.Vector(-oldx,59.5,-5.4),A.Rotation()))
  for visual in {o.Name:o for o in [*reset.VisualParts,*reset.Links]}.values():visual.Placement=transform.multiply(visual.Placement)
  access=doc.getObject(prefix+'ResetToolAccess');access.Placement.Base=A.Vector(newx,-59.5,-.1);access.Height=1.7
  for style in json.loads((ROOT/'design/cases.json').read_text())['styles']:
   obj=doc.getObject(prefix+'Case_'+style+'_base')
   if obj:
    cut=add('Part::Cut','ResetAccess_'+style);cut.Base=obj.Links[0];cut.Tool=access;obj.Links=[cut];visible(cut,False)
  drills=json.loads((ROOT/'design/revF-drills.json').read_text())[side]
  for i,d in enumerate(drills):
   if d['ref']=='J1':
    native=doc.getObject(prefix+'PadDrill'+str(i));n=0 if d['pin']=='1' else 1;px,py=J1[side]['pads'][n];native.Radius=.375;native.Placement.Base=A.Vector(px,-py,3.7)
  lead_objects={}
  for battery,routes in spec['profiles'].items():
   objects=[]
   for i,route in enumerate(routes):
    shape=wire_shape(route,side=='right')
    if battery=='adafruit-1570':o=part('battery-lead-'+str(i));o.Shape=shape;o.Label='105 mm lead · continuous nominal route'
    else:
     o=feature('Wire301230_'+str(i),shape,(.62,.18,.16) if i==0 else (.18,.19,.20));visible(o,False);o.addProperty('App::PropertyString','BatteryLeadStyle','Flan36');o.BatteryLeadStyle=battery;o.addProperty('App::PropertyInteger','LeadIndex','Flan36');o.LeadIndex=i
    if o.ViewObject is not None:o.ViewObject.ShapeColor=(.62,.18,.16) if (i==1 if side=='left' else i==0) else (.18,.19,.20)
    if not hasattr(o,'BatteryLeadStyle'):o.addProperty('App::PropertyString','BatteryLeadStyle','Flan36');o.BatteryLeadStyle=battery;o.addProperty('App::PropertyInteger','LeadIndex','Flan36');o.LeadIndex=i
    objects.append(o.Name)
   lead_objects[battery]=objects
  for i,name in enumerate(lead_objects['adafruit-1570']):
   original=doc.getObject(name);active=doc.addObject('App::Link',prefix+'ActiveBatteryLead'+str(i));active.setLink(original);replace(original,active);
   if active.ViewObject is not None:active.ViewObject.OverrideMaterial=False
  report['halves'][side]={'j1':J1[side],'display_socket':{'part_id':side+'-display-socket','body_size_mm':[13.2,3,5],'body_z_mm':[5.4,10.4],'pin_reserve_z_mm':[2,10.4],'moving_male_spacer_z_mm':[10.4,12.4],'moving_male_contacts_z_mm':[10.4,13.4],'xy_qualified':False,'engagement_qualified':False},'reset_center_xy':RESET[side],'reset_side':'B.Cu','reset_tool_radius_mm':1.4,'rear_lead_notch_xy':[[117.65 if side=='left' else 40.15,47.6],[119.85 if side=='left' else 42.35,49.4]],'battery_aperture_xy':[[116.55 if side=='left' else 30.95,13.2],[129.05 if side=='left' else 43.45,47.6]],'lead_objects':lead_objects}
 receipt=doc.addObject('App::DocumentObjectGroup','SlimStackReceipt');receipt.Label='Slim stack · nominal electronics interfaces';receipt.addProperty('App::PropertyString','RecipeJSON','Flan36');receipt.RecipeJSON=json.dumps(report,sort_keys=True);doc.recompute()
 return report

def cell_motion_checks(doc,side):
 """Separate intended flexible terminal attachment from remaining pouch space.

 This check does not validate wire flex or pack tolerances. The cell-motion box
 is the complete cradle cavity under the rigid cage roof; only the explicitly
 bounded nominal terminal join is allowed to meet it.
 """
 prefix='L_' if side=='left' else 'R_'
 x=116.55 if side=='left' else 30.95
 motion=Part.makeBox(12.5,33.2,4.2,A.Vector(x,-46.8,2))
 attachment=Part.makeBox(2.2,2.2,2.0,A.Vector(117.65 if side=='left' else 40.15,-46.8,3.8))
 spec=json.loads(doc.getObject('SlimStackReceipt').RecipeJSON)['halves'][side]
 result={}
 for battery,names in spec['lead_objects'].items():
  result[battery]=[]
  for name in names:
   lead=doc.getObject(name).Shape;touch=motion.common(lead);outside=touch.cut(attachment).Volume if touch.Volume>.000001 else 0
   result[battery].append({'lead':name,'attachment_overlap_mm3':round(touch.Volume,6),'outside_attachment_overlap_mm3':round(outside,6)})
 return result

def validate(doc):
 result={'physical_acceptance':False,'halves':{}}
 for side,prefix in [('left','L_'),('right','R_')]:
  assembly=doc.getObject(prefix+'Half');saved_placement=A.Placement(assembly.Placement);assembly.Placement=A.Placement();doc.recompute()
  try:
   parts={o.PartID[len(side)+1:]:o.Shape.copy() for o in doc.Objects if getattr(o,'PartID','').startswith(side+'-')}
   selected=['pcb','cradle','battery-retainer','mcu-riser','mcu','mcu-sockets','display-sled','display','display-socket','jst','reset','slider','tray','electronics-lid',*[f'frame-target-{i}' for i in range(3)],*[f'screw-{i}' for i in range(1,6)]]
   keys=key_reserves(side);collisions=[]
   for i,a in enumerate(selected):
    for b in selected[i+1:]:
     if a=='tray' and b.startswith('screw-'):continue
     v=overlap(parts[a],parts[b])
     if v>.001:collisions.append({'a':a,'b':b,'volume_mm3':round(v,6)})
   for a in ['jst','reset','display-socket']:
    for name,shape in keys.items():
     v=overlap(parts[a],shape)
     if v>.001:collisions.append({'a':a,'b':name,'volume_mm3':round(v,6)})
   profiles={};spec=json.loads(doc.getObject('SlimStackReceipt').RecipeJSON)['halves'][side];moving=Part.makeCompound([parts['display'],parts['display-sled']])
   for battery,names in spec['lead_objects'].items():
    battery_shape=next(o.Shape for o in doc.Objects if o.Name.startswith(prefix) and getattr(o,'BatteryStyle',None)==battery);leads=[doc.getObject(n).Shape for n in names];static_hits=[];service=[]
    for i,lead in enumerate(leads):
     for name,shape in [*[(n,parts[n]) for n in selected],*keys.items(),('battery',battery_shape),('other-lead',leads[1-i])]:
      v=overlap(lead,shape)
      if v>.001:static_hits.append({'lead':i,'part':name,'volume_mm3':round(v,6)})
    for dz in [0,.1,.2,.3,.5,.75,1,1.5,2,3,4,5,6,8,10,12,16,24]:
     moved=moving.copy();moved.translate(A.Vector(0,0,dz))
     for name,shape in [*[(n,parts[n]) for n in selected if n not in ['electronics-lid','display-sled','display'] and not n.startswith('frame-target-')],*keys.items(),('battery',battery_shape),*[(f'lead-{i}',s) for i,s in enumerate(leads)]]:
      v=overlap(moved,shape)
      if v>.001:service.append({'lift_mm':dz,'part':name,'volume_mm3':round(v,6)})
    profiles[battery]={'lead_static_collisions':static_hits,'display_sled_lift_collisions':service}
   probe=Part.makeCylinder(1.,10.26,A.Vector(RESET[side][0],-RESET[side][1],-8));probe_hits=[]
   for name,shape in parts.items():
    if name=='reset':continue
    vol=overlap(probe,shape)
    if vol>.001:probe_hits.append({'part':name,'volume_mm3':round(vol,6)})
   result['halves'][side]={'bottom_reset_probe_collisions':probe_hits,'cell_motion':cell_motion_checks(doc,side),'static_collisions':collisions,'profiles':profiles,'jst_bounds_mm':bounds(parts['jst'])}
  finally:
   assembly.Placement=saved_placement;doc.recompute()
 return result
