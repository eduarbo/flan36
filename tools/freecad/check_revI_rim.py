"""Read native case symmetry and exposed opening-to-rim distances from actual solids.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import sys,os,json,hashlib,math
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import Part
R=Path(__file__).resolve().parents[2];G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(R/'mechanical/revI/Flan36.FCStd'))
for prefix in ['L_','R_']:doc.getObject(prefix+'Half').Placement=A.Placement()
doc.recompute();parts={o.PartID:o.Shape.copy() for o in doc.Objects if hasattr(o,'PartID')}
# Exact plane reflection preserves analytic surfaces for the Boolean comparison.
symmetry={}
for name in ['tray','key-plate']:
 a=parts['left-'+name].mirror(A.Vector(80,0,0),A.Vector(1,0,0));b=parts['right-'+name]
 mismatch=a.cut(b).Volume+b.cut(a).Volume
 assert mismatch<1e-5,(name,mismatch)
 symmetry[name]={'symmetric_difference_mm3':mismatch,'left_volume_mm3':parts['left-'+name].Volume,'right_volume_mm3':b.Volume}
layout=json.loads((R/'design/layout.json').read_text())['halves'];study=json.loads((R/'validation/revI-outline.json').read_text())
rows=[]
curve_checks=[]
for side,prefix in [('left','L_'),('right','R_')]:
 for name in ['OuterPadSketch','PlatePadSketch']:
  sketch=doc.getObject(prefix+name);arcs=[g for g in sketch.Geometry if isinstance(g,Part.ArcOfCircle)]
  assert len(arcs)==21 and not any(isinstance(g,Part.BSplineCurve) for g in sketch.Geometry),(prefix,name,'local native arcs missing')
 for name in ['tray','key-plate']:
  shape=parts[side+'-'+name];assert shape.isValid()
  bound=shape.BoundBox.XMax if side=='left' else shape.BoundBox.XMin
  assert abs(bound-(135 if side=='left' else 25))<1e-5,(side,name,bound)
  curve_checks.append({'side':side,'part':name,'flank_mm':bound,'native_local_arcs':True})
for side in ['left','right']:
 plate=parts[side+'-key-plate'];keys={k['ref']:k for k in layout[side]}
 for spec in study['halves'][side]['normal_samples']:
  k=keys[spec['key']];face=spec['face'];normal={'north':(0,-1),'south':(0,1),'east':(1,0),'west':(-1,0)}[face]
  # Face semantics are left-local; mirror the local X parameter on the right.
  angle=-math.radians(k['angle']);a,b=spec['face_local_range_mm'];lengths=[]
  for i in range(9):
   t=a+(b-a)*i/8;x,y=(t,normal[1]*7) if normal[1] else(normal[0]*7,t)
   nx,ny=normal
   if side=='right':x=-x;nx=-nx
   qx=k['x']+x*math.cos(angle)-y*math.sin(angle);qy=k['y']+x*math.sin(angle)+y*math.cos(angle)
   dx=nx*math.cos(angle)-ny*math.sin(angle);dy=nx*math.sin(angle)+ny*math.cos(angle)
   ray=Part.makeLine(A.Vector(qx,-qy,7),A.Vector(qx+dx*5.75,-qy-dy*5.75,7))
   length=plate.common(ray).Length;assert abs(length-4.75)<.00002,(side,spec,length);lengths.append(length)
  rows.append({'side':side,'key':spec['key'],'face':face,'min_mm':min(lengths),'max_mm':max(lengths),'samples':len(lengths)})
report={'scope':'Actual native plate solids, 216 normal samples; tray and plate mirrored through X=80','curve_checks':curve_checks,'symmetry':symmetry,'normal_samples':rows,'nominal_rim_mm':4.75,'tolerance_mm':.00002,'physical_acceptance':False,'source_sha256':hashlib.sha256((R/'mechanical/revI/Flan36.FCStd').read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(R/'validation/revI-rim-solids.json').write_text(json.dumps(report,indent=2)+'\n')
sys.__stdout__.write('PASS: native tray/plate mirror and 216 exposed normal samples at 4.75 mm\n');sys.__stdout__.flush();A.closeDocument(doc.Name)
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0)
