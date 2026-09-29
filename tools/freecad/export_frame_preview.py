"""Export native frame preview meshes without the unrelated assembly STEP work.
Preview only; full mechanical export and checks remain required for delivery.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,os,sys
from pathlib import Path
import FreeCAD as A
import MeshPart
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
values=sys.argv[1:]
while values and not values[0].startswith('--'):values.pop(0)
a=p.parse_args(values);a.output.mkdir(parents=True,exist_ok=True);doc=A.openDocument(str(a.source));doc.recompute()
for side,prefix in [('left','L_'),('right','R_')]:
 doc.getObject(prefix+'Half').Placement=A.Placement();doc.recompute()
 for o in doc.Objects:
  if not o.Name.startswith(prefix) or o.TypeId=='App::Link' or not hasattr(o,'FrameStyle'):continue
  for part in o.MaterialParts:
   m=MeshPart.meshFromShape(Shape=part.Shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
   assert m.isSolid(),part.Name
   m.write(str(a.output/f'{side}-frame-{o.FrameStyle}-{part.ColorRole}.stl'))
print('Exported native frame preview meshes',file=sys.__stdout__,flush=True)
A.closeDocument(doc.Name);os._exit(0)
