"""Check final inlay sections after Booleans, not just recipe widths.
A 0.8 mm round feature core must survive in every connected color island.
This detects clipped slivers; it does not qualify a nozzle, toolpath or bonding.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
from shapely.geometry import Polygon,LineString
from shapely import set_precision
from shapely.ops import unary_union,polygonize
import flush_frames as F
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
values=sys.argv[1:]
while values and not values[0].startswith('--'):values.pop(0)
a=parser.parse_args(values)
doc=A.openDocument(str(a.source));doc.recompute();roof=float(doc.Parameters.FrameTop)
result={'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'section_z_mm':roof-.2,'contour_deflection_mm':.001,'minimum_island_core_diameter_mm':.8,'physical_acceptance':False,'frames':{},'failures':[]}
for side,prefix in [('left','L_'),('right','R_')]:
 doc.getObject(prefix+'Half').Placement=A.Placement();doc.recompute()
 for style in F.STYLES:
  obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final');records=[]
  for part in obj.MaterialParts:
   if part.ColorRole=='body':continue
   lines=[]
   for wire in part.Shape.slice(A.Vector(0,0,1),roof-.2):
    for edge in wire.Edges:
     pts=edge.discretize(Deflection=.001)
     lines.append(set_precision(LineString([(p.x,p.y) for p in pts]),.000001))
   # Section wires can revisit a shared vertex. Polygonize individual native
   # edges and classify cells by exact solid occupancy, including inner holes.
   cells=[]
   for polygon in polygonize(unary_union(lines)):
    probe=polygon.representative_point()
    if part.Shape.isInside(A.Vector(probe.x,probe.y,roof-.2),.00001,True):cells.append(polygon)
   region=unary_union(cells)
   if region.is_empty or not region.is_valid:raise ValueError((part.Name,'invalid or empty material section'))
   expected_area=part.Shape.Volume/.4
   if abs(region.area-expected_area)>max(.06,.005*expected_area):raise ValueError((part.Name,'section does not account for native volume',region.area,expected_area))
   islands=list(region.geoms) if hasattr(region,'geoms') else [region]
   for index,island in enumerate(islands):
    core=island.buffer(-.399) # 0.001 mm section approximation allowance.
    record=dict(role=part.ColorRole,island=index,area_mm2=island.area,core_survives=not core.is_empty)
    records.append(record)
    if core.is_empty:result['failures'].append(dict(frame=side+'-'+style,**record))
  result['frames'][side+'-'+style]=records
result['passed']=not result['failures'];a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'frames':len(result['frames']),'failures':result['failures'],'passed':result['passed']}),file=sys.__stdout__,flush=True)
A.closeDocument(doc.Name)
os._exit(0 if result['passed'] else 1)
