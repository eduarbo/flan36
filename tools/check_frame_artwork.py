#!/usr/bin/env python3
"""Fast layout preflight against a measured native roof; exact CAD is authoritative.
Run with FreeCAD's bundled Python (Shapely), --domain <native roof.json>.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,json,math
from pathlib import Path
from shapely import wkt
from shapely.geometry import box,Point,Polygon,LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
def rounded(xy,r):
 x0,y0,x1,y1=xy
 return box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=64) if r else box(*xy)
def footprint(f):
 k=f['kind']
 if k in ('box','roundrect','roundrect_ring'):
  g=rounded(f['xy'],f.get('radius_mm',0))
  return g.difference(rounded(f['inner_xy'],f['inner_radius_mm'])) if k=='roundrect_ring' else g
 if k in ('disc','ring'):
  g=Point(f['xy']).buffer(f['radius_mm'],quad_segs=128)
  return g.difference(Point(f['xy']).buffer(f['radius_mm']-f['width_mm'],quad_segs=128)) if k=='ring' else g
 if k=='polygon':return Polygon(f['points'])
 if k=='stroke':return LineString(f['points']).buffer(f['width_mm']/2,quad_segs=128)
 if k=='path':
  points=[];current=None
  for op,*v in f['commands']:
   if op in ('M','L'):current=tuple(v);points.append(current)
   elif op=='C':
    a=current;b=v[:2];c=v[2:4];d=v[4:6]
    for i in range(1,257):
     t=i/256;s=1-t;points.append(tuple(s**3*a[j]+3*s*s*t*b[j]+3*s*t*t*c[j]+t**3*d[j] for j in range(2)))
    current=tuple(d)
   elif op!='Z':raise ValueError(op)
  return Polygon(points)
 raise ValueError(k)
def run():
 p=argparse.ArgumentParser();p.add_argument('--domain',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT/'build/frame-fidelity');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 d=json.loads(a.domain.read_text());roof=wkt.loads(d['roof_wkt']);supported=wkt.loads(d['supported_wkt'])
 spec=json.loads((ROOT/'design/frame-finishes.json').read_text());results=[];svg=[]
 for i,(style,t) in enumerate(spec['styles'].items()):
  shapes={f['id']:footprint(f) for f in t['features']}
  for f in t['features']:
   g=shapes[f['id']];lost=g.difference(supported).area
   results.append(dict(style=style,id=f['id'],valid=g.is_valid,lost_area_mm2=lost))
  # This view is explicitly the flat authored layout, not a CAD acceptance.
  ox=10+(i%6)*270;oy=45+(i//6)*635
  svg.append(f'<g transform="translate({ox} {oy}) scale(10) translate(-111 -11)">')
  svg.append(roof.svg(fill_color=t['colors']['body'],opacity=1).replace('stroke="#555555"','stroke="none"'))
  for role in reversed(t.get('priority',['accent','secondary','detail'])):
   g=unary_union([shapes[f['id']] for f in t['features'] if f['role']==role])
   svg.append(g.svg(fill_color=t['colors'][role],opacity=1).replace('stroke="#555555"','stroke="none"'))
  svg.append('</g>');svg.append(f'<text x="{ox}" y="{oy+590}" font-size="25" font-family="sans-serif">{t["label"]}</text>')
 errors=[r for r in results if not r['valid'] or r['lost_area_mm2']>.002]
 # The previous nominal bezel passed surviving-island checks while the support
 # mask removed its crossbars. Prove this guard detects that exact regression.
 old=footprint(dict(kind='roundrect',xy=[113.6,16.5,132,51.2],radius_mm=2))
 old_loss=old.difference(supported).area
 assert old_loss>1 and not old.intersection(supported).buffer(-.399).is_empty
 (a.out/'artwork-preflight.json').write_text(json.dumps(dict(features=results,errors=errors,
     old_truncated_bezel_rejected=True,old_lost_area_mm2=old_loss),indent=2)+'\n')
 (a.out/'artwork-layout.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1640" height="1300"><rect width="100%" height="100%" fill="#efeee7"/>'+''.join(svg)+'</svg>')
 print(json.dumps(dict(features=len(results),errors=errors)))
 if errors:raise SystemExit(1)
if __name__=='__main__':run()
