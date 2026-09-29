#!/usr/bin/env python3
"""Center J2 in the unrouted PCB studies without rewriting unrelated objects.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,re
from pathlib import Path
from update_revI_slim_pcb import children
ROOT=Path(__file__).resolve().parents[1]

def update(text,side):
    assert not any(re.match(r'\((segment|via|zone)\s',s) for _,_,s in children(text))
    matches=[(a,b,s) for a,b,s in children(text) if s.startswith('(footprint ') and re.search(r'\(property\s+"Reference"\s+"J2"',s)]
    assert len(matches)==1
    a,b,footprint=matches[0]
    at=re.search(r'\(at\s+([\d.eE+-]+)\s+([\d.eE+-]+)([^)]*)\)',footprint)
    target=117.92 if side=='left' else 31.92
    old=117.72 if side=='left' else 32.12
    assert abs(float(at[2])-50.8)<1e-6 and min(abs(float(at[1])-x) for x in [old,target])<1e-6
    replacement=f'(at {target:.6f} {at[2]}{at[3]})'
    changed=footprint[:at.start()]+replacement+footprint[at.end():]
    return text[:a]+changed+text[b:]

if __name__=='__main__':
    result={'scope':'Only J2 footprint X translation; copper routing remains absent','fabrication_ready':False,'halves':{}}
    for side in ['left','right']:
        p=ROOT/f'hardware/revI/flan36-{side}.kicad_pcb';old=p.read_text();new=update(old,side)
        p.write_text(new)
        result['halves'][side]={'target_xy':[117.92 if side=='left' else 31.92,50.8],'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (ROOT/'validation/revI-approved-display-pcb.json').write_text(json.dumps(result,indent=2)+'\n')
