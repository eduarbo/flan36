"""Native corrections for the 2026-10-07 audit; historical recipes stay intact.

All dependencies are standard FreeCAD expressions and Boolean features. Opening
and editing the saved file requires no Python proxy or this generator.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
from pathlib import Path
import FreeCAD as A
import Part

ROOT=Path(__file__).resolve().parents[2]


def build_materials(recipe,style,master):
    """Clip fixed approved XY colors to a moving native shell and roof band.

    Ordinary inlays remain 0.4 mm deep. The display collar is through-colored
    down to its relief ceiling; the pin cover is a separate 0.4 mm roof. Filled
    artwork masks avoid leaving the old aperture behind when the window moves.
    """
    import approved_frames as M
    import flush_frames as F
    doc=recipe.doc;prefix='L_' if recipe.side=='left' else 'R_'
    theme=master['styles'][style];flat=M.regions(recipe.side,style,uncut=True)
    def box(name,x,y,z,w,d,h):
        node=recipe.add('Part::Box',style+'_Param_'+name)
        node.Length=w;node.Width=d;node.Height=h;node.Placement.Base=A.Vector(x,y,z)
        return node
    surface=box('Surface',0,-120,13.19,160,140,.4)
    surface.setExpression('Placement.Base.z','Parameters.FrameTop - 0.4 mm')
    relief=doc.getObject(prefix+'LevelDisplayPCBRelief')
    header=doc.getObject(prefix+'LevelHeaderServiceWell')
    collar=box('Collar',0,0,12.725,15.9,37.9,.865)
    for prop in ['Placement.Base.x','Placement.Base.y','Length','Width']:
        collar.setExpression(prop,relief.Name+'.'+prop)
    collar.setExpression('Placement.Base.z',relief.Name+'.Placement.Base.z + '+relief.Name+'.Height')
    collar.setExpression('Height','Parameters.FrameTop - '+relief.Name+'.Placement.Base.z - '+relief.Name+'.Height')
    hole=box('HeaderZone',0,0,0,13.7,3.5,30)
    for prop in ['Placement.Base.x','Placement.Base.y','Length','Width']:
        hole.setExpression(prop,header.Name+'.'+prop)
    collar=recipe.cut(style+'_Param_CollarWithoutHeader',collar,hole)
    depth=recipe.combine(style+'_Param_Depth',[surface,collar])
    materials=[]
    for role in M.ROLES[1:]:
        node=recipe.add('Part::Feature',style+'_Param_'+role+'_Face');node.Shape=flat[role]
        sweep=recipe.add('Part::Extrusion',style+'_Param_'+role+'_Sweep')
        sweep.Base=node;sweep.Dir=A.Vector(0,0,1);sweep.Solid=True;sweep.LengthFwd=30
        band=recipe.common(style+'_Param_'+role+'_Depth',sweep,depth)
        color=recipe.common(style+'_Param_'+role+'_Material',band,recipe.smooth)
        F.prop(color,'ColorRole','App::PropertyString',role);color.Label=theme['label']+' · '+role
        materials.append(color)
    occupied=recipe.combine(style+'_Param_Occupied',materials)
    body=recipe.cut(style+'_Param_Body',recipe.smooth,occupied)
    F.prop(body,'ColorRole','App::PropertyString','body');body.Label=theme['label']+' · structural shell'
    materials=[body]+materials
    final=recipe.add('Part::MultiFuse',style+'_Final');final.Shapes=materials;final.Refine=False
    final.Label='Frame · '+theme['label']+' · approved / parametric'
    values=[('FrameStyle','App::PropertyString',style),('MaterialParts','App::PropertyLinkList',materials),
      ('SmoothSource','App::PropertyLink',recipe.smooth),('PrototypePrintable','App::PropertyBool',True),
      ('InlayDepth','App::PropertyLength',.4),('ApprovedMasterSHA256','App::PropertyString',
       doc.HanafudaApproval.MasterSHA256 if style=='hanafuda' else M.PLAN['master_sha256']),
      ('ModelStatus','App::PropertyString','Approved fixed XY artwork, clipped by native edited shell; physical fit untested'),
      ('ArtworkFeatures','App::PropertyLinkList',[]),('ParametricMaterialPartition','App::PropertyBool',True),
      ('MaterialSpecSHA256','App::PropertyString',hashlib.sha256(json.dumps(recipe.spec['styles'][style],sort_keys=True).encode()).hexdigest()),
      ('SeamCorrectionSHA256','App::PropertyString',doc.DisplaySeamCorrection.MasterSHA256)]
    for name,kind,value in values:F.prop(final,name,kind,value)
    if recipe.side=='right':F.prop(final,'ArtworkOrientation','App::PropertyString','same-reading-direction')
    return final


def display_chain(doc):
    for prefix in ['L_','R_']:
        for name in ['SlimDisplaySocketHousing','SlimDisplaySocketPins','SlimDisplayMaleSpacer',
                     'SlimDisplayMaleContacts','LevelDisplaySolderReserve','LevelDisplayPCBRelief',
                     'LevelHeaderServiceWell','SledCableTunnelTool','SledCableCrossingTool']:
            obj=doc.getObject(prefix+name)
            current=float(obj.Placement.Base.y)
            obj.setExpression('Placement.Base.y',f'{current+2.4:.12g} mm - Parameters.DisplayShiftY')
        # The roof cover follows FrameTop, retaining its 0.4 mm thickness.
        well=doc.getObject(prefix+'LevelHeaderServiceWell')
        well.setExpression('Height','Parameters.FrameTop - 0.4 mm - Parameters.DisplayBottom + 0.59 mm')


def usb_corridor(doc,side,clearance=0):
    x=116.8 if side=='left' else 31.2
    return Part.makeBox(12+2*clearance,20+2*clearance,5+2*clearance,
        A.Vector(x-clearance,-18.8-clearance+7.5-float(doc.Parameters.MCUShiftY),float(doc.Parameters.MCUBottom)-2.1-clearance))


def usb_access(doc):
    report={}
    for side,prefix in [('left','L_'),('right','R_')]:
        history=doc.getObject(prefix+'Construction')
        cutter=doc.addObject('Part::Box',prefix+'AuditUSBAccess')
        cutter.Length=12.4;cutter.Width=20.4;cutter.Height=5.4
        cutter.Placement.Base=A.Vector((116.8 if side=='left' else 31.2)-.2,-19,5.9)
        cutter.setExpression('Placement.Base.z','Parameters.MCUBottom - 2.3 mm')
        # Follow the existing MCUShiftY = 7.5 mm reference datum.
        cutter.setExpression('Placement.Base.y','-11.5 mm - Parameters.MCUShiftY')
        history.addObject(cutter)
        for style in ['solid','rim','terrace']:
            base=doc.getObject(prefix+'Case_'+style+'_base')
            before=base.Shape.copy();assert len(base.Links)==1
            cut=doc.addObject('Part::Cut',prefix+'AuditUSB_'+style)
            cut.Base=base.Links[0];cut.Tool=cutter;cut.Refine=True;history.addObject(cut)
            base.Links=[cut];doc.recompute([base])
            # A native Cut can only subtract its explicit tool. Measure the
            # actual removed region locally instead of two huge self-Booleans.
            from slim_stack import overlap
            removed=before.common(cutter.Shape)
            assert abs(before.Volume-base.Shape.Volume-removed.Volume)<1e-5
            assert base.Shape.isValid() and len(base.Shape.Solids)==1
            report[side+'-'+style]={'removed_mm3':removed.Volume,'added_mm3':0.0}
            import sys
            print('USB access: '+side+' / '+style,file=sys.__stdout__,flush=True)
        for obj in [cutter,*[doc.getObject(prefix+'AuditUSB_'+s) for s in ['solid','rim','terrace']]]:obj.Visibility=False
    return report


def install_diodes(doc):
    """Use the same component-local rigid transform as actual bottom KiCad CAD."""
    import ImportGui
    import flush_frames as F
    from export_pcb_components import footprints
    source=ROOT/'components/sources/D_SOD-123.step'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='b3dc4065573abc72e3d5b4cca0e908f72a24205a41b6284b1f75ccacbe99adf8'
    temp=A.newDocument('DiodeSource');ImportGui.insert(str(source),temp.Name);temp.recompute()
    original=next(o for o in temp.Objects if hasattr(o,'Shape') and o.Shape.Solids)
    shape=original.Shape.copy();colors=list(original.ViewObject.DiffuseColor)
    A.closeDocument(temp.Name);A.setActiveDocument(doc.Name)
    report={}
    for side,prefix in [('left','L_'),('right','R_')]:
        fps={r:v for r,v in footprints(ROOT/f'hardware/revI/flan36-{side}.kicad_pcb').items() if r.startswith('D')}
        assert len(fps)==18
        nodes=[]
        for ref,fp in sorted(fps.items()):
            assert fp['layer']=='B.Cu' and 'D_SOD-123' in fp['block']
            x,y,angle=fp['pose'];node=doc.addObject('Part::Feature',prefix+'Diode_'+ref)
            node.Shape=shape.copy()
            node.Placement=A.Placement(A.Vector(x,-y,3.8),A.Rotation(A.Vector(0,0,1),angle).multiply(A.Rotation(A.Vector(1,0,0),180)))
            node.setExpression('Placement.Base.z','Parameters.PCBTop - 1.6 mm')
            node.Label=ref+' · SOD-123 · underside';node.ViewObject.ShapeColor=(.12,.13,.14)
            # The pinned single-solid model has one library color; distinguish its
            # large horizontal ceramic faces from the narrow metal terminations.
            node.ViewObject.DiffuseColor=colors
            F.prop(node,'PCBReference','App::PropertyString',ref);nodes.append(node)
            doc.getObject(prefix+'Construction').addObject(node);node.Visibility=False
        compound=doc.addObject('Part::Compound',prefix+'Diodes');compound.Links=nodes
        for name,kind,value in [('PartID','App::PropertyString',side+'-diodes'),('DisplayName','App::PropertyString','18 × SOD-123 diodes'),('ViewerGroup','App::PropertyString','pcb'),('Layer','App::PropertyString','pcb'),('PrototypePrintable','App::PropertyBool',False),('ModelStatus','App::PropertyString','Pinned KiCad SOD-123 nominal CAD at actual B.Cu footprints; solder unmeasured')]:F.prop(compound,name,kind,value)
        compound.Label='18 × SOD-123 diodes · underside';compound.ViewObject.ShapeColor=(.14,.15,.16)
        doc.getObject(prefix+'Half').addObject(compound)
        report[side]={r:{'pose':v['pose'],'layer':v['layer']} for r,v in fps.items()}
    doc.recompute()
    return report


def validate_materials(doc,side,smooth,obj,output_dir=None):
    """Check actual solid partitions and backing, including supported edits."""
    import approved_frames as M
    import flush_frames as F
    import MeshPart
    M.use_document(doc);params=doc.Parameters;roof=float(params.FrameTop)
    values={k:float(getattr(params,k)) for k in ['FrameTop','FrameRoof','WindowMargin','DisplayShiftY']}
    for name,lo,hi in [('FrameTop',13.59,13.99),('FrameRoof',1.2,1.4),('WindowMargin',.1,.3),('DisplayShiftY',2.4,3.4)]:
        if not lo-1e-8<=values[name]<=hi+1e-8:
            raise ValueError(f'{name}={values[name]} mm is outside the checked study interval {lo}..{hi} mm; requalify geometry before export')
    whole=obj.Shape;blank=smooth.Shape
    assert whole.isValid() and len(whole.Solids)==1,(obj.Name,'frame disconnected')
    removed=blank.cut(whole).Volume;added=whole.cut(blank).Volume
    assert removed+added<1e-5,(obj.Name,'partition differs from current blank',removed,added)
    prefix='L_' if side=='left' else 'R_'
    glass=doc.getObject(prefix+'NiceViewVisual2').Shape
    assert whole.common(glass).Volume<1e-7,(obj.Name,'glass collision')
    gap=whole.distToShape(glass)[0]
    assert abs(gap-values['WindowMargin'])<1e-6,(obj.Name,'glass margin',gap)
    top=M.top_faces(blank,roof);flat=M.regions(side,obj.FrameStyle,uncut=True)
    reference=all(abs(values[k]-v)<1e-7 for k,v in {'FrameTop':13.59,'FrameRoof':1.4,'WindowMargin':.1,'DisplayShiftY':2.4}.items())
    frozen=M.frozen_regions(side,obj.FrameStyle) if reference else None
    relief=doc.getObject(prefix+'LevelDisplayPCBRelief').Shape.optimalBoundingBox(False,False)
    exclusion=Part.makeBox(relief.XLength,relief.YLength,30,A.Vector(relief.XMin,relief.YMin,0))
    material_records=[];pairs={};errors={}
    for i,part in enumerate(obj.MaterialParts):
        shape=part.Shape;role=part.ColorRole
        assert shape.isValid() and shape.Solids and all(s.isClosed() for s in shape.Solids),(part.Name,'invalid material')
        if role=='body':assert len(shape.Solids)==1,(part.Name,'structural shell disconnected')
        target=flat[role].common(top);actual=M.top_faces(shape,roof)
        err=actual.cut(target).Area+target.cut(actual).Area
        assert err<.002,(obj.Name,role,'edited top differs from clipped approved art',err)
        if frozen:
            original_error=actual.cut(frozen[role]).Area+frozen[role].cut(actual).Area
            assert original_error<.002,(obj.Name,role,'reference differs from frozen approval',original_error)
        errors[role]=err
        for other in obj.MaterialParts[i+1:]:
            collision=shape.common(other.Shape).Volume;assert collision<1e-5
            pairs[role+'/'+other.ColorRole]=collision
        backing_missing=0.;backing_probe_area=0.
        if role!='body':
            for face in shape.Faces:
                b=face.optimalBoundingBox(False,False)
                if abs(b.ZMin-(roof-.4))<1e-6 and abs(b.ZMax-b.ZMin)<1e-6:
                    ordinary=face.cut(exclusion)
                    if ordinary.Area<1e-7:continue
                    probe=ordinary.extrude(A.Vector(0,0,-.8))
                    backing_missing+=probe.cut(blank).Volume;backing_probe_area+=ordinary.Area
            assert backing_missing<1e-6,(part.Name,'ordinary backing below 0.8 mm',backing_missing)
            ordinary=shape.cut(exclusion)
            if ordinary.Volume>1e-7:
                b=ordinary.optimalBoundingBox(False,False)
                assert abs(b.ZMin-(roof-.4))<1e-6 and abs(b.ZMax-roof)<1e-6,(part.Name,'ordinary inlay depth')
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
        assert mesh.isSolid(),(part.Name,'open material mesh')
        if output_dir:
            out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);stem=f'{side}-frame-{obj.FrameStyle}-{role}'
            mesh.write(str(out/(stem+'.stl')));shape.exportStep(str(out/(stem+'.step')))
        material_records.append({'role':role,'volume_mm3':shape.Volume,'solids':len(shape.Solids),'closed_mesh':True,
            'ordinary_backing_probe_area_mm2':backing_probe_area,'missing_backing_volume_mm3':backing_missing})
    F.prop(obj,'FrameFaceRoles','App::PropertyString',json.dumps(F.face_roles(obj)))
    return {'style':obj.FrameStyle,'side':side,'parameters_mm':values,'top_face_difference_mm2':errors,
        'saved_planar_approval_compared':reference,'material_parts':material_records,'pair_intersections_mm3':pairs,
        'union_removed_volume_mm3':removed,'union_added_volume_mm3':added,'glass_gap_mm':gap,'roof_mm':roof,
        'ordinary_inlay_depth_mm':.4,'minimum_ordinary_backing_mm':.8,'physical_acceptance':False}
