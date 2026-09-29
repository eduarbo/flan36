"""Build planar approval faces from exact artwork commands, never production solids.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import Part

ROOT=Path(__file__).resolve().parents[2]
assert os.environ.get('QT_QPA_PLATFORM')=='offscreen'
G.showMainWindow();G.getMainWindow().hide()
OUT=ROOT/'design/proposals/frame-master-r3'
master=json.loads((OUT/'master.json').read_text())
digest=hashlib.sha256((OUT/'master.json').read_bytes()).hexdigest()
for path, expected in master['source_sha256'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected, ('Source drift',path)
V=lambda p:A.Vector(p[0],-p[1],0)


def face(commands):
    edges=[];p=None;start=None
    for command in commands:
        op,*v=command
        if op=='M': p=v;start=v
        elif op=='L':
            if V(p).distanceToPoint(V(v))>1e-9:edges.append(Part.makeLine(V(p),V(v)))
            p=v
        elif op=='C':
            bez=Part.BezierCurve();bez.setPoles([V(p),V(v[:2]),V(v[2:4]),V(v[4:])]);edges.append(bez.toShape());p=v[4:]
        elif op=='A':
            rx,ry,rot,large,sweep,x,y=v
            assert rx==ry and rot==0
            dx,dy=x-p[0],y-p[1];d=math.hypot(dx,dy)
            h=math.sqrt(max(0,rx*rx-d*d/4))*(-1 if bool(large)==bool(sweep) else 1)
            cx=(p[0]+x)/2-dy/d*h;cy=(p[1]+y)/2+dx/d*h
            a=math.atan2(p[1]-cy,p[0]-cx);b=math.atan2(y-cy,x-cx)
            delta=(b-a)%(2*math.pi) if sweep else -((a-b)%(2*math.pi))
            mid=[cx+rx*math.cos(a+delta/2),cy+rx*math.sin(a+delta/2)]
            edges.append(Part.Arc(V(p),V(mid),V([x,y])).toShape());p=[x,y]
        elif op=='Z':
            if V(p).distanceToPoint(V(start))>1e-9:edges.append(Part.makeLine(V(p),V(start)))
            p=start
        else:raise ValueError(op)
    f=Part.Face(Part.Wire(edges));assert f.isValid()
    return f


outer=face(master['outer_commands']);window=face(master['aperture_commands']);domain=outer.cut(window)
xd=master['construction']['xy_domains']
relief=face(xd['relief_commands']);header=face(xd['header_commands'])
zones={'cover':header.common(domain),'collar':relief.common(domain).cut(header),'ordinary':domain.cut(relief)}
zone_union=zones['cover'].fuse(zones['collar']).fuse(zones['ordinary'])
assert zone_union.cut(domain).Area+domain.cut(zone_union).Area<1e-7
for k,s in zones.items():
    for n,t in zones.items():
        if k!=n:assert s.common(t).Area<1e-7
for opt in master['construction']['cover_options']:
    assert abs(opt['cover_z_mm'][0]-master['common']['solder_reserve_top_z_mm']-.2)<1e-7
    assert abs(opt['collar_z_mm'][1]-opt['collar_z_mm'][0]-opt['collar_thickness_mm'])<1e-7
# Freshly inspect the native datum. Never save this document.
src=A.openDocument(str(ROOT/'mechanical/revI/Flan36.FCStd'));src.L_Half.Placement=A.Placement();src.recompute()
def bounds(o):
    b=o.Shape.BoundBox
    return [b.XMin,-b.YMax,b.ZMin,b.XMax,-b.YMin,b.ZMax]
native={name:bounds(src.getObject(name)) for name in ['L_GlassWindow','L_LevelDisplayPCBRelief','L_LevelHeaderServiceWell','L_LevelDisplaySolderReserve','L_SlimDisplayMaleContacts'] if src.getObject(name)}
gw=native['L_GlassWindow'];expected=master['aperture_bounds_mm']
assert max(abs(a-b) for a,b in zip([gw[0]-111,gw[1]-11,gw[3]-111,gw[4]-11],expected))<1e-6, (gw,expected)
assert abs(float(src.Parameters.FrameTop)-master['common']['frame_face_z_mm'])<1e-6
assert abs(native['L_LevelDisplaySolderReserve'][5]-12.99)<1e-6
profile=json.loads((ROOT/'design/revI-frame-profiles.json').read_text())['left']['outer']
native_poly=Part.Face(Part.makePolygon([A.Vector(x-111,-y+11,0) for x,y in profile+profile[:1]]))
assert outer.cut(native_poly).Area+native_poly.cut(outer).Area<.03
A.closeDocument(src.Name)

doc=A.newDocument('FrameArtworkR3');doc.Label='Flan36 R3 · PLANAR approval artwork · NOT PRINTABLE'
report=dict(master_sha256=digest,source_sha256=master['source_sha256'],status='PLANAR_GEOMETRY_CHECKED_NOT_PHYSICALLY_QUALIFIED',native_bounds_mm=native,styles={})
report['construction_zone_areas_mm2']={k:s.Area for k,s in zones.items()}
def pathdata(commands):
    return ' '.join(c[0]+' '+' '.join(f'{v:.6f}'.rstrip('0').rstrip('.') if v else '0' for v in c[1:]) for c in commands)
for index,(key,style) in enumerate(master['styles'].items()):
    svg=ET.parse(OUT/(key+'.svg')).getroot()
    assert svg.attrib['width']=='24mm' and svg.attrib['height']=='56mm' and svg.attrib['viewBox']=='0 0 24 56'
    paths={p.attrib['id']:p for p in svg.findall('{http://www.w3.org/2000/svg}path')}
    assert paths[key+'-body'].attrib['d']==pathdata(master['outer_commands']+master['aperture_commands'])
    for f in style['features']:
        p=paths[key+'-'+f['id']]
        assert p.attrib['d']==pathdata(f['commands']+(master['aperture_commands'] if f['window_cut'] else []))
        assert p.attrib['fill']==style['palette'][f['color']]
    group=doc.addObject('App::Part',key);group.Label=style['label']+' · 24 × 56 mm'
    group.addProperty('App::PropertyString','MasterSHA256');group.MasterSHA256=digest
    group.addProperty('App::PropertyString','Purpose');group.Purpose='Unapproved 2D faces. Extrude only after artwork and cover approval.'
    regions={c:Part.Shape() for c in style['palette']};regions['body']=domain
    raw=[]
    for item in style['features']:
        f=face(item['commands'])
        if item['window_cut']:f=f.cut(window)
        outside=f.cut(domain).Area
        assert outside<1e-7,(key,item['id'],'outside',outside)
        assert f.Area>.01
        for color in regions:
            if not regions[color].isNull():regions[color]=regions[color].cut(f)
        color=item['color'];regions[color]=f if regions[color].isNull() else regions[color].fuse(f)
        raw.append((item,f))
    union=None;result={};feature_checks=[]
    for color,shape in regions.items():
        if shape.isNull() or shape.Area<1e-7:continue
        assert shape.isValid() and not shape.Solids
        for other,other_shape in regions.items():
            if other!=color and not other_shape.isNull():assert shape.common(other_shape).Area<1e-7,(key,color,other)
        o=doc.addObject('Part::Feature',key+'_'+color);o.Label=color+' / '+style['palette'][color];o.Shape=shape
        o.addProperty('App::PropertyString','ColorHex');o.ColorHex=style['palette'][color]
        o.ViewObject.ShapeColor=tuple(int(o.ColorHex[i:i+2],16)/255 for i in [1,3,5]);group.addObject(o)
        union=shape if union is None else union.fuse(shape)
        result[color]=dict(area_mm2=shape.Area,faces=len(shape.Faces),color=style['palette'][color])
    for item,f in raw:
        visible=f.common(regions[item['color']]).Area
        assert visible>.01,(key,item['id'],'disappeared')
        # OCC's cached face BoundBox can use coarse display tessellation or
        # a Bezier control hull. Measure edge samples for the independent check;
        # dimension sheets use analytic curve extrema from the master itself.
        samples=[p for edge in f.Edges for p in edge.discretize(Deflection=.00001)]
        bb=[min(p.x for p in samples),min(-p.y for p in samples),max(p.x for p in samples),max(-p.y for p in samples)]
        feature_checks.append(dict(id=item['id'],bounds_mm=bb,bounds_method='edge samples, 0.00001 mm deflection',authored_area_mm2=f.Area,visible_same_color_area_mm2=visible))
    delta=union.cut(domain).Area+domain.cut(union).Area
    assert delta<1e-7 and abs(union.BoundBox.XLength-24)<1e-6 and abs(union.BoundBox.YLength-56)<1e-6
    transform=A.Matrix();transform.A11=-1;transform.A14=49;transform.A24=-11
    mirrored=union.copy();mirrored.transformShape(transform,False,False)
    assert abs(mirrored.Area-union.Area)<1e-7 and abs(mirrored.BoundBox.XMin-25)<1e-6 and abs(mirrored.BoundBox.XMax-49)<1e-6, (key,mirrored.Area,union.Area,mirrored.BoundBox)
    report['styles'][key]=dict(regions=result,features=feature_checks,partition_difference_mm2=delta,svg_paths_and_colors_exact=True,right_full_curve_transform_checked=True)
    group.Placement.Base=A.Vector(32*(index%4),-66*(index//4),0)
doc.recompute();target=OUT/'Artwork-R3.FCStd';doc.saveAs(str(target));A.closeDocument(doc.Name)
check=A.openDocument(str(target));count=0
for o in check.Objects:
    if hasattr(o,'ColorHex'):
        assert o.Shape.isValid() and len(o.Shape.Solids)==0 and abs(o.Shape.BoundBox.ZLength)<1e-8;count+=1
        key,color=o.Name.rsplit('_',1)
        assert abs(o.Shape.Area-report['styles'][key]['regions'][color]['area_mm2'])<1e-7
        assert o.ColorHex==report['styles'][key]['regions'][color]['color']
assert count==sum(len(s['regions']) for s in report['styles'].values())
report['planar_objects_reopened']=count
report['native_plan_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
A.closeDocument(check.Name)
(OUT/'geometry-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified 11 planar designs; reopened',count,'color regions. Production CAD unchanged.',file=sys.__stdout__,flush=True)
os._exit(0)
