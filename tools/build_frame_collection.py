#!/usr/bin/env python3
"""Generate reference-bound, solid-color native frame recipes in left KiCad XY.
The PCB relief is NOT decorative space: preserve complete motifs outside it.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
styles={}
def box(id,role,xy,r=0):return dict(id=id,role=role,kind='roundrect' if r else 'box',xy=xy,**({'radius_mm':r} if r else {}))
def disc(id,role,x,y,r):return dict(id=id,role=role,kind='disc',xy=[x,y],radius_mm=r)
def ring(id,role,x,y,r,w):return dict(id=id,role=role,kind='ring',xy=[x,y],radius_mm=r,width_mm=w)
def poly(id,role,p):return dict(id=id,role=role,kind='polygon',points=p)
def path(id,role,c):return dict(id=id,role=role,kind='path',commands=c)
def stroke(id,role,p,w=1):return dict(id=id,role=role,kind='stroke',points=p,width_mm=w)
def field(bottom=54.1,role='detail'):
    # Explicit hole surrounds BOTH glass and header access, and the thin PCB
    # collar. It is authored this way; the support mask must remove zero volume.
    return dict(id='ScreenField',role=role,kind='roundrect_ring',xy=[112.2,12.2,133.8,bottom],radius_mm=1.1,inner_xy=[114.45,14.65,131.15,53.25],inner_radius_mm=.3)
def add(id,label,description,colors,labels,features,reference=None,signature=None):
    for f in features:f['id']+='R2'
    styles[id]=dict(label=label,description=description,colors=dict(zip(['body','detail','accent','secondary'],colors)),labels=dict(zip(['body','detail','accent','secondary'],labels)),features=features)
    if reference:styles[id]['reference']=dict(path='design/references/frame-concepts/'+reference+'.png',signature=signature)
# Flan keeps the caramel concept's flowing edge in solid, flush colors.
add('flan','Flan','A caramel sweep, custard shell and rounded dessert medallion.',
 ['#f2dfaf','#68422f','#b96732','#dfab50'],['Custard','Cocoa','Caramel','Golden custard'],[
 path('CaramelFlow','accent',[
 ['M',112.35,12.4],['L',132.8,12.4],['C',132.6,14.3,129,14.3,124,14.3],['L',114.15,14.3],
 ['C',113.8,24,113.9,39,114.1,50],['C',114.2,56,117.4,59.5,117.8,60.6],['L',116.3,61.4],
 ['C',112.5,58,112.35,51,112.35,43],['Z']]),
 box('Medallion','accent',[118.5,56.1,132.4,65.4],3),
 poly('Dessert','secondary',[[122,58.3],[128,58.3],[129.1,62.8],[120.9,62.8]]),
 box('Glaze','detail',[121.7,57.6,128.3,58.7],.5),box('Saucer','detail',[120.3,63.6,129.7,64.5],.4)],
 'caramel',['Flowing caramel edge','Rounded lower medallion','Flat solid-color interpretation'])
styles['flan']['priority']=['detail','secondary','accent']
add('tape','Tape','Diagonal orange corner, dark screen field, twin reels and three lower slats.',
 ['#d2cec1','#303738','#e27136','#f0e9d6'],['Shell','Tape window','Transport orange','Reels'],[
 field(),poly('DiagonalStripe','accent',[[126.2,12.3],[128.4,12.3],[130.35,14.3],[128.15,14.3]]),
 box('ScreenStripe','accent',[112.5,53.7,133.5,55.0],.3),
 box('ReelBridge','detail',[117,57.4,129,59.1]),
 disc('ReelLeft','secondary',117,58.25,2.25),disc('ReelRight','secondary',129,58.25,2.25),
 *[disc('ReelHub'+str(i),'detail',x,58.25,.9) for i,x in enumerate([117,129])],
 *[box('Slat'+str(i),'detail',[115,61.8+i*1.55,131,62.65+i*1.55],.4) for i in range(3)]],
 'tape',['Diagonal upper orange stripe','Continuous dark screen field','Orange screen foot','Two separated reels with dark bridge','Three lower slats'])
# Dark reel cores sit above the pale discs, rather than being swallowed by them.
styles['tape']['priority']=['accent','detail','secondary']
# The dark bridge needs explicit circular ends so it does not cover the reels.
styles['tape']['features'][3]=box('ReelBridgeR2','detail',[119.2,57.8,126.8,58.7])
add('orbit','Orbit','A broad forest field, asymmetric orange sweep and integrated ivory disc.',
 ['#eee5cd','#315c4e','#df7339','#eee5cd'],['Ivory','Forest','Orange sweep','Ivory disc'],[
 field(65.8),path('Crescent','accent',[
 ['M',112.45,32.5],['C',112.5,44,112.9,50.9,114.15,54.5],
 ['C',116.5,62.9,121.1,66.1,128,64.1],['C',130.2,63.6,132.5,62.5,133.5,61.1],
 ['L',133.5,55.8],['C',131.6,59.8,129.1,61.1,126.7,60.7],
 ['C',125.6,60.5,125.9,56.5,122.5,56.5],['C',119.4,56.5,119.6,59.5,117.8,57.5],
 ['C',113.5,54.5,113.2,48.4,112.45,32.5],['Z']]),disc('IvoryDisc','secondary',122.8,60.4,2.6)],
 'orbit',['Dominant forest field','Continuous asymmetric orange crescent','Ivory disc nested into sweep'])
styles['orbit']['priority']=['secondary','accent','detail']
add('manga','Manga','Broad ink panels, ivory diagonals, four lower circles and a red corner.',
 ['#f0eadb','#27282e','#da453d','#f0eadb'],['Paper','Ink','Vermilion','Paper gutters'],[
 field(54.8),poly('TopGutter','secondary',[[128.2,12.3],[130.0,12.3],[133.5,15.8],[133.5,17.6]]),
 poly('DiagonalPanel','detail',[[112.4,54.9],[115.5,54.9],[133.6,60.2],[133.6,61.8]]),
 *[disc('PanelDot'+str(i),'detail',x,y,1.55) for i,(x,y) in enumerate([(116,59.9),(121.0,59.9),(116,64.1),(121,64.1)])],
 poly('RedCorner','accent',[[127.4,61.95],[133.5,64],[133.5,65.8],[127.4,65.8]])],
 'manga',['Broad ink screen field','Ivory diagonal gutters','Four black circles in a two-by-two grid','Red lower-right panel'])
# Four native cubic teardrops in quadrants, not cardinal circles.
petal=[['M',113,55.1],['C',118.5,55.1,121.5,56.5,121.5,58.3],['C',121.5,61.0,113,60.4,113,55.1],['Z']]
def mirror_commands(commands,mx=False,my=False):
    out=[]
    for command in commands:
        op,*values=command
        for i in range(0,len(values),2):
            if mx:values[i]=246-values[i]
            if my:values[i+1]=120.8-values[i+1]
        out.append([op,*values])
    return out
add('talavera','Talavera','Cobalt teardrop petals in four quadrants around a concave terracotta star.',
 ['#f1e6ca','#244e91','#c36443','#244e91'],['Ivory glaze','Cobalt border','Terracotta','Cobalt petals'],[
 field(),*[path('Petal'+str(i),'secondary',mirror_commands(petal,mx,my)) for i,(mx,my) in enumerate([(False,False),(True,False),(False,True),(True,True)])],
 path('TerracottaStar','accent',[
 ['M',123,58.7],['C',123.45,59.6,123.8,59.95,124.75,60.4],
 ['C',123.8,60.85,123.45,61.2,123,62.1],['C',122.55,61.2,122.2,60.85,121.25,60.4],
 ['C',122.2,59.95,122.55,59.6,123,58.7],['Z']])],
 'talavera',['Continuous cobalt screen field','Four teardrop petals in quadrants','Concave terracotta center','Ivory negative space'])
add('gameboy','Game Boy','Pocket-console bezel, cross pad and two berry-colored buttons.',
 ['#dcd6ba','#42454d','#973c60','#a6a392'],['Warm shell','Graphite','Berry buttons','Speaker'],[
 field(),box('DpadH','detail',[113.5,57.0,120.7,59.2]),box('DpadV','detail',[116,54.5,118.2,61.7]),
 disc('A','accent',130.1,56.3,1.8),disc('B','accent',126.7,59.2,1.8),
 *[stroke('Speaker'+str(i),'secondary',[[124+i*2.5,63.3],[125+i*2.5,65.3]],.9) for i in range(4)],box('Start','secondary',[114.2,64,119,65],.5)])
add('nes','NES','A restrained controller strip with red action buttons.',
 ['#c6c7be','#32363b','#c94b3e','#8a8d8d'],['Console gray','Controller black','Action red','Mid gray'],[
 field(),box('Deck','detail',[112.5,54.1,133.5,63],.8),
 box('DpadH','secondary',[114,57.2,120.5,59.2]),box('DpadV','secondary',[116.3,54.9,118.3,61.4]),
 disc('A','accent',130.5,58.7,1.8),disc('B','accent',126,58.7,1.8),box('Header','secondary',[113,12.8,127,13.8],.3),box('Signature','accent',[125,64.6,132.7,65.7])])
add('snes','SNES','A soft gray console with two lavender button tones.',
 ['#d1d0c9','#464751','#746198','#aca0c2'],['Console gray','Graphite','Deep lavender','Lilac'],[
 field(),box('DpadH','detail',[113.5,57.2,120.1,59.2]),box('DpadV','detail',[115.8,54.9,117.8,61.5]),
 disc('A','accent',131,59.35,1.65),disc('B','accent',127.8,62.55,1.65),disc('X','secondary',127.8,56.15,1.65),disc('Y','secondary',124.6,59.35,1.65),
 box('Power','accent',[114,12.7,121,14.1],.7),box('Reset','secondary',[124,12.7,131,14.1],.7),box('Select','secondary',[115,64.7,123,65.9],.6)])
add('phone','2000s Phone','Navy faceplate, silver keypad and green call key.',
 ['#263c55','#b8bbb5','#87ad67','#455469'],['Navy shell','Silver keys','Call green','Navigation'],[
 field(),box('Earpiece','detail',[119,12.7,127,14.0],.6),box('Nav','secondary',[120,54.8,126,57.2],1.2),
 box('Call','accent',[113.7,54.8,118.5,57],1),box('End','detail',[127.5,54.8,132.3,57],1),
 *[box('Key'+str(r)+str(c),'detail',[114+c*6.3,58.2+r*2.9,118.2+c*6.3,60.2+r*2.9],.8) for r in range(3) for c in range(3)]])
add('walkman','Walkman','Cobalt portable audio, yellow controls and speaker bars.',
 ['#275273','#192d3b','#e4b54b','#acbcc0'],['Cobalt','Tape door','Transport yellow','Silver'],[
 field(),box('Header','accent',[112.4,12.4,133.6,14.4],.8),
 *[box('Speaker'+str(i),'detail',[114,54.8+i*2.2,124.5,55.8+i*2.2],.5) for i in range(5)],
 box('ControlStrip','accent',[127,54.7,132.5,65.9],1),poly('Play','secondary',[[128.3,56.3],[131.4,57.9],[128.3,59.5]]),box('Stop','secondary',[128.5,61.7,131,64.2],.4)])
styles['walkman']['priority']=['secondary','accent','detail']
add('ipod','iPod','White face, a complete silver click wheel and a continuous screen border.',
 ['#f0eee5','#656f79','#afb4b1','#d8d9d2'],['White shell','Screen gray','Wheel ring','Center key'],[
 field(),ring('Wheel','accent',123,60.4,5.5,1.8),disc('Center','secondary',123,60.4,2.2),box('Hold','secondary',[121,12.8,125,14.2],.6)])
spec=dict(schema='flan36-frame-collection-1',revision='I',description='Reference-bound compositions with explicit openings. Every authored motif must survive the support mask intact.',roles=['body','detail','accent','secondary'],decoration_mode='flush-co-print',inlay_depth_mm=.4,minimum_backing_mm=.8,minimum_nominal_stroke_mm=.85,mirror_sum_x_mm=160,default_style='flan',strict_feature_containment=True,unsupported_collar_xy_mm=[114.85,15.1,130.75,53.0],retired_styles=['smooth','bevel','facet','handheld','tv','cyberpunk','cartridge','arcade','mecha','kintsugi'],styles=styles)
current=json.loads((ROOT/'design/frame-finishes.json').read_text())
if any(t.get('approved_master') for t in current['styles'].values()):
 raise SystemExit('Approved artwork is installed. Use install_approved_frames.py and the exact master; this legacy generator would overwrite it.')
(ROOT/'design/frame-finishes.json').write_text(json.dumps(spec,indent=2)+'\n')
print('Generated',len(styles),'reference-bound frame recipes')
