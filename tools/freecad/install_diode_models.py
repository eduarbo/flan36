"""Add only current diode 3D references; preserve all other PCB fields.
Also retain pinned source face colors in the native assembly and its viewer.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G,Part
from export_pcb_components import footprints,children,local_shape,export,difference
from check_pcb_step_registration import calibrate,cli_export,sha
ROOT=Path(__file__).resolve().parents[2]
def run():
    args=sys.argv[1:]
    while args and not args[0].startswith('--'):args.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args(args)
    G.showMainWindow();G.getMainWindow().hide();work=ROOT/'build/audit-fixes-20261007/diodes'
    import ImportGui
    calibration=calibrate(work/'calibration')
    d=A.newDocument('DiodeColors');ImportGui.insert(str(ROOT/'components/sources/D_SOD-123.step'),d.Name);d.recompute()
    original=next(o for o in d.Objects if hasattr(o,'Shape') and o.Shape.Solids);shape=original.Shape.copy();colors=list(original.ViewObject.DiffuseColor)
    if len(colors)==1:colors=colors*len(shape.Faces)
    assert len(colors)==len(shape.Faces) and len(set(tuple(c) for c in colors))==3
    A.closeDocument(d.Name)
    local=shape.copy();local.translate(A.Vector(0,0,calibration['local_z_correction_mm']['B.Cu']))
    report={'models':{},'calibration':calibration,'pcb_changes':{},'actual_registration':{},'physical_acceptance':False}
    export('diode-sod123',local,colors,ROOT/'hardware/revI/models',report)
    doc=A.openDocument(str(a.source));poses={p:A.Placement(doc.getObject(p+'Half').Placement) for p in ['L_','R_']}
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:
        path=ROOT/f'hardware/revI/flan36-{side}.kicad_pcb';before=path.read_text();fps=footprints(path)
        expected=[ref for ref in fps if ref.startswith('D')];assert len(expected)==18
        after=before;nodes=[];visuals=[]
        for ref in expected:
            fp=fps[ref];block=fp['block'];models=[x for x in children(block) if x.startswith('(model ')]
            model='(model "${KIPRJMOD}/models/diode-sod123.step"\n (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'
            if models:assert len(models)==1 and 'diode-sod123.step' in models[0]
            new=block.replace(models[0],model) if models else block[:-1].rstrip()+'\n'+model+'\n)'
            assert after.count(block)==1;after=after.replace(block,new)
            node=doc.getObject(prefix+'Diode_'+ref);node.ViewObject.DiffuseColor=colors;nodes.append(node)
            for index,color in enumerate(sorted(set(tuple(c) for c in colors))):
                name=prefix+'Diode_'+ref+'_Color'+str(index)
                visual=doc.getObject(name) or doc.addObject('Part::Feature',name)
                visual.Shape=Part.makeCompound([face for face,c in zip(shape.Faces,colors) if tuple(c)==color])
                visual.Placement=A.Placement(node.Placement);visual.Label=ref+(' · cathode / metal' if index else ' · body')
                visual.ViewObject.ShapeColor=color[:3];doc.getObject(prefix+'Construction').addObject(visual);visual.Visibility=False;visuals.append(visual)
        path.write_text(after)
        # Delete only the newly inserted model blocks from the postimage and
        # compare exact unchanged footprint bodies plus every other root item.
        post=footprints(path)
        for ref,old in fps.items():
            scrub=lambda b:'\n'.join(x for x in children(b) if not x.startswith('(model '))
            assert scrub(old['block'])==scrub(post[ref]['block'])
            if ref not in expected:assert old['block']==post[ref]['block']
        oldroot=[x for x in children(before) if not x.startswith('(footprint ')]
        newroot=[x for x in children(after) if not x.startswith('(footprint ')]
        assert oldroot==newroot
        compound=doc.getObject(prefix+'Diodes')
        if 'VisualParts' not in compound.PropertiesList:compound.addProperty('App::PropertyLinkList','VisualParts','Flan36')
        compound.VisualParts=visuals;compound.ViewObject.DiffuseColor=[c for node in nodes for c in colors]
        report['pcb_changes'][side]={'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':sha(path),'model_references_added':expected,'footprints_pads_nets_contours_tracks_unchanged':True}
        # Real KiCad export of every diode in a single filtered component set.
        actual=cli_export(path,work/(side+'-all-diodes.step'),'--no-board-body','--component-filter',','.join(expected))
        actual.translate(A.Vector(0,0,calibration['kicad_to_native_z_mm']))
        native=Part.makeCompound([n.Shape for n in nodes]);delta=difference(native,actual)
        assert delta<.001,(side,'diode registration',delta)
        report['actual_registration'][side]={'references':expected,'difference_mm3':delta,'actual_export_sha256':sha(work/(side+'-all-diodes.step'))}
    from configuration import apply,extract
    from keycap_config import normalize
    cfg=normalize(json.loads((ROOT/'design/configurations/default.json').read_text()));apply(doc,cfg)
    for p,pose in poses.items():doc.getObject(p+'Half').Placement=pose
    doc.AuditRepairs20261007.RecipeSHA256=sha(ROOT/'tools/freecad/audit_repairs.py')
    doc.recompute();doc.save();A.closeDocument(doc.Name)
    check=A.openDocument(str(a.source));check.recompute();assert extract(check)==cfg;A.closeDocument(check.Name)
    report['source_sha256']=sha(a.source);report['passed']=True
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 36 colored native diode instances registered to actual KiCad STEP; only model references changed',file=sys.__stdout__,flush=True)
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
