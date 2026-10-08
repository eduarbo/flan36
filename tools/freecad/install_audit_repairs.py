"""Apply audit corrections to a separate, source-bound native candidate.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G
import audit_repairs as R
import approved_frames as M
import flush_frames as F
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(x):print(x,file=sys.__stdout__,flush=True)
def run():
    args=sys.argv[1:]
    while args and not args[0].startswith('--'):args.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);o=p.parse_args(args)
    assert o.source.resolve()!=o.output.resolve() and not o.output.exists()
    sourcehash=sha(o.source);o.output.parent.mkdir(parents=True,exist_ok=True)
    G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(o.source));doc.recompute()
    assert doc.getObject('FrameArtworkOrientation') and doc.getObject('DisplaySeamCorrection')
    assert not doc.getObject('AuditRepairs20261007')
    poses={p:A.Placement(doc.getObject(p+'Half').Placement) for p in ['L_','R_']}
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute()
    caps={o.Name:(o.Mesh.Topology,str(o.Placement)) for o in doc.Objects if o.Name.startswith(('L_K','R_K')) and hasattr(o,'Mesh')}
    marker=doc.addObject('App::DocumentObjectGroup','AuditRepairs20261007')
    F.prop(marker,'SourceSHA256','App::PropertyString',sourcehash)
    F.prop(marker,'RecipeSHA256','App::PropertyString',sha(ROOT/'tools/freecad/audit_repairs.py'))
    hana=doc.addObject('App::DocumentObjectGroup','HanafudaApproval')
    F.prop(hana,'MasterSHA256','App::PropertyString',sha(M.HANAFUDA_PATH))
    F.prop(hana,'MasterPath','App::PropertyString',str(M.HANAFUDA_PATH.relative_to(ROOT)))
    R.display_chain(doc);log('Display dependency chain corrected')
    usb=R.usb_access(doc);log('Local USB access corrected')
    diodes=R.install_diodes(doc);log('36 actual-footprint bottom diode models installed')
    styles=(*M.APPROVED,'hanafuda');checks={}
    for side in ['left','right']:
        _,records=F.build_styles(doc,side,styles=styles)
        checks[side]=records
        # Disconnected old fixed-floor color builders have no active consumers.
        prefix='L_' if side=='left' else 'R_'
        old=[o.Name for o in doc.Objects if any(o.Name.startswith(prefix+'FlushFrame_'+s+'_R4_') for s in M.APPROVED)]
        for name in reversed(old):doc.removeObject(name)
    doc.recompute();doc.saveAs(str(o.output.parent/'geometry-checkpoint.FCStd'))
    from configuration import apply,extract
    from keycap_config import normalize
    cfg=normalize(json.loads((ROOT/'design/configurations/default.json').read_text()));apply(doc,cfg)
    for name,(topology,placement) in caps.items():
        item=doc.getObject(name);now=item.Mesh.Topology
        assert len(now[0])==len(topology[0]) and now[1]==topology[1],(name,'cap topology changed')
        delta=max((a-b).Length for a,b in zip(now[0],topology[0]))
        assert delta<1e-5 and str(item.Placement)==placement,(name,'cap pose changed',delta,str(item.Placement),placement)
    for p,pose in poses.items():doc.getObject(p+'Half').Placement=pose
    doc.recompute();assert not any('Invalid' in obj.State or obj.TypeId.endswith('Python') for obj in doc.Objects)
    doc.Label='Flan36';doc.saveAs(str(o.output));A.closeDocument(doc.Name)
    reopened=A.openDocument(str(o.output));reopened.recompute();assert extract(reopened)==cfg
    assert not any('Invalid' in obj.State or obj.TypeId.endswith('Python') for obj in reopened.Objects)
    A.closeDocument(reopened.Name);assert sha(o.source)==sourcehash
    report={'source_sha256':sourcehash,'output_sha256':sha(o.output),'native_saved_reopened':True,'usb_cuts':usb,'diode_poses':diodes,'frames':checks,'physical_acceptance':False}
    (o.output.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n');log('PASS: saved/reopened native candidate, reference artwork and cap poses preserved')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
