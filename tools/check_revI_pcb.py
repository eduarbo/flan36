#!/usr/bin/env python3
"""Read actual KiCad transforms/pads/edges, preserving electrical state.
Historical pre-routing check. For current routed boards use check_routed_pcb.py.
Run with KiCad Python after CLI DRC for both historical halves.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,re,collections,math
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1]
if any(p.LoadBoard(str(ROOT/f'hardware/revI/flan36-{s}.kicad_pcb')).GetTracks() for s in ('left','right')):
    raise SystemExit('Current boards are routed. Use tools/check_routed_pcb.py; this gate describes the historical placement study.')
def snapshot(path):
    board=p.LoadBoard(str(path));result={};assert len(board.GetTracks())==0
    for f in board.GetFootprints():
        xy=[f.GetPosition().x,f.GetPosition().y]
        result[f.GetReference()]={'xy':xy,'angle':f.GetOrientationDegrees(),'layer':board.GetLayerName(f.GetLayer()),'locked':f.IsLocked(),'symbol':f.GetPath().AsString(),'uuid':f.m_Uuid.AsString(),
         'pads':sorted((q.GetNumber(),q.GetPosition().x-xy[0],q.GetPosition().y-xy[1],q.GetNetname(),q.GetDrillSize().x,q.GetDrillSize().y,q.GetSize().x,q.GetSize().y) for q in f.Pads()),'models':[m.m_Filename for m in f.Models()]}
    return board,result
profiles=json.loads((ROOT/'design/revI-profiles.json').read_text());layout=json.loads((ROOT/'design/layout.json').read_text())
transforms=json.loads((ROOT/'validation/revI-pcb-outline.json').read_text())
slim=json.loads((ROOT/'validation/revI-slim-pcb.json').read_text())
report={'kicad_version':p.GetBuildVersion(),'fabrication_ready':False,'halves':{}}
pattern=r'\(gr_line\s+\(start\s+([\d.eE+-]+)\s+([\d.eE+-]+)\)\s+\(end\s+([\d.eE+-]+)\s+([\d.eE+-]+)\).*?\(layer\s+"?Edge.Cuts"?\)'
for side in ['left','right']:
    old=ROOT/f'hardware/revH/filo36-{side}.kicad_pcb';new=ROOT/f'hardware/revI/flan36-{side}.kicad_pcb'
    board,actual=snapshot(new);_,original=snapshot(old);assert set(actual)==set(original)
    for ref,state in actual.items():
        before=original[ref];after=dict(state)
        if ref in transforms['allowed_footprint_changes'] or ref in ['SW2','J2']:
            target=(slim['halves'][side]['j1_at'][:2] if ref=='J1' else slim['halves'][side]['reset_at'] if ref=='SW2' else [0,0] if ref=='J2' else transforms['halves'][side]['transforms'][ref]['to'])
            if ref=='J2':target=json.loads((ROOT/'validation/revI-approved-display-pcb.json').read_text())['halves'][side]['target_xy']
            assert all(abs(p.ToMM(state['xy'][i])-target[i])<2e-6 for i in range(2))
            after['xy']=before['xy']
        if ref=='J1':
            assert state['angle']%360==slim['halves'][side]['j1_at'][2]%360 and state['layer']=='F.Cu';after['angle']=before['angle']
        if ref=='SW2':
            assert state['layer']=='B.Cu' and state['angle']==0;after['layer']=before['layer']
        # Translated integer coordinates can differ by one KiCad internal unit.
        assert {k:v for k,v in before.items() if k!='pads'}=={k:v for k,v in after.items() if k!='pads'},ref
        for a,b in zip(before['pads'],after['pads']):
            if ref=='J1':
                assert a[0]==b[0] and a[3]==b[3],(ref,'net changed',a,b)
                expected=(0,0) if b[0]=='1' else (0,2 if side=='left' else -2)
                assert all(abs(p.ToMM(b[i+1])-expected[i])<1e-6 for i in range(2)),(ref,b)
                assert all(abs(p.ToMM(b[i])-v)<1e-6 for i,v in [(4,.75),(5,.75),(6,1.2),(7,1.75)]),(ref,b)
            elif ref=='SW2':
                assert a[0]==b[0] and a[3:]==b[3:] and abs(a[1]-b[1])<=1 and abs(a[2]+b[2])<=1,(ref,a,b)
            else:
                assert a[0]==b[0] and a[3:]==b[3:] and max(abs(a[i]-b[i]) for i in [1,2])<=1,(ref,a,b)
    for key in layout['halves'][side]:
        f=actual[key['ref']];assert f['locked'] and abs(f['angle']-key['angle'])<1e-6
        assert all(abs(p.ToMM(f['xy'][i])-key[axis])<1e-6 for i,axis in enumerate(['x','y']))
    actual_edges=[tuple(sorted([(float(m[1]),float(m[2])),(float(m[3]),float(m[4]))])) for m in re.finditer(pattern,new.read_text(),re.S)]
    x0,x1=(116.55,129.05) if side=='left' else(30.95,43.45)
    aperture=[[116.55,13.2],[129.05,13.2],[129.05,47.6],[119.85,47.6],[119.85,49.4],[117.65,49.4],[117.65,47.6],[116.55,47.6]]
    if side=='right':aperture=[[160-x,y] for x,y in aperture]
    contours=[profiles[side]['pcb_outline'],aperture,*profiles[side]['pcb_cutouts']]
    expected=[tuple(sorted(tuple(round(x,6) for x in q) for q in [a,b])) for poly in contours for a,b in zip(poly,poly[1:]+poly[:1])]
    assert sorted(actual_edges)==sorted(expected),'CAD/KiCad contour mismatch'
    drc=json.loads((ROOT/f'build/revI/drc-{side}.json').read_text());counts=dict(collections.Counter(v['type'] for v in drc['violations']));assert not counts,counts
    rows=[]
    for f in board.GetFootprints():
        for q in f.Pads():
            if q.GetAttribute()==p.PAD_ATTRIB_NPTH:continue
            if not q.IsOnLayer(p.F_Cu) and not q.IsOnLayer(p.B_Cu):continue
            poly=q.GetEffectivePolygon(p.F_Cu if q.IsOnLayer(p.F_Cu) else p.B_Cu)
            for i in range(poly.OutlineCount()):
                chain=poly.COutline(i);rows.append({'ref':f.GetReference(),'pad':q.GetNumber(),'net':q.GetNetname(),'polygon':[list(p.ToMM(chain.CPoint(j))) for j in range(chain.PointCount())]})
    (ROOT/f'build/revI/pads-{side}.json').write_text(json.dumps(rows))
    report['halves'][side]={'pcb_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'footprints_nets_uuid_models_preserved_except_explicit_PH_pad_and_reset_flip_changes':len(actual)==46,'allowed_transforms':transforms['halves'][side]['transforms'],'approved_display_header':json.loads((ROOT/'validation/revI-approved-display-pcb.json').read_text())['halves'][side],'slim_electronics':slim['halves'][side],'locked_original_keys':18,'outline_matches_cad_to_mm':.000001,'drc_violations':counts,'unconnected_items':len(drc['unconnected_items'])}
(ROOT/'validation/revI-electrical.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
