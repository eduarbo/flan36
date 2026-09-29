#!/usr/bin/env python3
"""Six new directions in exact millimetre paths; no production CAD writes.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from prepare_frame_redesign_r5 import rect,poly,disc
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/proposals/frame-redesign-r6'
ROLES=('body','detail','accent','secondary')
def transform(commands,scale=1,dx=0,dy=0):
    result=[]
    for op,*v in commands:
        assert op in ('M','L','C','Z')
        result.append([op,*[round(n*scale+(dx if i%2==0 else dy),8) for i,n in enumerate(v)]])
    return result
def logo(x,y,width):
    svg=ET.parse(ROOT/'docs/branding/outline/flan36-outline-symbol-black.svg').getroot()
    tokens=re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?',svg.find('{http://www.w3.org/2000/svg}path').attrib['d'])
    commands=[];i=0
    while i<len(tokens):
        op=tokens[i];n={'M':2,'L':2,'C':6,'Z':0}[op];commands.append([op,*map(float,tokens[i+1:i+n+1])]);i+=n+1
    s=width/326.8183
    return transform(commands,s,x-45.4969*s,y-13.4988*s)
def author():
    source=json.loads((ROOT/'design/proposals/display-seam-r1/master.json').read_text())
    m={k:copy.deepcopy(source[k]) for k in ['units','origin','left_xy','right_transform','envelope_mm','outer_commands','aperture_commands','aperture_bounds_mm','bezel','common','construction','transfer']}
    m['construction_history']={
      'source':'design/proposals/display-seam-r1/master.json',
      'original_option_b_extent':m['construction']['option_b_extent'],
      'original_cover_status':m['construction']['cover_options'][0]['status'],
      'disposition':'Historical mechanical changes already incorporated in the current blank. R6 does not apply a second raise or display translation.'}
    m['construction']['option_b_extent']='Use the existing Z13.59 frame face and case top. The historical +0.20 mm raise and display-chain translation are already incorporated; do not apply them again.'
    m['construction']['cover_options'][0]['status']='CURRENT_BASELINE_GEOMETRY; new artwork is proposed, and physical fit remains unqualified.'
    m.update(schema='flan36-frame-redesign-1',revision='R6',status='PROPOSED_NOT_APPROVED',
      request_ref='user:20260929:reinvent-rejected-r5-frames',
      scope=['flan','tape','orbit','manga','nes','walkman'],styles={},physical_acceptance=False,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['mechanical/revI/Flan36.FCStd','design/proposals/display-seam-r1/master.json','docs/branding/outline/flan36-outline-symbol-black.svg']},
      display_context={'pcb_bounds_mm':[5,5.1,19,41.1],'glass_bounds_mm':[5.15,7.65,18.85,37.95],'lcd_bounds_mm':[6.628,10.26,17.372,35.54],
        'render_rule':'Actual modeled component footprints; LCD content illustrative. No fictitious aperture fill.'},
      manufacturing={'nozzle_mm':.4,'layer_mm':.2,'decorations':'flush complementary material volumes','gradients':False,'status':'Exact review geometry; slicing and physical fit unqualified.'},
      changes={'rejected_proposal':'R5','mechanics':'Use current corrected blank unchanged. No stack, case, opening or mounting changes.',
        'art_direction':'Full-face compositions and new references, rather than six small control clusters below the same bezel.'})
    def style(key,label,ref,colors,note):
        s=dict(label=label,replaces=ref,palette=dict(zip(ROLES,colors)),note=note,features=[]);m['styles'][key]=s;return s
    def f(s,id,role,commands,window=False):s['features'].append(dict(id=id,color=role,commands=commands,window_cut=window))
    def box(s,id,role,x,y,w,h,r=0):f(s,id,role,rect(x,y,w,h,r))
    def dot(s,id,role,x,y,r):f(s,id,role,disc(x,y,r))
    def field(s,role='detail'):f(s,'UniformBezel',role,rect(2.65,5.15,18.7,35.3,2.4),True)

    s=style('flan','Caramelo','Flan',['#F4DEAB','#502E28','#AE592F','#D59A4D'],
      'An espresso screen surround, broad caramel pool and the original outline mark reversed into the glaze. A warm dessert object, without a badge.')
    field(s)
    f(s,'GlazeHeader','accent',[['M',1.2,1.2],['L',22.8,1.2],['L',22.8,3.35],['C',18.4,3.35,18.5,4.25,15.3,4.25],['C',12,4.25,11.2,2.85,8.2,2.85],['C',5.8,2.85,4.3,4.2,1.2,4.2],['Z']])
    f(s,'CaramelPool','accent',[['M',1.2,43],['C',6.8,40.3,9.1,44,13,43.4],['C',17,42.8,19.1,40.8,22.8,42.3],['L',22.8,53.6],['C',22.8,54.4,22.4,54.8,21.6,54.8],['L',2.4,54.8],['C',1.6,54.8,1.2,54.4,1.2,53.6],['Z']])
    f(s,'OriginalOutline','body',logo(4.65,44.6,14.7))
    for i,x in enumerate([.85,22.25]):box(s,'SugarRib'+str(i),'secondary',x,15,.9,17,.45)
    box(s,'GoldGlint','secondary',4.6,3.35,4.2,.9,.45)

    s=style('tape','Lucha','Tape',['#2448A7','#F6EAD1','#DA4D3D','#182E53'],
      'Cobalt wrestling-mask graphics: twin brow flashes, long red cheek stripes and a cream mouth guard. The display becomes part of the mask.')
    field(s)
    left=[['M',2.4,1.25],['C',6.5,1.25,8.8,2.2,10.7,4.1],['L',7.9,4.1],['C',6.1,3.15,4.3,3.0,2.4,3.0],['Z']]
    f(s,'BrowLeft','accent',left)
    f(s,'BrowRight','accent',[[op,*[24-v if i%2==0 else v for i,v in enumerate(vals)]] for op,*vals in left])
    for i,x in enumerate([.8,22.2]):box(s,'Cheek'+str(i),'accent',x,10,1,27,.5)
    f(s,'MouthGuard','detail',poly([(2.4,43),(7.3,44.3),(16.7,44.3),(21.6,43),(19.7,50.8),(16.1,52.2),(7.9,52.2),(4.3,50.8)]))
    f(s,'MouthOpening','secondary',poly([(6.1,45.7),(17.9,45.7),(16.4,49.3),(7.6,49.3)]))
    box(s,'Lip','detail',9.6,46.6,4.8,.9,.3)
    f(s,'Chin','accent',poly([(9,50.5),(15,50.5),(14,54.8),(10,54.8)]))

    s=style('orbit','Hanafuda','Orbit',['#F1E7D2','#252B2E','#D84932','#456348'],
      'A lacquer-card landscape: vermilion sun above an ink mountain, ivory snowcap and pine-green foothills. Broad color regions keep the tiny landscape legible.')
    field(s)
    dot(s,'HeaderSun','accent',12,2.6,1.8)
    for i,x in enumerate([.8,22.3]):box(s,'CardRule'+str(i),'secondary',x,9,.9,27,.45)
    dot(s,'RisingSun','accent',12,47.5,5.3)
    f(s,'Mountain','detail',poly([(1.7,54.6),(10.9,45.9),(13.1,45.9),(22.3,54.6)]))
    f(s,'Snowcap','body',poly([(7.8,48.83),(10.9,45.9),(13.1,45.9),(16.2,48.83),(13.5,48.3),(12,49.1),(10.5,48.3)]))
    f(s,'PineGround','secondary',[['M',1.2,54.8],['L',1.2,52.8],['C',7.1,51.15,10,54.1,15,53.3],['C',18.9,52.65,20.4,52.6,22.8,53.35],['L',22.8,54.8],['Z']])

    s=style('manga','Mecha','Manga',['#E7E6DA','#293746','#C7473C','#D8AE4A'],
      'An original robot faceplate: gold V crest, red armor slashes, broad vent panel and angular chin. Every detail remains flush.')
    field(s)
    f(s,'VCrest','secondary',poly([(4.2,1.2),(7.3,1.2),(12,3.45),(16.7,1.2),(19.8,1.2),(12,4.4)]))
    for i,x in enumerate([.7,22.25]):
        f(s,'ArmorSlash'+str(i),'accent',poly([(x,11),(x+1.05,13),(x+1.05,32),(x,34)]))
    f(s,'VentPlate','detail',poly([(2.6,42.4),(21.4,42.4),(19.5,51.5),(15.8,54.3),(8.2,54.3),(4.5,51.5)]))
    for side,x in [('L',4.9),('R',14.1)]:
        for j in range(3):box(s,'Vent'+side+str(j),'body',x,44.3+j*1.9,5,1,.3)
    f(s,'ChinArmor','accent',poly([(9.1,49.6),(14.9,49.6),(15.55,52.5),(12,54.8),(8.45,52.5)]))
    box(s,'ChinGlint','secondary',11.55,50.55,.9,2.25,.3)

    s=style('nes','Cartucho 8','NES',['#CBC8BB','#30343B','#B9433C','#CFA552'],
      'The whole frame reads as a game cartridge: red label header, molded-looking side ribs and a gold contact bank. No miniature controller.')
    field(s)
    box(s,'LabelHeader','accent',2.7,1.25,18.6,2.5,.45)
    box(s,'LabelNotch','body',10.5,1.25,3,1,.2)
    for side,x in [('L',.75),('R',22.3)]:
        for j in range(5):box(s,'ShellRib'+side+str(j),'detail',x,13+j*4.3,.95,2.7,.35)
    box(s,'ConnectorWell','detail',1.3,42.45,21.4,12.2,.7)
    box(s,'LabelFooter','body',3.2,43.65,17.6,2.1,.3)
    box(s,'TitleBlock','accent',3.2,43.65,5.7,2.1,.3)
    for j in range(7):box(s,'GoldContact'+str(j),'secondary',3.4+j*2.6,47.1,1.6,6.1,.35)

    s=style('walkman','Terminal','Walkman',['#DCE0D5','#283E38','#C6D75A','#DF7C4E'],
      'A compact cyberdeck in sage, graphite and acid yellow: offset header, circuit-like side rails, terminal prompt and a large orange return key.')
    field(s)
    f(s,'HeaderLabel','accent',poly([(2.4,1.2),(18.9,1.2),(21.6,3.85),(2.4,3.85)]))
    box(s,'HeaderSlot','detail',4.2,2.05,8.1,.9,.35)
    for side,x in [('L',.75),('R',22.35)]:
        box(s,'Trace'+side,'detail',x,10,.9,25,.35)
        for j,y in enumerate([12.2,31.1]):box(s,'TracePad'+side+str(j),'accent',x-.1,y,1.1,2.2,.3)
    box(s,'TerminalDeck','detail',1.25,42.15,21.5,12.6,.9)
    f(s,'Prompt','accent',poly([(3.4,44.3),(7.6,47.2),(3.4,50.1),(3.4,48.65),(5.6,47.2),(3.4,45.75)]))
    box(s,'Cursor','accent',7.55,49.1,4.25,1.05,.25)
    box(s,'ReturnKey','secondary',13.8,44,7.1,8.6,.65)
    f(s,'ReturnArrow','detail',poly([(18.8,45.7),(19.85,45.7),(19.85,49.3),(17,49.3),(17,50.5),(15.25,48.8),(17,47.1),(17,48.25),(18.8,48.25)]))
    box(s,'DeckStatus','body',3.4,52,8.2,.9,.35)
    return m
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);master=author();(OUT/'master.json').write_text(json.dumps(master,indent=2)+'\n')
    print('Authored R6:',', '.join(s['label'] for s in master['styles'].values()))
