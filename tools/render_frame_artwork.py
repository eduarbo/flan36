#!/usr/bin/env python3
"""Dimensioned SVG/PNG approval sheets from one exact artwork master.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,html,json,subprocess,textwrap
from pathlib import Path
from prepare_frame_redesign_r5 import rect
ROOT=Path(__file__).resolve().parents[1]
def path(commands,color):
    d=' '.join(c[0]+' '+' '.join(format(v,'.12g') for v in c[1:]) for c in commands)
    return f'<path d="{d}" fill="{color}" fill-rule="evenodd"/>'
def text(x,y,t,size=19,weight='normal',color='#253936'):
    return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(str(t))}</text>'
def render(out):
    master=json.loads((out/'master.json').read_text());digest=hashlib.sha256((out/'master.json').read_bytes()).hexdigest();rev=master['revision']
    def drawing(key,context=False):
        s=master['styles'][key];p=s['palette'];b=''
        if context:
            for name,color in [('pcb','#111915'),('glass','#303836'),('lcd','#BFC8AD')]:
                x,y,x2,y2=master['display_context'][name+'_bounds_mm'];b+=path(rect(x,y,x2-x,y2-y),color)
            b+='<g fill="#4C5949" font-family="monospace" font-size="1.5" text-anchor="middle"><text x="12" y="21">BASE</text><text x="12" y="27">BLE</text></g>'
        b+=path(master['outer_commands']+master['aperture_commands'],p['body'])
        for f in s['features']:b+=path(f['commands']+(master['aperture_commands'] if f['window_cut'] else []),p[f['color']])
        return b
    def svg(name,w,h,b,mm=False,png=False):
        suffix='mm' if mm else ''
        s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}{suffix}" height="{h}{suffix}" viewBox="0 0 {w} {h}"><metadata>Flan36 {rev}; exact artwork, selection status in master; master SHA256 {digest}</metadata>{b}</svg>\n'
        f=out/(name+'.svg');f.write_text(s)
        if png:subprocess.run(['rsvg-convert','-o',str(out/(name+'.png')),str(f)],check=True)
    def swatches(s,x,y,spacing=225):
        b=''
        for i,(role,c) in enumerate(s['palette'].items()):
            xx=x+(i%2)*spacing;yy=y+(i//2)*30
            b+=f'<rect x="{xx}" y="{yy-18}" width="21" height="21" rx="3" fill="{c}" stroke="#ABB4AA"/>'+text(xx+30,yy,c,17)
        return b
    keys=list(master['styles'])
    for key,s in master['styles'].items():
        name=(s['code']+' / ' if s.get('code') else '')+s['label']
        subtitle=s.get('tagline','Replaces '+s['replaces'])
        state='Selected artwork · geometry retained' if s.get('decision')=='SELECTED' else 'Proposal for approval · exact editable geometry'
        svg(key,24,56,drawing(key),True)
        svg(key+'-preview',24,56,drawing(key,True),True)
        b='<rect width="600" height="960" fill="#F6F3E9"/>'+text(36,48,name.upper(),32,'bold')+text(36,80,f'{rev} / {subtitle}',17)
        b+=f'<g transform="translate(156,118) scale(12)">{drawing(key,True)}</g>'+swatches(s,36,833,280)
        b+=text(36,907,'24 × 56 mm · solid colors · flush artwork',18)+text(36,939,state,16)
        svg(key+'-card',600,960,b,png=True)
        b='<rect width="1280" height="1040" fill="#F6F3E9"/>'+text(40,50,name.upper()+' / EXACT ARTWORK',30,'bold')
        b+=text(40,84,rev+' · 24 × 56 mm · four solid-color roles · no raised decoration',18)
        b+=f'<g transform="translate(85,163) scale(11)">{drawing(key,True)}</g>'
        b+='<path d="M85 140H349 M62 163V779" stroke="#647D74" fill="none"/>'+text(170,129,'24.00 mm',17)+text(7,480,'56.00',16)
        b+=text(425,164,'COMPOSITION',20,'bold')
        for i,line in enumerate(textwrap.wrap(s['note'],73)):b+=text(425,199+i*28,line,18)
        b+=text(425,320,'FIXED INTERFACE',20,'bold')
        lines=['The current corrected mechanical blank is unchanged.','Opening: 13.90 × 30.50 mm, centered on the glass.','Nominal glass clearance: 0.10 mm on each side.','Frame face: Z13.59 mm. Glass top: Z13.39 mm.','Screen bezel: exact 2.40 mm outward offset.','Body corners: TL / BL / BR R1.20, TR R2.40.','Four complementary color volumes, flush at the face.','All paths and colors come directly from master.json.']
        for i,line in enumerate(lines):b+=text(425,357+i*29,line,18)
        b+=text(425,639,'PALETTE',20,'bold')+swatches(s,425,684,270)
        b+=text(40,845,('SELECTED ARTWORK' if s.get('decision')=='SELECTED' else 'PROPOSED / NOT APPROVED')+' / NOT A PRINT RELEASE',20,'bold')
        b+=text(40,881,'0.4 mm nozzle target. Exact paths do not qualify slicing, thin tips, bonding or physical fit.',18)
        b+=text(40,914,'Display context uses real modeled footprints. LCD content is illustrative.',18)
        b+=text(40,1004,'MASTER SHA256 '+digest,13)
        svg(key+'-dimensioned',1280,1040,b,png=True)
    def sheet(selected,name,columns,title='FLAN36 / NEW DIRECTIONS'):
        rows=(len(selected)+columns-1)//columns;cell=540;w=columns*cell+60;h=rows*780+140
        b=f'<rect width="{w}" height="{h}" fill="#F6F3E9"/>'+text(30,46,title,32,'bold')+text(30,77,rev+' · exact paths · solid colors · approval proposals',19)
        for i,key in enumerate(selected):
            x=30+(i%columns)*cell;y=124+(i//columns)*780;s=master['styles'][key]
            label=(s['code']+' / ' if s.get('code') else '')+s['label']
            b+=text(x,y,label.upper(),28,'bold')+text(x,y+28,s.get('tagline','Replaces '+s['replaces']),16)
            b+=f'<g transform="translate({x+124},{y+56}) scale(11.5)">{drawing(key,True)}</g>'
            b+=swatches(s,x+26,y+728,270)
        b+=text(30,h-20,'24 × 56 mm · original mechanical interface · no new artwork installed in production CAD',17)
        svg(name,w,h,b,png=True)
    groups=master.get('presentation',{}).get('collections')
    if groups:
        sheet([k for g in groups for k in g['keys']],'collection',3)
        for g in groups:sheet(g['keys'],g['name'],min(3,len(g['keys'])),g['title'])
    else:
        sheet(keys,'collection',3)
        for i,name in enumerate(['collection-a','collection-b','collection-c']):sheet(keys[i*2:i*2+2],name,2)
    print('Rendered exact',rev,'artwork and',len(keys),'individually viewable cards')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();render(a.directory.resolve())
