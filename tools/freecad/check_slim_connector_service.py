"""Read-only continuous PH housing and gripping-tool clearance study.

Nominal contact and wire-flex geometry remains unqualified. This checker keeps
all wires and explicitly reports the motion that needs their deformation.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/freecad'))
from slim_stack import overlap,bounds,ph_plug_pieces,key_reserves

def sweep_box(shape,delta):
 """Exact continuous axis-aligned translation sweep of a rectangular solid."""
 b=shape.BoundBox;v=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
 for i,q in enumerate(delta):v[i]+=min(q,0);v[i+3]+=max(q,0)
 return Part.makeBox(v[3]-v[0],v[4]-v[1],v[5]-v[2],A.Vector(*v[:3]))

def hits(shape,obstacles):
 result=[]
 for name,other in obstacles.items():
  vol=overlap(shape,other)
  if vol>.001:result.append({'part':name,'volume_mm3':round(vol,6)})
 return result

def cap_reserves(doc,side):
 """Bound the selected native cap variant using its unchanged native pose."""
 catalog=json.loads((ROOT/'keycaps/catalog.json').read_text());variants={v['id']:v for v in catalog['variants']};result={};prefix='L_' if side=='left' else 'R_'
 for key in catalog['layout'][side]:
  obj=doc.getObject(prefix+key['ref']);item=variants[obj.KeycapVariant];(x,y,z),(X,Y,Z)=item['bounds_mm']
  # configuration.py reflects the source STL Y axis before applying this pose.
  shape=Part.makeBox(X-x,Y-y,Z-z,A.Vector(x,-Y,z));shape.Placement=obj.Placement.multiply(shape.Placement);result['cap-bound-'+key['ref']]=shape
 return result

def check(doc):
 result={'schema':'flan36-PH-release-2','physical_acceptance':False,'wire_flex_validated':False,'release_stroke_mm':5.,'lift_mm':24.,
  'sweep_method':'Continuous union of translated rectangular neck and flange solids; exact for the modeled rectilinear housing, no early tilt.',
  'sequence':['Remove magnetic frame with its steel targets.','Lift nice!view, its male header, and display support together; J2 female socket remains on PCB.','Lift nice!nano from its sockets.','Grip exposed PHR-2 flange from above, slide5 mm toward the key field, then lift24 mm. Flexible leads must be released from their loose stored bends during this operation.'],
  'assumptions':['Housing engagement4.85 mm and a5 mm release stroke are inferred from original nominal reconstruction, not a measured connector.','J2 female5 mm height and male2 mm spacer follow the supplier installation dimensions. The13.2 ×3 mm XY and contact geometry are conservative assumptions, not supplier tolerances.','Two opposed0.8 mm thick,1 mm deep jaw tips contact the upper flange atz8.65–9.65 mm. This is an access reserve, not a qualified tool design.','Choc obstacles are transformed bounds of all licensed body/stem sub-meshes.','All flexible leads are kept in their stored pose and intersections with the moving housing are reported. Their deformation and forces during unplugging are NOT validated.'],
  'halves':{}}
 for side,prefix,sign in [('left','L_',1),('right','R_',-1)]:
  assembly=doc.getObject(prefix+'Half');pose=A.Placement(assembly.Placement)
  try:
   assembly.Placement=A.Placement();doc.recompute()
   objects={o.PartID[len(side)+1:]:o for o in doc.Objects if getattr(o,'PartID','').startswith(side+'-')}
   assert 'display-socket' in objects,'Missing retained J2 socket'
   plug=doc.getObject(prefix+'SlimPHPlug').Shape.copy();pieces=ph_plug_pieces(side);nominal=pieces[0].fuse(pieces[1])
   assert plug.cut(nominal).Volume+nominal.cut(plug).Volume<1e-6,'Housing sweep does not match native plug'
   fixed={name:o.Shape for name,o in objects.items() if name not in ['electronics-lid','display','display-sled','mcu','jst','battery'] and not name.startswith(('frame-target-','battery-lead-'))};fixed.update(key_reserves(side));fixed.update(cap_reserves(doc,side))
   for suffix in ['SlimPHHeader','SlimPHPin0','SlimPHPin1']:fixed[suffix]=doc.getObject(prefix+suffix).Shape
   unplug=Part.makeCompound([sweep_box(s,[-5*sign,0,0]) for s in pieces]);shifted=[]
   for shape in pieces:s=shape.copy();s.translate(A.Vector(-5*sign,0,0));shifted.append(s)
   lift=Part.makeCompound([sweep_box(s,[0,0,24]) for s in shifted]);path=Part.makeCompound([unplug,lift])
   grips=[Part.makeBox(1,.8,1,A.Vector(117.2 if side=='left' else 41.8,y,8.65)) for y in [-55.3,-61.9]]
   approach=Part.makeCompound([sweep_box(s,[0,0,16]) for s in grips]);release=Part.makeCompound([sweep_box(s,[-5*sign,0,0]) for s in grips]);griplifts=[]
   for shape in grips:s=shape.copy();s.translate(A.Vector(-5*sign,0,0));griplifts.append(sweep_box(s,[0,0,24]))
   grip_path=Part.makeCompound([approach,release,*griplifts]);rigid=[];griphits=[];wire_hits={};terminals={}
   spec=json.loads(doc.getObject('SlimStackReceipt').RecipeJSON)['halves'][side]
   for battery,names in spec['lead_objects'].items():
    cell=next(o.Shape for o in doc.Objects if o.Name.startswith(prefix) and o.TypeId!='App::Link' and getattr(o,'BatteryStyle',None)==battery);obstacles={**fixed,'battery-'+battery:cell}
    rigid.extend({'battery':battery,**item} for item in hits(path,obstacles))
    wire_hits[battery]=hits(path,{name:doc.getObject(name).Shape for name in names})
    griphits.extend({'battery':battery,**item} for item in hits(grip_path,{**obstacles,**{name:doc.getObject(name).Shape for name in names}}))
    terminals[battery]=[{'lead':i,'to_plug_mm':round(doc.getObject(name).Shape.distToShape(plug)[0],6),'to_cell_mm':round(doc.getObject(name).Shape.distToShape(cell)[0],6)} for i,name in enumerate(names)]
   housing=doc.getObject(prefix+'SlimDisplaySocketHousing').Shape
   result['halves'][side]={'retained_display_socket':{'part_id':side+'-display-socket','body_size_mm':[13.2,3,5],'body_bounds_mm':bounds(housing),'width_depth_qualified':False,'engagement_qualified':False,'moving_male_header_part_id':side+'-display','moving_male_spacer_size_mm':[13.2,3,2]},'retained_obstacles':sorted(fixed),'rigid_housing_collisions':rigid,'rigid_housing_path_clear':not rigid,'grip_tool_collisions':griphits,'grip_tool_path_clear':not griphits,'stored_wire_intersections_requiring_flex':wire_hits,'nominal_terminal_distances':terminals,'mated_plug_bounds_mm':bounds(plug),'conservative_choc_bounds_count':18,'conservative_cap_bounds_count':18}
  finally:assembly.Placement=pose;doc.recompute()
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'mechanical/revI/Flan36.FCStd');parser.add_argument('--output',type=Path,default=ROOT/'validation/revI-connector-service.json');args,_=parser.parse_known_args()
 doc=A.openDocument(str(args.source.resolve()));result=check(doc);result['source_sha256']=hashlib.sha256(args.source.read_bytes()).hexdigest();result['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
 sys.__stdout__.write(json.dumps({s:{'rigid_clear':v['rigid_housing_path_clear'],'grip_clear':v['grip_tool_path_clear'],'rigid_collisions':v['rigid_housing_collisions'],'grip_collisions':v['grip_tool_collisions'],'terminal_distances':v['nominal_terminal_distances']} for s,v in result['halves'].items()},indent=2)+'\n');sys.__stdout__.flush();A.closeDocument(doc.Name)
 if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0)
if __name__=='__main__':main()
