"""Assert corrected native edit, USB and component contracts on both halves.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import Part
import audit_repairs as R
import approved_frames as M
import flush_frames as F
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [getattr(b,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
def log(s):print(s,file=sys.__stdout__,flush=True)
def run():
    argv=sys.argv[1:]
    while argv and not argv[0].startswith('--'):argv.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args(argv)
    digest=sha(args.source);doc=A.openDocument(str(args.source));assert doc.getObject('AuditRepairs20261007')
    for prefix in ['L_','R_']:doc.getObject(prefix+'Half').Placement=A.Placement()
    doc.recompute();reference={k:float(getattr(doc.Parameters,k)) for k in ['DisplayShiftY','WindowMargin','FrameTop','FrameRoof']}
    assert reference=={'DisplayShiftY':2.4,'WindowMargin':.1,'FrameTop':13.59,'FrameRoof':1.4}
    names=['NiceViewVisual0','NiceViewVisual1','NiceViewVisual2','NiceViewVisual3','GlassWindow','SlimDisplayMaleSpacer','SlimDisplayMaleContacts','SlimDisplaySocketHousing','SlimDisplaySocketPins','LevelDisplaySolderReserve','LevelDisplayPCBRelief','LevelHeaderServiceWell','SlimDisplayHeaderClearance']
    chain={p+n:bounds(doc.getObject(p+n).Shape) for p in ['L_','R_'] for n in names}
    styles=[*M.APPROVED,'hanafuda'];targets=[doc.getObject(p+'FlushFrame_'+s+'_Final') for p in ['L_','R_'] for s in styles]
    targets.extend(doc.getObject(n) for n in chain)
    report={'source_sha256':digest,'checker_sha256':sha(__file__),'states':{},'usb':{},'diodes':{},'physical_acceptance':False}
    for side,prefix in [('left','L_'),('right','R_')]:
        corridor=R.usb_corridor(doc,side)
        for style in ['level','solid','rim','terrace']:
            for part in ['base','plate']:
                obj=doc.getObject(prefix+'Case_'+style+'_'+part);hit=obj.Shape.common(corridor).Volume
                assert hit<.001,(obj.Name,'USB',hit);report['usb'][obj.Name]=hit
        diodes=doc.getObject(prefix+'Diodes');assert len(diodes.Links)==18
        b=bounds(diodes.Shape);assert abs(b[2]-2.54)<1e-6 and abs(b[5]-3.8)<1e-6
        report['diodes'][side]={'count':18,'underside_bounds_mm':b,'nominal_floor_z_mm':1.4,'nominal_floor_gap_mm':b[2]-1.4}
    log('Both halves: all 16 case parts clear USB; 36 diode bounds checked')
    for label,edits in [('reference',{}),('display',{'DisplayShiftY':3.4}),('window',{'WindowMargin':.3}),('roof',{'FrameTop':13.99}),('combined',{'DisplayShiftY':3.4,'WindowMargin':.3,'FrameTop':13.99})]:
        for name,value in {**reference,**edits}.items():doc.Parameters.set(doc.Parameters.getCellFromAlias(name),str(value)+' mm')
        doc.recompute(targets)
        state={}
        if label=='display':
            for name,old in chain.items():
                actual=bounds(doc.getObject(name).Shape);expected=list(old);expected[1]-=1;expected[4]-=1
                assert max(abs(a-b) for a,b in zip(actual,expected))<1e-6,(name,'datum chain did not follow',actual,expected)
            report['complete_display_chain_y_delta_mm']=-1
        for side,prefix in [('left','L_'),('right','R_')]:
            for style in styles:
                obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final')
                state[side+'-'+style]=R.validate_materials(doc,side,F.find_smooth(doc,side),obj)
        report['states'][label]=state
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps({**report,'passed':False},indent=2)+'\n')
        log('PASS material partitions / backing / glass: '+label+' · 12 frames')
    # Save the combined edit; standard dependencies must survive without generator code.
    trial=args.report.parent/'edited-reopened.FCStd';trial.parent.mkdir(parents=True,exist_ok=True)
    doc.recompute();doc.saveAs(str(trial));log('Combined edit saved; checking reopen');A.closeDocument(doc.Name);doc=A.openDocument(str(trial));doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:
        for style in styles:R.validate_materials(doc,side,F.find_smooth(doc,side),doc.getObject(prefix+'FlushFrame_'+style+'_Final'))
    report['combined_saved_reopened']=True
    targets=[doc.getObject(p+'FlushFrame_'+s+'_Final') for p in ['L_','R_'] for s in styles]
    targets.extend(doc.getObject(n) for n in chain)
    # Unsupported edits are rejected by the same validator used before export.
    doc.Parameters.set(doc.Parameters.getCellFromAlias('FrameRoof'),'1.1 mm');doc.recompute([doc.L_FlushFrame_talavera_Final])
    try:R.validate_materials(doc,'left',F.find_smooth(doc,'left'),doc.L_FlushFrame_talavera_Final)
    except ValueError as exc:assert 'FrameRoof' in str(exc);report['unsupported_roof_rejected']=True
    else:raise AssertionError('Unsupported roof accepted')
    for name,value in reference.items():doc.Parameters.set(doc.Parameters.getCellFromAlias(name),str(value)+' mm')
    doc.recompute(targets)
    for side,prefix in [('left','L_'),('right','R_')]:
        for style in styles:R.validate_materials(doc,side,F.find_smooth(doc,side),doc.getObject(prefix+'FlushFrame_'+style+'_Final'))
    A.closeDocument(doc.Name);assert sha(args.source)==digest
    report.update(reference_restored=True,source_unchanged=True,passed=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n');log('PASS: current native edit matrix, saved/reopened and negative parameter gate')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
