"""Check painted native faces, visible links and configuration save/reopen.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import sys,json,hashlib,os,traceback
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/freecad'))
from configuration import apply,extract,apply_finish
from keycap_config import normalize
from frame_finishes import palette,rgb,role
OUT=ROOT/'build/viewer-multicolor';OUT.mkdir(exist_ok=True)
result={};source=ROOT/'mechanical/revI/Flan36.FCStd'
def verify(doc):
    records=[]
    for side,prefix in [('left','L_'),('right','R_')]:
        link=doc.getObject(prefix+'ActiveFrame');cover=link.LinkedObject
        assert not link.ViewObject.OverrideMaterial
        colors=cover.ViewObject.DiffuseColor
        assert len(colors)==len(cover.Shape.Faces)
        actual={tuple(round(v*255) for v in color[:3]) for color in colors}
        expected={tuple(round(v*255) for v in rgb(c)) for c in palette(cover.FrameStyle,extract(doc)['frames'][side]['color'],extract(doc)['frames'][side]['accents']).values()}
        assert actual==expected,(side,actual,expected)
        records.append({'side':side,'style':cover.FrameStyle,'colored_faces':len(colors),'distinct_colors':len(actual),'visible_link_inherits_materials':link.Visibility and not link.ViewObject.OverrideMaterial})
    return records
try:
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    G.showMainWindow();G.getMainWindow().hide()
    print('Opening native finish source',file=sys.__stdout__,flush=True)
    doc=A.openDocument(str(source));doc.recompute();cfg=extract(doc);records=[]
    for style in ['handheld','tv','cyberpunk','cartridge','arcade','mecha','kintsugi']:
        for side in ['left','right']:cfg['frames'][side]={'style':style,'color':palette(style)['body']}
        cfg=normalize(cfg);apply(doc,cfg);assert extract(doc)==cfg;records.extend(verify(doc))
    cfg['frames']['left']['color']='#ad7656';cfg['frames']['left']['accents']={'detail':'#182532','accent':'#b9e49c','secondary':'#e38997'};apply(doc,cfg);assert extract(doc)==cfg
    cell=doc.Parameters.getCellFromAlias('FrameTop');doc.Parameters.set(cell,'17.2 mm');doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:apply_finish(doc,doc.getObject(prefix+'ActiveFrame').LinkedObject,side,cfg['frames'][side]['color'])
    verify(doc)
    target=OUT/'multicolor.FCStd';doc.saveAs(str(target));A.closeDocument(doc.Name);doc=A.openDocument(str(target));doc.recompute();assert extract(doc)==cfg;verify(doc)
    # Export the visible colored link scene, with only frames visible, for inspection.
    for obj in doc.Objects:
        if obj.TypeId=='App::Part':obj.Visibility=True
        elif hasattr(obj,'ViewObject'):obj.Visibility=False
    for prefix in ['L_','R_']:doc.getObject(prefix+'ActiveFrame').Visibility=True
    # Qt's offscreen macOS platform has no OpenGL context: saveImage aborts
    # outside Python exception handling. Geometry/material assertions above
    # remain mandatory; the regular VTK/viewer checks provide rendered QA.
    native_screenshot=os.environ.get('QT_QPA_PLATFORM')!='offscreen'
    if native_screenshot:
        G.activeDocument().activeView().viewTop();G.activeDocument().activeView().fitAll();G.activeDocument().activeView().saveImage(str(OUT/'freecad.png'),1000,600,'White')
    A.closeDocument(doc.Name);assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    result={'passed':True,'source_unchanged':True,'source_sha256':digest,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'styles':records,'json_body_override_roundtrip':True,'edited_roof_mm':17.2,'saved_reopened_colors':True,'native_screenshot_rendered':native_screenshot,'rendered_qa':'Separate VTK and browser material/image checks; no native screenshot claimed for offscreen Qt.'}
except Exception:
    result={'passed':False,'error':traceback.format_exc()}
(OUT/'freecad.json').write_text(json.dumps(result,indent=2)+'\n')
# Scoped helper process only; avoids bundled Qt teardown instability.
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':os._exit(0 if result.get('passed') else 1)
