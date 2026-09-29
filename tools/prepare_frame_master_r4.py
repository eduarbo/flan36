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
OUT = ROOT / 'design/proposals/frame-master-r4'
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
APERTURE = rect(4.75, 7.35, 14.5, 31.1)
BEZEL_WIDTH = 2.4
BEZEL_BOUNDS = [2.35,4.95,21.65,40.85]
STYLES = {}


def style(key, label, palette, note):
    s = dict(label=label, palette=palette, note=note, features=[])
    STYLES[key] = s
    return s


def feature(s, name, color, commands, window_cut=False):
    s['features'].append(dict(id=name, color=color, commands=commands, window_cut=window_cut))


def field(s, color='detail'):
    # Exact outward offset of the aperture, including radius = offset at its
    # square corners. The frame envelope is not used to size the bezel.
    feature(s, 'ScreenField', color, rect(2.35,4.95,19.3,35.9,BEZEL_WIDTH), True)


def box(s, name, color, x, y, w, h, r=0):
    feature(s, name, color, rect(x, y, w, h, r))


def dot(s, name, color, x, y, r):
    feature(s, name, color, circle(x, y, r))


def cross(s, x, y, color, size=7.2, arm=2.4):
    a=(size-arm)/2
    feature(s, 'Dpad', color, polygon([(x+a,y),(x+a+arm,y),(x+a+arm,y+a),
      (x+size,y+a),(x+size,y+a+arm),(x+a+arm,y+a+arm),(x+a+arm,y+size),
      (x+a,y+size),(x+a,y+a+arm),(x,y+a+arm),(x,y+a),(x+a,y+a)]))


s=style('flan','Flan',['#F2DFAF','#68422F','#B96732','#DFAB50'],'Uniform caramel bezel, separate glaze header and centered dessert seal.')
field(s,'accent')
box(s,'GlazeHeader','detail',6,1.6,12,1.4,.7)
box(s,'DessertSeal','accent',5.1,42.85,13.8,11.8,3.4)
feature(s,'Custard','secondary',polygon([(9.1,46.15),(14.9,46.15),(16.2,50.75),(7.8,50.75)]))
box(s,'Glaze','detail',8.8,44.95,6.4,1.2,.5)
box(s,'Saucer','detail',7.2,52,9.6,1,.5)

s=style('tape','Tape',['#D2CEC1','#303738','#E27136','#F0E9D6'],'Uniform graphite bezel, separate orange header, two reels and three even slats.')
field(s)
feature(s,'Diagonal','accent',polygon([(15.5,1.35),(17.7,1.35),(20.1,3.75),(17.9,3.75)]))
box(s,'ReelBridge','detail',6,44.6,12,1.8)
dot(s,'LeftReel','secondary',6,45.5,2.5);dot(s,'RightReel','secondary',18,45.5,2.5)
dot(s,'LeftHub','detail',6,45.5,1);dot(s,'RightHub','detail',18,45.5,1)
for i in range(3):box(s,'Slat'+str(i),'detail',4.5,49.95+i*1.9,15,1,.5)

s=style('orbit','Orbit',['#EEE5CD','#315C4E','#DF7339','#EEE5CD'],'Uniform forest bezel and a separate crescent panel with a nested ivory disc.')
field(s)
box(s,'ForestPanel','detail',2.35,42.05,19.3,12.75,2.4)
feature(s,'Crescent','accent',[['M',4.1,44],['C',4.1,49,6.2,53.3,10.6,53.6],
 ['C',15.2,54.2,18.8,52.9,20.3,48],['L',20.3,44.8],
 ['C',18.1,50.4,16.2,51.4,13.8,50.9],['C',11.8,50.4,12.7,45.1,9.6,45.1],
 ['C',6.3,45.1,7.4,49,5.8,47.9],['C',4.8,47,4.3,45.4,4.1,44],['Z']])
dot(s,'IvoryDisc','secondary',9.6,48.8,2.4)

s=style('manga','Manga',['#F0EADB','#27282E','#DA453D','#F0EADB'],'Uniform ink bezel; separated diagonals, an even four-dot grid and red corner.')
field(s)
feature(s,'HeaderSlash','detail',polygon([(15.5,1.35),(17.7,1.35),(20.1,3.75),(17.9,3.75)]))
feature(s,'DiagonalPanel','detail',polygon([(2.35,42.05),(6.05,42.05),(21.65,47.2),(21.65,48.6)]))
for i,(x,y) in enumerate([(5.7,47.5),(10.7,47.5),(5.7,52.1),(10.7,52.1)]):dot(s,'PanelDot'+str(i),'detail',x,y,1.6)
feature(s,'RedCorner','accent',polygon([(16,49.25),(21.65,51.1),(21.65,54.6),(16,54.6)]))

s=style('talavera','Talavera',['#F1E6CA','#244E91','#C36443','#244E91'],'Exactly 2.40 mm cobalt bezel; centered aperture and a 12.40 mm square mirrored flower.')
field(s)
petal=[['M',5.8,42.4],['C',9.45,42.4,11.3,44.32,11.3,46.03],
 ['C',11.3,48.92,5.8,49.88,5.8,42.4],['Z']]
for i,(mx,my) in enumerate([(False,False),(True,False),(False,True),(True,True)]):
    cmds=[]
    for c in petal:
        op,*v=c
        for n in range(0,len(v),2):
            if mx:v[n]=24-v[n]
            if my:v[n+1]=97.2-v[n+1]
        cmds.append([op,*v])
    feature(s,'Petal'+str(i),'secondary',cmds)
feature(s,'TerracottaStar','accent',[['M',12,47.2],['C',12.35,47.95,12.65,48.25,13.4,48.6],
 ['C',12.65,48.95,12.35,49.25,12,50],['C',11.65,49.25,11.35,48.95,10.6,48.6],
 ['C',11.35,48.25,11.65,47.95,12,47.2],['Z']])

s=style('gameboy','Game Boy',['#DCD6BA','#42454D','#973C60','#A6A392'],'Uniform graphite bezel, berry buttons and three wider diagonal speaker marks.')
field(s);cross(s,2.8,42.85,'detail')
dot(s,'A','accent',19.2,44.7,1.9);dot(s,'B','accent',15.5,47.9,1.9)
box(s,'Select','secondary',3.5,52.45,4.7,1.2,.6)
for i in range(3):feature(s,'Speaker'+str(i),'secondary',polygon([(13.3+i*2.55,51.5),(14.4+i*2.55,51.5),(15.5+i*2.55,54.5),(14.4+i*2.55,54.5)]))

s=style('nes','NES',['#C6C7BE','#32363B','#C94B3E','#8A8D8D'],'Aligned graphite bezel and controller deck with balanced button spacing.')
field(s);box(s,'Deck','detail',2.35,42.05,19.3,10,.8);cross(s,3.55,43.75,'secondary',6.4,2.2)
dot(s,'A','accent',18.65,47.7,1.8);dot(s,'B','accent',14.15,47.7,1.8)
box(s,'Signature','accent',13.15,53.4,8.5,1.2,.3)
box(s,'Header','secondary',2.35,2,10,1.2,.6)

s=style('snes','SNES',['#D1D0C9','#464751','#746198','#ACA0C2'],'Uniform bezel, equal header capsules and a regular lavender button diamond.')
field(s);cross(s,2.7,43.3,'detail',6.6,2.2)
for name,c,x,y in [('A','accent',19.8,47.8),('B','accent',16.5,51.1),('X','secondary',16.5,44.5),('Y','secondary',13.2,47.8)]:dot(s,name,c,x,y,1.7)
box(s,'Power','accent',3.8,1.8,6.4,1.4,.7);box(s,'Reset','secondary',13.8,1.8,6.4,1.4,.7)
box(s,'Select','secondary',3.8,52.7,6.4,1.2,.6)

s=style('phone','2000s Phone',['#263C55','#B8BBB5','#87AD67','#455469'],'Centered earpiece, uniform silver bezel, regular keypad and balanced navigation keys.')
field(s);box(s,'Earpiece','detail',8,1.8,8,1.2,.6)
box(s,'Nav','secondary',9.4,42.2,5.2,2.2,1.1)
box(s,'Call','accent',3.15,42.2,4.4,2.2,1.1);box(s,'End','detail',16.45,42.2,4.4,2.2,1.1)
for r in range(3):
    for c in range(3):box(s,f'Key{r}{c}','detail',3.6+c*6.2,45.7+r*3.1,4.4,2.1,.8)

s=style('walkman','Walkman',['#275273','#192D3B','#E4B54B','#ACBCC0'],'Uniform dark bezel, aligned yellow header, five equally spaced speaker marks.')
field(s);box(s,'Header','accent',2.35,1.6,19.3,1.8,.8)
for i in range(5):box(s,'Speaker'+str(i),'detail',2.35,42.75+i*2.4,10.5,1.2,.6)
box(s,'Transport','accent',16.15,42.2,5.5,12.3,1)
feature(s,'Play','secondary',polygon([(17.55,44),(20.45,45.7),(17.55,47.4)]))
box(s,'Stop','secondary',17.65,50,2.5,2.5,.4)

s=style('ipod','iPod',['#F0EEE5','#656F79','#AFB4B1','#D8D9D2'],'Uniform screen surround and concentric 11 mm click wheel on the frame centerline.')
field(s);dot(s,'Wheel','accent',12,48.6,5.5);dot(s,'WheelVoid','body',12,48.6,3.8);dot(s,'Center','secondary',12,48.6,2.2)
box(s,'Hold','secondary',9.6,1.8,4.8,1.2,.6)

for s in STYLES.values():
    s['palette'] = dict(zip(['body','detail','accent','secondary'], s['palette']))

SOURCE_PATHS=['mechanical/revI/Flan36.FCStd','design/revI-frame-profiles.json','design/revI.json']
master=dict(schema='flan36-frame-artwork-master-1', revision='R4', status='PROPOSED_NOT_APPROVED',
 original_request='Exact dimensioned and colored approval designs, then literal transfer to CAD; all eleven frame styles retained.',
 units='mm', origin='Left frame top-left envelope corner', left_xy=[111,11],
 right_transform='KiCad x = 49 - local_x; y = 11 + local_y. CAD uses -KiCad_y.',
 source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
 envelope_mm=[24,56], outer_commands=OUTLINE, aperture_commands=APERTURE,
 aperture_bounds_mm=[4.75,7.35,19.25,38.45],
 native_baseline=dict(aperture_bounds_mm=[4.55,7.35,19.05,38.45],frame_face_z_mm=13.39),
 bezel=dict(width_mm=2.4,outer_bounds_mm=BEZEL_BOUNDS,outer_radius_mm=2.4,
  definition='Exact outward Euclidean offset of the rectangular aperture. Four straight widths and corner normal distances are 2.40 mm.',
  exterior_side_margins_mm=[2.35,2.35],screen_center_x_mm=12),
 alignment_change=dict(status='PROPOSED_NOT_IMPLEMENTED',left_display_header_translation_mm=[.2,0,0],
  right_display_header_translation_mm=[-.2,0,0],
  coupled_parts=['Display module and glass','Complete male/female connectors: housings, spacers, contacts and solder reserves','Display relief and header service well','Display header PCB footprint'],
  fixed_parts=['MCU','Battery','Frame envelope','Mounting datums'],
  reason='Center the display and bezel on X12.00 while preserving glass and connector clearances.',
  acceptance='Adopt only with the artwork. Translate the complete display mating chain; verify PCB routes and complete assembly clearances before release.'),
 printing_target=dict(nozzle_diameter_mm=.4,layer_height_mm=.2,cover_layers_nominal=2,
  frame_orientation='Colored face down; cover thickness is measured from that bed-facing surface.',
  status='DESIGN_TARGET_NOT_SLICED_OR_PRINT_QUALIFIED',
  limitations='Nozzle diameter is not extrusion width or layer height. Raising the face does not qualify all case walls, tapered artwork tips, clearances or supports.'),
 common=dict(frame_face_z_mm=13.59,glass_top_z_mm=13.39,pcb_top_z_mm=12.49,pcb_bottom_z_mm=11.49,
  solder_reserve_top_z_mm=12.99,pin_tip_z_mm=12.79,relief_top_z_mm=12.725,
  relief_bounds_mm=[4.05,4.1,19.95,42],header_cover_bounds_mm=[5.15,38.1,18.85,41.6],
  glass_bounds_mm=[5.15,7.65,18.85,37.95],
  outer_corner_radii_mm=dict(top_left=1.2,top_right=2.4,bottom_right=1.2,bottom_left=1.2)),
 construction=dict(ordinary_inlay_depth_mm=.4,ordinary_backing_mm=1.0,
  collar='Color runs through the 0.865 mm collar. Relief remains at Z12.725. No extra recess or cream gap.',
  xy_domains=dict(face='outer minus aperture',
   relief_commands=rect(4.05,4.1,15.9,37.9),header_commands=rect(5.15,38.1,13.7,3.5),
   cover='header intersect face',collar='(relief intersect face) minus cover',ordinary='face minus relief'),
  cover_options=[dict(id='B',face_z_mm=13.59,cover_thickness_mm=.4,underside_z_mm=13.19,nominal_solder_clearance_mm=.2,
    ordinary_inlay_z_mm=[13.19,13.59],ordinary_roof_bottom_z_mm=12.19,minimum_ordinary_backing_mm=1.0,
    collar_z_mm=[12.725,13.59],collar_thickness_mm=.865,cover_z_mm=[13.19,13.59],matching_case_top_z_mm=13.59,
    status='SELECTED_BY_USER; construction remains unimplemented and physically unqualified.')],
  option_b_extent='Raise the whole frame face and matching case top by 0.20 mm. Retain underside Z datums. Apply the separate proposed display-chain XY translation explicitly.',
  selected_cover='B',selection_authority='User requested case +0.20 mm for the 0.40 mm cover and a 0.40 mm nozzle target.',production_ready=False),
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
        result+=svgpath(rect(5.15,7.65,13.7,30.3),'#303C3C')
        result+=svgpath(rect(5.9,8.4,12.2,28.8),'#BEC8AD')
        result+='<g fill="#515B47" font-family="monospace" text-anchor="middle" font-size="1.6"><text x="12" y="17">BASE</text><text x="12" y="23">BLE</text><text x="12" y="29">L</text></g>'
        result+=svgpath(OUTLINE,'none',stroke='#A1AAA1',stroke_width='.08')
    return result


def svgdoc(width,height,body,physical=False):
    units='mm' if physical else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}{units}" height="{height}{units}" viewBox="0 0 {width} {height}"><metadata>FLAN36 R4 / master SHA256 {DIGEST} / PROPOSED NOT APPROVED</metadata>{body}</svg>\n'


for key in STYLES:
    (OUT/(key+'.svg')).write_text(svgdoc(24,56,drawing(key),True))


def text(x,y,t,size=17,fill='#233D39',**attrs):
    at=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())
    return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{fill}" {at}>{t}</text>'


def sheet(keys,name):
    cols=4;rows=math.ceil(len(keys)/cols);w=1280;h=150+rows*455
    b=f'<rect width="{w}" height="{h}" fill="#F6F5F0"/>'
    b+=text(40,45,'FLAN36 / EXACT FRAME ARTWORK',27,font_weight='bold')
    b+=text(40,77,'R4 approval proposal · 24 × 56 mm · solid colors · identical display aperture',18)
    b+=text(40,105,'2.40 mm uniform bezels · selected +0.20 mm face · proposed display centering +0.20 mm',15)
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


b='<rect width="1300" height="940" fill="#F6F5F0"/>'
b+=text(40,46,'TALAVERA / UNIFORM BEZEL',28,font_weight='bold')
b+=text(40,79,'R4 · exact paths and solid colors · approval drawing',18)
x,y,sc=130,147,11
b+=f'<g transform="translate({x},{y}) scale({sc})">{drawing("talavera",True)}</g>'
b+=dimension(x,y-22,x+24*sc,y-22,'24.00 mm',x+72,y-35)
b+=dimension(x-30,y,x-30,y+56*sc,'56.00',45,y+310)
# Four identical side dimensions; no artwork-dependent bezel sizing.
for xa,ya,xb,yb,tx,ty in [(2.35,23,4.75,23,-4.5,23),(19.25,23,21.65,23,24.5,23),
 (12,4.95,12,7.35,14,6.5),(12,38.45,12,40.85,14,40.7)]:
 b+=dimension(x+xa*sc,y+ya*sc,x+xb*sc,y+yb*sc,'2.40',x+tx*sc,y+ty*sc)
b+=text(465,150,'2.40 mm ON ALL FOUR SIDES',23,font_weight='bold')
b+=text(465,184,'Outer bezel: 19.30 × 35.90 mm / R2.40',18)
b+=text(465,215,'Aperture: 14.50 × 31.10 mm / square corners',18)
b+=text(465,246,'Exact outward offset, including the rounded corners.',17)
b+=text(465,292,'CENTERED DISPLAY — PROPOSED CHANGE',18,font_weight='bold')
b+=text(465,325,'Center X12.00; exterior side margins 2.35 / 2.35 mm.',17)
b+=text(465,356,'Aperture X4.75–19.25 / Y7.35–38.45 mm.',17)
b+=text(465,387,'Move display, contacts, relief and PCB header +0.20 mm X.',17)
b+=text(465,418,'Mirror on the right. Battery and MCU stay in place.',17)
b+=text(465,464,'BALANCED FLOWER',18,font_weight='bold')
b+=text(465,497,'12.40 × 12.40 mm · center X12.00 / Y48.60',18)
b+=text(465,528,'Four mirrored cubic petals, with a centered terracotta star.',17)
b+=text(465,574,'SOLID COLORS / FLUSH SURFACE',18,font_weight='bold')
for i,(label,col) in enumerate([('Ivory','#F1E6CA'),('Cobalt','#244E91'),('Terracotta','#C36443')]):
 yy=610+i*38;b+=f'<rect x="465" y="{yy-18}" width="24" height="24" rx="3" fill="{col}" stroke="#CACCC4"/>'
 b+=text(501,yy,label+'  '+col,18)
b+=text(40,802,'SELECTED: WHOLE FRAME AND MATCHING CASE FACE +0.20 mm',20,font_weight='bold')
b+=text(40,835,'Face Z13.59 · glass Z13.39 · cover 0.40 mm · nominal solder gap 0.20 mm · collar 0.865 mm',17)
b+=text(40,865,'Existing shell corners retained: TL / BL / BR R1.20, TR R2.40. Bezel has its own constant-offset corners.',16)
b+=text(40,893,'Artwork and display centering await approval. Full CAD, PCB and 0.40 mm-nozzle slicing are still pending.',16)
b+=text(40,924,'MASTER '+DIGEST[:16]+' · HEX colors are digital targets; physical filament matching needs samples.',13)
(OUT/'talavera-dimensioned.svg').write_text(svgdoc(1300,940,b))

b='<rect width="1280" height="810" fill="#F6F5F0"/>'
b+=text(40,45,'SELECTED CONSTRUCTION / +0.20 mm FACE',28,font_weight='bold')
b+=text(40,78,'0.40 mm cover · 0.20 mm nominal solder clearance · no raised artwork',18)
x,y,scale=70,190,160
zz=lambda z:y+(13.7-z)*scale
b+=f'<rect x="{x}" y="{zz(13.59)}" width="420" height="{.4*scale}" fill="#244E91"/>'
b+=f'<rect x="{x}" y="{zz(12.49)}" width="420" height="{1.0*scale}" fill="#628975"/>'
for dx in [35,110,185,260,335]:
 b+=f'<rect x="{x+dx}" y="{zz(12.99)}" width="45" height="{.5*scale}" fill="#A9AFB1"/>'
b+=line(x,zz(13.39),x+450,zz(13.39),'#B66A47')
for z,label in [(13.59,'Face / case Z13.59'),(13.19,'Cover underside Z13.19'),(12.99,'Solder reserve Z12.99'),(12.49,'Display PCB top Z12.49'),(11.49,'Display PCB bottom Z11.49')]:
 b+=text(x+470,zz(z)+5,label,17)
b+=text(70,590,'Blue: cover. Gray: nominal solder reserve. Green: display PCB.',17)
b+=text(70,620,'The line through the cover marks glass top Z13.39 (0.20 mm below the new face).',17)
b+=text(70,661,'PRINT TARGET: 0.40 mm nozzle / 0.20 mm layers / colored frame face down.',19,font_weight='bold')
b+=text(70,695,'The cover spans two nominal layers. Nozzle size controls XY extrusion; layer height controls Z.',17)
b+=text(70,726,'This does not certify every wall or tapered motif. Final solids still require slicing and a fit coupon.',17)
b+=text(40,785,'MASTER '+DIGEST[:16]+' · Z scale 160 px/mm; horizontal section schematic, not an assembly-clearance test.',13)
(OUT/'section.svg').write_text(svgdoc(1280,810,b))
print('Prepared',len(STYLES),'exact 2D master proposals;',DIGEST)
