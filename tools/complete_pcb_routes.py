"""Finish candidate routing on a conservative 0.1 mm grid. Require independent DRC.
Adapted from the earlier Piantor Slim local router.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import sys,json,math,heapq
from pathlib import Path
import pcbnew as p
import numpy as np
from scipy.ndimage import binary_dilation
from shapely.geometry import Point,box,Polygon,LineString
from shapely.affinity import rotate
from shapely import contains_xy
root=Path(__file__).resolve().parents[1]
board_path=Path(sys.argv[1]); report_path=Path(sys.argv[2]);side=sys.argv[3]
b=p.LoadBoard(str(board_path))
j=json.loads(report_path.read_text())
profiles=json.loads((root/'design/revI-profiles.json').read_text())[side]
outline=Polygon(profiles['pcb_outline'])
aperture=[[116.55,13.2],[129.05,13.2],[129.05,47.6],[119.85,47.6],[119.85,49.4],[117.65,49.4],[117.65,47.6],[116.55,47.6]]
if side=='right':aperture=[[160-x,y] for x,y in aperture]
for contour in [aperture,*profiles['pcb_cutouts']]:outline=outline.difference(Polygon(contour))
step=.1;nx,ny=1620,960
X,Y=np.meshgrid(np.arange(nx)*step,np.arange(ny)*step)
inside=contains_xy(outline.buffer(-.65),X,Y)
mm=p.ToMM;v=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
allpads=[q for f in b.GetFootprints() for q in f.Pads()]
trackwidth=.2
keep=Polygon()
obstacles=[]
for q in allpads:
 x,y=mm(q.GetPosition().x),mm(q.GetPosition().y);sx,sy=mm(q.GetSize().x),mm(q.GetSize().y)
 if q.GetAttribute()==p.PAD_ATTRIB_NPTH:
  # Drill obstacle remains regardless of electrical net.
  sx,sy=mm(q.GetDrillSize().x),mm(q.GetDrillSize().y)
  shape=Point(x,y).buffer(max(sx,sy)/2+.36)
  obstacles.append((None,[0,1],shape));continue
 shape=Point(x,y).buffer(sx/2) if q.GetShape()==p.PAD_SHAPE_CIRCLE else rotate(box(x-sx/2,y-sy/2,x+sx/2,y+sy/2),-q.GetOrientationDegrees(),origin=(x,y))
 layers=[i for i,l in enumerate([p.F_Cu,p.B_Cu]) if q.IsOnLayer(l)]
 obstacles.append((q.GetNetname(),layers,shape.buffer(.31)))
for t in b.GetTracks():
 a=(mm(t.GetStart().x),mm(t.GetStart().y));z=(mm(t.GetEnd().x),mm(t.GetEnd().y))
 if isinstance(t,p.PCB_VIA):shape=Point(*a).buffer(mm(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2+.31);layers=[0,1]
 else:shape=LineString([a,z]).buffer(mm(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2+.31);layers=[0 if t.GetLayer()==p.F_Cu else 1]
 obstacles.append((t.GetNetname(),layers,shape))
def mark(arr,shape,layers):
 if shape.is_empty:return
 xa,ya,xb,yb=shape.bounds;ix0=max(0,int(xa/step)-1);ix1=min(nx,int(xb/step)+2);iy0=max(0,int(ya/step)-1);iy1=min(ny,int(yb/step)+2)
 if ix1<=ix0 or iy1<=iy0:return
 mask=contains_xy(shape,X[iy0:iy1,ix0:ix1],Y[iy0:iy1,ix0:ix1])
 for l in layers:arr[l,iy0:iy1,ix0:ix1]|=mask
lookup={str(q.m_Uuid.AsString()):q for q in allpads}
lookup.update({str(t.m_Uuid.AsString()):t for t in b.GetTracks()})
def endpoint(item):
 obj=lookup[item['uuid']];x,y=item['pos']['x'],item['pos']['y'];net=obj.GetNetname()
 if isinstance(obj,p.PAD):ls=[i for i,l in enumerate([p.F_Cu,p.B_Cu]) if obj.IsOnLayer(l)]
 elif isinstance(obj,p.PCB_VIA):ls=[0,1]
 else:ls=[0 if obj.GetLayer()==p.F_Cu else 1]
 return obj,net,x,y,ls
# Route the long display clock/data paths before the matrix crowds the MCU bay.
def priority(e):
 net=endpoint(e['items'][0])[1]
 return {'/ROW0':0,'/ROW1':1,'/ROW2':2,'/ROW3':3,'/COL0':4,'/COL1':5,'/COL2':6,'/COL3':7,'/DISP_MOSI':8,'/DISP_SCK':9}.get(net,10 if any('of U1' in x['description'] for x in e['items']) else 11)
ordered=sorted(j['unconnected_items'],key=priority)
for number,error in enumerate(ordered):
 a,c=map(endpoint,error['items']);assert a[1]==c[1];name=a[1]
 blocked=np.array([~inside,~inside]);mark(blocked,keep.buffer(.31),[0,1])
 for net,layers,shape in obstacles:
  if net!=name:mark(blocked,shape,layers)
 via_block=binary_dilation(blocked[0]|blocked[1],iterations=3)
 # Drill-to-drill clearance also applies when a PTH pad is on the target net.
 for pad in allpads:
  if pad.GetAttribute()==p.PAD_ATTRIB_PTH:
   px,py=mm(pad.GetPosition().x),mm(pad.GetPosition().y);dr=max(mm(pad.GetDrillSize().x),mm(pad.GetDrillSize().y))/2
   mark(via_block[np.newaxis,:,:],Point(px,py).buffer(dr+.45),[0])
 starts=[(l,round(a[3]/step),round(a[2]/step)) for l in a[4]];goals={(l,round(c[3]/step),round(c[2]/step)) for l in c[4]}
 for n in starts+list(goals):assert not blocked[n],(name,n,'blocked endpoint')
 def h(n):return min(abs(n[1]-g[1])+abs(n[2]-g[2])+10*(n[0]!=g[0]) for g in goals)
 pq=[];dist={};prev={}
 for n in starts:dist[n]=0;heapq.heappush(pq,(h(n),0,n))
 end=None
 while pq:
  _,cost,n=heapq.heappop(pq)
  if cost!=dist.get(n):continue
  if n in goals:end=n;break
  l,yy,xx=n
  candidates=[((l,yy+dy,xx+dx),1) for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]]
  if not via_block[yy,xx]:candidates.append(((1-l,yy,xx),8))
  for nxt,delta in candidates:
   ll,yyy,xxx=nxt
   if not(0<=xxx<nx and 0<=yyy<ny) or blocked[nxt]:continue
   nc=cost+delta
   if nc>=dist.get(nxt,1e20):continue
   dist[nxt]=nc;prev[nxt]=n;heapq.heappush(pq,(nc+h(nxt),nc,nxt))
 if end is None:
  diagnostic={'net':name,'starts':starts,'goals':list(goals),'reachable_nodes':len(dist),'reachable_bounds':[[min(n[i] for n in dist),max(n[i] for n in dist)] for i in range(3)],'nearby_obstacles':[(n,ls,list(sh.bounds)) for n,ls,sh in obstacles if sh.distance(Point(c[2],c[3]))<2 or sh.distance(Point(a[2],a[3]))<2]}
  board_path.with_suffix('.failure.json').write_text(json.dumps(diagnostic,indent=2))
 assert end is not None,(name,'no route')
 path=[end]
 while path[-1] in prev:path.append(prev[path[-1]])
 path.reverse();segments=[]
 def addline(x1,y1,x2,y2,l):
  if math.hypot(x1-x2,y1-y2)<1e-5:return
  t=p.PCB_TRACK(b);t.SetStart(v(x1,y1));t.SetEnd(v(x2,y2));t.SetLayer([p.F_Cu,p.B_Cu][l]);t.SetWidth(p.FromMM(trackwidth));t.SetNetCode(a[0].GetNetCode());b.Add(t)
  obstacles.append((name,[l],LineString([(x1,y1),(x2,y2)]).buffer(.41)))
 addline(a[2],a[3],path[0][2]*step,path[0][1]*step,path[0][0])
 # Keep only turns and layer transitions.
 pts=[path[0]]
 for i in range(1,len(path)-1):
  before=tuple(path[i][k]-path[i-1][k] for k in range(3));after=tuple(path[i+1][k]-path[i][k] for k in range(3))
  if before!=after:pts.append(path[i])
 pts.append(path[-1])
 for aa,cc in zip(pts,pts[1:]):
  x1,y1=aa[2]*step,aa[1]*step;x2,y2=cc[2]*step,cc[1]*step
  if aa[0]!=cc[0]:
   assert x1==x2 and y1==y2
   vi=p.PCB_VIA(b);vi.SetPosition(v(x1,y1));vi.SetWidth(p.FromMM(.6));vi.SetDrill(p.FromMM(.3));vi.SetViaType(p.VIATYPE_THROUGH);vi.SetLayerPair(p.F_Cu,p.B_Cu);vi.SetNetCode(a[0].GetNetCode());b.Add(vi)
   obstacles.append((name,[0,1],Point(x1,y1).buffer(.61)))
  else:addline(x1,y1,x2,y2,aa[0])
 addline(path[-1][2]*step,path[-1][1]*step,c[2],c[3],path[-1][0])
 p.SaveBoard(str(board_path),b)
 print(number+1,name,len(pts),'segments',flush=True)
b.BuildConnectivity();p.SaveBoard(str(board_path),b)
