#!/usr/bin/env python3
"""Historical pre-slim revision delivery/provenance checks; no hardware approval.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
m=json.loads((ROOT/'design/revI.json').read_text())
if 'slim_flush' in m:
    raise SystemExit('This gate describes the historical raised-frame snapshot. Run tools/check_slim_flush_delivery.py for the current revision.')
assert sha('mechanical/revI/Flan36.FCStd')==m['fcstd_sha256']
for source in m['inputs']:assert sha(source['path'])==source['sha256'],source
for s in ['left','right']:
    for name,p in m['parts'].items():assert sha('mechanical/revI/'+name+'.stl')==p['stl_sha256'],name
cases=json.loads((ROOT/'validation/revI-cases.json').read_text());assert cases['source_sha256']==sha('mechanical/revI/Flan36.FCStd') and cases['checker_sha256']==sha('tools/freecad/check_cases.py') and len(cases['measurements'])==6
mechanical=json.loads((ROOT/'validation/revI-mechanical.json').read_text())
for half in mechanical['halves'].values():
    assert not half['collisions']
    assert set(half['case_variants'])=={'solid','rim','terrace'}
    for case in half['case_variants'].values():assert case['closed_meshes'] and case['connected_solids'] and not case['component_collisions_mm3']
    volumes=[round(c['base_volume_mm3'],3) for c in half['case_variants'].values()];assert len(set(volumes))==3
    assert set(half['battery_variants'])=={'adafruit-1570','301230'}
    assert not any(x['component_collisions_mm3'] for x in half['battery_variants'].values())
    assert set(half['frame_variants'])=={'smooth','bevel','facet','handheld','tv','cyberpunk'}
    for f in half['frame_variants'].values():assert not f['component_collisions_mm3'] and f['usb_envelope_collision_mm3']==0 and f['closed_mesh']
render=json.loads((ROOT/'validation/revI-render.json').read_text());assert render['model_sha256']==sha('design/revI.json')
assert render['renderer_sha256']==sha('tools/render_revI.py')
for item in render['meshes']:assert sha(item['path'])==item['sha256']
for view,item in render['views'].items():assert sha(f'docs/images/revI-{view}.png')==item['image_sha256']
f=json.loads((ROOT/'validation/revI-frames-render.json').read_text());assert f['image_sha256']==sha('docs/images/revI-frames.png')
assert f['renderer_sha256']==sha('tools/render_frames.py')
for item in f['sources']:assert sha(item['path'])==item['sha256']
assert 'docs/images/revI-assembled.png' in (ROOT/'README.md').read_text()
for p in [ROOT/'README.md',ROOT/'ATTRIBUTION.md',ROOT/'CONTRIBUTING.md',*(ROOT/'docs').glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if target.startswith(('https:','http:','#','mailto:')):continue
        assert (p.parent/target.split('#')[0]).exists(),(str(p),target)
case_images=json.loads((ROOT/'validation/revI-cases-render.json').read_text());assert case_images['viewer_sha256']==sha('docs/index.html') and case_images['checker_sha256']==sha('viewer/check.cjs')
for name,digest in case_images['images'].items():assert sha('docs/images/revI-case-'+name+'.png')==digest
ui=json.loads((ROOT/'build/viewer-ui-check.json').read_text());assert ui['viewer_sha256']==sha('docs/index.html') and not ui['runtime_errors'] and ui['glb_selected_vertices_exact']
finishes=json.loads((ROOT/'validation/revI-freecad-finishes.json').read_text())
assert finishes['passed'] and finishes['source_sha256']==sha('mechanical/revI/Flan36.FCStd')
native=json.loads((ROOT/'validation/revI-freecad.json').read_text());assert native['source_sha256']==sha('mechanical/revI/Flan36.FCStd')
outline=json.loads((ROOT/'validation/revI-outline.json').read_text())
for path,digest in outline['inputs'].items():assert sha(path)==digest,path
caps=json.loads((ROOT/'validation/revI-keycaps.json').read_text())
assert caps['catalog_sha256']==sha('keycaps/catalog.json') and caps['layout_sha256']==sha('design/layout.json')
electrical=json.loads((ROOT/'validation/revI-electrical.json').read_text());assert electrical['fabrication_ready'] is False
for side,half in electrical['halves'].items():
    assert not half['drc_violations'] and half['unconnected_items']==104
    assert half['pcb_sha256']==sha(f'hardware/revI/flan36-{side}.kicad_pcb')
    assert half['footprints_pads_nets_drills_uuid_models_preserved_except_allowed_transforms'] and half['locked_original_keys']==18
# Native App::Link delegates FrameStyle, so the 12 bodies plus 2 active links are sampled.
assert native['mixed_cases_and_open_cover_roundtrip'] and native['legacy_configuration_normalized']
assert native['opaque_side_wall_samples']==168 and native['configuration_roundtrip'] and native['mixed_battery_profiles_roundtrip']
service=json.loads((ROOT/'validation/revI-service.json').read_text())
assert service['source_sha256']==sha('mechanical/revI/Flan36.FCStd')
assert service['checker_sha256']==sha('tools/freecad/check_revI_service.py')
for v in service['coupons'].values():assert sha(v['path'])==v['sha256']
rim=json.loads((ROOT/'validation/revI-rim-solids.json').read_text())
assert rim['source_sha256']==sha('mechanical/revI/Flan36.FCStd')
assert rim['checker_sha256']==sha('tools/freecad/check_revI_rim.py')
assert sum(r['samples'] for r in rim['normal_samples'])==216
assert all(abs(r['min_mm']-4.75)<.00002 and abs(r['max_mm']-4.75)<.00002 for r in rim['normal_samples'])
assert len(rim['curve_checks'])==4 and all(r['native_local_arcs'] for r in rim['curve_checks'])
assert outline['lcd_flank_protrusion_mm']==0 and outline['thumb_curve_tangent_continuity']
assert all(r['symmetric_difference_mm3']<1e-5 for r in rim['symmetry'].values())
corner=json.loads((ROOT/'validation/revI-frame-corner.json').read_text())
assert corner['source_sha256']==sha('mechanical/revI/Flan36.FCStd') and corner['checker_sha256']==sha('tools/freecad/check_frame_corner.py')
assert len(corner['shared_corner_checks'])==12 and corner['previous_corner_rejected']
assert all(c['outside_case_corner_mm3']<1e-6 and c['radius_mm']==2.4 for c in corner['shared_corner_checks'])
stack=json.loads((ROOT/'validation/revI-stack-study.json').read_text())
assert stack['source_sha256']==sha('mechanical/revI/Flan36.FCStd') and stack['checker_sha256']==sha('tools/freecad/study_stack_height.py')
assert stack['candidates']['14.8']['collisions_mm3'] and not stack['candidates']['15.6']['collisions_mm3']
assert m['parameter_values_mm']['FrameTop']==16.6, 'Exploratory height must not silently replace the printable source'
rim_image=json.loads((ROOT/'validation/revI-rim-render.json').read_text())
assert rim_image['image_sha256']==sha('docs/images/revI-rim.png')
assert rim_image['renderer_sha256']==sha('tools/render_rim.py') and rim_image['profile_sha256']==sha('design/revI-profiles.json')
fasteners=json.loads((ROOT/'validation/revI-fasteners.json').read_text())
for p,h in fasteners['inputs'].items():assert sha(p)==h,p
assert fasteners['checked_reference_choice_head_pairs']==2268 and fasteners['minimum_xy_clearance_mm']>0
assert outline['mirror_max_error_mm']==0 and outline['regression_previous_outline_rejected']
# Current customization and component additions carry their own acceptance evidence.
components=json.loads((ROOT/'validation/revI-components.json').read_text());assert components['source_sha256']==sha('mechanical/revI/Flan36.FCStd') and components['model_identity_without_reflection'] and components['switch_instances']==36
assert all(c['positive_board_support_area_mm2']>15 and c['solder_reserve_intersection_mm3']<1e-6 for c in components['checks'])
pcb_models=json.loads((ROOT/'validation/revI-pcb-component-models.json').read_text());assert pcb_models['source_sha256']==sha('mechanical/revI/Flan36.FCStd') and pcb_models['checker_sha256']==sha('tools/freecad/export_pcb_components.py')
assert len(pcb_models['models'])==11
for item in pcb_models['models'].values():assert item['sha256']==sha(item['path']) and item['import_difference_mm3']<.001 and item['native_placement_difference_mm3']<.001 and item['color_area_error_mm2']<1e-4
for side in ['left','right']:
    assert pcb_models['models'][side+'-slider']['distinct_colors']==3 and pcb_models['models'][side+'-reset']['distinct_colors']==4
for side,digest in pcb_models['pcb_unchanged'].items():assert digest==sha(f'hardware/revI/flan36-{side}.kicad_pcb')
themes=json.loads((ROOT/'validation/revI-theme-customization.json').read_text());assert themes['viewer_sha256']==sha('docs/index.html') and themes['custom_case_and_four_frame_colors_in_glb'] and not themes['runtime_errors']
kit=json.loads((ROOT/'validation/revI-print-kit.json').read_text());assert kit['passed'] and kit['no_manufacturing_acceptance']
for pack in kit['kits']:assert all(p['closed'] and p['stl_bytes_identical'] and p['oriented_surface_preserved'] for p in pack['parts'])
assert sha('docs/parts.md')==json.loads((ROOT/'validation/revI-parts-links.json').read_text())['document_sha256']
assert not subprocess.check_output(['git','diff','2ec6c4c','--name-only','--','hardware/revF','design/layout.json'],cwd=ROOT).strip(),'PCB/layout changed outside revision scope'
print('PASS: current native source, 12 closed cover variants, 168 side-wall samples, renders, viewer, documentation paths, preserved historical PCB/layout.')
