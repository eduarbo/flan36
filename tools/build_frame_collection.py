#!/usr/bin/env python3
"""Generate the eleven solid-color frame recipes. Coordinates are mm in left KiCad XY.
This updates only the canonical design specification; CAD installation is separate.
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
def stroke(id,role,p,w=1):return dict(id=id,role=role,kind='stroke',points=p,width_mm=w)
def bezel(r=2):return box('ScreenBorder','detail',[113.6,16.5,132,51.2],r)
def add(id,label,description,colors,labels,features):
    styles[id]=dict(label=label,description=description,colors=dict(zip(['body','detail','accent','secondary'],colors)),labels=dict(zip(['body','detail','accent','secondary'],labels)),features=features)
add('flan','Flan','Custard shell, cocoa window and a broad caramel drip. The signature default.',
 ['#f2dfaf','#68422f','#b96732','#dfab50'],['Custard','Cocoa','Caramel','Golden custard'],[
 bezel(),box('CaramelCrown','accent',[111,11,135,15.5]),box('CaramelDrip','accent',[111.8,13.5,114.3,25.5],1.2),
 poly('Dessert','secondary',[[118,55],[128,55],[130,62],[116,62]]),box('Glaze','accent',[117.8,54,128.2,56.2],1),box('Saucer','detail',[114.8,63.3,131.2,64.5],.6)])
add('tape','Tape','Cassette window, two reels and an orange transport stripe.',
 ['#d2cec1','#303738','#e27136','#f0e9d6'],['Shell','Tape window','Transport orange','Reels'],[
 bezel(),box('Stripe','accent',[112,12.4,134,15],.5),box('Cassette','detail',[113.3,52.5,132.7,61.3],1.8),
 ring('ReelL','secondary',118.2,56.8,2.65,1.1),ring('ReelR','secondary',127.8,56.8,2.65,1.1),box('Tape','secondary',[120.6,56.25,125.4,57.35]),
 box('Transport','accent',[113.5,63,124.5,64.5],.7),poly('Play','secondary',[[128,62.5],[131.5,64],[128,65.5]])])
add('orbit','Orbit','Seventies green, an orange orbit and a small satellite.',
 ['#eee5cd','#315c4e','#df7339','#d9bf73'],['Ivory','Forest','Orbit orange','Satellite'],[
 bezel(2.7),ring('Orbit','accent',122.8,58.7,6,1.4),disc('Satellite','secondary',130.8,55.7,1.7),disc('Core','detail',122.8,58.7,2),
 box('Horizon','secondary',[115,13,130,14.5],.7)])
add('manga','Manga','Bold ink panels, broad speed lines and a vermilion corner.',
 ['#f0eadb','#27282e','#da453d','#99988e'],['Paper','Ink','Vermilion','Halftone blocks'],[
 bezel(.8),poly('Corner','accent',[[125,53],[135,50],[135,66],[128,66],[128,60]]),
 stroke('Panel','detail',[[113,53],[121,55],[121,64.8],[113,63]],1.3),
 box('SpeedA','detail',[112.3,13,123,14.3]),box('SpeedB','detail',[125,13,133.5,14.3]),
 disc('DotA','secondary',115.4,57.7,1),disc('DotB','secondary',118.5,58.6,1),disc('DotC','secondary',115.4,60.8,1)])
add('talavera','Talavera','Cobalt ceramic borders and a four-petal tile with a terracotta center.',
 ['#f1e6ca','#244e91','#c36443','#3d8b89'],['Ivory glaze','Cobalt','Terracotta','Teal'],[
 bezel(1.6),disc('PetalN','detail',123,54.7,2.1),disc('PetalS','detail',123,62.6,2.1),disc('PetalW','detail',119,58.65,2.1),disc('PetalE','detail',127,58.65,2.1),disc('Center','accent',123,58.65,1.55),
 poly('DiamondL','secondary',[[112.5,58.6],[114.2,56.9],[115.9,58.6],[114.2,60.3]]),poly('DiamondR','secondary',[[130.1,58.6],[131.8,56.9],[133.5,58.6],[131.8,60.3]]),
 box('TopRule','accent',[113,13,133,14.2],.5)])
add('gameboy','Game Boy','Pocket-console bezel, cross pad and two berry-colored buttons.',
 ['#dcd6ba','#42454d','#973c60','#a6a392'],['Warm shell','Graphite','Berry buttons','Speaker'],[
 bezel(2.5),box('DpadH','detail',[113.5,56.3,120.7,58.5]),box('DpadV','detail',[116,53.8,118.2,61]),
 disc('A','accent',130.1,54.7,1.8),disc('B','accent',126.7,58,1.8),
 *[stroke('Speaker'+str(i),'secondary',[[124+i*2.5,63],[125+i*2.5,65]],.9) for i in range(4)],
 box('Start','secondary',[114.2,63.4,119,64.4],.5)])
add('nes','NES','A restrained controller strip with red action buttons.',
 ['#c6c7be','#32363b','#c94b3e','#8a8d8d'],['Console gray','Controller black','Action red','Mid gray'],[
 bezel(.5),box('Deck','detail',[112.5,53,133.5,62.2],.8),
 box('DpadH','secondary',[114,56.6,120.5,58.6]),box('DpadV','secondary',[116.3,54.3,118.3,60.8]),
 disc('A','accent',130.5,58.1,1.8),disc('B','accent',126,58.1,1.8),
 box('Stripe1','secondary',[113,12.6,133,13.6]),box('Stripe2','secondary',[113,14.6,133,15.6]),box('Signature','accent',[125,64,132.7,65.2])])
add('snes','SNES','A soft gray console with two lavender button tones.',
 ['#d1d0c9','#464751','#746198','#aca0c2'],['Console gray','Graphite','Deep lavender','Lilac'],[
 bezel(2.4),box('DpadH','detail',[113.5,56.2,120.1,58.2]),box('DpadV','detail',[115.8,53.9,117.8,60.5]),
 disc('A','accent',131,57.3,1.65),disc('B','accent',127.8,60.5,1.65),disc('X','secondary',127.8,54.1,1.65),disc('Y','secondary',124.6,57.3,1.65),
 box('Power','accent',[114,13,121,15],1),box('Reset','secondary',[124,13,131,15],1),box('Select','secondary',[115,63.8,123,65],.6)])
add('phone','2000s Phone','Navy faceplate, silver keypad and green call key.',
 ['#263c55','#b8bbb5','#87ad67','#455469'],['Navy shell','Silver keys','Call green','Navigation'],[
 bezel(2.8),box('Earpiece','detail',[119,13,127,14.3],.6),
 box('Nav','secondary',[120,52,126,55],1.2),box('Call','accent',[113.7,52,118.5,54.2],1),box('End','detail',[127.5,52,132.3,54.2],1),
 *[box('Key'+str(r)+str(c),'detail',[114+c*6.3,56+r*3.1,118.2+c*6.3,58+r*3.1],.8) for r in range(3) for c in range(3)]])
add('walkman','Walkman','Cobalt portable audio, yellow controls and speaker bars.',
 ['#275273','#192d3b','#e4b54b','#acbcc0'],['Cobalt','Tape door','Transport yellow','Silver'],[
 bezel(.9),box('Header','accent',[112.4,12.4,133.6,15.3],.8),
 *[box('Speaker'+str(i),'detail',[114,53+i*2.2,124.5,54+i*2.2],.5) for i in range(5)],
 box('ControlStrip','accent',[127,52.8,132.5,64],1),poly('Play','secondary',[[128.3,54.4],[131.4,56],[128.3,57.6]]),
 box('Stop','secondary',[128.5,59.8,131,62.3],.4)])
add('ipod','iPod','White face, soft silver click wheel and a dark screen border.',
 ['#f0eee5','#656f79','#afb4b1','#d8d9d2'],['White shell','Screen gray','Wheel ring','Center key'],[
 bezel(2.2),ring('Wheel','accent',123,58.6,6.1,2),disc('Center','secondary',123,58.6,2.2),
 
 box('Hold','secondary',[121,13,125,14.4],.6)])
styles['walkman']['priority']=['secondary','accent','detail']
spec=dict(schema='flan36-frame-collection-1',revision='I',description='Eleven native solid-color motifs. Recessed material volumes end at the common frame roof; no gradients or raised decorations.',roles=['body','detail','accent','secondary'],decoration_mode='flush-co-print',inlay_depth_mm=.4,minimum_backing_mm=.8,minimum_nominal_stroke_mm=.9,mirror_sum_x_mm=160,default_style='flan',retired_styles=['smooth','bevel','facet','handheld','tv','cyberpunk','cartridge','arcade','mecha','kintsugi'],styles=styles)
(ROOT/'design/frame-finishes.json').write_text(json.dumps(spec,indent=2)+'\n')
print('Generated',len(styles),'frame recipes')
