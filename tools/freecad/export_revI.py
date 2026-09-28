"""Export the active revI FCStd, preserving manual changes in the source document.

Run through run_macos.py to export the saved reference without rebuilding it.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import os
import sys
from pathlib import Path
import FreeCAD as A
import Part
import MeshPart


def exact_common(a, b):
    """Same Boolean volume; prune only solid children that cannot overlap in 3D."""
    def possible(x, y):
        return all(min(getattr(x, axis+'Max'), getattr(y, axis+'Max')) >
                   max(getattr(x, axis+'Min'), getattr(y, axis+'Min'))
                   for axis in ('X','Y','Z'))
    if not possible(a.BoundBox,b.BoundBox):return Part.makeCompound([])
    def solid_only(s):
        if s.ShapeType=='Solid':return True
        return s.ShapeType in ('Compound','CompSolid') and all(solid_only(c) for c in s.childShapes())
    if not solid_only(a) or not solid_only(b):return a.common(b)
    aa,bb=a.Solids,b.Solids
    if not aa or not bb:return a.common(b)
    ax,bx=[x.BoundBox for x in aa],[x.BoundBox for x in bb]
    pairs=[(i,j) for i,x in enumerate(ax) for j,y in enumerate(bx) if possible(x,y)]
    if not pairs:return Part.makeCompound([])
    ai,bi=sorted({i for i,j in pairs}),sorted({j for i,j in pairs})
    sa=aa[ai[0]] if len(ai)==1 else Part.makeCompound([aa[i] for i in ai])
    sb=bb[bi[0]] if len(bi)==1 else Part.makeCompound([bb[j] for j in bi])
    return sa.common(sb)

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ.get('FLAN36_EXPORT_OUT',ROOT/'mechanical/revI')).resolve()
OUT.mkdir(parents=True,exist_ok=True)
META_OUT=Path(os.environ.get('FLAN36_EXPORT_METADATA',ROOT/'design/revI.json'))
REPORT_OUT=Path(os.environ.get('FLAN36_EXPORT_REPORT',ROOT/'validation/revI-mechanical.json'))
doc=A.ActiveDocument
standalone=os.environ.get('FILO_FREECAD_SUBPROCESS')=='1' and globals().get('__name__')=='__main__'
if standalone:
    import FreeCADGui as G
    G.showMainWindow();G.getMainWindow().hide()
    saved_source=OUT/'Flan36.FCStd'
    saved_source_hash=hashlib.sha256(saved_source.read_bytes()).hexdigest()
    doc=A.openDocument(str(saved_source))
if not doc or not doc.getObject('Parameters'):
    raise RuntimeError('Open mechanical/revI/Flan36.FCStd first.')
doc.recompute()
metadata=json.loads((ROOT/'design/revI.json').read_text())
# Preserve the prior label-only export bridge as history, not current provenance.
if 'analyzed_native_sha256' in metadata.get('export_execution',{}):
    metadata['historical_export_execution']=metadata.pop('export_execution')
report={'scope':'Native PartID solids only; switch/keycap meshes and unqualified socket registration excluded; not a manufacturing release','halves':{},'unresolved':[
    'No routed PCB or integrated firmware', 'Actual module/socket/contact dimensions and retention',
    'Battery cable routing, strain relief and bending radii', 'Window tolerance and PCB copper-to-edge rule',
    'Printed fits, insertion/extraction loads, charging, RF and measured power']}
metadata['parts']={}
metadata['frameVariants']={}
metadata['batteryLeadProfiles']={}
metadata['parameter_values_mm']={a:getattr(doc.Parameters,a).Value for a in metadata['parameters']}
metadata['slim_flush']={'decoration':'flush co-print material volumes',
    'inlay_depth_mm':.4,'minimum_backing_mm':.8,'physical_acceptance':False}
if doc.getObject('LevelStackReceipt'):
    metadata['level_stack']=json.loads(doc.LevelStackReceipt.RecipeJSON)
stack_recipe=json.loads(doc.getObject('SlimStackReceipt').RecipeJSON)
for side, recipe in stack_recipe['halves'].items():
    metadata['halves'][side]['battery_opening']=[v for point in recipe['battery_aperture_xy'] for v in point]
    metadata['halves'][side]['rear_lead_notch_xy']=recipe['rear_lead_notch_xy']
    metadata['halves'][side]['reset']={'center_xy':recipe['reset_center_xy'],
        'layer':recipe['reset_side'],'tool_radius_mm':recipe['reset_tool_radius_mm']}
for side,prefix in [('left','L_'),('right','R_')]:
    assembly=doc.getObject(prefix+'Half'); old=assembly.Placement
    assembly.Placement=A.Placement();doc.recompute()
    objects=[o for o in doc.Objects if hasattr(o,'PartID') and o.PartID.startswith(side+'-')]
    objects=[o for o in objects if assembly.DisplayCoverInstalled or o.Layer!='lid']
    shapes={o.PartID[len(side)+1:]:o.Shape for o in objects}
    active=doc.getObject(prefix+'ActiveBattery');reference=active.LinkedObject.Shape
    assert all(abs(getattr(shapes['battery'].BoundBox,k)-getattr(reference.BoundBox,k))<1e-6 for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']),(side,'active battery placement differs from profile')
    for o in objects:
        shape=o.Shape
        assert not shape.isNull() and shape.isValid(),(o.Name,'invalid shape')
        if o.PrototypePrintable:assert len(shape.Solids)==1,(o.PartID,'disconnected solids',len(shape.Solids))
        name=o.PartID
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
        if o.PrototypePrintable:assert mesh.isSolid(),(name,'open mesh')
        mesh.write(str(OUT/(name+'.stl')))
        if o.PrototypePrintable:shape.exportStep(str(OUT/(name+'.step')))
        visuals=[]
        for index,child in enumerate(getattr(o,'VisualParts',[])):
            visualpath=f'{name}-visual-{index}.stl';vm=MeshPart.meshFromShape(Shape=child.Shape,LinearDeflection=.035,AngularDeflection=.15,Relative=False);vm.write(str(OUT/visualpath))
            visuals.append({'path':'mechanical/revI/'+visualpath,'color':'#'+''.join(f'{round(c*255):02x}' for c in child.ViewObject.ShapeColor[:3]),'name':child.Label})
        b=shape.BoundBox
        metadata['parts'][name]={'object':o.Name,'role':o.Label,'group':o.Layer,'prototype_part':o.PrototypePrintable,
            'bounds_mm':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],
            'visuals':visuals,'stl_sha256':hashlib.sha256((OUT/(name+'.stl')).read_bytes()).hexdigest()}
    print(side,'active parts exported; checking intersections',flush=True)
    # Pair checks include real PCB battery opening and mounting holes.
    issues=[];pairs={}
    for i,(a,sa) in enumerate(shapes.items()):
        for b,sb in list(shapes.items())[i+1:]:
            v=exact_common(sa,sb).Volume
            if v>.001:
                screw=a if a.startswith('screw-') else b if b.startswith('screw-') else None
                # Only the deliberate tapped M2 thread envelope may overlap.
                allowed=0
                if screw and 'tray' in (a,b):
                    index=int(screw.split('-')[-1])-1
                    spec=json.loads((ROOT/'design/revI-mounts.json').read_text())['left'][index]
                    x,y=spec['xy'];x=x if side=='left' else 160-x
                    tip=spec['seat_z']-spec['length']
                    thread=Part.makeCylinder(1,3.8-tip,A.Vector(x,-y,tip))
                    allowed=exact_common(sa,sb).common(thread).Volume
                if v-allowed>.001:issues.append({'a':a,'b':b,'volume_mm3':round(v,6),'allowed_thread_volume_mm3':round(allowed,6)})
            pairs[a+' / '+b]=round(v,6)
    print(side,'active pairs checked; checking batteries',flush=True)
    battery_checks={}
    for obj in [o for o in doc.Objects if hasattr(o,'BatteryStyle') and o.TypeId!='App::Link' and o.Name.startswith(prefix)]:
        shape=obj.Shape;ident=obj.BatteryStyle
        mm=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
        mm.write(str(OUT/(side+'-battery-'+ident+'.stl')))
        hits={n:round(exact_common(shape,other).Volume,6) for n,other in shapes.items() if n!='battery' and exact_common(shape,other).Volume>.001}
        assert not hits,(side,ident,hits)
        battery_checks[ident]={'component_collisions_mm3':hits,'bounds_mm':[getattr(shape.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]}
    if doc.getObject('SlimStackReceipt'):
        for profile,names in json.loads(doc.SlimStackReceipt.RecipeJSON)['halves'][side]['lead_objects'].items():
            wires=[]
            for index,source in enumerate(names):
                shape=doc.getObject(source).Shape
                wiremesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
                assert wiremesh.isSolid(),(source,'open wire mesh')
                filename=f'{side}-battery-lead-{profile}-{index}.stl'
                wiremesh.write(str(OUT/filename))
                wire_color=doc.getObject(source).ViewObject.ShapeColor
                wires.append({'index':index,'stl':filename,'stl_sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest(),
                    'color':'#'+''.join(f'{round(c*255):02x}' for c in wire_color[:3])})
            metadata['batteryLeadProfiles'][side+'-'+profile]=wires
    # Check every interchangeable cover, not just the selected frame.
    print(side,'checking frame variants',flush=True)
    frame_checks={}
    for obj in [o for o in doc.Objects if hasattr(o,'FrameStyle') and o.Name.startswith(prefix) and o.TypeId!='App::Link']:
        print(side,'frame',obj.FrameStyle,flush=True)
        shape=obj.Shape;assert shape.isValid() and len(shape.Solids)==1,(obj.Name,'invalid cover')
        frame_mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
        assert frame_mesh.isSolid();name=side+'-frame-'+obj.FrameStyle
        frame_mesh.write(str(OUT/(name+'.stl')));shape.exportStep(str(OUT/(name+'.step')))
        # Flush color is owned by complementary closed volumes, not inferred
        # from triangle centroids. Preserve their common assembly coordinates.
        materials=[]
        for child in getattr(obj,'MaterialParts',[]):
            material=child.Shape
            assert not material.isNull() and material.isValid(),(child.Name,'invalid material volume')
            assert material.Solids and all(s.isClosed() for s in material.Solids),(child.Name,'open material solid')
            role=child.ColorRole
            assert role in ('body','detail','accent','secondary'),(child.Name,role)
            stem=name+'-'+role
            mm=MeshPart.meshFromShape(Shape=material,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
            assert mm.isSolid(),(stem,'open material mesh')
            mm.write(str(OUT/(stem+'.stl')));material.exportStep(str(OUT/(stem+'.step')))
            materials.append({'role':role,'stl':stem+'.stl','step':stem+'.step',
                'stl_sha256':hashlib.sha256((OUT/(stem+'.stl')).read_bytes()).hexdigest(),
                'step_sha256':hashlib.sha256((OUT/(stem+'.step')).read_bytes()).hexdigest(),
                'volume_mm3':material.Volume,'solids':len(material.Solids)})
        metadata['frameVariants'][side+'-'+obj.FrameStyle]={
            'stl':name+'.stl','step':name+'.step','material_parts':materials,
            'roof_mm':doc.Parameters.FrameTop.Value,
            'color_construction':'complementary co-print volumes' if materials else 'single body'}
        hits={n:round(exact_common(shape,s).Volume,6) for n,s in shapes.items() if n!='electronics-lid' and exact_common(shape,s).Volume>.001}
        # Nominal 12 x 5 mm USB plug envelope + straight insertion corridor.
        px=116.8 if side=='left' else 160-128.8
        plug=Part.makeBox(12,20,5,A.Vector(px,-18.8,doc.Parameters.MCUBottom.Value-2.1))
        hit=exact_common(shape,plug).Volume
        frame_checks[obj.FrameStyle]={'component_collisions_mm3':hits,'usb_envelope_collision_mm3':round(hit,6),'volume_mm3':shape.Volume,'closed_mesh':True}
        assert not hits and hit<.001,(name,frame_checks[obj.FrameStyle])
    print(side,'checking case variants',flush=True)
    case_checks={}
    for style in json.loads((ROOT/'design/cases.json').read_text())['styles']:
        print(side,'case',style,flush=True)
        pair={g:doc.getObject(prefix+'Case_'+style+'_'+g).Shape for g in ['base','plate']}
        hits={}
        for group,shape in pair.items():
            assert shape.isValid() and len(shape.Solids)==1,(side,style,group,'invalid case')
            mm=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
            assert mm.isSolid(),(side,style,group,'open case mesh')
            name=side+'-case-'+style+'-'+group
            mm.write(str(OUT/(name+'.stl')));shape.exportStep(str(OUT/(name+'.step')))
            for name,other in shapes.items():
                if name in ['tray','key-plate']:continue
                common=exact_common(shape,other);hit=common.Volume
                if group=='base' and name.startswith('screw-') and hit>.001:
                    spec=json.loads((ROOT/'design/revI-mounts.json').read_text())['left'][int(name.split('-')[-1])-1]
                    x,y=spec['xy'];x=x if side=='left' else 160-x;tip=spec['seat_z']-spec['length']
                    hit-=common.common(Part.makeCylinder(1,3.8-tip,A.Vector(x,-y,tip))).Volume
                if hit>.001:hits[group+' / '+name]=hit
            for frame in [o for o in doc.Objects if o.Name.startswith(prefix) and hasattr(o,'FrameStyle') and o.TypeId!='App::Link']:
                hit=exact_common(shape,frame.Shape).Volume
                if hit>.001:hits[group+' / frame '+frame.FrameStyle]=hit
        hit=exact_common(pair['base'],pair['plate']).Volume
        if hit>.001:hits['base / plate']=hit
        assert not hits,(side,style,hits)
        case_checks[style]={'closed_meshes':True,'connected_solids':True,'component_collisions_mm3':hits,
            'base_volume_mm3':pair['base'].Volume,'plate_volume_mm3':pair['plate'].Volume}
    compound=Part.makeCompound(list(shapes.values()));compound.exportStep(str(OUT/(side+'-assembly.step')))
    b=compound.BoundBox
    # North is max CAD Y, i.e. smallest KiCad Y.
    electronics=[shapes[k] for k in ['electronics-lid','mcu','display','battery','cradle','mcu-riser','display-sled','mcu-sockets','jst','slider','reset'] if k in shapes]
    north=-max(s.BoundBox.YMax for s in electronics)
    report['halves'][side]={'case_variants':case_checks,'display_cover_installed':assembly.DisplayCoverInstalled,'battery_variants':battery_checks,'frame_variants':frame_checks,'pair_intersections_mm3':pairs,'collisions':issues,
        'assembly_bounds_mm':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],
        'case_bounds_mm':[getattr(shapes['tray'].BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']],
        'electronics_north_kicad_y_mm':north,'frame_top_mm':shapes['electronics-lid'].BoundBox.ZMax if 'electronics-lid' in shapes else None,
        'display_top_mm':shapes['display'].BoundBox.ZMax,
        'adjacent_key_north_y_mm':10.755147934,'electronics_overhang_adjacent_mm':max(0,10.755147934-north),
        'battery_to_usb_vertical_gap_mm':shapes['mcu'].BoundBox.ZMin-shapes['battery'].BoundBox.ZMax,
        'cage_to_opening_per_side_mm':doc.Parameters.SlotClearance.Value,
        'nominal_copper_to_opening_mm':.62-doc.Parameters.SlotClearance.Value}
    metadata['halves'][side]['size_mm']=[b.XLength,b.YLength]
    assembly.Placement=old
    print(side,'parts',len(objects),'collisions',issues,flush=True)
doc.recompute()
metadata['inputs']=[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in [
    'design/level-case-workflow.json','tools/freecad/level_stack.py','tools/freecad/install_level_stack.py','design/cases.json','design/frame-finishes.json','design/frame-extensions.json','design/slim-flush-workflow.json','tools/freecad/flush_frames.py','tools/freecad/slim_stack.py','tools/freecad/install_slim_flush.py','tools/freecad/extra_frames.py','tools/freecad/install_extra_frames.py','tools/freecad/components.py','tools/freecad/switch_instances.py','components/switches.json','components/sources.json','tools/frame_finishes.py','tools/keycap_config.py','tools/freecad/configuration.py','design/layout.json','design/revI-profiles.json','design/revI-frame-profiles.json','keycaps/catalog.json','design/revI-mounts.json','design/batteries.json','design/revI-magnets.json','design/revI-wire-study.json','tools/freecad/build_revI.py','tools/freecad/export_revI.py']]
metadata['fcstd_sha256']=hashlib.sha256((OUT/'Flan36.FCStd').read_bytes()).hexdigest()
report['source_sha256']=metadata['fcstd_sha256']
report['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
metadata['export_execution']={'native_sha256':metadata['fcstd_sha256'],
    'exporter_sha256':report['checker_sha256'],'receipt':'validation/revI-mechanical.json'}
META_OUT.write_text(json.dumps(metadata,indent=2)+'\n')
REPORT_OUT.write_text(json.dumps(report,indent=2)+'\n')
assert not any(v['collisions'] for v in report['halves'].values()),'Unresolved nominal intersections; see validation/revI-mechanical.json'
print('PASS: native solids, closed printable meshes, nominal part intersections',flush=True)
if standalone:
    assert hashlib.sha256(saved_source.read_bytes()).hexdigest()==saved_source_hash,'Saved source changed during export'
    A.closeDocument(doc.Name)
    print('PASS: saved native reference exported without modification',file=sys.__stdout__,flush=True)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
