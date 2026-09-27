#!/usr/bin/env python3
"""Audit source cap stems and native/viewer placements; render actual mesh sections.
Run with the CAD Python runtime (numpy + matplotlib). No geometry is modified.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,math,struct,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parents[1]
used={}
def read(path):
 raw=(ROOT/path).read_bytes();used[path]=hashlib.sha256(raw).hexdigest();return raw
def mesh(path):
 raw=read(path);n=struct.unpack_from('<I',raw,80)[0]
 return np.ndarray((n,),dtype=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]),buffer=raw,offset=84)['v'].astype(float)
def section(tri,axis,value):
 segments=[]
 for t in tri:
  points=[]
  for a,b in zip(t,np.roll(t,-1,axis=0)):
   da,db=a[axis]-value,b[axis]-value
   if da*db<0:points.append(a+(b-a)*(-da/(db-da)))
  if len(points)==2:segments.append(points)
 return np.array(segments)
catalog=json.loads(read('keycaps/catalog.json'));variants={v['id']:v for v in catalog['variants']};cfg=catalog['default_configuration'];scene=json.loads(read('build/viewer-scene.json'))
with zipfile.ZipFile(ROOT/'mechanical/revI/Flan36.FCStd') as z:xml=ET.fromstring(z.read('Document.xml'))
read('mechanical/revI/Flan36.FCStd')
objects={o.get('name'):o for o in xml.findall('.//ObjectData/Object')}
def placement(name):return objects[name].find("./Properties/Property[@name='Placement']/PropertyPlacement").attrib
count=0
for side,keys in catalog['layout'].items():
 for k in keys:
  prefix=side[0].upper();cap=placement(prefix+'_'+k['ref']);switch=placement(prefix+'_Switch_'+k['ref']);v=variants[cfg['keycaps'][side][k['ref']]['variant']]
  assert all(abs(float(cap[a])-float(switch[a]))<1e-8 for a in ['Px','Py'])
  assert abs(float(cap['Pz'])-v['seating_z_mm'])<1e-8
  q=np.array([float(cap['Q'+str(i)]) for i in range(4)]);angle=math.radians(k['angle']+cfg['keycaps'][side][k['ref']]['rotation_deg'])/2;expected=np.array([0,0,math.sin(angle),math.cos(angle)])
  assert min(np.linalg.norm(q-expected),np.linalg.norm(q+expected))<1e-8
  part=next(p for p in scene['parts'] if p['group']=='keycaps' and p['side']==side and p['key_ref']==k['ref'])
  assert np.allclose(part['position'],[k['x']+(161 if side=='right' else 0),v['seating_z_mm'],k['y']],atol=1e-8)
  assert part['angle_deg']==k['angle']+cfg['keycaps'][side][k['ref']]['rotation_deg'];count+=1
errors=[]
for v in variants.values():
 pts=mesh(v['path']).reshape(-1,3);tips=pts[pts[:,2]<pts[:,2].min()+.05];axis=0 if v['stem_axis_deg']==0 else 1
 for sign in [-1,1]:
  tip=tips[tips[:,axis]*sign>0];center=(tip[:,:2].min(0)+tip[:,:2].max(0))/2;expected=np.zeros(2);expected[axis]=sign*2.85;errors.append(float(np.linalg.norm(center-expected)))
 assert abs(float(pts[:,2].min())+v['seating_z_mm']-11.7)<.00001
assert max(errors)<.005
stem=mesh('mechanical/revI/component-choc-stem-0.stl')
# The inner slot walls at X=2.25/3.45, Y=±1.5 provide an independent datum.
cut=section(stem,2,6.25)
for center in [-2.85,2.85]:
 pts=cut.reshape(-1,3);slot=pts[(abs(pts[:,0]-center)<.8)&(abs(pts[:,1])<1.7)]
 assert np.allclose((slot[:,:2].min(0)+slot[:,:2].max(0))/2,[center,0],atol=1e-6)
 assert np.allclose(np.ptp(slot[:,:2],axis=0),[1.2,3],atol=1e-6)
normal=variants['choc_stem_choc_size_normal'];cap=mesh(normal['path']);cap[:,:,1]*=-1;cap[:,:,2]+=normal['seating_z_mm'];stem[:,:,2]+=5.4
housing=mesh('mechanical/revI/component-choc-body-0.stl');housing[:,:,2]+=5.4
fig,axes=plt.subplots(1,2,figsize=(12,5.4),facecolor='#f6f5ef')
for ax,axis,value,title in [(axes[0],1,.0001,'Front section · both cap stems'),(axes[1],0,2.8501,'Side section · through one stem')]:
 ax.set_facecolor('#f6f5ef');dims=[i for i in range(3) if i!=axis]
 for tri,color,label in [(housing,'#899591','Switch housing'),(stem,'#be4b55','Moving switch stem'),(cap,'#277c6b','KLP Lamé Normal')]:
  lines=section(tri,axis,value)[:,:,dims];ax.add_collection(LineCollection(lines,colors=color,linewidths=2,label=label))
 ax.set_xlim(-10,10);ax.set_ylim(9,19);ax.set_aspect('equal');ax.set_title(title,fontsize=12,loc='left');ax.set_xlabel('mm from switch center');ax.set_ylabel('mm above base');ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.12)
 axes[0].axhline(13.45,color='#be4b55',lw=.8,ls='--',alpha=.6)
axes[0].annotate('1.75 mm\nnominal insertion',xy=(2.85,12.5),xytext=(5.1,16.4),fontsize=9,arrowprops={'arrowstyle':'->','color':'#495e58'})
fig.legend(*axes[1].get_legend_handles_labels(),loc='upper left',bbox_to_anchor=(.07,.89),ncol=3,fontsize=10,frameon=False)
fig.suptitle('Caps and switches share the same mounting centers',fontsize=16,x=.07,ha='left')
fig.text(.07,.055,'Actual STL sections at assembled positions. Digital alignment verified; printed fit and travel remain untested.',fontsize=10,color='#53645d')
fig.tight_layout(rect=[.02,.12,1,.9]);image='docs/images/revI-keycap-registration.png';fig.savefig(ROOT/image,dpi=160);plt.close(fig)
report={'source_head':'34d69bf887787b4aaabbb1c555699c0ed5f60c16','scope':'Source mesh registration and default native/viewer placements; not physical fit qualification','native_and_viewer_caps_checked':count,'source_variants_checked':len(variants),'maximum_source_prong_center_error_mm':max(errors),'slot_centers_mm':[[-2.85,0],[2.85,0]],'slot_inner_section_mm':[1.2,3],'cap_tip_z_mm':11.7,'switch_stem_top_z_mm':float(stem[:,:,2].max()),'nominal_insertion_mm':float(stem[:,:,2].max())-11.7,'geometry_changed':False,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources':used,'section_image':image,'section_image_sha256':hashlib.sha256((ROOT/image).read_bytes()).hexdigest()}
(ROOT/'validation/revI-keycap-registration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
