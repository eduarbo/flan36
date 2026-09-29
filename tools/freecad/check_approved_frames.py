"""Read back every native frame; bind approved solids to the saved planar master.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import approved_frames as M
import flush_frames as F

def run():
    values=sys.argv[1:]
    while values and not values[0].startswith('--'):values.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args(values)
    digest=hashlib.sha256(args.source.read_bytes()).hexdigest()
    doc=A.openDocument(str(args.source));doc.recompute()
    report={'source_sha256':digest,'approved_master_sha256':M.PLAN['master_sha256'],'frames':{},'contact_alignment':{},'physical_acceptance':False}
    for side,prefix in [('left','L_'),('right','R_')]:
        doc.getObject(prefix+'Half').Placement=A.Placement();doc.recompute()
        for style in F.STYLES:
            obj=doc.getObject(prefix+'FlushFrame_'+style+'_Final')
            report['frames'][side+'-'+style]=F.validate_variant(doc,side,F.find_smooth(doc,side),obj)
        if doc.getObject('DisplaySeamCorrection'):
            glass=doc.getObject(prefix+'NiceViewVisual2').Shape
            smooth=F.find_smooth(doc,side).Shape
            gap=smooth.distToShape(glass)[0]
            assert abs(gap-.1)<1e-6 and smooth.common(glass).Volume<1e-8
            window=doc.getObject(prefix+'GlassWindow').Shape.BoundBox
            expected_window=[116.05,129.95] if side=='left' else [30.05,43.95]
            assert abs(window.XMin-expected_window[0])<1e-6 and abs(window.XMax-expected_window[1])<1e-6
            assert abs(window.YMin+49.05)<1e-6 and abs(window.YMax+18.55)<1e-6
            report.setdefault('display_seam',{})[side]={'glass_gap_mm':gap,'intersection_mm3':0,'opening_mm':[window.XLength,window.YLength]}
        expected=sorted([(117.92+2.54*i) if side=='left' else (31.92+2.54*i) for i in range(5)])
        pins=doc.getObject(prefix+'SlimDisplaySocketPins').Shape
        circles=[e.Curve for e in pins.Edges if isinstance(e.Curve,Part.Circle) and abs(e.Curve.Radius-.3)<1e-6]
        actual=sorted(set(round(c.Center.x,6) for c in circles if abs(c.Center.y+50.8)<1e-6))
        assert len(actual)==5 and max(abs(a-b) for a,b in zip(actual,expected))<1e-6,(side,actual)
        drills=[o for o in doc.Objects if o.Name.startswith(prefix+'PadDrill') and abs(o.Placement.Base.y+50.8)<1e-6 and any(abs(o.Placement.Base.x-x)<1e-6 for x in expected)]
        assert len(drills)==5 and all(abs(float(o.Radius)-.5)<1e-6 for o in drills)
        report['contact_alignment'][side]={'native_pin_and_drill_centers_x':actual,'radial_clearance_mm':.2}
    A.closeDocument(doc.Name)
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==digest
    report['passed']=True;report['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 22 native frames; approved saved faces and all PCB pin centers agree',file=sys.__stdout__,flush=True)

if __name__=='__main__':
    import Part
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
