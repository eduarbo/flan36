"""Literal approved artwork paths to native, flush material solids.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,math
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parents[2]
PLAN=json.loads((ROOT/'design/approved-frame-master-r4.json').read_text())
MASTER_PATH=ROOT/PLAN['master_path']
assert hashlib.sha256(MASTER_PATH.read_bytes()).hexdigest()==PLAN['master_sha256']
MASTER=json.loads(MASTER_PATH.read_text())
APPROVED=tuple(PLAN['approved_styles'])
ROLES=('body','detail','accent','secondary')
_FROZEN={}
_CONTEXT=None
_READABLE_RIGHT=False

def use_document(doc):
    """Choose the recorded correction for this document, preserving R4 replay."""
    global MASTER_PATH,MASTER,_CONTEXT,_READABLE_RIGHT
    orientation=doc.getObject('FrameArtworkOrientation')
    _READABLE_RIGHT=orientation is not None
    if orientation:
        assert orientation.Mode=='same-reading-direction'
        assert json.loads(orientation.StylesJSON)==list(APPROVED)
    correction=doc.getObject('DisplaySeamCorrection')
    path=ROOT/(correction.MasterPath if correction else PLAN['master_path'])
    digest=correction.MasterSHA256 if correction else PLAN['master_sha256']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Frame master changed'
    if _CONTEXT!=digest:
        MASTER_PATH=path;MASTER=json.loads(path.read_text());_FROZEN.clear();_CONTEXT=digest
    return correction

def frozen_regions(side,style):
    """Compare against the saved approval artifact, not only today's parser."""
    if not _FROZEN:
        corrected=MASTER.get('revision')=='R4-seam-1'
        path=MASTER_PATH.parent/('Seam-candidate.FCStd' if corrected else 'Artwork-R4.FCStd')
        receipt=json.loads((MASTER_PATH.parent/'geometry-check.json').read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['native_sha256' if corrected else 'native_plan_sha256']
        active=A.ActiveDocument
        source=A.openDocument(str(path))
        for name in APPROVED:
            for role in ROLES:_FROZEN[name,role]=source.getObject(name+'_'+role+('_Plan' if corrected else '')).Shape.copy()
        A.closeDocument(source.Name)
        if active:A.setActiveDocument(active.Name)
    readable=side=='right' and _READABLE_RIGHT
    transform=A.Matrix();transform.A14=111 if side=='left' else (25 if readable else 49);transform.A24=-11
    if side=='right' and not readable:transform.A11=-1
    result={}
    for role in ROLES:
        shape=_FROZEN[style,role].copy();shape.transformShape(transform,False,False);result[role]=shape
    if readable:
        # Only the artwork is translated. The structural outline has unequal
        # corner radii, so its body region must keep the right-hand domain.
        domain,_=domains(side)
        for role in ROLES[1:]:domain=domain.cut(result[role])
        result['body']=domain
    return result

def face(commands,side,artwork=False):
    def pt(p):
        x=111+p[0] if side=='left' else (25+p[0] if artwork and _READABLE_RIGHT else 49-p[0])
        return A.Vector(x,-11-p[1],0)
    edges=[];p=start=None
    for op,*v in commands:
        if op=='M':p=start=v
        elif op=='L':
            if pt(p).distanceToPoint(pt(v))>1e-9:edges.append(Part.makeLine(pt(p),pt(v)))
            p=v
        elif op=='C':
            b=Part.BezierCurve();b.setPoles([pt(p),pt(v[:2]),pt(v[2:4]),pt(v[4:])]);edges.append(b.toShape());p=v[4:]
        elif op=='A':
            r,ry,rot,large,sweep,x,y=v;assert r==ry and rot==0
            dx,dy=x-p[0],y-p[1];d=math.hypot(dx,dy)
            h=math.sqrt(max(0,r*r-d*d/4))*(-1 if bool(large)==bool(sweep) else 1)
            cx=(p[0]+x)/2-dy/d*h;cy=(p[1]+y)/2+dx/d*h
            aa=math.atan2(p[1]-cy,p[0]-cx);bb=math.atan2(y-cy,x-cx)
            delta=(bb-aa)%(2*math.pi) if sweep else -((aa-bb)%(2*math.pi))
            mid=[cx+r*math.cos(aa+delta/2),cy+r*math.sin(aa+delta/2)]
            edges.append(Part.Arc(pt(p),pt(mid),pt([x,y])).toShape());p=[x,y]
        elif op=='Z':
            if pt(p).distanceToPoint(pt(start))>1e-9:edges.append(Part.makeLine(pt(p),pt(start)))
            p=start
        else:raise ValueError(op)
    out=Part.Face(Part.Wire(edges));assert out.isValid();return out

def domains(side):
    outer=face(MASTER['outer_commands'],side);win=face(MASTER['aperture_commands'],side)
    domain=outer.cut(win);xd=MASTER['construction']['xy_domains']
    relief=face(xd['relief_commands'],side);header=face(xd['header_commands'],side)
    return domain,dict(ordinary=domain.cut(relief),collar=relief.common(domain).cut(header),cover=header.common(domain))

def regions(side,style):
    domain,_=domains(side);window=face(MASTER['aperture_commands'],side)
    result={r:Part.Shape() for r in ROLES};result['body']=domain
    for f in MASTER['styles'][style]['features']:
        shape=face(f['commands'],side,artwork=True)
        if f['window_cut']:shape=shape.cut(window)
        assert shape.cut(domain).Area<1e-7,(style,f['id'],'outside master')
        for role in ROLES:
            if not result[role].isNull():result[role]=result[role].cut(shape)
        role=f['color'];result[role]=shape if result[role].isNull() else result[role].fuse(shape)
    return result

def build(recipe,style):
    import flush_frames as F
    correction=use_document(recipe.doc)
    side=recipe.side;doc=recipe.doc;theme=MASTER['styles'][style];flat=regions(side,style);domain,zones=domains(side)
    blank=recipe.smooth
    materials=[];occupied=[];features=[]
    for role in ROLES[1:]:
        volumes=[]
        for zone,floor in [('ordinary',13.19),('collar',12.725),('cover',13.19)]:
            section=flat[role].common(zones[zone])
            if section.isNull() or section.Area<1e-8:continue
            node=recipe.add('Part::Feature',style+'_R4_'+role+'_'+zone+'_Face');node.Shape=section
            volume=recipe.add('Part::Extrusion',style+'_R4_'+role+'_'+zone)
            volume.Base=node;volume.Dir=A.Vector(0,0,1);volume.Solid=True
            volume.Placement.Base.z=floor;volume.setExpression('LengthFwd',f'Parameters.FrameTop - {floor} mm')
            volumes.append(volume)
        assert volumes,(style,role,'empty color')
        material=recipe.combine(style+'_R4_'+role,volumes)
        F.prop(material,'ColorRole','App::PropertyString',role);material.Label=theme['label']+' · '+role
        materials.append(material);occupied.append(material)
    used=recipe.combine(style+'_R4_Occupied',occupied)
    body=recipe.cut(style+'_R4_Body',blank,used);F.prop(body,'ColorRole','App::PropertyString','body')
    body.Label=theme['label']+' · structural shell';materials=[body]+materials
    final=recipe.add('Part::MultiFuse',style+'_Final');final.Shapes=materials;final.Refine=False
    final.Label='Frame · '+theme['label']+' · approved R4'
    for name,kind,value in [('FrameStyle','App::PropertyString',style),('MaterialParts','App::PropertyLinkList',materials),('SmoothSource','App::PropertyLink',blank),('PrototypePrintable','App::PropertyBool',True),('InlayDepth','App::PropertyLength',.4),('ApprovedMasterSHA256','App::PropertyString',PLAN['master_sha256']),('ModelStatus','App::PropertyString','Approved R4 artwork; nominal assembly only, physical fit untested'),('MaterialSpecSHA256','App::PropertyString',hashlib.sha256(json.dumps(recipe.spec['styles'][style],sort_keys=True).encode()).hexdigest()),('ArtworkFeatures','App::PropertyLinkList',features)]:F.prop(final,name,kind,value)
    if correction:
        F.prop(final,'SeamCorrectionSHA256','App::PropertyString',correction.MasterSHA256)
        final.Label='Frame · '+theme['label']+' · R4 / corrected display seam'
    if _READABLE_RIGHT and side=='right':
        F.prop(final,'ArtworkOrientation','App::PropertyString','same-reading-direction')
    return final

def top_faces(shape,z):
    flat=[]
    for f in shape.Faces:
        b=f.BoundBox
        if abs(b.ZMin-z)<1e-6 and abs(b.ZMax-z)<1e-6:
            q=f.copy();q.translate(A.Vector(0,0,-z));flat.append(q)
    return Part.makeCompound(flat)

def validate(doc,side,smooth,obj,spec=None,output_dir=None):
    import flush_frames as F
    import MeshPart
    correction=use_document(doc)
    roof=float(doc.Parameters.FrameTop);assert abs(roof-13.59)<1e-7
    expected=regions(side,obj.FrameStyle);frozen=frozen_regions(side,obj.FrameStyle);domain,zones=domains(side);whole=obj.Shape
    assert whole.isValid() and len(whole.Solids)==1,(obj.Name,'frame disconnected')
    assert whole.cut(smooth.Shape).Volume+smooth.Shape.cut(whole).Volume<1e-5
    material_records=[];role_errors={};pairs={}
    for i,part in enumerate(obj.MaterialParts):
        shape=part.Shape;role=part.ColorRole
        assert shape.isValid() and shape.Solids and all(s.isClosed() for s in shape.Solids),(part.Name,'invalid material')
        if role=='body':assert len(shape.Solids)==1,(part.Name,'structural body disconnected')
        measured=top_faces(shape,roof);target=expected[role]
        err=measured.cut(target).Area+target.cut(measured).Area
        assert err<.002,(side,obj.FrameStyle,role,'top differs from approved artwork',err)
        frozen_err=measured.cut(frozen[role]).Area+frozen[role].cut(measured).Area
        assert frozen_err<.002,(side,obj.FrameStyle,role,'top differs from saved planar approval',frozen_err)
        role_errors[role]=err
        for other in obj.MaterialParts[i+1:]:
            v=shape.common(other.Shape).Volume;assert v<1e-5,(part.Name,other.Name,v);pairs[role+'/'+other.ColorRole]=v
        if role!='body':
            expected_volumes=[]
            for zone,z0 in [('ordinary',13.19),('collar',12.725),('cover',13.19)]:
                f=target.common(zones[zone])
                if f.Area>1e-8:
                    s=f.extrude(A.Vector(0,0,roof-z0));s.translate(A.Vector(0,0,z0));expected_volumes.append(s)
            target3d=Part.makeCompound(expected_volumes)
            v=shape.cut(target3d).Volume+target3d.cut(shape).Volume
            assert v<1e-5,(part.Name,'wrong Z construction',v)
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
        assert mesh.isSolid(),(part.Name,'open mesh')
        record={'role':role,'volume_mm3':shape.Volume,'solids':len(shape.Solids),'closed_mesh':True}
        if output_dir:
            p=Path(output_dir);p.mkdir(parents=True,exist_ok=True);stem=f'{side}-frame-{obj.FrameStyle}-{role}'
            mesh.write(str(p/(stem+'.stl')));shape.exportStep(str(p/(stem+'.step')))
        material_records.append(record)
    F.prop(obj,'FrameFaceRoles','App::PropertyString',json.dumps(F.face_roles(obj)))
    return dict(style=obj.FrameStyle,side=side,artwork_orientation='same-reading-direction' if _READABLE_RIGHT else 'historical-mirrored',approved_master_sha256=PLAN['master_sha256'],seam_correction_sha256=correction.MasterSHA256 if correction else None,top_face_difference_mm2=role_errors,saved_planar_approval_compared=True,exact_z_domains=True,material_parts=material_records,pair_intersections_mm3=pairs,roof_mm=roof,physical_acceptance=False)
