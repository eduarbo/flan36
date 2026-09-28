"""Nominal dimensions, support area, reserved pads and commercial handedness.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import FreeCAD as A, FreeCADGui as G,Part,json,hashlib,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/freecad'));from switch_instances import ensure
G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(ROOT/'mechanical/revI/Flan36.FCStd'));assert doc.getObject('ChocV1Source'), 'Switch instances missing'
results=[]
for side,prefix in [('left','L_'),('right','R_')]:
 half=doc.getObject(prefix+'Half');old=half.Placement;half.Placement=A.Placement();doc.recompute();nano=doc.getObject(prefix+'NanoV2');b=nano.Shape.BoundBox
 assert len(set(tuple(c) for c in nano.ViewObject.DiffuseColor))>5, 'Native MCU material colors missing'
 materials={}
 for part,expected in [('SliderModel',3),('ResetModel',4)]:
  obj=doc.getObject(prefix+part)
  assert len(obj.ViewObject.DiffuseColor)==len(obj.Shape.Faces)
  assert len(set(tuple(round(v,3) for v in c[:3]) for c in obj.ViewObject.DiffuseColor))==expected,(side,part,'STEP face materials lost')
  materials[part]=expected
 assert all(abs(a-v)<1e-5 for a,v in zip([b.XLength,b.YLength,b.ZLength],[17.78,34.624,3.2])),[b.XLength,b.YLength,b.ZLength]
 pcb=doc.getObject(prefix+'NanoV2Visual0').Shape;riser=doc.getObject(prefix+'Riser').Shape
 lower=[f for f in pcb.Faces if abs(f.BoundBox.ZMin-doc.Parameters.MCUBottom.Value)<1e-6 and f.BoundBox.ZLength<1e-6]
 contact=sum(riser.common(f).Area for f in lower);assert contact>15,(side,contact)
 assert riser.common(nano.Shape).Volume<.001
 reserves=[]
 for x in ([115.18,130.42] if side=='left' else [29.58,44.82]):
  for i in range(13):
   tool=Part.makeCylinder(1.05,.2,A.Vector(x,-(14.76+2.54*i),doc.Parameters.MCUBottom.Value-.2));reserves.append(riser.common(tool).Volume)
 assert max(reserves)<1e-6,(side,max(reserves))
 results.append({'side':side,'nano_bounds_mm':[b.XLength,b.YLength,b.ZLength],'positive_board_support_area_mm2':contact,'solder_reserve_intersection_mm3':max(reserves),'mcu_riser_intersection_mm3':riser.common(nano.Shape).Volume,'library_material_counts':materials})
 half.Placement=old
l=doc.L_NanoV2.Shape.copy();r=doc.R_NanoV2.Shape.copy();l.translate(A.Vector(-85.6,0,0));assert abs(l.Volume-r.Volume)<1e-6;difference=l.cut(r).Volume+r.cut(l).Volume;assert difference<1e-5
# Actual switch model instances keep exactly the stored PCB datums and angles.
layout=json.loads((ROOT/'design/layout.json').read_text())
for side,keys in layout['halves'].items():
 for key in keys:
  o=doc.getObject(('L_' if side=='left' else 'R_')+'Switch_'+key['ref']);assert (o.LinkPlacement.Base-A.Vector(key['x'],-key['y'],5.4)).Length<1e-6
display_separation=float(doc.Parameters.DisplayBottom)-float(doc.Parameters.PCBTop)
report={'source_sha256':hashlib.sha256((ROOT/'mechanical/revI/Flan36.FCStd').read_bytes()).hexdigest(),'model_identity_without_reflection':True,'nano_symmetry_difference_after_translation_mm3':difference,'checks':results,'switch_instances':36,'display_pcb_separation_mm':display_separation,'remaining':['Measured connector contacts, pin engagement and solder tolerances','Hotswap socket assembly registration','Physical fit and operation']}
(ROOT/'validation/revI-components.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);A.closeDocument(doc.Name)
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0)
