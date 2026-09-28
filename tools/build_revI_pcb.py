#!/usr/bin/env python3
"""Derive Contour board mechanics from the preserved unrouted study.
Only board outline, battery aperture, magnet clearances and six enumerated
auxiliary/mount transforms change. Never overwrite routed or manual work.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,re,shutil,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'hardware/revI')
source=ROOT/'hardware/revH';dest=parser.parse_args().output.resolve()
if dest.exists():raise SystemExit('Refusing to overwrite existing revI work. Preserve it first.')
shutil.copytree(source,dest)
for old in dest.glob('filo36-*'):
    if old.suffix not in ['.kicad_pcb','.kicad_sch','.kicad_pro']:continue
    new=old.with_name(old.name.replace('filo36','flan36'))
    new.write_text(old.read_text().replace('filo36','flan36').replace('FILO36','FLAN36'));old.unlink()
profiles=json.loads((ROOT/'design/revI-profiles.json').read_text())
mounts=json.loads((ROOT/'design/revI-mounts.json').read_text())['left']
def root_children(text):
    depth=0;quoted=False;escaped=False;start=None
    for i,c in enumerate(text):
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='(':
            depth+=1
            if depth==2:start=i
        elif c==')':
            if depth==2:yield start,i+1,text[start:i+1]
            depth-=1
report={'scope':'Mechanical Contour revision; unrouted, not fabrication approved','allowed_footprint_changes':['H1','H3','H4','H5','J1','SW1'],'halves':{}}
for side in ['left','right']:
    src=source/f'filo36-{side}.kicad_pcb';path=dest/src.name.replace('filo36','flan36');text=src.read_text();children=list(root_children(text))
    assert not any(re.match(r'\((segment|via)\s',s) for a,b,s in children),'Routing found; preserve it'
    changes={}
    for a,b,s in reversed(children):
        if re.match(r'\(gr_',s) and '"Edge.Cuts"' in s:text=text[:a]+text[b:];continue
        if not s.startswith('(footprint '):continue
        ref=re.search(r'\(property\s+"Reference"\s+"([^\"]+)"',s)[1]
        if ref not in report['allowed_footprint_changes']:continue
        at=re.search(r'\(at\s+([\d.eE+-]+)\s+([\d.eE+-]+)([^)]*)\)',s)
        x,y=map(float,at.group(1,2));before=[x,y]
        if ref.startswith('H'):
            x,y=next(m['xy'] for m in mounts if m['id']==ref);x=x if side=='left' else 160-x
        else:
            y+=2
            if ref=='SW1':x+=-1.6 if side=='left' else 1.6
        replacement=f'(at {x:.6f} {y:.6f}{at[3]})'
        modified=s[:at.start()]+replacement+s[at.end():]
        text=text[:a]+modified+text[b:];changes[ref]={'from':before,'to':[x,y]}
    text=text.replace('FILO36 revH - UNROUTED STUDY','FILO36 revI - UNROUTED')
    label=re.search(r'\(gr_text "FILO36 revI - UNROUTED"[\s\S]*?\(at ([^)]*)\)',text)
    if label:
        at=re.search(r'\(at [^)]*\)',label[0]);start=label.start()+at.start();end=label.start()+at.end()
        text=text[:start]+f'(at {91 if side=="left" else 69} 62 0)'+text[end:]
    x0,x1=(116.55,129.05) if side=='left' else (30.95,43.45)
    outlines=[profiles[side]['pcb_outline'],[[x0,14],[x1,14],[x1,47.6],[x0,47.6]],*profiles[side]['pcb_cutouts']]
    edges=[]
    for points in outlines:
        for a,b in zip(points,points[1:]+points[:1]):
            edges.append(f'(gr_line (start {a[0]:.6f} {a[1]:.6f}) (end {b[0]:.6f} {b[1]:.6f}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
    at=text.rfind(')');text=text[:at]+'\n'+'\n'.join(edges)+'\n'+text[at:]
    text='\n'.join(line.rstrip() for line in text.splitlines())+'\n';path.write_text(text.replace('filo36','flan36').replace('FILO36','FLAN36'))
    report['halves'][side]={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'pcb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'transforms':changes,'outline_segments':len(edges),'routing_changes':0}
from update_revI_slim_pcb import apply as apply_slim
slim_report=apply_slim(dest)
report['allowed_footprint_changes'].append('SW2')
for side in ['left','right']:
    report['halves'][side]['pcb_sha256']=slim_report['halves'][side]['after_sha256']
    report['halves'][side]['slim_electronics']=slim_report['halves'][side]
    report['halves'][side]['transforms']['J1']['to']=slim_report['halves'][side]['j1_at'][:2]
    report['halves'][side]['transforms']['SW2']={'from':[123 if side=='left' else 37,59.5],'to':slim_report['halves'][side]['reset_at']}
(ROOT/'validation/revI-slim-pcb.json').write_text(json.dumps(slim_report,indent=2)+'\n')
(ROOT/'validation/revI-pcb-outline.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
