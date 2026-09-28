#!/usr/bin/env python3
"""Rebuild catalog from all 38 pinned, unchanged Choc-stem upstream STLs.
Run with the documented CAD Python runtime (numpy + shapely).
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from shapely.geometry import MultiPoint
from keycap_config import polygon,gap
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'keycaps/variants-source.json').read_text())
layout=json.loads((ROOT/'design/layout.json').read_text())['halves']
frames={}
for side,profile in json.loads((ROOT/'design/revI-profiles.json').read_text()).items():
    # The rectangle contains the analytical frame arcs and every themed relief;
    # an inscribed tessellation alone would slightly underestimate curved edges.
    x0=min(p[0] for p in profile['hood']);x1=max(p[0] for p in profile['hood'])
    y0=min(p[1] for p in profile['hood']);y1=max(p[1] for p in profile['hood'])
    frames[side]=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
variants=[]
for f in manifest['files']:
    raw=(ROOT/f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==f['git_blob']
    n=struct.unpack_from('<I',raw,80)[0]
    points=np.ndarray((n,),dtype=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]),buffer=raw,offset=84)['v'].reshape(-1,3)
    lo,hi=points.min(0),points.max(0);tips=points[points[:,2]<lo[2]+.05]
    axis=0 if np.ptp(tips[:,0])>np.ptp(tips[:,1]) else 90
    ident=Path(f['path']).stem.lower();size='Choc' if '_Choc_Size_' in f['path'] else 'MX'
    profile=Path(f['path']).stem.split('_Size_')[1].replace('_',' ')
    variants.append(dict(id=ident,label=f'{size} · {profile}',path=f['path'],source=f['source'],sha256=f['sha256'],
        bounds_mm=[lo.tolist(),hi.tolist()],stem_tip_z_mm=float(lo[2]),seating_z_mm=round(11.7-float(lo[2]),5),
        stem_axis_deg=axis,rotations_deg=[axis,axis+180],hull_xy_mm=[list(x) for x in MultiPoint(points[:,:2]).convex_hull.exterior.coords][:-1],
        qualified_reference_positions=[]))
cases=json.loads((ROOT/'design/cases.json').read_text())
finishes=json.loads((ROOT/'design/frame-finishes.json').read_text());flan=finishes['styles']['flan']['colors']
byid={v['id']:v for v in variants};cfg={'schema':'flan36-config-1','revision':'I','keycaps':{},'frames':{},'batteries':{'left':'adafruit-1570','right':'adafruit-1570'}}
cfg['cases']={side:{'style':cases['default'],'cover':True} for side in layout}
for side,keys in layout.items():
    cfg['keycaps'][side]={k['ref']:{'variant':'choc_stem_choc_size_'+('thumb' if k['row']==3 else 'normal_homing' if k['ref']=='K14' else 'normal'),'rotation_deg':0,'color':'#45967b' if k['row']==3 else '#e9dfc6'} for k in keys}
    cfg['frames'][side]={'style':'flan','color':flan['body'],'accents':{k:v for k,v in flan.items() if k!='body'}}
    cfg['cases'][side].update(base_color=flan['body'],plate_color=flan['body'] if cfg['cases'][side]['style']=='level' else flan['detail'],match_frame=True)
    for key in keys:cfg['keycaps'][side][key['ref']]['color']=[flan['detail'],flan['accent'],flan['secondary']][key['col']] if key['row']==3 else flan['body']
base={s:{k['ref']:polygon(byid[cfg['keycaps'][s][k['ref']]['variant']]['hull_xy_mm'],k,0) for k in keys} for s,keys in layout.items()}
for v in variants:
    for side,keys in layout.items():
        for k in keys:
            for turn in v['rotations_deg']:
                p=polygon(v['hull_xy_mm'],k,turn)
                d=min([gap(p,frames[side])]+[gap(p,q) for ref,q in base[side].items() if ref!=k['ref']])
                if d>=.2-1e-7:v['qualified_reference_positions'].append({'side':side,'key':k['ref'],'rotation_deg':turn,'clearance_mm':round(d,5)})
    v['status']='conditional' if v['qualified_reference_positions'] else 'unqualified'
    v['note']='Check the complete configuration before applying.' if v['qualified_reference_positions'] else '1.5U: no qualified position with the reference neighbors; unavailable in this layout.'
    print(v['label'],len(v['qualified_reference_positions']),flush=True)
catalog={'schema':'flan36-klp-catalog-1','revision':'I','upstream':manifest['upstream'],'commit':manifest['commit'],'license':'CC-BY-SA-4.0','author':'braindefender',
    'qualification':'Conservative convex XY envelopes, including stems. >=0.20 mm separating-axis clearance. Every chosen configuration rechecked. Nominal stem-tip datum 11.7 mm; unmeasured physical seating.',
    'minimum_clearance_mm':.2,'study_travel_mm':3.5,'minimum_pressed_mesh_z_mm':8.2,'plate_top_mm':7.6,
    'case_styles':cases['styles'],
    'battery_profiles':json.loads((ROOT/'design/batteries.json').read_text())['profiles'],
    'layout':layout,'frame_envelopes':frames,'frame_styles':{k:v['label'] for k,v in finishes['styles'].items()},'retired_frame_styles':{k:'flan' for k in finishes['retired_styles']},'variants':variants,'default_configuration':cfg}
(ROOT/'keycaps/catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n')
(ROOT/'design/configurations').mkdir(exist_ok=True)
(ROOT/'design/configurations/default.json').write_text(json.dumps(cfg,indent=2)+'\n')
print('Qualified variants',sum(bool(v['qualified_reference_positions']) for v in variants),'/',len(variants))
