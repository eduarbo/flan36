#!/usr/bin/env python3
"""Dimension every proposed frame from its validated planar geometry.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import html
import json
import math
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/proposals/frame-master-r3'
master=json.loads((OUT/'master.json').read_text())
report=json.loads((OUT/'geometry-check.json').read_text())
digest=hashlib.sha256((OUT/'master.json').read_bytes()).hexdigest()
assert digest==report['master_sha256']


def exact_bounds(commands):
    """Analytic extrema, independent of FreeCAD's tessellated display bounds."""
    points=[];p=start=None
    for op,*v in commands:
        if op=='M':p=start=v;points.append(p)
        elif op=='L':p=v;points.append(p)
        elif op=='C':
            controls=[p,v[:2],v[2:4],v[4:]];ts={0,1}
            for axis in [0,1]:
                a,b,c,d=[q[axis] for q in controls]
                qa=-a+3*b-3*c+d;qb=2*(a-2*b+c);qc=b-a
                if abs(qa)<1e-12:
                    if abs(qb)>1e-12:ts.add(-qc/qb)
                else:
                    disc=qb*qb-4*qa*qc
                    if disc>=0:ts.update([(-qb+math.sqrt(disc))/(2*qa),(-qb-math.sqrt(disc))/(2*qa)])
            for t in ts:
                if 0<=t<=1:points.append([sum(w*q[i] for w,q in zip([(1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3],controls)) for i in [0,1]])
            p=v[4:]
        elif op=='A':
            r,ry,rotation,large,sweep,x,y=v;assert r==ry and rotation==0
            dx,dy=x-p[0],y-p[1];length=math.hypot(dx,dy)
            h=math.sqrt(max(0,r*r-length*length/4))*(-1 if bool(large)==bool(sweep) else 1)
            cx=(p[0]+x)/2-dy/length*h;cy=(p[1]+y)/2+dx/length*h
            a=math.atan2(p[1]-cy,p[0]-cx);b=math.atan2(y-cy,x-cx)
            delta=(b-a)%(2*math.pi) if sweep else (a-b)%(2*math.pi)
            for q in [0,math.pi/2,math.pi,3*math.pi/2]:
                travel=(q-a)%(2*math.pi) if sweep else (a-q)%(2*math.pi)
                if travel<=delta+1e-9:points.append([cx+r*math.cos(q),cy+r*math.sin(q)])
            p=[x,y];points.append(p)
        elif op=='Z':p=start
    return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]


def text(x,y,t,size=17,**attrs):
    at=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())
    return f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="#233D39" {at}>{html.escape(str(t))}</text>'


for key,s in master['styles'].items():
    if key=='talavera':continue # Detailed main sheet already includes the motif.
    svg=(OUT/(key+'.svg')).read_text();body=svg.split('</metadata>',1)[1].rsplit('</svg>',1)[0]
    b='<rect width="1280" height="1000" fill="#F6F5F0"/>'
    b+=text(40,45,s['label'].upper()+' / DIMENSIONED APPROVAL ARTWORK',27,font_weight='bold')
    b+=text(40,78,'24 × 56 mm · aperture 14.50 × 31.10 mm · origin top-left · X right / Y down',18)
    b+=f'<g transform="translate(75,145) scale(10)">{body}</g>'
    b+='<path d="M75 129 L315 129 M59 145 L59 705" fill="none" stroke="#70837D"/>'
    b+=text(157,118,'24.00 mm',17)+text(12,438,'56.00',15)
    b+=text(380,138,'FEATURE BOUNDS / mm',18,font_weight='bold')
    b+=text(380,165,'Curves are authoritative in master.json. Bounds below are rounded to 0.01 mm.',14)
    b+=text(380,197,'Feature / painter order',15,font_weight='bold')
    for x,t in [(715,'X min'),(835,'Y min'),(955,'Width'),(1080,'Height')]:b+=text(x,197,t,15,font_weight='bold')
    for i,f in enumerate(report['styles'][key]['features']):
        bounds=exact_bounds(s['features'][i]['commands'])
        assert max(abs(a-b) for a,b in zip(bounds,f['bounds_mm']))<.01, (key,f['id'])
        yy=230+i*29;x1,y1,x2,y2=bounds
        b+=text(380,yy,f'{i+1:02}  '+f['id'],15)
        for x,v in [(715,x1),(835,y1),(955,x2-x1),(1080,y2-y1)]:b+=text(x,yy,f'{v:.2f}',15)
    b+=text(380,780,'OUTER RADII: TL / BL / BR R1.20; TR R2.40. Aperture: X4.55 / Y7.35.',15)
    for i,(role,col) in enumerate(s['palette'].items()):
        xx=40+i*306;b+=f'<rect x="{xx}" y="838" width="24" height="24" rx="3" fill="{col}" stroke="#BAC2B8"/>'
        b+=text(xx+32,856,role+' '+col,16)
    b+=text(40,901,'Unapproved 2D artwork. A: face Z13.39 / 0.20 mm cover. B: face Z13.59 / 0.40 mm cover.',17)
    b+=text(40,935,'Color regions remain flush. Pin-cover selection and physical print/fit qualification are pending.',17)
    b+=text(40,976,'MASTER '+digest,12)
    (OUT/(key+'-dimensioned.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="1000" viewBox="0 0 1280 1000">{b}</svg>\n')

for name in ['collection','section',*[k+'-dimensioned' for k in master['styles']]]:
    subprocess.run(['rsvg-convert','-o',str(OUT/(name+'.png')),str(OUT/(name+'.svg'))],check=True)
print('Rendered collection, section and all eleven dimensioned sheets.')
