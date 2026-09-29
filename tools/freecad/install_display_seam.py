"""Apply the glass-centered seam correction to a separate native candidate.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import FreeCADGui as G
import Part
import approved_frames as M
import flush_frames as F
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(s):print(s,file=sys.__stdout__,flush=True)
def run():
    values=sys.argv[1:]
    while values and not values[0].startswith('--'):values.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args(values)
    assert args.source.resolve()!=args.output.resolve() and not args.output.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    from configuration import extract,apply_finish
    from install_slim_flush import protected,assembly_signature
    from preserve_document_label import preserve_document_label
    sourcehash=sha(args.source);masterpath='design/proposals/display-seam-r1/master.json';masterhash=sha(ROOT/masterpath)
    master=json.loads((ROOT/masterpath).read_text());assert master['source_sha256']['mechanical/revI/Flan36.FCStd']==sourcehash
    G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(args.source));doc.recompute()
    assert not doc.getObject('DisplaySeamCorrection') and doc.getObject('ApprovedFrameMasterR4')
    cfg=extract(doc);label=doc.Label;caps={k:v for k,v in protected(doc).items() if '_K' in k}
    poses={s:A.Placement(doc.getObject(p+'Half').Placement) for s,p in [('left','L_'),('right','R_')]}
    for prefix in ['L_','R_']:doc.getObject(prefix+'Half').Placement=A.Placement()
    doc.recompute()
    untouched={o.Name:o.Shape.copy() for o in doc.Objects if hasattr(o,'PartID') and o.PartID.split('-',1)[1]!='electronics-lid'}
    art={o.Name:o.Shape.copy() for o in doc.Objects if hasattr(o,'ArtworkID')}
    marker=doc.addObject('App::DocumentObjectGroup','DisplaySeamCorrection')
    for name,value in [('MasterPath',masterpath),('MasterSHA256',masterhash),('SourceSHA256',sourcehash)]:
        marker.addProperty('App::PropertyString',name);setattr(marker,name,value)
    marker.addProperty('App::PropertyString','Scope');marker.Scope='Glass opening and approved uniform bezel only; deferred artwork unchanged; physical fit unqualified'
    doc.Parameters.set(doc.Parameters.getCellFromAlias('WindowMargin'),'0.10 mm')
    for prefix in ['L_','R_']:
        doc.getObject(prefix+'GlassWindow').setExpression('Placement.Base.y','-46.55 mm - Parameters.DisplayShiftY - Parameters.WindowMargin')
    doc.recompute();M.use_document(doc)
    report={'source_sha256':sourcehash,'master_sha256':masterhash,'approved_styles':list(M.APPROVED),'frames':{},'halves':{},'physical_acceptance':False}
    for side,prefix in [('left','L_'),('right','R_')]:
        smooth=F.find_smooth(doc,side);domain,_=M.domains(side);top=M.top_faces(smooth.Shape,13.59)
        assert top.cut(domain).Area+domain.cut(top).Area<.002
        glass=doc.getObject(prefix+'NiceViewVisual2').Shape
        gap=smooth.Shape.distToShape(glass)[0];assert abs(gap-.1)<1e-6
        assert smooth.Shape.common(glass).Volume<1e-8
        log('Building corrected approved frames: '+side)
        _,checks=F.build_styles(doc,side,styles=M.APPROVED)
        report['frames'].update({side+'-'+k:v for k,v in checks.items()})
        for style in M.PLAN['deferred_styles']:
            obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final')
            report['frames'][side+'-'+style]=F.validate_variant(doc,side,smooth,obj)
            colors=F.load_spec()['styles'][style]['colors'];obj.ViewObject.DiffuseColor=[F.rgb(colors[r]) for r in F.face_roles(obj)]
        report['halves'][side]={'glass_gap_mm':gap,'glass_intersection_mm3':smooth.Shape.common(glass).Volume,'frame_top_mm':float(doc.Parameters.FrameTop)}
    for name,old in untouched.items():
        now=doc.getObject(name).Shape
        assert old.cut(now).Volume+now.cut(old).Volume<1e-5,(name,'unrelated geometry changed')
    for name,old in art.items():
        now=doc.getObject(name).Shape
        assert old.cut(now).Volume+now.cut(old).Volume<1e-5,(name,'deferred artwork changed')
    for side,prefix in [('left','L_'),('right','R_')]:
        apply_finish(doc,doc.getObject(prefix+'ActiveFrame').LinkedObject,side,cfg['frames'][side]['color'],cfg['frames'][side]['accents'])
        doc.getObject(prefix+'Half').Placement=poses[side]
    doc.recompute();assert extract(doc)==cfg
    assert {k:v for k,v in protected(doc).items() if '_K' in k}==caps
    signature=assembly_signature(doc);tmp=args.output.with_name('unlabelled.FCStd');doc.saveAs(str(tmp));A.closeDocument(doc.Name)
    preserve_document_label(tmp,args.output,label);tmp.unlink()
    doc=A.openDocument(str(args.output));doc.recompute();assert assembly_signature(doc)==signature and extract(doc)==cfg
    assert not any('Invalid' in o.State or o.TypeId.endswith('Python') for o in doc.Objects)
    A.closeDocument(doc.Name);assert sha(args.source)==sourcehash
    report.update(output_sha256=sha(args.output),saved_reopened_recomputed=True,configuration_unchanged=True,cap_geometry_unchanged=True,excluded_artwork_xy_unchanged=True,unrelated_parts_unchanged=True)
    (args.output.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n');log('PASS: seam candidate reopened, datums and artwork preserved')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
