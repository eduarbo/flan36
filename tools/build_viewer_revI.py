#!/usr/bin/env python3
"""Pack unchanged revI meshes for the interactive viewer. Millimetres throughout.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import base64
import hashlib
import json
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

ROOT = Path(__file__).resolve().parents[1]
model = json.loads((ROOT/'design/revI.json').read_text())
layout = json.loads((ROOT/'design/layout.json').read_text())
scene = {'revision':'I', 'units':'mm', 'geometries':{}, 'parts':[], 'sources':[], 'batteryLeadProfiles':{}}
catalog=json.loads((ROOT/'keycaps/catalog.json').read_text());cfg=catalog['default_configuration'];variants={v['id']:v for v in catalog['variants']}
frame_finishes=json.loads((ROOT/'design/frame-finishes.json').read_text())
frame_extensions=json.loads((ROOT/'design/frame-extensions.json').read_text())
decorated_styles=set(frame_finishes['styles'])|set(frame_extensions['styles'])
frame_variants=model.get('frameVariants',{})
scene['catalog']=catalog
scene['presets']={p.stem:json.loads(p.read_text()) for p in (ROOT/'design/configurations').glob('*.json')}
for p in sorted((ROOT/'design/configurations').glob('*.json')):
    scene['sources'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
groups = {
    'tray':('Base', 'base', '#253639',0),
    'key-plate':('Plate', 'plate','#34494a',9),
    'electronics-lid':('Electronics cover','lid','#304d4e',72),
    'pcb':('PCB · unrouted outline','pcb','#22664c',3),
    'battery':('Battery · two profiles','battery','#b8c1bf',20),
    'mcu':('nice!nano v2 · nominal model','mcu','#1b433b',36),
    'display':('nice!view · nominal model','display','#172c2a',52),
    'cradle':('Open-bottom battery locator','supports','#78908a',20),
    'battery-retainer':('PCB-captured cage','supports','#78908a',24),
    'mcu-riser':('Controller support','supports','#647d78',36),
    'display-sled':('Display support','supports','#526e67',52),
    'mcu-sockets':('Controller sockets','connectors','#273631',3),
    'display-socket':('Display socket · retained on PCB','connectors','#273631',3),
    'jst':('Battery connector · envelope','connectors','#d9d3bc',3),
    'reset':('E-Switch TL3342','connectors','#545e58',3),
    'slider':('C&K PCM12','connectors','#45514a',3),
}


def digest(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def pack(array, dtype):
    return base64.b64encode(np.asarray(array,dtype=dtype).tobytes()).decode('ascii')


def mesh(path):
    if path in scene['geometries']:return path
    reader=vtk.vtkSTLReader();reader.SetFileName(str(ROOT/path));reader.Update()
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(reader.GetOutput())
    normals.SetFeatureAngle(45);normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.Update()
    data=normals.GetOutput()
    points=vtk_to_numpy(data.GetPoints().GetData()).copy()[:,[0,2,1]]
    ns=vtk_to_numpy(data.GetPointData().GetNormals()).copy()[:,[0,2,1]]
    if path.startswith('mechanical/revI/'):
        points[:,2]*=-1; ns[:,2]*=-1
    cells=vtk_to_numpy(data.GetPolys().GetData()).reshape(-1,4)
    assert np.all(cells[:,0]==3)
    # CAD (x,y,z) -> viewer (x,z,y) reflects handedness; reverse every triangle.
    indices=cells[:,[1,2,3] if path.startswith('mechanical/revI/') else [1,3,2]].reshape(-1)
    scene['geometries'][path]={'positions':pack(points,'<f4'),'normals':pack(ns,'<f4'),
                             'indices':pack(indices,'<u4'),'triangles':len(cells),
                             'bounds_mm':[points.min(axis=0).tolist(),points.max(axis=0).tolist()]}
    scene['sources'].append({'path':path,'sha256':digest(path)})
    return path


def colored_mesh(parent,visuals):
    positions=[];normals=[];indices=[];groups=[];colors=[];vertex=0;offset=0
    for v in visuals:
        source=scene['geometries'][mesh(v['path'])]
        a=lambda key,dtype:np.frombuffer(base64.b64decode(source[key]),dtype=dtype)
        p=a('positions','<f4');n=a('normals','<f4');i=a('indices','<u4')
        positions.append(p);normals.append(n);indices.append(i+vertex)
        groups.append({'start':offset,'count':len(i),'materialIndex':len(colors)});colors.append(v['color']);vertex+=len(p)//3;offset+=len(i)
    ident=parent+'#materials';ps=np.concatenate(positions)
    scene['geometries'][ident]={'positions':pack(ps,'<f4'),'normals':pack(np.concatenate(normals),'<f4'),'indices':pack(np.concatenate(indices),'<u4'),'triangles':offset//3,'groups':groups,'bounds_mm':[ps.reshape(-1,3).min(0).tolist(),ps.reshape(-1,3).max(0).tolist()]}
    return ident,colors


def frame_materials(side,style):
    """Use native volume boundaries, never triangle-centroid surface painting."""
    ident=f'{side}-frame-{style}'
    parts=frame_variants.get(f'{side}-{style}',{}).get('material_parts',[])
    if style in decorated_styles and not parts:
        raise ValueError(f'Missing native flush materials for {ident}; regenerate CAD exports')
    if not parts:return []
    roles=[part['role'] for part in parts]
    assert 'body' in roles and len(roles)==len(set(roles)),(ident,'missing/duplicate roles')
    positions=[];normals=[];indices=[];groups=[];vertex=0;offset=0
    for part in parts:
        assert part['role'] in frame_finishes['roles'],(ident,part['role'])
        filename=part['stl'];assert Path(filename).name==filename,(ident,'expected STL basename')
        source=scene['geometries'][mesh('mechanical/revI/'+filename)]
        unpack=lambda key,dtype:np.frombuffer(base64.b64decode(source[key]),dtype=dtype)
        p=unpack('positions','<f4');n=unpack('normals','<f4');i=unpack('indices','<u4')
        assert len(i)>0 and len(i)%3==0,(ident,part['role'],'empty material')
        positions.append(p);normals.append(n);indices.append(i+vertex)
        groups.append({'start':offset,'count':len(i),'materialIndex':frame_finishes['roles'].index(part['role'])})
        vertex+=len(p)//3;offset+=len(i)
    ps=np.concatenate(positions)
    scene['geometries'][f'mechanical/revI/{ident}.stl']={
        'positions':pack(ps,'<f4'),'normals':pack(np.concatenate(normals),'<f4'),
        'indices':pack(np.concatenate(indices),'<u4'),'triangles':offset//3,'groups':groups,
        'material_parts':[{'role':p['role'],'path':'mechanical/revI/'+p['stl']} for p in parts],
        'bounds_mm':[ps.reshape(-1,3).min(0).tolist(),ps.reshape(-1,3).max(0).tolist()]}
    return parts

def add(name,side,group,color,position,explode,geometry=None,primitive=None,angle=0):
    part={'name':side+' · '+name,'side':side,'group':group,'color':color,
          'position':position,'explode_mm':explode,'angle_deg':angle}
    if geometry:
        part['geometry']=geometry
        if geometry.startswith('mechanical/revI/'):
            part['part_id']=Path(geometry.split('#')[0]).stem
    if primitive:part['primitive']=primitive
    scene['parts'].append(part)


switches=json.loads((ROOT/'components/switches.json').read_text());switch_meshes={name:colored_mesh(name,entries) for name,entries in switches.items() if isinstance(entries,list)}

for side,keys in layout['halves'].items():
    offset=0 if side=='left' else 161
    for name,(label,group,color,explode) in groups.items():
        path=f'mechanical/revI/{side}-{name}.stl';visuals=model['parts'][side+'-'+name].get('visuals',[])
        geometry,colors=colored_mesh(path,visuals) if visuals else (mesh(path),None)
        add(label,side,group,color,[offset,0,0],explode,geometry)
        if colors:scene['parts'][-1]['materials']=colors
    for i in range(1,4):
        add(f'Washer {i}',side,'fasteners','#89918a',[offset,0,0],9,mesh(f'mechanical/revI/{side}-washer-{i}.stl'))
    for style in catalog['case_styles']:
        for group in ['base','plate']:mesh(f'mechanical/revI/{side}-case-{style}-{group}.stl')
    for style in catalog['frame_styles']:
        mesh(f'mechanical/revI/{side}-frame-{style}.stl')
        frame_materials(side,style)
    for key in keys:
        choice=cfg['keycaps'][side][key['ref']];v=variants[choice['variant']]
        add('KLP '+key['ref'],side,'keycaps','#45967b' if key['row']==3 else '#e9dfc6',
            [offset+key['x'],v['seating_z_mm'],key['y']],22,mesh(v['path']),angle=key['angle']+choice['rotation_deg'])
        scene['parts'][-1]['key_ref']=key['ref']
        for name,label in [('choc-body','Choc housing'),('choc-stem','Choc stem')]:
            geometry,colors=switch_meshes[name]
            add(label+' '+key['ref'],side,'switches',colors[0],[offset+key['x'],5.4,key['y']],14,geometry=geometry,angle=key['angle'])
            scene['parts'][-1]['materials']=colors
    for i in range(1,6):add(f'Structural screw {i}',side,'fasteners','#56615b',[offset,0,0],9,mesh(f'mechanical/revI/{side}-screw-{i}.stl'))
    for i in range(3):
        add(f'Captive magnet {i+1}',side,'fasteners','#8c9597',[offset,0,0],0,mesh(f'mechanical/revI/{side}-magnet-{i}.stl'))
        add(f'Captive frame target {i+1}',side,'lid','#899193',[offset,0,0],72,mesh(f'mechanical/revI/{side}-frame-target-{i}.stl'))
    for i in range(2):
        profile=model['batteryLeadProfiles'][f'{side}-{cfg["batteries"][side]}']
        lead=next(part for part in profile if part['index']==i)
        add(f'Battery lead {i+1}',side,'connectors',lead.get('color','#ad453d' if i==0 else '#353738'),[offset,0,0],24,mesh(f'mechanical/revI/{side}-battery-lead-{i}.stl'))
        scene['parts'][-1]['battery_lead_index']=i
    for ident in catalog['battery_profiles']:
        mesh(f'mechanical/revI/{side}-battery-{ident}.stl')
        leads=model['batteryLeadProfiles'][f'{side}-{ident}']
        assert sorted(part['index'] for part in leads)==[0,1],(side,ident,'battery lead pair missing')
        scene['batteryLeadProfiles'][f'{side}-{ident}']=[]
        for part in leads:
            filename=f'{side}-battery-lead-{ident}-{part["index"]}.stl'
            assert part['stl']==filename,(side,ident,'unexpected lead filename')
            path=mesh('mechanical/revI/'+filename)
            scene['batteryLeadProfiles'][f'{side}-{ident}'].append({'index':part['index'],'geometry':path,
                'color':part.get('color','#ad453d' if part['index']==0 else '#353738')})
    for i,(x,y) in enumerate([(26,26),(57,15),(28,70),(125,83)]):
        add(f'Foot {i+1}',side,'fasteners','#29352e',[offset+(x if side=='left' else 160-x),-.6,y],0,
            primitive={'kind':'cylinder','radius':3,'height':1.2})
    cx=122.8 if side=='left' else 37.2
    add('LCD · illustrative content',side,'display','#c5d1ba',[offset+cx,model['parameter_values_mm']['DisplayBottom']+1.92,33.9],52,
        primitive={'kind':'screen','size':[10.744,.025,25.28],'text':'BASE / BLE / L' if side=='left' else 'LINK / BAT / R'})

for v in catalog['variants']:
    if v['qualified_reference_positions']:mesh(v['path'])
# Exact native bytes; never derive printable parts from the presentation scene.
printing={'assets':{},'supports':['cradle','battery-retainer','mcu-riser','display-sled','washer-1','washer-2','washer-3'],
 'joining':{'case':'3 M2x6 + 2 M2x4 per half; tap the 1.7 mm pilots to M2',
 'installed_frame':'3 captive diameter 2 x 3 mm magnets and 3 ferromagnetic diameter 2 x 4 mm pins per half',
 'clips':False,'acceptance':'Physical fit, thread strength, retention force and insertion process untested'}}
for side in ['left','right']:
    names=[f'{side}-case-{style}-{group}' for style in catalog['case_styles'] for group in ['base','plate']]
    names += [f'{side}-frame-{style}' for style in catalog['frame_styles']]
    names += [f'{side}-{name}' for name in printing['supports']]
    for name in names:
        path=f'mechanical/revI/{name}.stl'
        if name.split(side+'-')[1] in printing['supports']:assert model['parts'][name]['prototype_part']
        printing['assets'][name]={'id':name,'path':path,'sha256':digest(path),'stl':base64.b64encode((ROOT/path).read_bytes()).decode()}
        if name.startswith(side+'-frame-'):
            style=name[len(side+'-frame-'):]
            material_parts=frame_variants.get(f'{side}-{style}',{}).get('material_parts',[])
            if material_parts:
                printing['assets'][name]['material_parts']=[]
                for part in material_parts:
                    material_path='mechanical/revI/'+part['stl']
                    printing['assets'][name]['material_parts'].append({'role':part['role'],
                        'path':material_path,'sha256':digest(material_path),
                        'stl':base64.b64encode((ROOT/material_path).read_bytes()).decode()})
scene['printing']=printing
top_key=min(k['y']-8.244852066 for k in layout['halves']['left'] if k['row']==0)
adjacent=next(k for k in layout['halves']['left'] if k['ref']=='K05')['y']-8.244852066
hood_min=min(p[1] for p in model['halves']['left']['electronics_cover'])
frame_top=model['parameter_values_mm']['FrameTop']
scene['measurements']={'bay_width_mm':24,'plate_top_mm':7.6,'cover_top_mm':frame_top,'themed_relief_top_mm':frame_top,
                       'decoration_relief_mm':0,'frame_materials':'Native recessed co-print volumes; flush top',
                       'cover_ahead_of_top_cap_mm':round(max(0,top_key-hood_min),3),
                       'cover_ahead_of_adjacent_cap_mm':round(max(0,adjacent-hood_min),3)}
for path in ['design/revI.json','design/layout.json','tools/build_viewer_revI.py','components/switches.json','components/sources.json','keycaps/catalog.json']:
    scene['sources'].append({'path':path,'sha256':digest(path)})
scene['limits']=['Commercial representations combine documented nominal dimensions, licensed community CAD and inferred package detail; see components/README.md', 'Unrouted PCB',
                 'Nominal lead-storage paths; actual terminations, insulation and finished-pack tolerances unverified', 'PCB aperture 12.5 mm; both nominal cells fit. Magnetic force, print-in capture/temperature and physical fit need coupons',
                 'Generic Choc v1 source model; purchased switch fit, keycap seating and travel unmeasured. Hotswap socket placement remains unqualified. Feet illustrative; nominal screws do not prove thread strength',
                 'Exploded positions are a viewing aid, not a validated extraction path']
(ROOT/'build').mkdir(exist_ok=True)
(ROOT/'build/viewer-scene.json').write_text(json.dumps(scene,separators=(',',':'))+'\n')
print(f'Packed {len(scene["parts"])} objects, {len(scene["geometries"])} unchanged meshes; 36 keycaps.')
