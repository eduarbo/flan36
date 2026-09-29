#!/usr/bin/env python3
"""Hanafuda retained; three Mecha and three Kumiko approval alternatives.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy,hashlib,json,math
from pathlib import Path
from prepare_frame_redesign_r5 import rect,poly,disc
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/proposals/frame-redesign-r7'
ROLES=('body','detail','accent','secondary')
def vertices(x,y,r,n=6,angle=0):
    return [(round(x+r*math.cos(angle+i*2*math.pi/n),8),round(y+r*math.sin(angle+i*2*math.pi/n),8)) for i in range(n)]
def ring(x,y,r,width,n=6,angle=0):
    return poly(vertices(x,y,r,n,angle))+poly(vertices(x,y,r-width/math.cos(math.pi/n),n,angle))
def segment(a,b,width=.8):
    dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);nx=-dy/length*width/2;ny=dx/length*width/2
    return poly([(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),(b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)])
def author():
    old=json.loads((ROOT/'design/proposals/frame-redesign-r6/master.json').read_text())
    m={k:copy.deepcopy(v) for k,v in old.items() if k not in ['styles','scope','changes','request_ref','source_sha256','revision','status']}
    m.update(revision='R7',status='HANAFUDA_SELECTED_OTHER_ARTWORK_PROPOSED',request_ref='user:20260929:retain-hanafuda-redesign-mecha-add-kumiko',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['mechanical/revI/Flan36.FCStd','design/proposals/frame-redesign-r6/master.json']},
        scope=['hanafuda','mecha-recon','mecha-reactor','mecha-hangar','kumiko-asanoha','kumiko-kikko','kumiko-kasane'],
        decisions={'retained':{'hanafuda':'R6 geometry and palette retained exactly by user selection'},'rejected_r6':['flan','tape','manga','nes','walkman'],'pending':'Choose Mecha and Kumiko alternatives before artwork integration.'},
        changes={'mechanics':'Same current mechanical blank. No installation or production change.','artwork':'Retain Hanafuda. Replace the selection gallery with three new Mecha and three Kumiko alternatives. Rejected alternatives remain only in revision history.'},
        references=[{'title':'Tanihata traditional Kumiko pattern catalogue','url':'https://kumikowoodworking.com/products/category/auspicious-omens-motifs/','use':'Pattern vocabulary only. Original geometric artwork; no commercial image tracing.'},{'title':'Shion Kumiko pattern catalogue','url':'https://www.shion-kumiko.com/order-guide/kumiko-patterns/','use':'Asanoha and kikko vocabulary. Kasane is an original diagonal composition, not a named historical pattern.'}],styles={})
    h=copy.deepcopy(old['styles']['orbit']);h.update(label='Hanafuda',code='H',family='Retained',decision='SELECTED',tagline='Selected · unchanged from R6');m['styles']['hanafuda']=h
    def style(key,code,label,family,palette,note):
        s=dict(label=label,code=code,family=family,decision='PROPOSED',tagline=family+' · choose a proposal',replaces=family,palette=dict(zip(ROLES,palette)),note=note,features=[]);m['styles'][key]=s;return s
    def f(s,id,color,commands,window=False):s['features'].append(dict(id=id,color=color,commands=commands,window_cut=window))
    def box(s,id,color,x,y,w,h,r=0):f(s,id,color,rect(x,y,w,h,r))
    def dot(s,id,color,x,y,r):f(s,id,color,disc(x,y,r))
    def field(s):f(s,'UniformBezel','detail',rect(2.65,5.15,18.7,35.3,2.4),True)
    def line(s,id,color,a,b,w=.8):f(s,id,color,segment(a,b,w))
    def mirrored(s,id,color,points):
        f(s,id+'L',color,poly(points));f(s,id+'R',color,poly([(24-x,y) for x,y in points]))

    s=style('mecha-recon','M1','Recon','Mecha',['#382D55','#7561A7','#C7DD58','#F0DEBB'],
      'Purple scout armor with asymmetric lime panels, a broad directional mark and split cream sensor slots. No face, chin or V-shaped crest.')
    field(s)
    f(s,'ForeheadPanel','accent',poly([(2.2,1.3),(15.8,1.3),(19.1,4.05),(5.5,4.05)]))
    box(s,'ForeheadSlot','body',4.8,2.0,6.4,.8,.25)
    f(s,'HeaderCap','secondary',poly([(18.7,1.3),(21.8,1.3),(21.8,4.05)]))
    for suffix,x in [('L',.8),('R',22.1)]:
        f(s,'Spine'+suffix,'accent',poly([(x,11),(x+1.1,12.7),(x+1.1,28.8),(x,30.5)]))
        box(s,'SpineStop'+suffix,'secondary',x,32.2,1.1,4.4,.3)
    f(s,'ScoutDeck','detail',poly([(1.4,42.4),(20.8,42.4),(22.6,44.3),(22.6,54.6),(3.3,54.6),(1.4,52.7)]))
    f(s,'Direction','accent',poly([(3,44.1),(8.3,44.1),(12.4,48.5),(8.3,53),(3,53),(7.4,48.5)]))
    for i in range(3):box(s,'Sensor'+str(i),'secondary',14.4+i*2.25,45.1,1.05,5.8,.3)
    box(s,'DeckSeam','body',14.4,52.15,5.55,.85,.3)

    s=style('mecha-reactor','M2','Reactor','Mecha',['#E4E7DE','#293E4E','#43BBC4','#D89848'],
      'Pale armor around an ink-blue screen. A cyan reactor ring, amber core and segmented side channels replace the previous robot-face motif.')
    field(s)
    box(s,'TopChannel','detail',3.05,1.3,17.9,2.65,.6)
    box(s,'TopEmitter','accent',5.4,2.15,13.2,.95,.3)
    for side,x in [('L',.75),('R',22.25)]:
        for i in range(4):box(s,'Channel'+side+str(i),'accent',x,12+i*5.4,1,3.8,.3)
        box(s,'EndStop'+side,'secondary',x,35.2,1,2.7,.3)
    f(s,'ReactorWell','detail',poly(vertices(12,48.7,6.0,8,math.pi/8)))
    f(s,'ReactorRing','accent',ring(12,48.7,4.45,1.0,8,math.pi/8))
    f(s,'ReactorCore','secondary',poly(vertices(12,48.7,2.0,6,math.pi/6)))
    for x in [2.2,20.8]:box(s,'MountMark'+str(x),'detail',x,46.2,1,5.0,.3)
    box(s,'LowerDatum','secondary',9.6,54.25,4.8,.6,.2)

    s=style('mecha-hangar','M3','Hangar','Mecha',['#C5BDA5','#35413D','#D16F3D','#EAE4CF'],
      'Industrial service armor in sand and graphite: offset header, orange latches and a diagonally split access hatch. Flat markings, no bolt heads or raised controls.')
    field(s)
    box(s,'HeaderWell','detail',1.5,1.3,14.0,2.6,.3)
    for i in range(3):f(s,'HeaderStripe'+str(i),'accent',poly([(2.4+i*3.8,1.3),(4.1+i*3.8,1.3),(6.1+i*3.8,3.9),(4.4+i*3.8,3.9)]))
    box(s,'HeaderID','secondary',17.1,1.3,5.4,2.6,.3)
    for x in [.7,22.3]:
        box(s,'Rail'+str(x),'detail',x,11,1,25,.25)
        box(s,'Latch'+str(x),'accent',x-.05,18,1.1,7,.2)
    f(s,'Hatch','detail',poly([(2.1,42.4),(21.9,42.4),(21.9,52.8),(20.1,54.6),(2.1,54.6)]))
    f(s,'HatchInset','secondary',poly([(3.2,43.5),(20.8,43.5),(20.8,49.2),(13.5,49.2),(10.3,52.1),(3.2,52.1)]))
    line(s,'HatchSplit','body',(4.5,51.6),(12.6,43.5),1.0)
    box(s,'HatchHandle','detail',13.9,45.35,5.2,1.1,.35)
    box(s,'LatchLower','accent',14.35,51.0,5.25,2.4,.3)
    box(s,'SerialDash','secondary',4.0,53.2,4.8,.8,.25)

    s=style('kumiko-asanoha','K1','Asanoha','Kumiko',['#493B2E','#E6CFA6','#B78752','#796044'],
      'A large sixfold hemp-leaf lattice framed in warm hinoki tones. Complete cells and deliberate broad strips keep the geometry readable at this small scale.')
    field(s)
    box(s,'HeaderBeam','accent',1.5,1.3,21,2.6,.25)
    for i in range(3):box(s,'HeaderJoint'+str(i),'detail',4.5+i*7,1.3,1,2.6)
    for x in [.8,22.3]:
        box(s,'SideBeam'+str(x),'accent',x,10,.9,27,.2)
        for y in [16,24,32]:box(s,'SideJoint'+str(x)+str(y),'detail',x,y,.9,1.1)
    f(s,'PanelBorder','detail',rect(1.4,42.4,21.2,12.3,.4)+rect(2.2,43.2,19.6,10.7,.05))
    center=(12,48.55);v=vertices(*center,5.3)
    f(s,'AsanohaHex','detail',ring(*center,5.3,.8))
    # A triangular kumiko cell divided at its centroid, repeated sixfold.
    for i in range(6):
        a=v[i];b=v[(i+1)%6];q=((center[0]+a[0]+b[0])/3,(center[1]+a[1]+b[1])/3)
        line(s,'Radial'+str(i),'detail',center,a,.8)
        for j,p in enumerate([center,a,b]):line(s,'Leaf'+str(i)+str(j),'detail',q,p,.8)
    for suffix,x in [('L',3.6),('R',20.4)]:
        line(s,'OuterBrace'+suffix+'A','secondary',(x,44.0),(x,53.1),.85)
        line(s,'OuterBrace'+suffix+'B','detail',(x,44.0),(6.7 if suffix=='L' else 17.3,48.55),.8)
        line(s,'OuterBrace'+suffix+'C','detail',(x,53.1),(6.7 if suffix=='L' else 17.3,48.55),.8)

    s=style('kumiko-kikko','K2','Kikko','Kumiko',['#EEE4CA','#72573E','#B39266','#B6B49A'],
      'Walnut-colored hexagonal lattice on a pale base, with a darker screen surround and quiet segmented side beams. Ten complete cells form a compact repeating panel.')
    field(s)
    for i,x in enumerate([5,12,19]):f(s,'HeaderCell'+str(i),'accent',poly(vertices(x,2.7,1.5)))
    for x in [.8,22.25]:
        for j in range(5):box(s,'SideJoint'+str(x)+str(j),'accent',x,10+j*5.1,.95,3.8,.2)
    box(s,'PanelGround','secondary',1.2,42.25,21.6,12.7,.45)
    for i in range(5):
        x=4.5+i*3.75
        for j in range(2):
            y=45.2+j*math.sqrt(3)*2.5+(i%2)*math.sqrt(3)*1.25
            f(s,'Hex'+str(i)+str(j),'detail',ring(x,y,2.5,.8))
    box(s,'FootBeam','accent',2.0,54.15,20,.8,.2)

    s=style('kumiko-kasane','K3','Kasane','Kumiko',['#2E4359','#E8D6B2','#BD955E','#627B8D'],
      'An original indigo-and-wood diagonal lattice. Offset diamond cells and contrasting intersections create a woven rhythm without changing the flat surface.')
    field(s)
    box(s,'HeaderGround','secondary',1.4,1.2,21.2,2.8,.3)
    for i in range(5):f(s,'HeaderGrain'+str(i),'accent',poly([(2.5+i*4,1.5),(3.4+i*4,1.5),(5.1+i*4,3.7),(4.2+i*4,3.7)]))
    for x in [.85,22.3]:
        box(s,'SideBeam'+str(x),'accent',x,10,.85,27,.2)
        for y in [14.5,22.5,30.5]:box(s,'Joint'+str(x)+str(y),'secondary',x,y,.85,1)
    f(s,'PanelBorder','detail',rect(1.4,42.5,21.2,12.2,.4)+rect(2.2,43.3,19.6,10.6,.05))
    for i,(x,y) in enumerate([(5.2,46.2),(12,46.2),(18.8,46.2),(8.6,51.1),(15.4,51.1)]):
        points=[(x,y-2.7),(x+3.2,y),(x,y+2.7),(x-3.2,y)]
        for j in range(4):line(s,'Diamond'+str(i)+str(j),'accent' if j%2 else 'detail',points[j],points[(j+1)%4],.85)
    box(s,'JoinLower','secondary',10.85,53.4,2.3,.85,.2)
    m['presentation']={'collections':[{'name':'mecha','title':'MECHA / THREE NEW PROPOSALS','keys':['mecha-recon','mecha-reactor','mecha-hangar']},{'name':'kumiko','title':'KUMIKO / THREE NEW PROPOSALS','keys':['kumiko-asanoha','kumiko-kikko','kumiko-kasane']}],'retained':['hanafuda']}
    return m
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);m=author();(OUT/'master.json').write_text(json.dumps(m,indent=2)+'\n')
    print('Authored R7: Hanafuda retained; M1-M3 and K1-K3 proposals')
