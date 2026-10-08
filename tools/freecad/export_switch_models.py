"""Export licensed KiSwitch geometry, keeping its native assembly datum.
The switch PCB datum is Z=0; placement and model limits are documented.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import FreeCAD as A,FreeCADGui as G,MeshPart,Part,sys,os,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'mechanical/revI';G.showMainWindow();d=A.openDocument(str(ROOT/'components/sources/SW_Kailh_Choc_V1.FCStd'));records={}
for name,labels in [('choc-body',['Upper_Housing','Lower_Housing','Pin_1','Pin_2']),('choc-stem',['Stem'])]:
 entries=[]
 for obj in d.Objects:
  if obj.Label not in labels:continue
  shape=obj.Shape.copy();shape.Placement=obj.getGlobalPlacement();p=OUT/f'component-{name}-{len(entries)}.stl';MeshPart.meshFromShape(Shape=shape,LinearDeflection=.06,AngularDeflection=.2,Relative=False).write(str(p));color={'Upper_Housing':'#d0d3cb','Lower_Housing':'#242729','Pin_1':'#b99f62','Pin_2':'#b99f62','Stem':'#ba4047'}[obj.Label]
  entries.append({'name':obj.Label,'path':str(p.relative_to(ROOT)),'color':color,'bounds_mm':[getattr(shape.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]})
 records[name]=entries
A.closeDocument(d.Name)
# Preserve the socket source in its own coordinate frame for inspection; do not
# modify source coordinates here; hotswap_geometry.py owns the verified assembly datum.
d=A.openDocument(str(ROOT/'components/sources/SW_Hotswap_Kailh_Choc_v1.FCStd'));o=d.getObject('Feature');s=o.Shape;p=OUT/'component-choc-socket.stl';MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.2,Relative=False).write(str(p));records['socket_source']={'path':str(p.relative_to(ROOT)),'bounds_mm':[getattr(s.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']],'status':'Source coordinates preserved for inspection; nominal assembly registration uses both mounting bores and both solder terminals. See validation/revI-hotswap-registration.json. Physical fit remains unqualified.','registration_recipe':'tools/freecad/hotswap_geometry.py'}
(ROOT/'components/switches.json').write_text(json.dumps(records,indent=2)+'\n');A.closeDocument(d.Name)
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0)
