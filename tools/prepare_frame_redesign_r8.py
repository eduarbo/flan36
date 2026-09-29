#!/usr/bin/env python3
"""Retain selected artwork and author one exact Evangelion Unit-01 proposal.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy, hashlib, json
from pathlib import Path
from prepare_frame_redesign_r5 import rect, poly

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'design/proposals/frame-redesign-r8'

def author():
    old = json.loads((ROOT/'design/proposals/frame-redesign-r7/master.json').read_text())
    approved = json.loads((ROOT/'design/proposals/display-seam-r1/master.json').read_text())
    m = {k: copy.deepcopy(v) for k,v in old.items() if k not in
         ['styles','scope','decisions','changes','request_ref','source_sha256','revision','status','references','presentation']}
    for key in ['outer_commands','aperture_commands']:
        assert m[key] == approved[key], key
    m.update(revision='R8', status='SELECTED_COLLECTION_EVANGELION_PENDING',
        request_ref='user:20260929:reject-r7-keep-approved-add-evangelion',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
          ['mechanical/revI/Flan36.FCStd','design/proposals/frame-redesign-r7/master.json','design/proposals/display-seam-r1/master.json']},
        decisions={'retained':['talavera','gameboy','snes','phone','ipod','hanafuda'],
          'rejected_r7':[k for k in old['styles'] if k != 'hanafuda'],
          'pending':'One Evangelion-inspired proposal; approval precedes production integration.'},
        changes={'mechanics':'Same mechanical blank, aperture, height and mounting interface.',
          'artwork':'Remove all R7 candidates from the current selection. Retain approved paths and palettes. Add one Unit-01-inspired direction with the exact M1 palette.'},
        references=[{'title':'Evangelion Unit-01, licensed Good Smile model',
          'url':'https://www.goodsmile.com/en/product/59101/MODEROID%2BEvangelion%2BUnit-01',
          'use':'Character reference only. Original geometric fan-art interpretation; no commercial image tracing.'}], styles={})
    for key,s in approved['styles'].items():
        t=copy.deepcopy(s)
        t.update(code='',family='Approved',decision='SELECTED',tagline='Approved · current assembly',replaces='Approved',integration='INSTALLED')
        m['styles'][key]=t
    h=copy.deepcopy(old['styles']['hanafuda'])
    h.update(integration='SELECTED_NOT_INSTALLED',tagline='Approved · integration pending')
    m['styles']['hanafuda']=h
    s=dict(label='Evangelion / Unit 01',code='E1',family='Evangelion',decision='PROPOSED',
        tagline='One new direction · exact M1 colors',replaces='Rejected Mecha proposals',
        palette=copy.deepcopy(old['styles']['mecha-recon']['palette']),
        note='Unit-01-inspired helmet with one long central horn, angular eyes and jaw armor. Flat shoulder markings flank a uniform screen bezel. The 01 identifier and all four HEX colors are part of the exact geometry.',features=[])
    m['styles']['evangelion']=s
    def f(id,color,commands,window=False):
        s['features'].append(dict(id=id,color=color,commands=commands,window_cut=window))
    def p(id,color,points): f(id,color,poly(points))
    def mirror(id,color,points):
        p(id+'L',color,points);p(id+'R',color,[(24-x,y) for x,y in points])
    f('UniformBezel','detail',rect(2.65,5.15,18.7,35.3,2.4),True)
    # A small, actual 01 stencil, not text that would disappear in CAD.
    f('Zero','accent',rect(8.1,1.2,3.6,2.8,.25)+rect(9,2,1.8,1.2,.05))
    p('One','accent',[(13.1,1.2),(14.7,1.2),(14.7,3.2),(15.7,3.2),(15.7,4),(12.4,4),(12.4,3.2),(13.8,3.2),(13.8,2),(13.1,2)])
    f('HeaderLeft','detail',rect(2.2,2,3.9,.9,.2))
    f('HeaderRight','detail',rect(17.9,2,3.9,.9,.2))
    # Shoulder-pylon silhouettes remain inside the perimeter, with no raised fins.
    mirror('Shoulder','accent',[(.8,9.0),(1.8,9.0),(1.8,25.5),(1.45,27),(.8,27)])
    mirror('ShoulderBreak','body',[(.8,13.4),(1.8,13.4),(1.8,14.3),(.8,14.3)])
    mirror('ShoulderLower','detail',[(.8,28.8),(1.8,28.8),(1.8,37.2),(.8,36.2)])
    # The horn and jaw form a recognizable single-unit helmet, replacing M1's arrow deck.
    mirror('HelmetPlate','detail',[(11.45,45.5),(8.7,44.6),(5.1,46.1),(5.7,50.3),(9.0,53.4),(11.55,54.5),(11.55,48.0)])
    p('Horn','accent',[(11.55,42.15),(12.45,42.15),(13.0,47.5),(12,49.0),(11,47.5)])
    mirror('TempleArmor','accent',[(5.1,46.1),(6.1,46.1),(6.7,49.7),(9.4,52.5),(8.7,53.1),(5.7,50.3)])
    mirror('EyeSocket','body',[(6.7,46.7),(10.9,47.8),(10.9,49.2),(6.95,48.35)])
    mirror('Eye','secondary',[(7.4,47.4),(10.2,48.1),(10.2,48.9),(7.55,48.25)])
    p('Mouth','body',[(9.1,50.5),(14.9,50.5),(14.2,52.05),(12,53.05),(9.8,52.05)])
    f('Teeth','secondary',rect(10.2,50.7,3.6,.8,.1))
    p('Chin','accent',[(10.45,53),(12,53.7),(13.55,53),(12.8,54.55),(11.2,54.55)])
    for x in [2.1,20.8]: f('LowerLatch'+str(x),'secondary',rect(x,47.2,1.1,4.8,.2))
    m['scope']=list(m['styles'])
    m['presentation']={'collections':[{'name':'evangelion','title':'EVANGELION / UNIT 01','keys':['evangelion']}],
        'retained':m['decisions']['retained']}
    return m

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'master.json').write_text(json.dumps(author(),indent=2)+'\n')
    print('Authored R8: six selected designs retained; one Evangelion proposal with M1 colors')
