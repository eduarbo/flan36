"""Measure actual visible and backed roof domains without modifying the native file.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
import FreeCAD as A
from shapely import set_precision
from shapely.geometry import LineString
from shapely.ops import polygonize,unary_union
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
values=sys.argv[1:]
while values and not values[0].startswith('--'):values.pop(0)
a=p.parse_args(values);doc=A.openDocument(str(a.source));doc.L_Half.Placement=A.Placement();doc.recompute()
blank=next(o for o in doc.Objects if o.Name.startswith('L_') and getattr(o,'FrameTemplate',False))
spec=json.loads((ROOT/'design/frame-finishes.json').read_text());roof=float(doc.Parameters.FrameTop)
supported=blank.Shape.copy();supported.translate(A.Vector(0,0,spec['minimum_backing_mm']));mask=blank.Shape.common(supported)
def region(shape,z):
 lines=[]
 for wire in shape.slice(A.Vector(0,0,1),z):
  for edge in wire.Edges:
   lines.append(set_precision(LineString([(p.x,-p.y) for p in edge.discretize(Deflection=.001)]),.000001))
 cells=[]
 for polygon in polygonize(unary_union(lines)):
  q=polygon.representative_point()
  if shape.isInside(A.Vector(q.x,-q.y,z),.00001,True):cells.append(polygon)
 result=unary_union(cells)
 if result.is_empty or not result.is_valid:raise ValueError('Invalid roof section')
 return result
report={'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'roof_mm':roof,
 'section_z_mm':roof-spec['inlay_depth_mm']/2,'minimum_backing_mm':spec['minimum_backing_mm'],
 'roof_wkt':region(blank.Shape,roof-spec['inlay_depth_mm']/2).wkt,
 'supported_wkt':region(mask,roof-spec['inlay_depth_mm']/2).wkt}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
print('Measured native roof and supported artwork domain',file=sys.__stdout__,flush=True)
A.closeDocument(doc.Name);os._exit(0)
