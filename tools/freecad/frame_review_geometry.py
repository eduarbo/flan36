"""Literal closed SVG-command faces, including even-odd compound logo paths.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import math
import FreeCAD as A
import Part

def face(commands):
    wires=[];edges=[];p=start=None
    def v(p):return A.Vector(p[0],-p[1],0)
    for op,*n in commands:
        if op=='M':
            assert not edges,'Close each path before a new move'
            p=start=n
        elif op=='L':
            if v(p).distanceToPoint(v(n))>1e-9:edges.append(Part.makeLine(v(p),v(n)))
            p=n
        elif op=='C':
            b=Part.BezierCurve();b.setPoles([v(p),v(n[:2]),v(n[2:4]),v(n[4:])]);edges.append(b.toShape());p=n[4:]
        elif op=='A':
            r,ry,rot,large,sweep,x,y=n;assert r==ry and rot==0
            dx,dy=x-p[0],y-p[1];d=math.hypot(dx,dy)
            h=math.sqrt(max(0,r*r-d*d/4))*(-1 if bool(large)==bool(sweep) else 1)
            cx=(p[0]+x)/2-dy/d*h;cy=(p[1]+y)/2+dx/d*h
            a=math.atan2(p[1]-cy,p[0]-cx);b=math.atan2(y-cy,x-cx)
            delta=(b-a)%(2*math.pi) if sweep else -((a-b)%(2*math.pi))
            mid=[cx+r*math.cos(a+delta/2),cy+r*math.sin(a+delta/2)]
            edges.append(Part.Arc(v(p),v(mid),v([x,y])).toShape());p=[x,y]
        elif op=='Z':
            if v(p).distanceToPoint(v(start))>1e-9:edges.append(Part.makeLine(v(p),v(start)))
            wires.append(Part.Wire(edges));edges=[];p=start
        else:raise ValueError(op)
    assert not edges and wires
    shape=Part.makeFace(wires,'Part::FaceMakerBullseye')
    assert shape.isValid() and shape.Area>0
    return shape

def regions(master,key):
    outer=face(master['outer_commands']);window=face(master['aperture_commands']);domain=outer.cut(window)
    roles=tuple(master['styles'][key]['palette']);result={r:Part.Shape() for r in roles};result['body']=domain
    features=[]
    for f in master['styles'][key]['features']:
        shape=face(f['commands'])
        if f['window_cut']:shape=shape.cut(window)
        excess=shape.cut(domain).Area
        assert excess<1e-7,(key,f['id'],'outside frame or over display',excess)
        features.append((f,shape.copy()))
        for role in roles:
            if not result[role].isNull():result[role]=result[role].cut(shape)
        role=f['color'];result[role]=shape if result[role].isNull() else result[role].fuse(shape)
    union=Part.makeCompound([s for s in result.values() if not s.isNull()])
    assert union.cut(domain).Area+domain.cut(union).Area<1e-6
    for i,(role,s) in enumerate(result.items()):
        for other,t in list(result.items())[i+1:]:assert s.common(t).Area<1e-7,(key,role,other)
    return result,features
