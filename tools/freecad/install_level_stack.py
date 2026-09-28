"""Create an isolated floor/flush/level native candidate; never overwrite input.

python3 tools/freecad/run_macos.py tools/freecad/install_level_stack.py \
  --source mechanical/revI/Flan36.FCStd --output build/level-case/candidate/Flan36.FCStd
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import FreeCADGui as G
import level_stack
import slim_stack
from install_slim_flush import protected,assembly_signature
from configuration import extract,apply as configure
from preserve_document_label import preserve_document_label

def say(s): print(s,file=sys.__stdout__,flush=True)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    argv=sys.argv[1:]
    if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1': argv=argv[argv.index(str(Path(__file__).resolve()))+1:]
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--quick',action='store_true')
    args=p.parse_args(argv);source=args.source.resolve();out=args.output.resolve()
    assert source!=out and not out.exists()
    out.parent.mkdir(parents=True,exist_ok=True)
    G.showMainWindow();G.getMainWindow().hide()
    source_hash=digest(source);doc=A.openDocument(str(source));say('Opened preserved native source')
    cfg=extract(doc);label=doc.Label
    keys=lambda:{k:v for k,v in protected(doc).items() if '_K' in k}
    before=keys()
    report={'source_sha256':source_hash,'physical_acceptance':False,'state':'candidate'}
    report['recipe']=level_stack.apply(doc);say('Floor, stack, connectors, wires and level shell built')
    doc.recompute()
    # Diagnostic checks run before expensive decoration. They cannot claim pass.
    from check_level_stack import AnalyticCollisionCache,cell_motion
    old_overlap,old_motion=slim_stack.overlap,slim_stack.cell_motion_checks
    try:
        slim_stack.overlap=AnalyticCollisionCache();slim_stack.cell_motion_checks=cell_motion
        report['stack_checks']=slim_stack.validate(doc)
    finally: slim_stack.overlap,slim_stack.cell_motion_checks=old_overlap,old_motion
    (out.parent/'diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
    say('Nominal collision and service diagnostics recorded')
    if not args.quick:
        import flush_frames
        # Existing native booleans already depend on Smooth and FrameTop.
        # Refresh their checks and face colors without rebuilding every sketch.
        report['frames']={}
        spec=flush_frames.load_spec()
        for side,prefix in [('left','L_'),('right','R_')]:
            half=doc.getObject(prefix+'Half');pose=A.Placement(half.Placement)
            half.Placement=A.Placement();doc.recompute()
            for style in flush_frames.STYLES:
                obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final')
                report['frames'][side+'-'+style]=flush_frames.validate_variant(doc,side,flush_frames.find_smooth(doc,side),obj,spec)
                colors=spec['styles'][style]['colors']
                obj.ViewObject.DiffuseColor=[flush_frames.rgb(colors[r]) for r in flush_frames.face_roles(obj)]
                say('Flush frame verified: '+side+' / '+style)
            half.Placement=pose;doc.recompute()
    for side in ('left','right'):
        cfg['cases'][side]['style']='level'
        cfg['cases'][side]['plate_color']=cfg['frames'][side]['color']
    configure(doc,cfg);doc.recompute()
    assert keys()==before,'36 cap transforms or meshes changed'
    report['signature']=assembly_signature(doc)
    tmp=out.with_name('unlabelled.FCStd');doc.saveAs(str(tmp));A.closeDocument(doc.Name)
    preserve_document_label(tmp,out,label);tmp.unlink()
    say('Saved candidate; reopening')
    doc=A.openDocument(str(out));doc.recompute()
    assert assembly_signature(doc)==report['signature']
    assert keys()==before
    assert not any(o.TypeId.endswith('Python') or 'Invalid' in o.State for o in doc.Objects)
    assert level_stack.apply(doc)==report['recipe']
    assert digest(source)==source_hash
    report.update(saved_reopened=True,key_geometry_preserved=True,native_idempotence=True,output_sha256=digest(out))
    report.pop('signature')
    (out.parent/'installation.json').write_text(json.dumps(report,indent=2)+'\n')
    A.closeDocument(doc.Name);say('Candidate saved and independently reopened; acceptance checks still required')

if __name__=='__main__':
    run();sys.stdout.flush();sys.stderr.flush();os._exit(0)
