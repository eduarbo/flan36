"""Read actual saved case solids: wall, floor and rim/plate joint.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,hashlib,sys,os
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import Part
R=Path(__file__).resolve().parents[2];source=R/'mechanical/revI/Flan36.FCStd';digest=hashlib.sha256(source.read_bytes()).hexdigest()
G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(source))
# Inspect the stored native solids; rebuilding and edit/reopen checks are separate.
rows=[]
for side,prefix in [('left','L_'),('right','R_')]:
 for style in ['solid','rim','terrace']:
  base=doc.getObject(prefix+'Case_'+style+'_base').Shape;plate=doc.getObject(prefix+'Case_'+style+'_plate').Shape
  assert base.isValid() and plate.isValid() and len(base.Solids)==len(plate.Solids)==1
  mx=lambda x:x if side=='left' else 160-x
  widths=[]
  for y in [29,46,63]:
   for z in [2.3,4.3]:
    ray=Part.makeLine(A.Vector(mx(17),-y,z),A.Vector(mx(23),-y,z))
    width=base.common(ray).Length;expected=1.05 if style=='terrace' else 1.3
    assert abs(width-expected)<1e-5,(side,style,'sidewall',width);widths.append(width)
  floor=base.common(Part.makeLine(A.Vector(mx(30),-46,-.1),A.Vector(mx(30),-46,3))).Length
  assert abs(floor-1.4)<1e-5,(side,style,'floor',floor)
  row={'side':side,'style':style,'sidewall_samples_mm':widths,'floor_sample_mm':floor}
  if style=='rim':
   ray=Part.makeLine(A.Vector(mx(18.25),-46,7),A.Vector(mx(23),-46,7))
   rim=base.common(ray).Length;ledge=plate.common(ray).Length;joint=4.75-rim-ledge
   assert abs(rim-.9)<1e-5 and abs(joint-.2)<1e-5 and abs(ledge-3.65)<1e-5,(side,rim,ledge,joint)
   row.update(rim_width_mm=rim,joint_mm=joint,plate_ledge_mm=ledge)
  rows.append(row)
assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
(R/'validation/revI-cases.json').write_text(json.dumps({'source_sha256':digest,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Stored native solids; representative straight-face wall and joint sections. Not printed strength or tolerance acceptance.','measurements':rows,'physical_acceptance':False},indent=2)+'\n')
A.closeDocument(doc.Name);sys.__stdout__.write('PASS: all six native case pairs; measured floors, sidewalls and raised-rim joints\n');sys.__stdout__.flush()
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0)
