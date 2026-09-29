"""Keep right frame artwork readable without changing its handed fit geometry.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse, hashlib, json, os, sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import FreeCAD as A
import FreeCADGui as G
import approved_frames as M
import flush_frames as F

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def area_difference(a,b):
    return a.cut(b).Area+b.cut(a).Area

def run():
    values=sys.argv[1:]
    while values and not values[0].startswith('--'):values.pop(0)
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(values)
    assert args.source.resolve()!=args.output.resolve() and not args.output.exists()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    from configuration import extract,apply_finish
    from install_slim_flush import protected,assembly_signature
    from preserve_document_label import preserve_document_label
    sourcehash=sha(args.source)
    G.showMainWindow();G.getMainWindow().hide()
    doc=A.openDocument(str(args.source));doc.recompute()
    assert doc.getObject('DisplaySeamCorrection')
    cfg=extract(doc);label=doc.Label
    poses={p:A.Placement(doc.getObject(p+'Half').Placement) for p in ['L_','R_']}
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute();before_protected=protected(doc)
    # Shape property values retain the old topology when a feature is recomputed.
    # Avoid deep-copying it: that destroys isSame identity for untouched parts
    # and needlessly runs expensive self-Booleans on the entire case.
    untouched={o.Name:o.Shape for o in doc.Objects if hasattr(o,'PartID')}
    left={o.Name:o.Shape for o in doc.Objects if o.Name.startswith('L_') and hasattr(o,'ColorRole')}
    blank=F.find_smooth(doc,'right');before_blank=blank.Shape.copy()
    M.use_document(doc)
    old_art=M.regions('right','gameboy')['detail']
    marker=doc.getObject('FrameArtworkOrientation');already_corrected=marker is not None
    if marker is None:
        marker=doc.addObject('App::DocumentObjectGroup','FrameArtworkOrientation')
        for name,value in [('Mode','same-reading-direction'),('StylesJSON',json.dumps(list(M.APPROVED))),('SourceSHA256',sourcehash)]:
            marker.addProperty('App::PropertyString',name);setattr(marker,name,value)
        marker.addProperty('App::PropertyString','Scope')
        marker.Scope='Right approved artwork translated from left by -86 mm X; structural domains unchanged'
    M.use_document(doc)
    report={'source_sha256':sourcehash,'orientation':'same-reading-direction','right_artwork_x_from_left_mm':-86,
            'already_corrected':already_corrected,'frames':{},'physical_acceptance':False}
    if not already_corrected:
        assert area_difference(old_art,M.regions('right','gameboy')['detail'])>1
        try:M.validate(doc,'right',blank,doc.getObject('R_FlushFrame_gameboy_Final'))
        except AssertionError as exc:
            assert 'top differs from approved artwork' in str(exc),str(exc)
        else:raise AssertionError('Former mirrored artwork was accepted')
        report['former_mirrored_artwork_rejected']=True
        F.build_styles(doc,'right',styles=M.APPROVED)
    for name,old in {**untouched,**left}.items():
        now=doc.getObject(name).Shape
        if old.isSame(now) or old.exportBrepToString()==now.exportBrepToString():continue
        print('Checking changed topology: '+name,file=sys.__stdout__,flush=True)
        assert old.cut(now).Volume+now.cut(old).Volume<1e-5,(name,'unrelated solid changed')
    assert before_blank.cut(blank.Shape).Volume+blank.Shape.cut(before_blank).Volume<1e-5
    assert protected(doc)==before_protected
    for prefix,pose in poses.items():
        side='left' if prefix=='L_' else 'right'
        apply_finish(doc,doc.getObject(prefix+'ActiveFrame').LinkedObject,side,cfg['frames'][side]['color'],cfg['frames'][side]['accents'])
        doc.getObject(prefix+'Half').Placement=pose
    doc.recompute();assert extract(doc)==cfg
    signature=assembly_signature(doc)
    tmp=args.output.with_name('unlabelled.FCStd');assert not tmp.exists()
    doc.saveAs(str(tmp));A.closeDocument(doc.Name)
    preserve_document_label(tmp,args.output,label);tmp.unlink()
    doc=A.openDocument(str(args.output));doc.recompute()
    assert assembly_signature(doc)==signature and extract(doc)==cfg
    assert not any('Invalid' in o.State or o.TypeId.endswith('Python') for o in doc.Objects)
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute();M.use_document(doc)
    for style in M.APPROVED:
        obj=doc.getObject('R_FlushFrame_'+style+'_Final')
        report['frames'][style]=M.validate(doc,'right',F.find_smooth(doc,'right'),obj)
        for role in M.ROLES[1:]:
            l=next(p for p in doc.getObject('L_FlushFrame_'+style+'_Final').MaterialParts if p.ColorRole==role)
            r=next(p for p in obj.MaterialParts if p.ColorRole==role)
            planar=M.top_faces(l.Shape,13.59);planar.translate(A.Vector(-86,0,0))
            error=area_difference(planar,M.top_faces(r.Shape,13.59))
            assert error<.002,(style,role,'not a translation',error)
    corrected=M.regions('right','gameboy')['detail']
    history=A.openDocument(str(args.source));history.recompute();M.use_document(history)
    assert area_difference(M.regions('right','gameboy')['detail'],old_art)<1e-7
    M.use_document(doc);assert area_difference(M.regions('right','gameboy')['detail'],corrected)<1e-7
    M.use_document(history);assert area_difference(M.regions('right','gameboy')['detail'],old_art)<1e-7
    A.closeDocument(history.Name);A.closeDocument(doc.Name)
    assert sha(args.source)==sourcehash
    report.update(output_sha256=sha(args.output),saved_reopened_recomputed=True,configuration_preserved=True,
                  left_materials_and_nonframe_parts_preserved=True,structural_blank_preserved=True,
                  all_right_decorative_roles_equal_translated_left=True,document_context_replay=True)
    (args.output.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: readable right artwork, unchanged handed fit, reopened native and historical replay',file=sys.__stdout__,flush=True)

if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
