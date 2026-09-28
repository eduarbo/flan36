#!/usr/bin/env python3
"""Verify browser print selections, exact native volumes and registered 3MF parts.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import json,zipfile,hashlib,struct,xml.etree.ElementTree as E
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/themes-print'
def triangles_stl(raw):
 n=struct.unpack_from('<I',raw,80)[0];assert len(raw)==84+50*n
 return np.stack([np.array(struct.unpack_from('<9f',raw,84+i*50+12)).reshape(3,3) for i in range(n)])
def canonical(triangles):
 # Allow cyclic starts, but never reversed winding.
 result=[]
 for t in triangles:
  p=[tuple(round(float(v),5) for v in row) for row in t];result.append(min(tuple(p[i:]+p[:i]) for i in range(3)))
 return sorted(result)
def topo(t):
 vertices={};faces=[]
 for tri in t:
  ids=[]
  for p in tri:
   key=tuple(round(float(v),5) for v in p)
   if key not in vertices:vertices[key]=len(vertices)
   ids.append(vertices[key])
  faces.append(ids)
 from collections import Counter
 edges=Counter(tuple(sorted((ids[i],ids[(i+1)%3]))) for ids in faces for i in range(3))
 return {'vertices':len(vertices),'edges':len(edges),'open_or_nonmanifold_edges':sum(v!=2 for v in edges.values()),'signed_volume_mm3':float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)}
results=[]
for filename,expected in [('complete.zip',19),('left-shells.zip',3)] + [(style+'-shells.zip',3) for style in ('handheld','tv','cyberpunk','cartridge','arcade','mecha','kintsugi')]:
 z=zipfile.ZipFile(OUT/filename);manifest=json.loads(z.read('manifest.json'));config=json.loads(z.read('Flan36-config.json'));assert config==manifest['configuration'];assert len(manifest['parts'])==expected
 assert all(p['side']=='left' for p in manifest['parts']) if filename!='complete.zip' else True
 if filename not in ('complete.zip','left-shells.zip'):
  style=filename.removesuffix('-shells.zip')
  assert config['frames']['left']['style']==style
  assert sum(p['id']=='left-frame-'+style for p in manifest['parts'])==1
 assert not any('right-frame' in p['id'] for p in manifest['parts'])
 assert sum('washer' in p['id'] for p in manifest['parts'])==(6 if filename=='complete.zip' else 0)
 records=[]
 for p in manifest['parts']:
  raw=z.read('STL/'+p['id']+'.stl');source=(ROOT/p['source']).read_bytes();assert raw==source;assert hashlib.sha256(raw).hexdigest()==p['source_sha256'];actual=triangles_stl(raw)
  import io
  colored=zipfile.ZipFile(io.BytesIO(z.read('3MF/'+p['id']+'.3mf')));rt=E.fromstring(colored.read('3D/3dmodel.model'));assert rt.attrib['unit']=='millimeter'
  content_types=E.fromstring(colored.read('[Content_Types].xml'))
  extensions={item.attrib['Extension'] for item in content_types if item.tag.endswith('Default')}
  assert all(name.rsplit('.',1)[-1] in extensions for name in colored.namelist() if name!='[Content_Types].xml'),'Every package part requires a declared content type'
  ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
  objects={o.attrib['id']:o for o in rt.findall('m:resources/m:object',ns)}
  build=rt.findall('m:build/m:item',ns);assert len(build)==1 and 'transform' not in build[0].attrib
  assembly=objects[build[0].attrib['objectid']];components=assembly.findall('m:components/m:component',ns)
  assert len(components)==len(p['material_parts'])
  assert {c.attrib['objectid'] for c in components}=={str(m['object_id']) for m in p['material_parts']}
  assert all('transform' not in c.attrib for c in components),'All material meshes use the same native registration'
  material_checks=[];volume_sum=0;counts={role:0 for role in ['body','detail','accent','secondary']};mins=[]
  for part in p['material_parts']:
   role=part['role'];obj=objects[str(part['object_id'])]
   assert obj.attrib['pid']=='1' and int(obj.attrib['pindex'])==['body','detail','accent','secondary'].index(role)
   pts=np.array([[float(v.attrib[a]) for a in ['x','y','z']] for v in obj.findall('m:mesh/m:vertices/m:vertex',ns)])
   faces=obj.findall('m:mesh/m:triangles/m:triangle',ns)
   ids=np.array([[int(v.attrib[a]) for a in ['v1','v2','v3']] for v in faces])
   assert not any('paint_color' in f.attrib for f in faces),'No inferred surface painting'
   restored=pts[ids]-np.array(p['translation_3mf_mm']);mins.append(pts.min(0))
   native=(ROOT/part['source']).read_bytes();assert hashlib.sha256(native).hexdigest()==part['source_sha256']
   expected_mesh=triangles_stl(native)
   assert restored.shape==expected_mesh.shape and np.max(np.abs(restored-expected_mesh))<1e-5
   assert canonical(restored)==canonical(expected_mesh)
   a,b=topo(expected_mesh),topo(restored)
   assert a['open_or_nonmanifold_edges']==b['open_or_nonmanifold_edges']==0,(p['id'],role,a,b)
   assert a['signed_volume_mm3']>0 and abs(a['signed_volume_mm3']-b['signed_volume_mm3'])<.001
   volume_sum+=a['signed_volume_mm3'];counts[role]+=len(faces)
   assert len(faces)==part['triangles']
   if part['source']!=p['source']:assert z.read('Materials/'+p['id']+'/'+role+'.stl')==native
   material_checks.append({'role':role,'triangles':len(faces),'closed':True,'native_surface_exact':True})
  assert np.max(np.abs(np.min(mins,axis=0)-np.array([10,10,0])))<1e-5
  for role in p['role_triangles']:assert counts[role['role']]==role['count']
  assert sum(counts.values())==p['triangles']
  fallback=topo(actual);assert fallback['open_or_nonmanifold_edges']==0 and fallback['signed_volume_mm3']>0
  # Tessellation can vary at partitioned curves. Native Boolean union identity is
  # checked separately; this catches missing/duplicated exported material volume.
  assert abs(volume_sum-fallback['signed_volume_mm3'])<max(.03,abs(fallback['signed_volume_mm3'])*.001),(p['id'],volume_sum,fallback)
  assert 'Metadata/project_settings.config' not in colored.namelist()
  palette=[v.attrib['displaycolor'][:7].lower() for v in rt.findall('m:resources/m:basematerials/m:base',ns)];assert palette==[p['colors'].get(k,p['colors']['body']) for k in ['body','detail','accent','secondary']]
  records.append({'id':p['id'],'stl_bytes_identical':True,'native_material_surfaces_preserved':True,'shared_registration':True,'closed':True,'fallback_triangles':len(actual),'colors':palette,'materials':material_checks})
 results.append({'file':filename,'zip_sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest(),'parts':records,'eye_solo_explosion_do_not_remove_printables':True})
report={'passed':True,'viewer_sha256':hashlib.sha256((ROOT/'docs/index.html').read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'kits':results,'slicer_palette_automatic_import':'not accepted; explicit manual mapping required','no_manufacturing_acceptance':True};(OUT/'print-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: exact native STLs, selected parts, washers, closed 3MF material volumes, shared transforms and color mappings')
