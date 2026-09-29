#!/usr/bin/env python3
"""Exact review artwork for the six deferred frames. Never writes production CAD.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy, hashlib, html, json, math, os, re, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/proposals/frame-redesign-r5'
ROLES=('body','detail','accent','secondary')

def rect(x,y,w,h,r=0):
    if not r:return [['M',x,y],['L',x+w,y],['L',x+w,y+h],['L',x,y+h],['Z']]
    return [['M',x+r,y],['L',x+w-r,y],['A',r,r,0,0,1,x+w,y+r],['L',x+w,y+h-r],['A',r,r,0,0,1,x+w-r,y+h],['L',x+r,y+h],['A',r,r,0,0,1,x,y+h-r],['L',x,y+r],['A',r,r,0,0,1,x+r,y],['Z']]
def poly(points):return [[('M' if i==0 else 'L'),*p] for i,p in enumerate(points)]+[['Z']]
def disc(x,y,r):return [['M',x-r,y],['A',r,r,0,1,1,x+r,y],['A',r,r,0,1,1,x-r,y],['Z']]
def d(commands):return ' '.join(c[0]+' '+' '.join(format(v,'.8g') for v in c[1:]) for c in commands)
def path(commands,color,**attrs):
    more=' '.join(f'{k.replace("_","-")}="{html.escape(str(v))}"' for k,v in attrs.items())
    return f'<path d="{d(commands)}" fill="{color}" fill-rule="evenodd" {more}/>'
def text(x,y,t,size=17,**attrs):
    more=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="#263937" {more}>{html.escape(str(t))}</text>'

def author():
    old=json.loads((ROOT/'design/proposals/frame-master-r4/master.json').read_text())
    master={k:copy.deepcopy(old[k]) for k in ['units','origin','left_xy','right_transform','envelope_mm','outer_commands','aperture_commands','aperture_bounds_mm','common','construction','transfer']}
    master.update(schema='flan36-frame-redesign-1',revision='R5',status='PROPOSED_NOT_APPROVED',
        scope=['flan','tape','orbit','manga','nes','walkman'],
        source_sha256={p:hashlib.sha256((Path(os.environ.get('FLAN36_REVIEW_SOURCE',ROOT/p)) if p.endswith('Flan36.FCStd') else ROOT/p).read_bytes()).hexdigest() for p in ['mechanical/revI/Flan36.FCStd','design/proposals/frame-master-r4/master.json','docs/branding/outline/flan36-outline-symbol-black.svg']},
        physical_acceptance=False,styles={},
        display_context={'pcb_bounds_mm':[5,5.1,19,41.1],'glass_bounds_mm':[5.15,7.65,18.85,37.95],
          'render_rule':'Render only actual PCB and glass footprints. Never fill an opening with fictitious dark material.'},
        manufacturing={'nozzle_mm':.4,'layer_mm':.2,'decorations':'flush material partitions','gradients':False,'status':'Exact paths; not sliced or physically qualified.'})
    styles=master['styles']
    master['aperture_commands']=rect(5.05,7.55,13.9,30.5)
    master['aperture_bounds_mm']=[5.05,7.55,18.95,38.05]
    master['seam_status']='Proposed glass-centered 0.10 mm clearance; not an invisible joint guarantee or physical fit qualification.'
    def style(key,label,palette,note):
        s=dict(label=label,palette=dict(zip(ROLES,palette)),note=note,features=[]);styles[key]=s;return s
    def f(s,id,color,commands,window=False):s['features'].append(dict(id=id,color=color,commands=commands,window_cut=window))
    def box(s,id,color,x,y,w,h,r=0):f(s,id,color,rect(x,y,w,h,r))
    def dot(s,id,color,x,y,r):f(s,id,color,disc(x,y,r))
    def field(s,color='detail'):f(s,'ScreenField',color,rect(2.65,5.15,18.7,35.3,2.4),True)
    def cross(s,id,color,x,y,size,arm):
        a=(size-arm)/2;f(s,id,color,poly([(x+a,y),(x+a+arm,y),(x+a+arm,y+a),(x+size,y+a),(x+size,y+a+arm),(x+a+arm,y+a+arm),(x+a+arm,y+size),(x+a,y+size),(x+a,y+a+arm),(x,y+a+arm),(x,y+a),(x+a,y+a)]))

    s=style('flan','Flan',['#F2DFAF','#68422F','#B96732','#DFAB50'],
        'The chosen outline symbol, without a badge or a replacement dessert icon. Caramel bezel and a flush glaze crown.')
    field(s,'accent')
    f(s,'GlazeCrown','detail',[['M',3.2,1.35],['L',20.8,1.35],['L',20.8,2.3],['C',18,2.3,17.8,3.5,16.5,3.5],['C',15.2,3.5,15.8,2.3,14.4,2.3],['L',3.2,2.3],['Z']])
    svg=ET.parse(ROOT/'docs/branding/outline/flan36-outline-symbol-black.svg').getroot()
    tokens=re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?',svg.find('{http://www.w3.org/2000/svg}path').attrib['d'])
    logo=[];i=0;scale=17.4/326.8183
    while i<len(tokens):
        op=tokens[i];n={'M':2,'L':2,'C':6,'Z':0}[op];v=list(map(float,tokens[i+1:i+1+n]));i+=1+n
        for j in range(0,n,2):v[j]=round(3.3+(v[j]-45.4969)*scale,8);v[j+1]=round(43.25+(v[j+1]-13.4988)*scale,8)
        logo.append([op,*v])
    f(s,'ChosenOutline','detail',logo)
    # A separate restrained highlight, not a new logo variation.
    box(s,'CaramelHighlight','secondary',6.6,3.2,4.2,.8,.4)

    s=style('tape','Tape',['#D2CEC1','#303738','#E27136','#F0E9D6'],
        'Full diagonal header, orange screen baseline, paired cassette spools and three equally spaced speaker slats.')
    field(s)
    f(s,'OrangeHeader','accent',poly([(13.6,1.25),(16.1,1.25),(19.4,4.05),(16.9,4.05)]))
    f(s,'GraphiteHeader','detail',poly([(17.3,1.25),(21.65,1.25),(21.65,4.05),(20.6,4.05)]))
    f(s,'ScreenBaseline','accent',[['M',2.65,38.05],['L',21.35,38.05],['A',2.4,2.4,0,0,1,18.95,40.45],['L',5.05,40.45],['A',2.4,2.4,0,0,1,2.65,38.05],['Z']])
    box(s,'TapeBridge','detail',6,44.7,12,1.6)
    for i,x in enumerate([6,18]):
        dot(s,'SpoolRim'+str(i),'detail',x,45.5,2.9);dot(s,'Spool'+str(i),'secondary',x,45.5,2.3)
        cross(s,'Hub'+str(i),'detail',x-1.15,44.35,2.3,.8)
    for i in range(3):box(s,'Speaker'+str(i),'detail',4.2,49.9+i*1.8,15.6,.9,.45)

    s=style('orbit','Orbit',['#EEE5CD','#315C4E','#DF7339','#EEE5CD'],
        'A continuous forest panel and a long orange orbital sweep. The ivory disc sits inside the sweep, as in the reference.')
    f(s,'ForestField','detail',rect(2.35,2.1,19.3,51.8,2.4),True)
    f(s,'OrbitSweep','accent',[['M',3.15,31.2],['C',3.15,40.6,4.1,50.8,9.4,52.25],['C',14.5,53.8,19.2,51.7,20.85,46.7],['L',20.85,42.3],['C',18.9,47.8,17.3,49.05,15.25,48.35],['C',13.9,47.95,14.8,44.1,11.2,44.1],['C',8.4,44.1,8.2,47.3,6.95,45.9],['C',4.65,43.2,4.2,37.2,3.15,31.2],['Z']])
    dot(s,'IvoryDisc','secondary',11.25,48.55,2.25)
    # Quiet navigation star in the otherwise unused header; no fake LCD artwork.
    cross(s,'Star','accent',10.6,2.85,2.8,.8)

    s=style('manga','Manga',['#F0EADB','#27282E','#DA453D','#F0EADB'],
        'Full ink panels separated by deliberate diagonal gutters, four dotted discs, and a red corner. The screen edge stays dark.')
    f(s,'InkField','detail',rect(1.55,1.25,20.9,40,1.2),True)
    f(s,'HeaderGutter','body',poly([(14.8,1.25),(17.2,1.25),(21.65,5.7),(20.7,6.65)]))
    f(s,'LowerSlash','detail',poly([(1.55,42.45),(4.55,42.45),(22.45,48.1),(22.45,50.1)]))
    for i,(x,y) in enumerate([(5.2,48.1),(10.7,48.1),(5.2,53),(10.7,53)]):
        dot(s,'InkDisc'+str(i),'detail',x,y,1.9)
        for j,(dx,dy) in enumerate([(-.65,-.65),(.65,-.65),(-.65,.65),(.65,.65)]):dot(s,'Tone'+str(i)+str(j),'secondary',x+dx,y+dy,.4)
    f(s,'RedCorner','accent',[['M',16.35,49.45],['L',22.45,51.35],['L',22.45,54.8],['L',16.35,54.8],['Z']])

    s=style('nes','NES',['#C6C7BE','#32363B','#C94B3E','#8A8D8D'],
        'A console vent header and a full controller deck: gray D-pad surround, two red buttons, centered select/start bars.')
    field(s)
    box(s,'PowerPanel','secondary',2.35,1.3,8.6,2.5,.4);box(s,'Power','accent',3.15,2.05,3.2,1,.25)
    for i in range(4):box(s,'TopVent'+str(i),'detail',13.35+i*2.4,1.35,1.2,2.4,.2)
    box(s,'ControllerDeck','detail',1.55,42.05,20.9,12.4,.9)
    cross(s,'PadSurround','secondary',2.75,43.25,7.8,2.8)
    cross(s,'Dpad','detail',3.55,44.05,6.2,1.8)
    for id,x in [('B',14.5),('A',19.3)]:
        box(s,id+'Well','body',x-2,46.55,4,4.9,.35);dot(s,id,'accent',x,48.55,1.6)
    box(s,'Select','secondary',4.1,52.25,3,1,.25);box(s,'Start','secondary',8.5,52.25,3,1,.25)
    box(s,'ButtonLabels','accent',13.1,52.55,7.5,.8,.25)

    s=style('walkman','Walkman',['#E4B54B','#192D3B','#275273','#ACBCC0'],
        'Yellow portable-player shell, a navy cassette-window bezel, a silver latch, striped speaker and blue transport controls.')
    field(s)
    box(s,'Latch','secondary',3.4,1.5,12.4,1.8,.4);box(s,'LatchSlot','detail',5.2,2,7.5,.8,.25)
    box(s,'Record','accent',18.2,1.5,3.3,1.8,.4)
    box(s,'SpeakerPanel','accent',2.35,42.3,11.9,12.2,.8)
    for i in range(5):box(s,'Speaker'+str(i),'detail',3.2,43.3+i*2.15,10.2,1.15,.55)
    box(s,'Transport','accent',15.45,42.3,6.2,12.2,.8)
    f(s,'Play','secondary',poly([(17,43.75),(20.05,45.5),(17,47.25)]))
    box(s,'PauseL','secondary',16.65,49,1,2.35,.2);box(s,'PauseR','secondary',19.1,49,1,2.35,.2)
    box(s,'Stop','secondary',17.5,52.1,1.85,1.5,.25)
    return master

def render(master):
    OUT.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(master,indent=2)+'\n';(OUT/'master.json').write_text(encoded)
    digest=hashlib.sha256(encoded.encode()).hexdigest();outer=master['outer_commands'];opening=master['aperture_commands']
    def drawing(key,context=False):
        s=master['styles'][key];p=s['palette'];b=''
        if context:
            # Actual footprints only. Any open side gap must remain visible.
            b+=path(rect(5,5.1,14,36),'#0B0C0E')
            b+=path(rect(5.15,7.65,13.7,30.3),'#303836')
            b+=path(rect(5.9,8.4,12.2,28.8),'#BEC8AD')
            b+='<g fill="#515B47" font-family="monospace" font-size="1.55" text-anchor="middle"><text x="12" y="19">BASE</text><text x="12" y="25">BLE</text></g>'
        b+=path(outer+opening,p['body'],id=key+'-body')
        for f in s['features']:b+=path(f['commands']+(opening if f['window_cut'] else []),p[f['color']],id=key+'-'+f['id'])
        return b
    def svg(w,h,b,mm=False):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}{"mm" if mm else ""}" height="{h}{"mm" if mm else ""}" viewBox="0 0 {w} {h}"><metadata>Flan36 R5 proposal, not approved. Master SHA256 {digest}</metadata>{b}</svg>\n'
    for key in master['styles']:
        (OUT/(key+'.svg')).write_text(svg(24,56,drawing(key),True))
        (OUT/(key+'-preview.svg')).write_text(svg(24,56,drawing(key,True),True))
    def sheet(keys,name):
        cols=3;w=1440;h=1080 if len(keys)>3 else 600
        b=f'<rect width="{w}" height="{h}" fill="#F6F5F0"/>'+text(42,47,'FLAN36 / FRAME REDESIGNS',29,font_weight='bold')
        b+=text(42,78,'R5 · exact millimetre paths · solid colors · approval proposals',18)
        for i,key in enumerate(keys):
            x=42+(i%3)*468;y=120+(i//3)*466;s=master['styles'][key]
            b+=text(x,y,s['label'].upper(),23,font_weight='bold')
            b+=f'<g transform="translate({x+82},{y+23}) scale(5.85)">{drawing(key,True)}</g>'
            for j,(r,c) in enumerate(s['palette'].items()):
                xx=x+(j%2)*210;yy=y+372+(j//2)*26
                b+=f'<rect x="{xx}" y="{yy-14}" width="17" height="17" rx="2" fill="{c}" stroke="#ABB5AE"/>'+text(xx+25,yy,c,15)
        b+=text(42,h-34,'24 × 56 mm · face Z13.59 mm · new artwork is not installed in production CAD',17)
        b+=text(42,h-12,'MASTER '+digest[:20]+' · Display context uses real footprints; seam correction is reviewed separately.',12)
        (OUT/(name+'.svg')).write_text(svg(w,h,b))
        subprocess.run(['rsvg-convert','-o',str(OUT/(name+'.png')),str(OUT/(name+'.svg'))],check=True)
    sheet(list(master['styles']),'collection');sheet(['flan','tape','orbit'],'collection-a');sheet(['manga','nes','walkman'],'collection-b')
    for key,s in master['styles'].items():
        h=1000;b='<rect width="1300" height="1000" fill="#F6F5F0"/>'
        b+=text(40,46,s['label'].upper()+' / EXACT APPROVAL ARTWORK',27,font_weight='bold')
        b+=text(40,80,'24 × 56 mm · four material roles · all artwork flush · no gradients',18)
        b+=f'<g transform="translate(85,153) scale(11)">{drawing(key,True)}</g>'
        b+='<path d="M85 130H349 M62 153V769" stroke="#647D74" fill="none"/>'+text(170,119,'24.00 mm',17)+text(7,470,'56.00',16)
        b+=text(425,150,'DESIGN',19,font_weight='bold')
        import textwrap
        for i,line in enumerate(textwrap.wrap(s['note'],78)):b+=text(425,183+i*27,line,17)
        b+=text(425,287,'SOURCE GEOMETRY',19,font_weight='bold')
        lines=['Origin: top-left; X right / Y down.','All paths, Bézier controls and circular arcs are in master.json.','The 1:1 SVG uses those exact paths and HEX colors.','Painter order is explicit; no scaling or tracing at CAD transfer.','Body corners: TL / BL / BR R1.20; TR R2.40.','Frame face: Z13.59. Glass top: Z13.39.','Artwork depth: 0.40 mm; display collar: through-color.']
        for i,line in enumerate(lines):b+=text(425,324+i*29,line,17)
        b+=text(425,567,'PALETTE',19,font_weight='bold')
        for i,(role,color) in enumerate(s['palette'].items()):
            yy=611+i*35;b+=f'<rect x="425" y="{yy-20}" width="25" height="25" rx="3" fill="{color}" stroke="#ABB5AE"/>'+text(465,yy,role+'  '+color,18)
        b+=text(40,830,'PROPOSAL / NOT APPROVED',20,font_weight='bold')
        b+=text(40,866,'Display shown from actual component footprints. No fictitious dark fill behind the aperture.',17)
        b+=text(40,900,'Exact artwork does not qualify extrusion widths, material bonding or the physical assembly.',17)
        b+=text(40,960,'MASTER '+digest,12)
        (OUT/(key+'-dimensioned.svg')).write_text(svg(1300,h,b))
        subprocess.run(['rsvg-convert','-o',str(OUT/(key+'-dimensioned.png')),str(OUT/(key+'-dimensioned.svg'))],check=True)
    print('Prepared six R5 proposals:',digest)

if __name__=='__main__':render(author())
