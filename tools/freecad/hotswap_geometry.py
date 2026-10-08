"""Register pinned KiSwitch socket CAD using two bores and solder-contact planes.
Nominal geometry only; solder thickness, force and real parts remain unqualified.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'components/sources/SW_Hotswap_Kailh_Choc_v1.FCStd'
SOURCE_SHA='9edce0ece1a32a929694912a38509c972078767c0f6456d6e5040359c57bae78'

def local_socket():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    d=A.openDocument(str(SOURCE));obj=d.getObject('Feature');shape=obj.Shape.copy()
    colors=list(obj.ViewObject.DiffuseColor) if obj.ViewObject else []
    if len(colors)==1:colors*=len(shape.Faces)
    A.closeDocument(d.Name)
    bores={}
    for edge in shape.Edges:
        c=edge.Curve
        if isinstance(c,Part.Circle) and abs(c.Radius-1.45)<1e-6 and abs(c.Axis.z)>.999:
            bores[(round(c.Center.x,6),round(c.Center.y,6))]=(c.Center.x,c.Center.y)
    assert len(bores)==2,bores
    origins=sorted(bores.values());targets=[(0,5.95),(5,3.75)]
    offsets=[(tx-x,ty-y) for (x,y),(tx,ty) in zip(origins,targets)]
    assert max(abs(a-b) for a,b in zip(*offsets))<1e-6
    dx,dy=offsets[0]
    candidates=[f for f in shape.Faces if isinstance(f.Surface,Part.Plane)
        and f.normalAt(0,0).z>.999 and (f.CenterOfMass.x<-2 or f.CenterOfMass.x>7)]
    z=max(f.CenterOfMass.z for f in candidates)
    contacts=[f for f in candidates if abs(f.CenterOfMass.z-z)<1e-6]
    assert len(contacts)==4 and all(abs(f.Area-.8)<1e-5 for f in contacts), [(f.Area,tuple(f.CenterOfMass),str(f.BoundBox)) for f in contacts]
    # Both solder-contact faces lie wholly inside the current 2.6 mm square pads.
    for face in contacts:
        px,py=(-3.275,5.95) if face.CenterOfMass.x<0 else (8.275,3.75)
        b=face.BoundBox
        assert px-1.3 < b.XMin+dx < b.XMax+dx < px+1.3
        assert py-1.3 < b.YMin+dy < b.YMax+dy < py+1.3
    shape.translate(A.Vector(dx,dy,-z))
    # Keep source locations inside an identity-placed compound so assigning a
    # per-key object Placement cannot discard the source registration.
    shape=Part.makeCompound([shape])
    assert shape.Placement.isIdentity()
    b=shape.optimalBoundingBox(False,False)
    assert abs(b.ZMin+1.85)<1e-6 and abs(b.ZMax-1.2)<1e-6, (b.ZMin,b.ZMax)
    assert shape.isValid() and shape.Solids
    report={'source_path':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,
        'source_bore_centers_xy_mm':origins,'footprint_holes_cad_xy_mm':targets,
        'source_solder_contact_z_mm':z,'source_to_pcb_underside_translation_mm':[dx,dy,-z],
        'solder_contact_faces':4,'solder_terminals':2,'solder_contacts_inside_pads':True,
        'local_bounds_mm':[getattr(b,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']],
        'datum':'Top of the two metal solder-contact faces on nominal PCB underside; body shoulder remains 0.15 mm below it.',
        'qualification':'Nominal source registration only; no physical fit or solder-thickness qualification.'}
    return shape,colors,report
