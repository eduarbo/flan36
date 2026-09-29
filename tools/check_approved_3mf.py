#!/usr/bin/env python3
"""Verify browser-generated multicolor meshes against native STL coordinates.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,struct,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/frame-collection/acceptance'
spec=json.loads((ROOT/'design/frame-finishes.json').read_text())
ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
def stl(path):
    data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n
    return [struct.unpack_from('<9f',data,84+i*50+12) for i in range(n)]
records=[]
for side in ['left','right']:
    for style,theme in spec['styles'].items():
        name=f'{side}-frame-{style}';path=OUT/(name+'.3mf')
        with zipfile.ZipFile(path) as z:tree=E.fromstring(z.read('3D/3dmodel.model'))
        assert tree.attrib['unit']=='millimeter'
        sources={role:stl(ROOT/f'mechanical/revI/{name}-{role}.stl') for role in spec['roles']}
        minimum=[min(tri[i] for tris in sources.values() for tri in tris for i in range(axis,9,3)) for axis in range(3)]
        shift=[(0 if axis==2 else 10)-v for axis,v in enumerate(minimum)]
        objects=tree.findall('m:resources/m:object',ns);assert len(objects)==5
        checks=[]
        for i,role in enumerate(spec['roles']):
            obj=next(o for o in objects if o.attrib['name']==name+'-'+role)
            assert obj.attrib['pindex']==str(i)
            vertices=[tuple(float(v.attrib[a]) for a in ['x','y','z']) for v in obj.findall('m:mesh/m:vertices/m:vertex',ns)]
            triangles=obj.findall('m:mesh/m:triangles/m:triangle',ns);assert len(triangles)==len(sources[role])
            maximum=0
            for native,face in zip(sources[role],triangles):
                actual=[x for k in ['v1','v2','v3'] for x in vertices[int(face.attrib[k])]]
                maximum=max(maximum,max(abs(actual[k]-native[k]-shift[k%3]) for k in range(9)))
            assert maximum<1e-8,(name,role,maximum)
            checks.append({'role':role,'triangles':len(triangles),'maximum_coordinate_error_mm':maximum})
        assembly=next(o for o in objects if o.find('m:components',ns) is not None)
        assert len(assembly.find('m:components',ns))==4
        assert all('transform' not in c.attrib for c in assembly.find('m:components',ns))
        records.append({'id':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'shared_translation_mm':shift,'materials':checks})
report={'passed':True,'registered_assemblies':records,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'physical_acceptance':False}
(ROOT/'validation/revI-approved-frames-3mf.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: all 22 3MF assemblies preserve native coordinates, triangle winding and color-role registration')
