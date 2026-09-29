#!/usr/bin/env python3
"""Adopt a verified R4 candidate, preserving unrelated exports.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import collections,hashlib,json,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
candidate=Path(sys.argv[1]).resolve();target=ROOT/'mechanical/revI'
install=read(candidate/'installation.json');meta=read(candidate/'revI.json');mechanical=read(candidate/'mechanical.json')
assert install['saved_reopened_recomputed'] and install['configuration_unchanged'] and install['cap_geometry_unchanged'] and install['excluded_artwork_xy_unchanged']
assert install['source_sha256']==sha(target/'Flan36.FCStd'),'Published native input changed'
assert install['output_sha256']==meta['fcstd_sha256']==mechanical['source_sha256']==sha(candidate/'Flan36.FCStd')
assert len(install['frames'])==22 and len(meta['frameVariants'])==22
geometry=read(candidate/'geometry.json');assert geometry['passed'] and geometry['source_sha256']==meta['fcstd_sha256'] and len(geometry['frames'])==22
assert all(not h['collisions'] for h in mechanical['halves'].values())
assert all(sha(ROOT/i['path'])==i['sha256'] for i in meta['inputs'])
styles=tuple(read(ROOT/'design/frame-finishes.json')['styles'])
changed_parts={'display','display-socket','display-sled','pcb','key-plate','electronics-lid'}
def allowed(name):
    if name=='Flan36.FCStd':return True
    for side in ['left','right']:
        if not name.startswith(side+'-'):continue
        tail=name[len(side)+1:]
        return any(tail.startswith('frame-'+style+'.') or tail.startswith('frame-'+style+'-') for style in styles) or tail.startswith('case-level-plate.') or tail=='assembly.step' or any(tail.startswith(p+'.') or tail.startswith(p+'-visual-') for p in changed_parts)
    return False

# An explicit geometric change list is stricter than copying the export directory.
# Unchanged STEP files retain their original timestamp/header and bytes.
adopted=[];unchanged=[];order_only=[]
for p in sorted(candidate.glob('*.stl')):
    if not allowed(p.name):
        original=target/p.name;assert original.is_file(),('Unexpected new mesh',p.name)
        if sha(original)!=sha(p):
            # OCC may enumerate identical facets in a different order. Preserve
            # the original bytes only after checking every full facet record,
            # including normals, vertex order/winding, attributes and duplicates.
            def facets(path):
                raw=path.read_bytes();n=struct.unpack_from('<I',raw,80)[0];assert len(raw)==84+50*n
                return collections.Counter(raw[i:i+50] for i in range(84,len(raw),50))
            assert facets(original)==facets(p),('Unrelated mesh geometry drift',p.name)
            order_only.append(p.name)
        unchanged.append(p.name)
for p in sorted(candidate.iterdir()):
    if p.suffix not in ['.stl','.step','.FCStd'] or not allowed(p.name):continue
    if not (target/p.name).exists() or sha(p)!=sha(target/p.name):shutil.copy2(p,target/p.name);adopted.append(p.name)
for src,dst in [('revI.json','design/revI.json'),('mechanical.json','validation/revI-mechanical.json'),('installation.json','validation/revI-approved-frames-native.json'),('geometry.json','validation/revI-approved-frames-geometry.json')]:shutil.copy2(candidate/src,ROOT/dst)
assert sha(target/'Flan36.FCStd')==meta['fcstd_sha256']
for name,part in meta['parts'].items():assert sha(target/(name+'.stl'))==part['stl_sha256']
for frame in meta['frameVariants'].values():
    for part in frame['material_parts']:
        assert sha(target/part['stl'])==part['stl_sha256'] and sha(target/part['step'])==part['step_sha256']
report={'adopted_files':adopted,'unrelated_stls_preserved':unchanged,'identical_facets_different_enumeration':order_only,'native_sha256':meta['fcstd_sha256'],'source_inputs_verified':True}
(ROOT/'build/approved-r4/adoption.json').write_text(json.dumps(report,indent=2)+'\n')
print('Adopted',len(adopted),'files; preserved',len(unchanged),'unrelated meshes')
