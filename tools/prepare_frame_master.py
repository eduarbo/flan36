#!/usr/bin/env python3
"""Author review-only, dimensioned frame artwork; never write production CAD.
SPDX-License-Identifier: GPL-3.0-or-later

All review drawings use the same millimetre paths stored in master.json.
Later CAD must consume those paths and painter order, not trace the PNGs.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'design/proposals/frame-master-r3'
OUT.mkdir(parents=True, exist_ok=True)


def rect(x, y, w, h, r=0):
    if not r:
        return [['M', x, y], ['L', x+w, y], ['L', x+w, y+h], ['L', x, y+h], ['Z']]
    return [['M', x+r, y], ['L', x+w-r, y], ['A', r, r, 0, 0, 1, x+w, y+r],
            ['L', x+w, y+h-r], ['A', r, r, 0, 0, 1, x+w-r, y+h],
            ['L', x+r, y+h], ['A', r, r, 0, 0, 1, x, y+h-r],
            ['L', x, y+r], ['A', r, r, 0, 0, 1, x+r, y], ['Z']]


def circle(x, y, r):
    return [['M', x-r, y], ['A', r, r, 0, 1, 1, x+r, y],
            ['A', r, r, 0, 1, 1, x-r, y], ['Z']]


def polygon(points):
    return [[('M' if i == 0 else 'L'), *p] for i, p in enumerate(points)] + [['Z']]


def pathdata(cmds):
    return ' '.join(c[0] + ' ' + ' '.join(f'{v:.6f}'.rstrip('0').rstrip('.') if v else '0' for v in c[1:]) for c in cmds)


OUTLINE = [['M', 1.2, 0], ['L', 21.6, 0], ['A', 2.4, 2.4, 0, 0, 1, 24, 2.4],
           ['L', 24, 54.8], ['A', 1.2, 1.2, 0, 0, 1, 22.8, 56], ['L', 1.2, 56],
           ['A', 1.2, 1.2, 0, 0, 1, 0, 54.8], ['L', 0, 1.2], ['A', 1.2, 1.2, 0, 0, 1, 1.2, 0], ['Z']]
APERTURE = rect(4.55, 7.35, 14.5, 31.1)
STYLES = {}


def style(key, label, palette, note):
    s = dict(label=label, palette=palette, note=note, features=[])
    STYLES[key] = s
    return s


def feature(s, name, color, commands, window_cut=False):
    s['features'].append(dict(id=name, color=color, commands=commands, window_cut=window_cut))


def field(s, color='detail', bottom=41.6):
    feature(s, 'ScreenField', color, rect(1.2, 1.2, 21.6, bottom-1.2, 1.7), True)


def box(s, name, color, x, y, w, h, r=0):
    feature(s, name, color, rect(x, y, w, h, r))


def dot(s, name, color, x, y, r):
    feature(s, name, color, circle(x, y, r))


def cross(s, x, y, color, size=7.2, arm=2.4):
    a=(size-arm)/2
    feature(s, 'Dpad', color, polygon([(x+a,y),(x+a+arm,y),(x+a+arm,y+a),
      (x+size,y+a),(x+size,y+a+arm),(x+a+arm,y+a+arm),(x+a+arm,y+size),
      (x+a,y+size),(x+a,y+a+arm),(x,y+a+arm),(x,y+a),(x+a,y+a)]))


s=style('flan','Flan',['#F2DFAF','#68422F','#B96732','#DFAB50'],'Custard, flowing caramel and a flat dessert seal. Default proposal.')
field(s, 'accent')
feature(s,'CaramelFlow','detail', [['M',1.6,3],['C',3,1.7,6,1.6,10,1.6],['L',20.5,1.6],
 ['C',20,3.5,17,3.4,13,3.5],['L',3.6,3.5],['L',3.6,34],['C',3.6,39,5,40,5.7,41.6],
 ['C',2.7,41.6,1.6,38,1.6,33],['Z']])
box(s,'DessertSeal','accent',5.1,43,13.8,11.5,3.4)
feature(s,'Custard','secondary',polygon([(9.1,46.3),(14.9,46.3),(16.2,50.9),(7.8,50.9)]))
box(s,'Glaze','detail',8.8,45.3,6.4,1.2,.5)
box(s,'Saucer','detail',7.2,52,9.6,.9,.4)

s=style('tape','Tape',['#D2CEC1','#303738','#E27136','#F0E9D6'],'Orange diagonal, two reels and three horizontal slats.')
field(s)
feature(s,'Diagonal','accent',polygon([(14,1.6),(16.2,1.6),(21.5,6.9),(19.3,6.9)]))
box(s,'ScreenFoot','accent',1.6,40.2,20.8,1.4,.3)
box(s,'ReelBridge','detail',6,44.3,12,2.2)
dot(s,'LeftReel','secondary',6,45.4,2.7);dot(s,'RightReel','secondary',18,45.4,2.7)
dot(s,'LeftHub','detail',6,45.4,1);dot(s,'RightHub','detail',18,45.4,1)
for i in range(3): box(s,'Slat'+str(i),'detail',4,49.9+i*1.8,16,1,.45)

s=style('orbit','Orbit',['#EEE5CD','#315C4E','#DF7339','#EEE5CD'],'Continuous forest field with asymmetric orange crescent and nested ivory disc.')
field(s,bottom=54.8)
feature(s,'Crescent','accent', [['M',1.6,28],['C',1.8,38,2.5,45,6,49.5],
 ['C',10,55.3,18.5,55,22.1,49.5],['L',22.1,44],['C',20,49,17,50.1,14.6,49.4],
 ['C',12.1,48.7,13.5,43.7,10,43.7],['C',6.6,43.7,7.4,47.1,5.4,44.5],
 ['C',2.8,41.1,2,33,1.6,28],['Z']])
dot(s,'IvoryDisc','secondary',10.2,47.7,2.8)

s=style('manga','Manga',['#F0EADB','#27282E','#DA453D','#F0EADB'],'Broad ink panels, diagonal paper gutters, four dots and red corner.')
field(s)
feature(s,'TopGutter','secondary',polygon([(15,1.5),(16.8,1.5),(22.3,7),(22.3,8.8)]))
feature(s,'DiagonalPanel','detail',polygon([(1.6,42.5),(5.3,42.5),(22.3,48.1),(22.3,50)]))
for i,(x,y) in enumerate([(5.1,47.9),(10,47.9),(5.1,52.5),(10,52.5)]):dot(s,'PanelDot'+str(i),'detail',x,y,1.65)
feature(s,'RedCorner','accent',polygon([(16,50),(22.3,52.1),(22.3,54.6),(16,54.6)]))

s=style('talavera','Talavera',['#F1E6CA','#244E91','#C36443','#244E91'],'Cobalt reaches the aperture. Four equal, uncompressed 5.1 mm petals in an 11.6 mm square.')
field(s,bottom=41.5)
petal=[['M',6.2,43.2],['C',9.6,43.2,11.3,45,11.3,46.6],['C',11.3,49.3,6.2,50.2,6.2,43.2],['Z']]
for i,(mx,my) in enumerate([(False,False),(True,False),(False,True),(True,True)]):
    cmds=[]
    for c in petal:
        op,*v=c
        for n in range(0,len(v),2):
            if mx:v[n]=24-v[n]
            if my:v[n+1]=98-v[n+1]
        cmds.append([op,*v])
    feature(s,'Petal'+str(i),'secondary',cmds)
feature(s,'TerracottaStar','accent',[['M',12,47.7],['C',12.3,48.4,12.6,48.7,13.3,49],
 ['C',12.6,49.3,12.3,49.6,12,50.3],['C',11.7,49.6,11.4,49.3,10.7,49],
 ['C',11.4,48.7,11.7,48.4,12,47.7],['Z']])

s=style('gameboy','Game Boy',['#DCD6BA','#42454D','#973C60','#A6A392'],'Flat cross pad, berry buttons and diagonal speaker slots.')
field(s);cross(s,2.4,43,'detail')
dot(s,'A','accent',19.5,44.8,1.9);dot(s,'B','accent',15.8,48,1.9)
box(s,'Select','secondary',3,52.2,4.7,1.1,.5)
for i in range(4): feature(s,'Speaker'+str(i),'secondary',polygon([(13+i*2.2,51.5),(13.85+i*2.2,51.5),(15.1+i*2.2,54.5),(14.25+i*2.2,54.5)]))

s=style('nes','NES',['#C6C7BE','#32363B','#C94B3E','#8A8D8D'],'Dark controller deck, gray cross and twin red buttons.')
field(s);box(s,'Deck','detail',1.6,42.6,20.8,9.6,.8);cross(s,3.2,43.7,'secondary',6.4,2.2)
dot(s,'A','accent',19.1,47.8,1.9);dot(s,'B','accent',14.6,47.8,1.9)
box(s,'Signature','accent',13.5,53.5,8.5,1)
box(s,'Header','secondary',3,2.8,13,1.2,.4)

s=style('snes','SNES',['#D1D0C9','#464751','#746198','#ACA0C2'],'Lavender four-button diamond and compact cross pad.')
field(s);cross(s,2.7,44,'detail',6.6,2.2)
for name,c,x,y in [('A','accent',20.1,48),('B','accent',16.8,51.3),('X','secondary',16.8,44.7),('Y','secondary',13.5,48)]:dot(s,name,c,x,y,1.7)
box(s,'Power','accent',3.2,2.5,7,1.4,.7);box(s,'Reset','secondary',13.5,2.5,7,1.4,.7)
box(s,'Select','secondary',3.2,53,7.7,1.2,.6)

s=style('phone','2000s Phone',['#263C55','#B8BBB5','#87AD67','#455469'],'Navy shell, navigation rocker, green call key and nine flat keypad inlays.')
field(s)
box(s,'Earpiece','body',8,2.8,8,1.3,.6)
box(s,'Nav','secondary',9,42.7,6,2.2,1.1)
box(s,'Call','accent',2.7,42.7,4.8,2.2,1.1);box(s,'End','detail',16.5,42.7,4.8,2.2,1.1)
for r in range(3):
    for c in range(3):box(s,f'Key{r}{c}','detail',3+c*6.3,46+r*3.1,4.4,2.1,.8)

s=style('walkman','Walkman',['#275273','#192D3B','#E4B54B','#ACBCC0'],'Yellow header and transport strip with five dark speaker bars.')
field(s);box(s,'Header','accent',1.6,1.6,20.8,2,.7)
for i in range(5):box(s,'Speaker'+str(i),'detail',3,43+i*2.4,10.5,1.1,.5)
box(s,'Transport','accent',16,42.8,5.5,11.7,1)
feature(s,'Play','secondary',polygon([(17.4,44.3),(20.3,46),(17.4,47.7)]))
box(s,'Stop','secondary',17.5,50,2.5,2.5,.3)

s=style('ipod','iPod',['#F0EEE5','#656F79','#AFB4B1','#D8D9D2'],'Complete 11 mm click wheel; no raised controls.')
field(s)
dot(s,'Wheel','accent',12,48.8,5.5);dot(s,'WheelVoid','body',12,48.8,3.8);dot(s,'Center','secondary',12,48.8,2.2)
box(s,'Hold','secondary',10,2.5,4,1.4,.6)

for s in STYLES.values():
    s['palette'] = dict(zip(['body','detail','accent','secondary'], s['palette']))

SOURCE_PATHS=['mechanical/revI/Flan36.FCStd','design/revI-frame-profiles.json','design/revI.json']
master=dict(schema='flan36-frame-artwork-master-1', revision='R3', status='PROPOSED_NOT_APPROVED',
 original_request='Exact dimensioned and colored approval designs, then literal transfer to CAD; all eleven frame styles retained.',
 units='mm', origin='Left frame top-left envelope corner', left_xy=[111,11],
 right_transform='KiCad x = 49 - local_x; y = 11 + local_y. CAD uses -KiCad_y.',
 source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
 envelope_mm=[24,56], outer_commands=OUTLINE, aperture_commands=APERTURE,
 aperture_bounds_mm=[4.55,7.35,19.05,38.45],
 common=dict(frame_face_z_mm=13.39, glass_top_z_mm=13.39, pcb_top_z_mm=12.49,
  solder_reserve_top_z_mm=12.99, pin_tip_z_mm=12.79, relief_top_z_mm=12.725,
  relief_bounds_mm=[3.85,4.1,19.75,42], header_cover_bounds_mm=[4.95,38.1,18.65,41.6],
  glass_bounds_mm=[4.95,7.65,18.65,37.95],
  outer_corner_radii_mm=dict(top_left=1.2,top_right=2.4,bottom_right=1.2,bottom_left=1.2)),
 construction=dict(ordinary_inlay_depth_mm=.4, ordinary_backing_mm=.8,
  collar='Color runs through the whole collar thickness: 0.665 mm in A, 0.865 mm in B. Relief stays at Z12.725. No extra recess and no cream gap.',
  xy_domains=dict(face='outer minus aperture',
   relief_commands=rect(3.85,4.1,15.9,37.9),
   header_commands=rect(4.95,38.1,13.7,3.5),
   cover='header intersect face',collar='(relief intersect face) minus cover',ordinary='face minus relief'),
  cover_options=[dict(id='A',face_z_mm=13.39,cover_thickness_mm=.2,underside_z_mm=13.19,nominal_solder_clearance_mm=.2,
    ordinary_inlay_z_mm=[12.99,13.39],ordinary_roof_bottom_z_mm=12.19,minimum_ordinary_backing_mm=.8,
    collar_z_mm=[12.725,13.39],collar_thickness_mm=.665,cover_z_mm=[13.19,13.39],matching_case_top_z_mm=13.39,
    status='Experimental membrane. Print integrity and actual solder envelope unqualified.'),
   dict(id='B',face_z_mm=13.59,cover_thickness_mm=.4,underside_z_mm=13.19,nominal_solder_clearance_mm=.2,
    ordinary_inlay_z_mm=[13.19,13.59],ordinary_roof_bottom_z_mm=12.19,minimum_ordinary_backing_mm=1.0,
    collar_z_mm=[12.725,13.59],collar_thickness_mm=.865,cover_z_mm=[13.19,13.59],matching_case_top_z_mm=13.59,
    status='Thicker roof option adds 0.20 mm to frame face; display is recessed 0.20 mm and matching case height would require approval.')],
  option_b_extent='Raise the whole frame face and matching case top by 0.20 mm. Retain all existing underside cavities and mounting datums. Never raise only the bridge.',
  selected_cover=None, production_ready=False),
 transfer=dict(method='Closed M/L/A/C/Z paths in millimetres. Subtract aperture. Resolve features in listed painter order, last wins. Extrude the resulting color partitions according to the approved Z schedule.',
  forbidden=['Redrawing from raster','Auto-scaling','Auto-repositioning','Clipping a motif to fit a support mask','Changing color values or paths after approval'],
  acceptance='CAD top-face symmetric difference below 0.002 mm2 per stable role (body/detail/accent/secondary), even when HEX values match; bounds within 0.01 mm; no feature disappearance; source digest equal to approved master. Transform full curves for the right half, never only endpoints.'),
 styles=STYLES)
encoded=json.dumps(master,indent=2)+'\n'
(OUT/'master.json').write_text(encoded)
DIGEST=hashlib.sha256(encoded.encode()).hexdigest()


def svgpath(commands, fill, **attrs):
    at=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())
    return f'<path d="{pathdata(commands)}" fill="{fill}" {at}/>'


def drawing(key, display=False):
    s=STYLES[key];p=s['palette']
    result=svgpath(OUTLINE+APERTURE,p['body'],fill_rule='evenodd',id=key+'-body')
    for f in s['features']:
        cmds=f['commands'] + (APERTURE if f['window_cut'] else [])
        result+=svgpath(cmds,p[f['color']],fill_rule='evenodd',id=key+'-'+f['id'])
    if display:
        # The open clearance reveals dark internals, not an ivory material strip.
        result=svgpath(APERTURE,'#20292A')+result
        result+=svgpath(rect(4.95,7.65,13.7,30.3),'#303C3C')
        result+=svgpath(rect(5.7,8.4,12.2,28.8),'#BEC8AD')
        result+='<g fill="#515B47" font-family="monospace" text-anchor="middle" font-size="1.6"><text x="11.8" y="17">BASE</text><text x="11.8" y="23">BLE</text><text x="11.8" y="29">L</text></g>'
        result+=svgpath(OUTLINE,'none',stroke='#A1AAA1',stroke_width='.08')
    return result


def svgdoc(width,height,body,physical=False):
    units='mm' if physical else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}{units}" height="{height}{units}" viewBox="0 0 {width} {height}"><metadata>FLAN36 R3 / master SHA256 {DIGEST} / PROPOSED NOT APPROVED</metadata>{body}</svg>\n'


for key in STYLES:
    (OUT/(key+'.svg')).write_text(svgdoc(24,56,drawing(key),True))


def text(x,y,t,size=17,fill='#233D39',**attrs):
    at=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())
    return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{fill}" {at}>{t}</text>'


def sheet(keys,name):
    cols=4;rows=math.ceil(len(keys)/cols);w=1280;h=150+rows*455
    b=f'<rect width="{w}" height="{h}" fill="#F6F5F0"/>'
    b+=text(40,45,'FLAN36 / EXACT FRAME ARTWORK',27,font_weight='bold')
    b+=text(40,77,'R3 approval proposal · 24 × 56 mm · solid colors · identical display aperture',18)
    b+=text(40,105,'Same paths as the 1:1 SVG files. Pin-cover construction A / B remains to be selected.',15)
    for i,key in enumerate(keys):
        x=40+(i%4)*312;y=140+(i//4)*455;s=STYLES[key]
        b+=text(x,y+5,f'{i+1:02} / {s["label"]}',20,font_weight='bold')
        b+=f'<g transform="translate({x+40},{y+24}) scale(5.4)">{drawing(key,True)}</g>'
        for j,(role,col) in enumerate(s['palette'].items()):
            xx=x+(j%2)*137;yy=y+349+(j//2)*30
            b+=f'<rect x="{xx}" y="{yy-15}" width="18" height="18" rx="3" fill="{col}" stroke="#CACCC4"/>'
            b+=text(xx+25,yy,col,14)
    b+=text(40,h-15,'MASTER '+DIGEST[:16]+' · Screen fill is contextual; the SVG aperture is an actual hole.',13)
    (OUT/name).write_text(svgdoc(w,h,b))


sheet(list(STYLES),'collection.svg')
sheet(['flan','tape','orbit','manga','talavera'],'selected.svg')


def line(x1,y1,x2,y2,color='#70837D',width=1):
    return f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{color}" stroke-width="{width}" fill="none"/>'


def dimension(x1,y1,x2,y2,label,tx,ty):
    b=line(x1,y1,x2,y2)
    for x,y in [(x1,y1),(x2,y2)]:b+=line(x-4,y-4,x+4,y+4)
    return b+text(tx,ty,label,16)


b='<rect width="1300" height="930" fill="#F6F5F0"/>'
b+=text(40,46,'TALAVERA / GEOMETRY FOR APPROVAL',28,font_weight='bold')
b+=text(40,79,'Exact millimetre paths · 24 × 56 mm envelope · no stretched petals',18)
x,y,sc=130,147,11
b+=f'<g transform="translate({x},{y}) scale({sc})">{drawing("talavera",True)}</g>'
b+=dimension(x,y-22,x+24*sc,y-22,'24.00 mm',x+72,y-35)
b+=dimension(x-30,y,x-30,y+56*sc,'56.00',45,y+310)
b+=dimension(x+4.55*sc,y+7.35*sc-10,x+19.05*sc,y+7.35*sc-10,'14.50',x+98,y+7.35*sc-22)
b+=text(465,145,'APERTURE',18,font_weight='bold')
b+=text(465,176,'14.50 × 31.10 mm',22)
b+=text(465,203,'X 4.55–19.05 / Y 7.35–38.45',17)
b+=text(465,230,'Existing rectangular opening preserved.',16)
b+=line(x+19.05*sc,y+20*sc,445,218)
b+=text(465,279,'COBALT TO THE OPENING',18,font_weight='bold')
b+=text(465,308,'No ivory strip between blue and aperture.',17)
b+=text(465,335,'Through-color collar: A 0.665 / B 0.865 mm.',17)
b+=line(x+20.5*sc,y+31*sc,445,322)
b+=text(465,390,'FOUR MIRRORED PETALS',18,font_weight='bold')
b+=text(465,419,'11.60 × 11.60 mm motif envelope',20)
b+=text(465,448,'5.10 mm petal width; unscaled cubic curves.',17)
b+=text(465,477,'Center: X 12.00 / Y 49.00 mm',17)
b+=text(465,506,'Compact square motif fits the real lower space.',17)
b+=line(x+17.8*sc,y+48*sc,445,462)
b+=text(465,558,'SOLID MATERIAL COLORS',18,font_weight='bold')
for i,(label,col) in enumerate([('Ivory','#F1E6CA'),('Cobalt','#244E91'),('Terracotta','#C36443')]):
    yy=590+i*38;b+=f'<rect x="465" y="{yy-18}" width="24" height="24" rx="3" fill="{col}" stroke="#CACCC4"/>'
    b+=text(501,yy,label+'  '+col,18)
b+=text(920,145,'OUTLINE RADII',18,font_weight='bold')
b+=text(920,180,'TL / BL / BR: R1.20',17)
b+=text(920,208,'TR: R2.40',17)
b+=text(920,244,'Taken from existing CAD;',16)
b+=text(920,269,'not symmetrized silently.',16)
b+=text(920,332,'1:1 MASTER',18,font_weight='bold')
b+=text(920,365,'Origin: top-left envelope',16)
b+=text(920,392,'X right / Y down / mm',16)
b+=text(920,438,'Same path coordinates',16)
b+=text(920,465,'feed SVG and future CAD.',16)
b+=text(40,811,'CONSTRUCTION IS NOT YET APPROVED',19,font_weight='bold')
b+=text(40,843,'Pin-cover A: 0.20 mm skin, unchanged face height. B: 0.40 mm skin, face +0.20 mm. See section.svg.',17)
b+=text(40,873,'Both leave 0.20 mm above the nominal solder reserve. Physical solder and print integrity remain unqualified.',17)
b+=text(40,905,'MASTER '+DIGEST[:16]+' · HEX values specify digital colors; filament matching requires physical samples.',14)
(OUT/'talavera-dimensioned.svg').write_text(svgdoc(1300,930,b))

b='<rect width="1280" height="840" fill="#F6F5F0"/>'
b+=text(40,45,'PIN COVER / EXACT NOMINAL SECTION',28,font_weight='bold')
b+=text(40,77,'At the five-contact row · all Z values measured from the case datum · proposal, not a fit qualification',17)
for i,opt in enumerate(master['construction']['cover_options']):
    x=55+i*625;y=310;scale=155
    zz=lambda z:y+(13.7-z)*scale
    b+=text(x,135,f'OPTION {opt["id"]}',23,font_weight='bold')
    b+=text(x,166,'Unchanged height / thin membrane' if i==0 else '+0.20 mm face / thicker cover',19)
    b+=f'<rect x="{x+15}" y="{zz(opt["face_z_mm"])}" width="330" height="{opt["cover_thickness_mm"]*scale}" fill="#244E91"/>'
    b+=f'<rect x="{x+15}" y="{zz(12.49)}" width="330" height="{scale*.5}" fill="#628975"/>'
    for dx in [38,101,164,227,290]:
        b+=f'<rect x="{x+dx}" y="{zz(12.99)}" width="32" height="{.5*scale}" fill="#A9AFB1"/>'
    b+=line(x+15,zz(13.39),x+370,zz(13.39),'#B66A47')
    b+=text(x+365,zz(opt['face_z_mm'])+5,f'Z {opt["face_z_mm"]:.2f}',16)
    b+=text(x+365,zz(13.19)+5,'Z 13.19',16)
    b+=text(x+365,zz(12.99)+5,'Z 12.99',16)
    b+=text(x+365,zz(12.49)+5,'Z 12.49',16)
    b+=text(x,235,f'Cover {opt["cover_thickness_mm"]:.2f} mm + nominal gap 0.20 mm',18)
    b+=text(x,262,'Glass top stays at Z 13.39 mm.',17)
    b+=text(x,610,'Blue: cover / gray: solder reserve / green: PCB',15)
    b+=text(x,640,'Illustrated solder shapes are an envelope, not measured joints.',14)
b+=text(40,704,'COMMON XY: header well X 4.95–18.65 / Y 38.10–41.60 mm. Aperture subtraction removes Y &lt; 38.45.',17)
b+=text(40,738,'A is an experimental thin skin. B changes frame height and needs the matching case adjustment to stay level.',17)
b+=text(40,772,'Neither option changes the battery/MCU/display positions. No cover has been selected or implemented.',17)
b+=text(40,813,'MASTER '+DIGEST[:16]+' · Drawing vertical scale is 155 px/mm; horizontal schematic is not a clearance model.',14)
(OUT/'section.svg').write_text(svgdoc(1280,840,b))
print('Prepared',len(STYLES),'exact 2D master proposals;',DIGEST)
