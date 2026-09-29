"""Install approved R4 geometry in a fresh native candidate; preserve configuration.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,hashlib,os,sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import FreeCADGui as G
import Part
import approved_frames as M
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def say(s):print(s,file=sys.__stdout__,flush=True)
def bbox(o):return [getattr(o.Shape.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]

def run():
    values=sys.argv[1:]
    while values and not values[0].startswith('--'):values.pop(0)
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(values);assert args.source.resolve()!=args.output.resolve() and not args.output.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    import flush_frames as F
    from configuration import extract,apply_finish
    from install_slim_flush import protected,assembly_signature
    from preserve_document_label import preserve_document_label
    G.showMainWindow();G.getMainWindow().hide();source_sha=sha(args.source)
    doc=A.openDocument(str(args.source));assert doc.getObject('ApprovedFrameMasterR4') is None,'R4 is already installed; use the pre-R4 input for reproduction'
    doc.recompute();cfg=extract(doc);label=doc.Label
    caps={k:v for k,v in protected(doc).items() if '_K' in k}
    report={'source_sha256':source_sha,'approved_master_sha256':M.PLAN['master_sha256'],'approved_styles':list(M.APPROVED),'deferred_styles':M.PLAN['deferred_styles'],'physical_acceptance':False,'halves':{},'frames':{}}
    poses={s:A.Placement(doc.getObject(p+'Half').Placement) for s,p in [('left','L_'),('right','R_')]}
    for p in ['L_','R_']:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute()
    protected_names=[o.Name for o in doc.Objects if hasattr(o,'PartID') and o.PartID.split('-',1)[1] in ['mcu','mcu-sockets','battery','cradle','battery-retainer','mcu-riser','jst','reset','slider']]
    before_protected={name:doc.getObject(name).Shape.copy() for name in protected_names}
    deferred_features={o.Name:o.Shape.copy() for o in doc.Objects if hasattr(o,'ArtworkID') and any(o.Name.startswith(p+'FlushFrame_'+s+'_') for p in ['L_','R_'] for s in M.PLAN['deferred_styles'])}
    doc.Parameters.set('B13','13.59 mm');doc.Parameters.set('B14','1.40 mm')
    before_sides={};drill_sets={}
    for side,prefix in [('left','L_'),('right','R_')]:
        dx=.2 if side=='left' else -.2
        names=[prefix+'NiceViewVisual'+str(i) for i in range(4)] + [prefix+n for n in ['SlimDisplaySocketHousing','SlimDisplaySocketPins','SlimDisplayMaleSpacer','SlimDisplayMaleContacts','LevelDisplaySolderReserve','LevelDisplayPCBRelief','LevelHeaderServiceWell','HeaderReliefTool']]
        names += [prefix+'DisplayContact'+str(i) for i in range(5)]
        nominal_x=117.72 if side=='left' else 32.12
        drills=[o for o in doc.Objects if o.Name.startswith(prefix+'PadDrill') and abs(o.Placement.Base.y+50.8)<1e-6 and any(abs(o.Placement.Base.x-(nominal_x+2.54*i))<1e-6 for i in range(5))]
        assert len(drills)==5 and all(abs(float(o.Radius)-.5)<1e-6 for o in drills),(side,'Expected five J2 drill tools')
        drill_sets[side]=[o.Name for o in drills];names += drill_sets[side]
        # Translate bearing surfaces rather than mounting datums. Cable tunnels remain fixed.
        names += [prefix+'DisplayLedge'+str(i) for i in range(3)]+[prefix+'DisplaySide'+str(i) for i in range(2)]
        before={n:bbox(doc.getObject(n)) for n in names};before_sides[side]=before
        for name in names:
            o=doc.getObject(name)
            expr=next((str(v) for p,v in o.ExpressionEngine if p in ['Placement.Base.x','.Placement.Base.x']),None)
            if expr:o.setExpression('Placement.Base.x',f'({expr}) + ({dx} mm)')
            else:o.Placement.Base.x+=dx
        window=doc.getObject(prefix+'GlassWindow')
        expr=next(str(v) for p,v in window.ExpressionEngine if p in ['Placement.Base.x','.Placement.Base.x'])
        window.setExpression('Placement.Base.x',f'({expr}) + ({dx} mm)')
        well=doc.getObject(prefix+'LevelHeaderServiceWell');well.Height=2.29
        # Match the approved exact corner curves, preserving the lower mounting cuts.
        outline=doc.addObject('Part::Feature',prefix+'R4ExactFrameOutline');outline.Shape=M.face(M.MASTER['outer_commands'],side)
        doc.getObject(prefix+'Construction').addObject(outline);outline.Visibility=False
        doc.getObject(prefix+'Frame_smooth_Pad').Base=outline
    say('Recomputing centered assembly and shared 13.59 mm shell')
    doc.recompute()
    say('Assembly recomputed; checking datums and guide gaps')
    for side,prefix in [('left','L_'),('right','R_')]:
        dx=.2 if side=='left' else -.2;before=before_sides[side]
        translated={}
        for name,old in before.items():
            now=bbox(doc.getObject(name));expected=[old[i]+(dx if i in [0,3] else 0) for i in range(6)]
            if name.endswith('LevelHeaderServiceWell'):expected[5]=13.19
            assert max(abs(x-y) for x,y in zip(now,expected))<1e-6,(name,old,now,expected)
            translated[name]={'before':old,'after':now}
        smooth=F.find_smooth(doc,side)
        top=M.top_faces(smooth.Shape,13.59);target,_=M.domains(side)
        err=top.cut(target).Area+target.cut(top).Area
        assert err<.002,(side,'blank top differs from master',err)
        glass=doc.getObject(prefix+'NiceViewVisual2');assert abs(bbox(glass)[5]-13.39)<1e-6
        expected_centers=sorted([(117.92+2.54*i) if side=='left' else (31.92+2.54*i) for i in range(5)])
        for nameset in [drill_sets[side],[prefix+'DisplayContact'+str(i) for i in range(5)]]:
            centers=sorted(doc.getObject(n).Placement.Base.x for n in nameset)
            assert max(abs(a-b) for a,b in zip(centers,expected_centers))<1e-6,(side,nameset,centers)
        board=doc.getObject(prefix+'NiceViewVisual0').Shape.BoundBox
        side0=doc.getObject(prefix+'DisplaySide0').Shape.BoundBox;side1=doc.getObject(prefix+'DisplaySide1').Shape.BoundBox
        guides=sorted([side0,side1],key=lambda b:b.XMin)
        gaps=[board.XMin-guides[0].XMax,guides[1].XMin-board.XMax]
        assert all(abs(g-.25)<1e-6 for g in gaps),(side,gaps)
        report['halves'][side]={'translated':translated,'guide_gaps_mm':gaps,'pcb_pin_radial_gap_mm':.2,'sled_pin_radial_gap_mm':.12,'blank_top_difference_mm2':err}
    for name,shape in before_protected.items():
        now=doc.getObject(name).Shape
        assert now.cut(shape).Volume+shape.cut(now).Volume<1e-6,(name,'protected geometry changed')
    say('Centered full mating chain, native drills and guide surfaces; positive gaps preserved')
    doc.saveAs(str(args.output.parent/'prepared.FCStd'))
    for side,prefix in [('left','L_'),('right','R_')]:
        # Existing excluded artwork retains its XY and colors; shared shell updates only.
        _,checks=F.build_styles(doc,side,styles=M.APPROVED)
        report['frames'].update({side+'-'+k:v for k,v in checks.items()})
        for style in M.PLAN['deferred_styles']:
            obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final')
            report['frames'][side+'-'+style]=F.validate_variant(doc,side,F.find_smooth(doc,side),obj)
            colors=F.load_spec()['styles'][style]['colors'];obj.ViewObject.DiffuseColor=[F.rgb(colors[r]) for r in F.face_roles(obj)]
        for name,old in deferred_features.items():
            obj=doc.getObject(name);new=obj.Shape.copy();new.translate(A.Vector(0,0,-.2))
            assert new.cut(old).Volume+old.cut(new).Volume<1e-5,(name,'excluded artwork changed')
        frame=doc.getObject(prefix+'ActiveFrame').LinkedObject
        apply_finish(doc,frame,side,cfg['frames'][side]['color'],cfg['frames'][side]['accents'])
        doc.getObject(prefix+'Half').Placement=poses[side]
    doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:
        frame=doc.getObject(prefix+'ActiveFrame').LinkedObject;apply_finish(doc,frame,side,cfg['frames'][side]['color'],cfg['frames'][side]['accents'])
    assert extract(doc)==cfg,'Existing configuration changed'
    assert {k:v for k,v in protected(doc).items() if '_K' in k}==caps,'Cap placement changed'
    rec=doc.addObject('App::DocumentObjectGroup','ApprovedFrameMasterR4')
    rec.addProperty('App::PropertyString','MasterSHA256');rec.MasterSHA256=M.PLAN['master_sha256']
    rec.addProperty('App::PropertyString','RecipeJSON');rec.RecipeJSON=json.dumps({'plan':M.PLAN,'source_sha256':source_sha})
    signature=assembly_signature(doc)
    tmp=args.output.with_name('unlabelled.FCStd');doc.saveAs(str(tmp));A.closeDocument(doc.Name);preserve_document_label(tmp,args.output,label);tmp.unlink()
    doc=A.openDocument(str(args.output));doc.recompute()
    assert assembly_signature(doc)==signature and extract(doc)==cfg
    assert not any('Invalid' in o.State or o.TypeId.endswith('Python') for o in doc.Objects)
    assert sha(args.source)==source_sha
    report.update(output_sha256=sha(args.output),saved_reopened_recomputed=True,configuration_unchanged=True,cap_geometry_unchanged=True,excluded_artwork_xy_unchanged=True)
    (args.output.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
    A.closeDocument(doc.Name);say('PASS: candidate reopened, exact approved art, deferred art and saved configuration preserved')
if __name__=='__main__':
    try:run()
    except Exception:
        import traceback
        traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
