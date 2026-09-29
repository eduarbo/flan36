#!/usr/bin/env python3
"""Bind the approved artwork, native exports, PCB and viewer acceptance.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def bound(p,h):assert sha(p)==h,('Stale evidence',p)
plan=read('design/approved-frame-master-r4.json');master=read(plan['master_path']);bound(plan['master_path'],plan['master_sha256'])
spec=read('design/frame-finishes.json');prior=json.loads(subprocess.check_output(['git','show','2de168b54146c2b135a6438bb1d6a5b30bcc0141:design/frame-finishes.json'],cwd=ROOT))
assert spec['default_style']==prior['default_style']=='flan'
for k in plan['approved_styles']:
    assert spec['styles'][k]['colors']==master['styles'][k]['palette']
    assert spec['styles'][k]['approved_master']=='R4'
for k in plan['deferred_styles']:
    current=dict(spec['styles'][k]);assert current.pop('approval_status')=='awaiting-redesign'
    assert current==prior['styles'][k],('Deferred artwork/palette changed',k)
native=sha('mechanical/revI/Flan36.FCStd');install=read('validation/revI-approved-frames-native.json');model=read('design/revI.json');mech=read('validation/revI-mechanical.json')
assert install['output_sha256']==model['fcstd_sha256']==mech['source_sha256']==native
assert all(install[k] for k in ['saved_reopened_recomputed','configuration_unchanged','cap_geometry_unchanged','excluded_artwork_xy_unchanged'])
assert install['approved_styles']==plan['approved_styles'] and len(install['frames'])==22
assert model['parameter_values_mm']['FrameTop']==13.59 and model['parameter_values_mm']['FrameRoof']==1.4
assert len(model['frameVariants'])==22
geometry=read('validation/revI-approved-frames-geometry.json');assert geometry['source_sha256']==native and geometry['passed'] and len(geometry['frames'])==22
bound('tools/freecad/check_approved_frames.py',geometry['checker_sha256'])
for k in plan['approved_styles']:
    for side in ['left','right']:assert geometry['frames'][side+'-'+k]['saved_planar_approval_compared']
for item in model['inputs']:bound(item['path'],item['sha256'])
bound('tools/freecad/export_revI.py',mech['checker_sha256'])
for name,part in model['parts'].items():bound('mechanical/revI/'+name+'.stl',part['stl_sha256'])
for variant in model['frameVariants'].values():
    assert variant['roof_mm']==13.59 and len(variant['material_parts'])==4
    for material in variant['material_parts']:
        bound('mechanical/revI/'+material['stl'],material['stl_sha256']);bound('mechanical/revI/'+material['step'],material['step_sha256'])
for side in ['left','right']:
    assert not mech['halves'][side]['collisions']
    assert model['r4_cap_clearance'][side]['volume_mm3']<.001
    assert model['halves'][side]['display_header']=={'x':117.92 if side=='left' else 31.92,'y':50.8}
    checks=install['halves'][side];assert all(abs(v-.25)<1e-6 for v in checks['guide_gaps_mm'])
    assert checks['pcb_pin_radial_gap_mm']==.2
    electrical=read('validation/revI-electrical.json')['halves'][side]
    bound(f'hardware/revI/flan36-{side}.kicad_pcb',electrical['pcb_sha256']);assert not electrical['drc_violations']
registration=read('validation/revI-bottom-reset-step.json');assert registration['passed'] and registration['source_sha256']==native
for side in ['left','right']:
    bound(f'hardware/revI/flan36-{side}.kicad_pcb',registration['halves'][side]['pcb_sha256'])
    for name,item in registration['halves'][side]['components'].items():
        assert item['actual_kicad_export_reimported'] and item['native_placement_difference_mm3']<.001
viewer=read('validation/revI-viewer.json')
for item in viewer['sources']:bound(item['path'],item['sha256'])
bound('docs/index.html',viewer['viewer_sha256']);bound('docs/offline.html',viewer['offline_sha256']);bound(viewer['printing']['path'],viewer['printing']['sha256'])
browser=read('build/frame-collection/acceptance/result.json');assert browser['passed'] and not browser['runtime_errors']
bound('docs/offline.html',browser['viewer_sha256'])
printing=read('validation/revI-approved-frames-3mf.json');assert printing['passed'] and len(printing['registered_assemblies'])==22
bound('tools/check_approved_3mf.py',printing['checker_sha256'])
for item in printing['registered_assemblies']:bound('build/frame-collection/acceptance/'+item['id']+'.3mf',item['sha256'])
report={'status':'DIGITAL_IMPLEMENTATION_VERIFIED','approved_styles':plan['approved_styles'],'deferred_styles':plan['deferred_styles'],'master_sha256':plan['master_sha256'],'native_sha256':native,'source_inputs_verified':True,'approved_palettes_exact':True,'deferred_artwork_and_palettes_preserved':True,'camera_and_configuration_checks':browser['checks'],'browser_report_sha256':sha('build/frame-collection/acceptance/result.json'),'viewer_sha256':viewer['viewer_sha256'],'offline_sha256':viewer['offline_sha256'],'checker_sha256':sha('tools/check_approved_frames.py'),'physical_acceptance':False,'fabrication_ready':False}
(ROOT/'validation/revI-approved-frames.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: five approved designs, six deferred artworks, centered native/PCB chain, registered print assets and viewer continuity')
