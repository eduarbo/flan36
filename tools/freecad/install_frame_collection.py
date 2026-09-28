"""Install current frames in an isolated copy without changing the electronics stack.
python3 tools/freecad/run_macos.py tools/freecad/install_frame_collection.py --source mechanical/revI/Flan36.FCStd --output build/frame-collection/candidate/Flan36.FCStd --export
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,os,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from install_slim_flush import digest,protected,assembly_signature
def args():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--export",action="store_true")
    values=sys.argv[1:]
    while values and not values[0].startswith("--"):values.pop(0)
    return parser.parse_args(values)

def stable(doc):
    signature=assembly_signature(doc)
    names={o.Name for o in doc.Objects if hasattr(o,'PartID') and not o.PartID.endswith('electronics-lid')}
    return {n:v for n,v in signature.items() if n in names}

def run():
    options=args();source=options.source.resolve();output=options.output.resolve()
    if output==source or output.exists():raise ValueError('Use a fresh isolated candidate')
    if os.environ.get('QT_QPA_PLATFORM')!='offscreen':raise RuntimeError('Use the offscreen helper')
    import FreeCAD as A
    import FreeCADGui as G
    import flush_frames as F
    from configuration import extract,apply_finish
    from preserve_document_label import preserve_document_label
    G.showMainWindow();G.getMainWindow().hide()
    source_hash=digest(source);doc=A.openDocument(str(source));doc.recompute();label=doc.Label
    before=protected(doc);other=stable(doc)
    parameters={n:float(getattr(doc.Parameters,n)) for n in json.loads((ROOT/'design/revI.json').read_text())['parameters']}
    cfg=extract(doc);spec=F.load_spec();palette=spec['styles']['flan']['colors']
    old=[o for o in doc.Objects if o.TypeId!='App::Link' and hasattr(o,'FrameStyle') and o.FrameStyle not in F.STYLES]
    templates={side:F.find_smooth(doc,side) for side in ['left','right']}
    report={'scope':'Frame collection replacement only; unchanged stack and assembly interfaces','source_sha256':source_hash,'physical_acceptance':False}
    report['frames']=F.apply(doc)
    for o in old:
        style=o.FrameStyle
        F.prop(o,'FormerFrameStyle','App::PropertyString',style);o.removeProperty('FrameStyle');o.Visibility=False
        if style=='smooth':
            F.prop(o,'FrameTemplate','App::PropertyBool',True);o.Label='Internal blank · frame construction only'
        else:o.Label='Retired construction · '+style
    for side,prefix in [('left','L_'),('right','R_')]:
        cover=doc.getObject(prefix+'FlushFrame_flan_Final');doc.getObject(prefix+'ActiveFrame').setLink(cover)
        cfg['frames'][side]={'style':'flan','color':palette['body'],'accents':{k:v for k,v in palette.items() if k!='body'}}
        cs=cfg['cases'][side];cs.update(base_color=palette['body'],plate_color=palette['body'] if cs['style']=='level' else palette['detail'],match_frame=True)
        doc.getObject(prefix+'Half').MatchFrameColor=True
        for group,name in [('base','ActiveTray'),('plate','ActivePlate')]:
            obj=doc.getObject(prefix+name).LinkedObject;color=F.rgb(cs[group+'_color'])
            obj.ViewObject.ShapeColor=color;obj.ViewObject.DiffuseColor=[color]*len(obj.Shape.Faces)
        for ref,cap in cfg['keycaps'][side].items():
            cap['color']=[palette['detail'],palette['accent'],palette['secondary']][int(ref[2])] if ref[1]=='3' else palette['body']
            doc.getObject(prefix+ref).ViewObject.ShapeColor=F.rgb(cap['color'])
        apply_finish(doc,cover,side,palette['body'],cfg['frames'][side]['accents'])
    doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:
        apply_finish(doc,doc.getObject(prefix+'ActiveFrame').LinkedObject,side,palette['body'],cfg['frames'][side]['accents'])
        doc.getObject(prefix+'ActiveFrame').Visibility=cfg['cases'][side]['cover']
    assert protected(doc)==before,'Caps or cases changed'
    assert stable(doc)==other,'Electronics or interfaces changed'
    assert extract(doc)==cfg
    assert not any(o.TypeId.endswith('Python') for o in doc.Objects)
    output.parent.mkdir(parents=True,exist_ok=True)
    signature=assembly_signature(doc)
    tmp=output.with_name('unlabelled.FCStd');doc.saveAs(str(tmp));A.closeDocument(doc.Name)
    preserve_document_label(tmp,output,label);tmp.unlink()
    with zipfile.ZipFile(output) as z:assert 'GuiDocument.xml' in z.namelist()
    doc=A.openDocument(str(output));doc.recompute()
    assert doc.Label==label and extract(doc)==cfg
    assert protected(doc)==before and stable(doc)==other
    assert assembly_signature(doc)==signature,'Saved geometry changed'
    assert {n:float(getattr(doc.Parameters,n)) for n in parameters}==parameters
    assert not any('Invalid' in o.State for o in doc.Objects)
    for side,prefix in [('left','L_'),('right','R_')]:
        styles=[o.FrameStyle for o in doc.Objects if o.Name.startswith(prefix) and o.TypeId!='App::Link' and hasattr(o,'FrameStyle')]
        assert sorted(styles)==sorted(F.STYLES),(side,styles)
    assert digest(source)==source_hash
    report.update(saved_reopened_recomputed=True,protected_36_caps_cases_electronics_and_parameters=True,exact_styles=list(F.STYLES),default_style='flan',output_sha256=digest(output))
    (output.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: native collection reopened; protected assembly unchanged',file=sys.__stdout__,flush=True)
    if options.export:
        os.environ['FLAN36_EXPORT_OUT']=str(output.parent)
        os.environ['FLAN36_EXPORT_METADATA']=str(output.parent/'revI.json')
        os.environ['FLAN36_EXPORT_REPORT']=str(output.parent/'mechanical.json')
        path=ROOT/'tools/freecad/export_revI.py'
        exec(compile(path.read_text(),str(path),'exec'),{'__file__':str(path)})
    A.closeDocument(doc.Name)
if __name__=='__main__':
    run();sys.stdout.flush();sys.stderr.flush();os._exit(0)
