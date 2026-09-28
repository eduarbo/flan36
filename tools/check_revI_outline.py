#!/usr/bin/env python3
"""Check Contour topology, copper, keys, fasteners and dual-cell budgets.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import Polygon,Point,box,LineString
from shapely.affinity import rotate
R=Path(__file__).resolve().parents[1];profiles=json.loads((R/'design/revI-profiles.json').read_text());layout=json.loads((R/'design/layout.json').read_text())
mounts=json.loads((R/'design/revI-mounts.json').read_text());batteries=json.loads((R/'design/batteries.json').read_text())['profiles']
electrical=json.loads((R/'validation/revI-electrical.json').read_text())
def rim_samples(outer, keys):
 rows=[];lookup={k['ref']:k for k in keys}
 faces=[*(('K0'+str(i),'north',-4,4) for i in range(1,6)),
        *((k,'west',-4,4) for k in ['K01','K11','K21']),
        ('K21','east',4,6),('K21','south',-4,4),('K22','south',-2,4),
        ('K30','west',-4,4)]
 for ref,face,a,b in faces:
  key=lookup[ref];angle=-math.radians(key['angle']);gaps=[]
  normal={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[face]
  n=(normal[0]*math.cos(angle)-normal[1]*math.sin(angle),normal[0]*math.sin(angle)+normal[1]*math.cos(angle))
  for i in range(9):
   t=a+(b-a)*i/8;x,y=(t,normal[1]*7) if normal[1] else(normal[0]*7,t)
   q=(key['x']+x*math.cos(angle)-y*math.sin(angle),key['y']+x*math.sin(angle)+y*math.cos(angle))
   hit=LineString([q,(q[0]+n[0]*40,q[1]+n[1]*40)]).intersection(outer.boundary)
   assert not hit.is_empty,(ref,face,'no exterior hit')
   gaps.append(Point(q).distance(hit))
  rows.append({'key':ref,'face':face,'sample_count':9,'face_local_range_mm':[a,b],
               'minimum_mm':min(gaps),'maximum_mm':max(gaps)})
 return rows

# Test the actual request, not only solid containment. The old geometry must fail.
baseline=json.loads((R/'design/revI-rim-baseline.json').read_text())
assert hashlib.sha256((R/'design/layout.json').read_bytes()).hexdigest()==baseline['layout_sha256']
old_samples=rim_samples(Polygon(baseline['outer']),layout['halves']['left'])
assert max(abs(v-4.75) for row in old_samples for v in [row['minimum_mm'],row['maximum_mm']])>1
left=profiles['left'];right=profiles['right']
for family in ['outer','inner','plate','pcb_outline','hood','control_vertices','rim_inset','rim_inner','terrace_inset','plate_frame_clearance']:
 assert len(left[family])==len(right[family])
 assert max(max(abs(160-a[0]-b[0]),abs(a[1]-b[1])) for a,b in zip(left[family],right[family]))<1e-10
assert 'revI-mounts' not in (R/'tools/build_revI_profiles.py').read_text()
report={'scope':'LCD-aligned flank and smooth thumb curve; actual copper and nominal fit; physical acceptance remains open','halves':{},'physical_acceptance':False}
for side,p in profiles.items():
 outer=Polygon(p['outer']);inner=Polygon(p['inner']);pcb=Polygon(p['pcb_outline']);reflect=lambda x:x if side=='left' else 160-x
 assert outer.is_valid and inner.is_valid and pcb.is_valid
 assert abs((outer.bounds[2] if side=='left' else outer.bounds[0])-p['lcd_flank_x_mm'])<1e-8
 segments=p['outer_segments']
 def unit(v):
  n=math.hypot(*v);return [a/n for a in v]
 def diff(a,b):return [x-y for x,y in zip(a,b)]
 def arc_tangent(a,end):
  u,v,w=a['start'],a['mid'],a['end'];d=2*(u[0]*(v[1]-w[1])+v[0]*(w[1]-u[1])+w[0]*(u[1]-v[1]))
  sq=lambda p:sum(x*x for x in p)
  c=[(sq(u)*(v[1]-w[1])+sq(v)*(w[1]-u[1])+sq(w)*(u[1]-v[1]))/d,(sq(u)*(w[0]-v[0])+sq(v)*(u[0]-w[0])+sq(w)*(v[0]-u[0]))/d]
  r=diff(w if end else u,c);t=unit([-r[1],r[0]])
  return t if sum(x*y for x,y in zip(t,diff(w,u)))>0 else [-x for x in t]
 for i,arc in enumerate(segments):
  if arc['kind']!='arc':continue
  before=segments[i-1];after=segments[(i+1)%len(segments)]
  assert before['end']==arc['start'] and after['start']==arc['end']
  for t,line in [(arc_tangent(arc,False),before),(arc_tangent(arc,True),after)]:
   assert max(abs(x-y) for x,y in zip(t,unit(diff(line['end'],line['start']))))<1e-7,(side,'local tangent')
 assert len(p['control_vertices'])==21 and p['exposed_margin_mm']==4.75 and p['thumb_margin_mm']==4.75
 # Each underside has a surviving straight face parallel to its own thumb key.
 for index,angle in [(13,25),(14,10),(15,-5)]:
  line=segments[2*index+1];dx,dy=diff(line['end'],line['start'])
  measured=math.degrees(math.atan2(dy,dx if side=='left' else -dx))%180
  assert abs(measured-angle%180)<1e-7,(side,index,measured)
 assert outer.covers(Point(reflect(30),70)) and not outer.covers(Point(reflect(51),70))
 assert outer.covers(LineString([(reflect(x),y) for x,y in [(79,79),(101,81),(122,86)]]))
 assert inner.covers(pcb) and pcb.boundary.distance(inner.boundary)>.349
 x0,x1=(116.55,129.05) if side=='left' else(30.95,43.45)
 current=electrical['halves'][side]
 assert hashlib.sha256((R/f'hardware/revI/flan36-{side}.kicad_pcb').read_bytes()).hexdigest()==current['pcb_sha256']
 interface=current['slim_electronics'];y0,y1=interface['battery_aperture_y']
 notch=interface['rear_lead_notch_xy']
 aperture=box(x0,y0,x1,y1).union(box(*notch[0],*notch[1]));board=pcb.difference(aperture)
 for q in p['pcb_cutouts']:board=board.difference(Polygon(q))
 assert board.is_valid and board.geom_type=='Polygon' and len(board.interiors)==3
 pads=json.loads((R/f'build/revI/pads-{side}.json').read_text());clearances=[]
 for q in pads:
  shape=Polygon(q['polygon']);assert board.covers(shape),(side,q['ref'],q['pad'],'outside board')
  d=shape.distance(board.boundary);assert d>=.499,(side,q['ref'],q['pad'],d)
  clearances.append({'ref':q['ref'],'pad':q['pad'],'clearance_mm':round(d,6)})
 gaps={}
 cuts=[]
 for k in layout['halves'][side]:
  cut=rotate(box(k['x']-7,k['y']-7,k['x']+7,k['y']+7),-k['angle'],origin=(k['x'],k['y']));assert outer.covers(cut)
  gaps[k['ref']]=round(cut.distance(outer.boundary),5);cuts.append(cut)
 exposed=['K01','K02','K03','K04','K05','K11','K21','K22','K30']
 assert all(gaps[k]>=3.99 for k in exposed),(side,gaps)
 # Bring the right side back to the left coordinate frame for identical face semantics.
 normal_samples=rim_samples(Polygon(profiles['left']['outer']),layout['halves']['left']) if side=='left' else rim_samples(Polygon([[160-x,y] for x,y in p['outer']]),[dict(k,x=160-k['x'],angle=-k['angle']) for k in layout['halves'][side]])
 for row in normal_samples:
  expected=4.75
  assert max(abs(v-expected) for v in [row['minimum_mm'],row['maximum_mm']])<.00002,(side,row,expected)
 fastener_clearance=[]
 for m in mounts['left']:
  pt=Point(reflect(m['xy'][0]),m['xy'][1]);assert outer.covers(pt.buffer(max(m['post_radius'],m['head_diameter']/2)))
  gap=min(pt.distance(c) for c in cuts);fastener_clearance.append({'id':m['id'],'post_to_cut_mm':gap-m['post_radius'],'head_to_cut_mm':gap-m['head_diameter']/2})
 assert min(v['post_to_cut_mm'] for v in fastener_clearance)>0
 batteries_report={ident:{'nominal_dimensions_mm':[v['width'],v['length'],v['height']],'aperture_lateral_gap_per_side_mm':(12.5-v['width'])/2,'cage_roof_clearance_mm':6.2-2-v['height']} for ident,v in batteries.items()}
 assert all(v['aperture_lateral_gap_per_side_mm']>=.25 for v in batteries_report.values())
 report['halves'][side]={'case_size_mm':[round(outer.bounds[2]-outer.bounds[0],3),round(outer.bounds[3]-outer.bounds[1],3)],'case_plan_area_mm2':round(outer.area,3),'intentional_corners':21,'exposed_rim_mm':4.75,'thumb_recess_rim_mm':4.75,'normal_samples':normal_samples,'fastener_clearances':fastener_clearance,'corner_strategy':'Locally bounded tangent arcs','nominal_wall_mm':1.3,'pcb_to_cavity_mm':round(pcb.boundary.distance(inner.boundary),5),'minimum_copper_to_edge_mm':min(x['clearance_mm'] for x in clearances),'copper_clearances':clearances,'all_fasteners_inside_silhouette':True,'switch_cut_to_outer_mm':gaps,'batteries':batteries_report}
report['mirror_max_error_mm']=0.0
report['lcd_flank_protrusion_mm']=0.0
report['thumb_curve_tangent_continuity']=True
angles=[]
for index in [-1,-2]:
 a=left['control_vertices'][index-1];b=left['control_vertices'][index];c=left['control_vertices'][(index+1)%len(left['control_vertices'])]
 u=[a[i]-b[i] for i in (0,1)];v=[c[i]-b[i] for i in (0,1)]
 angle=math.degrees(math.acos(sum(x*y for x,y in zip(u,v))/(math.hypot(*u)*math.hypot(*v))))
 assert abs(angle-90)<1e-8;angles.append(angle)
report['pinky_backbone_angles_degrees']=angles
prior=json.loads((R/'design/revI-lcd-curve-baseline.json').read_text())
assert Polygon(prior['outer']).bounds[2]-prior['lcd_flank_x_mm']>2.5 and prior['curve_segments']==0
report['regression_angular_protruding_outline_rejected']=True
assert baseline['layout_sha256']==hashlib.sha256((R/'design/layout.json').read_bytes()).hexdigest()
report['regression_previous_outline_rejected']=True
local_prior=json.loads((R/'design/revI-local-curves-baseline.json').read_text())
assert any(s['kind']=='bezier' for s in local_prior['segments']) and local_prior['corner_radius_mm']==.8
assert not any(s['kind']=='bezier' for s in left['outer_segments'])
report['regression_spanning_thumb_curve_rejected']=True
report['exceptions']=['Interior bridges between key groups', 'Frame-to-plate service joint', 'Thumb and recess faces retain 4.75 mm for the existing pads', 'Locally bounded tangent rounds; 4.75 mm finger faces']
report['inputs']={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in ['design/layout.json','design/revI-profiles.json','design/revI-mounts.json','design/batteries.json','tools/check_revI_outline.py','tools/build_revI_profiles.py','design/revI-rim-baseline.json','design/revI-lcd-curve-baseline.json','design/revI-local-curves-baseline.json']}
for p in ['validation/revI-electrical.json',*[f'hardware/revI/flan36-{s}.kicad_pcb' for s in ('left','right')],*[f'build/revI/pads-{s}.json' for s in ('left','right')]]:
 report['inputs'][p]=hashlib.sha256((R/p).read_bytes()).hexdigest()
(R/'validation/revI-outline.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: Aligned LCD flank, local tangent thumb curves, key-aligned finger rim, exact mirror, original-regression rejection, actual copper >=0.5mm, internal fasteners,36 unchanged cutouts and both nominal cells')
