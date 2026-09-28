"""Nominal commercial representations, with evidence in components/README.md.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import json
import FreeCAD as A, Part
ROOT=Path(__file__).resolve().parents[2]
V=A.Vector
COLORS={'pcb':(.045,.049,.053),'gold':(.77,.61,.28),'metal':(.67,.70,.73),'chip':(.09,.095,.105),'ceramic':(.63,.57,.43),'white':(.83,.84,.78),'glass':(.19,.22,.21),'flex':(.67,.39,.12)}
def box(x,y,z,w,l,h):return Part.makeBox(w,l,h,V(x,-y-l,z))
def rounded(x,y,z,w,l,h,r):
 s=box(x,y,z,w,l,h);edges=[e for e in s.Edges if abs(e.Vertexes[-1].Point.z-e.Vertexes[0].Point.z)>h-.001];return s.makeFillet(r,edges)
def ring(x,y,z,ro,ri,h):return Part.makeCylinder(ro,h,V(x,-y,z)).cut(Part.makeCylinder(ri,h+.02,V(x,-y,z-.01)))
def nano():
 # Origin at nominal PCB north edge; PCB underside Z=0. Same local geometry both halves.
 parts=[];add=lambda name,s,c:parts.append((name,s,COLORS[c]))
 board=rounded(-8.89,0,0,17.78,33.1,1,.65);board=board.cut(box(-4.5,-.1,-.1,9,6.3,1.2))
 pads=[]
 for x in [-7.62,7.62]:
  for i in range(13):
   y=1.16+i*2.54;hole=Part.makeCylinder(.5,1.4,V(x,-y,-.2));board=board.cut(hole)
   pads.extend([ring(x,y,.98,.94,.5,.045),ring(x,y,-.045,.94,.5,.065)])
 for x in [-2.54,0,2.54]:
  y=30.6;board=board.cut(Part.makeCylinder(.45,1.4,V(x,-y,-.2)));pads.append(ring(x,y,.98,.8,.45,.045))
 add('PCB · 17.78 × 33.1 mm',board,'pcb');add('ENIG pads · 2.54 mm pitch',Part.makeCompound(pads),'gold')
 usb=box(-4.45,-1.524,-1.1,8.9,7.6,3.2);opening=box(-4.08,-1.6,-.77,8.16,6.7,2.54);usb=usb.cut(opening)
 add('USB-C mid-mount shell',usb,'metal');add('USB-C tongue',box(-3.05,-1.2,.1,6.1,5,.55),'chip')
 add('nRF52840 · package placement inferred',rounded(-4.1,17.2,1,7,7,.78,.15),'chip')
 add('Power IC',box(2.5,8.2,1,2.4,2.5,.65),'chip');add('Charge IC',box(-5.1,7.8,1,1.8,2.7,.7),'chip')
 for x,y,w,l in [(2.9,14.0,2,3),(-1.8,26.0,1.8,3.2)]:add('Crystal',rounded(x,y,1,w,l,.65,.25),'metal')
 passives=[];terminals=[]
 for x,y,w,l in [(-4.9,12.2,1.4,.75),(-2.8,12.2,1.4,.75),(0,8.5,.7,1.4),(4.9,11.4,.7,1.4),(4.9,19.1,.7,1.4),(4.9,22,.7,1.4),(-4.8,27.5,1.1,.7),(3.7,27.8,1.1,.7),(1,12.0,.7,1.4)]:
  passives.append(box(x,y,1,w,l,.45));terminals.extend([box(x-.1,y,1,w+.2,l*.2,.48),box(x-.1,y+l*.8,1,w+.2,l*.2,.48)])
 add('Passives',Part.makeCompound(passives),'ceramic');add('Terminations',Part.makeCompound(terminals),'metal')
 add('Indicator LEDs · unlit',Part.makeCompound([box(-6.1,3.4,1,1,1.5,.5),box(5.1,3.4,1,1,1.5,.5)]),'white')
 return parts

def niceview():
 board=box(-7,0,0,14,36,1);pads=[]
 for i in range(5):
  # Manufacturer drawing: connector row is 1.3 mm from the 36 mm end.
  # Hole diameter remains an unmeasured nominal reserve, not vendor tolerance.
  x=-5.08+i*2.54;y=34.7;board=board.cut(Part.makeCylinder(.45,1.3,V(x,-y,-.1)));pads.append(ring(x,y,.99,.9,.45,.035))
 return [('PCB · 14 × 36 mm',board,COLORS['pcb']),('Five display contacts',Part.makeCompound(pads),COLORS['gold']),('Sharp glass',box(-6.85,2.55,1,13.7,30.3,.9),COLORS['glass']),('Flex and backing · inferred placement',box(-6,9.55,-1,12,19,1),COLORS['flex'])]

_cache={}
_facecolors={}
def standard(name):
 if name not in _cache:
  # Geometry-only Import drops STEP face materials. The builder initializes GUI
  # before this call, allowing ImportGui to retain the library's surface colors.
  import ImportGui
  source=A.newDocument('ComponentSource');ImportGui.insert(str(ROOT/'components/sources'/name),source.Name)
  obj=next(o for o in source.Objects if hasattr(o,'Shape') and not o.Shape.isNull());shape=obj.Shape.copy();colors=list(obj.ViewObject.DiffuseColor);colors=colors if len(colors)==len(shape.Faces) else [obj.ViewObject.ShapeColor]*len(shape.Faces)
  buckets={}
  for face,c in zip(shape.Faces,colors):buckets.setdefault(tuple(c[:3]),[]).append(face)
  _facecolors[name]=colors
  _cache[name]=(shape,[(f'{name} material {i}',Part.makeCompound(faces),color) for i,(color,faces) in enumerate(buckets.items())]);A.closeDocument(source.Name)
 return _cache[name]

def install(doc,history,name,label,parts,at,shift=None,zexpression=None,whole=None,whole_colors=None):
 children=[]
 for i,(title,shape,color) in enumerate(parts):
  o=doc.addObject('Part::Feature',name+'Visual'+str(i));history.addObject(o);o.Label=title;o.Shape=shape.copy();o.Placement.Base=V(*at);o.ViewObject.ShapeColor=color
  if shift:o.setExpression('Placement.Base.y',f'{at[1]} mm - Parameters.{shift}')
  if zexpression:o.setExpression('Placement.Base.z',zexpression)
  children.append(o)
 parent=doc.addObject('Part::Compound',name);history.addObject(parent);parent.Links=children;parent.Label=label
 parent.addProperty('App::PropertyLinkList','VisualParts','Filo36');parent.VisualParts=children
 if whole is not None:
  # Preserve the closed imported solid for mechanical checks; visual children are face groups.
  backing=doc.addObject('Part::Feature',name+'Solid');history.addObject(backing);backing.Shape=whole.copy();backing.Placement.Base=V(*at)
  parent.Links=[backing]
 doc.recompute();facecolors=whole_colors or [color for _,shape,color in parts for _ in shape.Faces]
 parent.addProperty('App::PropertyString','VisualFaceColors','Filo36');parent.VisualFaceColors=json.dumps(facecolors);parent.ViewObject.DiffuseColor=facecolors
 return parent
