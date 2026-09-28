#!/usr/bin/env python3
"""Adopt a fully checked frame candidate; preserve unrelated exported geometry.
python3 tools/adopt_frame_collection.py build/frame-collection/candidate
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
candidate=Path(sys.argv[1]).resolve();target=ROOT/'mechanical/revI'
spec=read(ROOT/'design/frame-finishes.json');install=read(candidate/'installation.json');sections=read(candidate/'sections.json');meta=read(candidate/'revI.json');mechanical=read(candidate/'mechanical.json')
assert install['saved_reopened_recomputed'] and install['protected_36_caps_cases_electronics_and_parameters']
assert install['source_sha256']==sha(target/'Flan36.FCStd'),'Published source changed after candidate creation'
assert install['output_sha256']==sections['source_sha256']==meta['fcstd_sha256']==mechanical['source_sha256']==sha(candidate/'Flan36.FCStd')
assert sections['passed'] and not sections['failures'] and len(sections['frames'])==22
expected={side+'-'+style for side in ['left','right'] for style in spec['styles']}
assert set(meta['frameVariants'])==expected and set(install['frames']['frames'])==expected
for side,checks in mechanical['halves'].items():
 assert not checks['collisions']
assert all(sha(ROOT/input['path'])==input['sha256'] for input in meta['inputs']),'Source input changed during export'
# Every pre-existing non-frame STL must remain byte-identical. STEP files for
# unchanged components are retained, avoiding timestamp-only file replacement.
allowed=lambda name:name=='Flan36.FCStd' or any(name.startswith(side+'-frame-'+style+'.') or name.startswith(side+'-frame-'+style+'-') for side in ['left','right'] for style in spec['styles']) or any(name.startswith(side+'-electronics-lid.') or name==side+'-assembly.step' for side in ['left','right'])
for p in candidate.glob('*.stl'):
 if not allowed(p.name):assert (target/p.name).exists() and sha(target/p.name)==sha(p),('Unrelated geometry drift',p.name)
newfiles=[p for p in sorted(candidate.iterdir()) if p.suffix in ['.stl','.step','.FCStd'] and allowed(p.name)]
assert len(newfiles)==227,len(newfiles)
for p in newfiles:shutil.copy2(p,target/p.name)
removed=[]
for side in ['left','right']:
 for old in spec['retired_styles']:
  for p in target.iterdir():
   if p.suffix in ['.stl','.step'] and (p.name.startswith(side+'-frame-'+old+'.') or p.name.startswith(side+'-frame-'+old+'-')):
    removed.append(p.name);p.unlink()
shutil.copy2(candidate/'revI.json',ROOT/'design/revI.json')
shutil.copy2(candidate/'mechanical.json',ROOT/'validation/revI-mechanical.json')
shutil.copy2(candidate/'installation.json',ROOT/'validation/revI-frame-collection-native.json')
shutil.copy2(candidate/'sections.json',ROOT/'validation/revI-frame-sections.json')
assert sha(target/'Flan36.FCStd')==meta['fcstd_sha256']
for id,record in meta['parts'].items():assert sha(target/(id+'.stl'))==record['stl_sha256'],id
for frame in meta['frameVariants'].values():
 for part in frame['material_parts']:
  assert sha(target/part['stl'])==part['stl_sha256'] and sha(target/part['step'])==part['step_sha256']
report=dict(adopted_files=[p.name for p in newfiles],removed_retired_exports=sorted(removed),native_sha256=meta['fcstd_sha256'],non_frame_stls_unchanged=True,source_inputs_verified=True)
(ROOT/'build/frame-collection/adoption.json').write_text(json.dumps(report,indent=2)+'\n')
print('Adopted',len(newfiles),'files; removed',len(removed),'retired exports; unrelated meshes unchanged')
