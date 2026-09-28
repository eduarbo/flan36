#!/usr/bin/env python3
"""Accept the current slim/flush digital delivery, never physical readiness.

Run after the native, PCB, viewer, HEX, battery-lead and nine print-kit checks.
Historical slim studies are preserved and are deliberately not current inputs.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'validation/revI-slim-flush.json'
EPS = .001  # Boolean reporting threshold, not a manufacturing tolerance.
SIDES = {'left', 'right'}
PROFILES = {'adafruit-1570', '301230'}
DECORATED = {'handheld', 'tv', 'cyberpunk', 'cartridge', 'arcade', 'mecha', 'kintsugi'}
ROLES = {'body', 'detail', 'accent', 'secondary'}
inputs = {}


def sha(path):
    file = ROOT/path
    if not file.is_file():
        raise ValueError('Missing current evidence: '+str(path))
    value = hashlib.sha256(file.read_bytes()).hexdigest()
    inputs[str(path)] = value
    return value


def read(path):
    sha(path)
    return json.loads((ROOT/path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bound_hash(path, expected):
    require(sha(path) == expected, 'Stale or changed input: '+str(path))


def native_report(path, source):
    report = read(path)
    require(report.get('source_sha256') == source, 'Native receipt has another source: '+path)
    return report


def viewer_report(path, viewer, checker=None):
    report = read(path)
    require(report.get('viewer_sha256') == viewer, 'Viewer receipt has another HTML: '+path)
    require(not report.get('runtime_errors'), 'Browser errors in '+path)
    if checker:
        bound_hash(checker, report['checker_sha256'])
    return report


def stl_bounds(path):
    sha(path)
    raw = (ROOT/path).read_bytes()
    require(len(raw) >= 84, 'Incomplete binary STL: '+path)
    count = struct.unpack_from('<I', raw, 80)[0]
    require(count > 0 and len(raw) == 84+50*count, 'Invalid binary STL: '+path)
    low, high = [float('inf')]*3, [-float('inf')]*3
    for i in range(count):
        values = struct.unpack_from('<9f', raw, 84+50*i+12)
        for j in range(3):
            for axis in range(3):
                v = values[3*j+axis]
                low[axis] = min(low[axis], v)
                high[axis] = max(high[axis], v)
    return low+high


def cell_motion(report, label):
    require(set(report) == PROFILES, 'Missing cell-motion profile: '+label)
    for profile, leads in report.items():
        require(len(leads) == 2, 'Cell-motion check needs exactly two leads: '+label+'/'+profile)
        require(all(lead['outside_attachment_overlap_mm3'] <= EPS for lead in leads),
                'Cell motion crosses a lead outside its attachment region: '+label+'/'+profile)


def connector_service(report, model, catalog, label):
    require(report['schema'] == 'flan36-PH-release-2', 'Superseded connector-service schema: '+label)
    require(report['physical_acceptance'] is False and report['wire_flex_validated'] is False,
            'Rigid connector geometry cannot qualify physical wire motion: '+label)
    require(report['release_stroke_mm'] == 5 and report['lift_mm'] == 24 and
            report['sweep_method'].startswith('Continuous union'), 'Incomplete connector release sweep: '+label)
    require(set(report['halves']) == SIDES and bool(report['assumptions']), 'Connector scope/limits missing: '+label)
    excluded = {'electronics-lid', 'display', 'display-sled', 'mcu', 'jst', 'battery'}
    for side, half in report['halves'].items():
        require(half['rigid_housing_path_clear'] is True and not half['rigid_housing_collisions'], 'Blocked PH housing release: '+label+'/'+side)
        require(half['grip_tool_path_clear'] is True and not half['grip_tool_collisions'], 'Blocked PH grip-tool path: '+label+'/'+side)
        socket = half['retained_display_socket']
        require(socket['part_id'] == side+'-display-socket' and socket['body_size_mm'] == [13.2,3,5], 'Missing conservative retained J2: '+label+'/'+side)
        require(socket['width_depth_qualified'] is False and socket['engagement_qualified'] is False, 'J2 dimensions/engagement are not physically qualified')
        require(socket['moving_male_header_part_id'] == side+'-display' and socket['moving_male_spacer_size_mm'] == [13.2,3,2], 'Display male header ownership/height changed')
        bounds = socket['body_bounds_mm']
        require(len(bounds) == 6 and max(abs(bounds[i+3]-bounds[i]-socket['body_size_mm'][i]) for i in range(3)) < 1e-5, 'J2 body reserve dimensions mismatch')
        require(abs(bounds[2]-model['parameter_values_mm']['PCBTop']) < 1e-5, 'J2 must remain on the PCB top')
        keys = {key['ref'] for key in catalog['layout'][side]}
        require(len(keys) == 18 and half['conservative_choc_bounds_count'] == half['conservative_cap_bounds_count'] == 18, 'Missing Choc/cap service reserves')
        native = {ident[len(side)+1:] for ident in model['parts'] if ident.startswith(side+'-')}
        fixed = {name for name in native if name not in excluded and not name.startswith(('frame-target-', 'battery-lead-'))}
        fixed |= {'SlimPHHeader', 'SlimPHPin0', 'SlimPHPin1'}
        fixed |= {prefix+key for key in keys for prefix in ('switch-bound-', 'cap-bound-')}
        require(set(half['retained_obstacles']) == fixed and 'display-socket' in fixed, 'Connector check omitted/changed a retained obstacle: '+label+'/'+side)
        require(set(half['nominal_terminal_distances']) == set(half['stored_wire_intersections_requiring_flex']) == PROFILES, 'Connector battery/lead profile coverage missing')
        for profile, leads in half['nominal_terminal_distances'].items():
            require(sorted(item['lead'] for item in leads) == [0,1], 'Connector terminal check requires both leads')
            require(all(item['to_plug_mm'] == item['to_cell_mm'] == 0 for item in leads), 'Disconnected nominal lead endpoint: '+label+'/'+side+'/'+profile)


def analytic_bounds(report):
    require(report['schema'] == 'flan36-analytic-bounds-regression-1' and report['passed'] is True,
            'Analytic bounds regression failed or is missing')
    require(report['source_unchanged'] is True and report['physical_acceptance'] is False,
            'Analytic measurement must preserve source and remain digital only')
    require(report['ordinary_bounds_must_change'] is False and report['analytic_api'] == 'Shape.optimalBoundingBox(False, False)',
            'Mesh-dependent ordinary bounds must not control analytic acceptance')
    require(report['tolerance'] == {'distance_mm':1e-8, 'volume_mm3':1e-8, 'area_mm2':1e-8},
            'Analytic bounds regression precision changed')
    expected = {prefix+'WireStudy'+str(i) for prefix in ('L_', 'R_') for i in range(2)}
    require(set(report['wires']) == expected, 'Analytic regression must cover all four stored leads')
    for name, wire in report['wires'].items():
        require(wire['passed'] is True and wire['exact_volume_mm3'] > 0 and wire['exact_area_mm2'] > 0,
                'Invalid analytic lead geometry: '+name)
        before = wire['analytic_bounds_mm']
        require(len(before) == 6 and all(before[i+3] > before[i] for i in range(3)), 'Invalid analytic lead bounds: '+name)
        require(len(wire['trials']) == 3 and {trial['deflection_mm'] for trial in wire['trials']} == {.2,.05,.01},
                'Missing tessellation trial: '+name)
        for trial in wire['trials']:
            require(trial['passed'] is True and trial['vertex_count_preserved'] is True and
                    trial['mesh_vertices'] > 0 and trial['mesh_triangles'] > 0, 'Invalid tessellation trial: '+name)
            for field in ('analytic_bounds_max_change_mm', 'symmetric_difference_mm3', 'volume_delta_mm3', 'area_delta_mm2', 'vertex_max_change_mm'):
                require(abs(trial[field]) <= 1e-8, 'Tessellation changed exact geometry/analytic bounds: '+name+'/'+field)
            after = trial['analytic_bounds_after_mm']
            require(len(after) == 6 and max(abs(a-b) for a,b in zip(before, after)) <= 1e-8,
                    'Analytic bound arrays changed under tessellation: '+name)


def run():
    workflow = read('design/slim-flush-workflow.json')
    installation = read('validation/revI-slim-flush-installation.json')
    source = sha('mechanical/revI/Flan36.FCStd')
    model = read('design/revI.json')
    catalog = read('keycaps/catalog.json')
    styles = set(catalog['frame_styles'])
    require(len(styles) == 10 and DECORATED < styles, 'Expected ten original frame choices')
    require(set(catalog['battery_profiles']) == PROFILES, 'Both battery profiles are required')
    require(model.get('manufacturing_ready') is False, 'Native metadata must remain unqualified')
    require(installation['source_sha256'] == workflow['source_fcstd_sha256'], 'Original request baseline changed')
    require(installation['output_sha256'] == model['fcstd_sha256'] == source, 'Candidate/native/export source mismatch')
    require(model['export_execution']['native_sha256'] == source and
            model['export_execution']['exporter_sha256'] == sha('tools/freecad/export_revI.py') and
            model['export_execution']['receipt'] == 'validation/revI-mechanical.json',
            'Current export provenance does not match native/exporter')
    bound_regression = native_report('validation/revI-analytic-bounds.json', source)
    bound_hash('tools/freecad/check_analytic_bounds.py', bound_regression['checker_sha256'])
    analytic_bounds(bound_regression)
    require(installation['physical_acceptance'] is False, 'Installation is digital only')
    for field in (
        'native_reopen_recompute',
        'configuration_preserved',
        'case_change_limited_to_reset_access',
        'protected_36_caps_preserved',
    ):
        require(installation.get(field) is True, 'Unverified native outcome: '+field)
    for path, digest in installation['immutable_inputs_sha256'].items():
        bound_hash(path, digest)
        original = subprocess.check_output(['git', 'show', workflow['source_commit']+':'+path], cwd=ROOT)
        require(hashlib.sha256(original).hexdigest() == digest, 'Protected input changed since request: '+path)
    for item in model['inputs']:
        bound_hash(item['path'], item['sha256'])
    for name, part in model['parts'].items():
        bound_hash('mechanical/revI/'+name+'.stl', part['stl_sha256'])
    with zipfile.ZipFile(ROOT/'mechanical/revI/Flan36.FCStd') as archive:
        require('GuiDocument.xml' in archive.namelist(), 'Native appearance is missing')
        tree = ET.fromstring(archive.read('Document.xml'))
        require(not any(e.attrib.get('type', '').endswith('Python') for e in tree.iter()), 'Custom Python proxy remains')

    roof = model['parameter_values_mm']['FrameTop']
    require(0 < roof < 16.6, 'Current electronics roof is not slimmer than the 16.6 mm reference')
    require(abs(roof-installation['stack']['target_frame_top_mm']) < 1e-6, 'Stack recipe and current roof differ')
    stack = installation['stack_checks']
    require(stack['physical_acceptance'] is False and set(stack['halves']) == SIDES, 'Incomplete stack checks')
    for side, half in stack['halves'].items():
        require(not half['static_collisions'] and set(half['profiles']) == PROFILES, 'Stack collision or missing profile: '+side)
        require(not half['bottom_reset_probe_collisions'], 'Bottom reset tool corridor blocked: '+side)
        cell_motion(half['cell_motion'], side+' installation')
        for profile, result in half['profiles'].items():
            require(not result['lead_static_collisions'], 'Lead collision: '+side+'/'+profile)
            require(not result['display_sled_lift_collisions'], 'Display service conflict: '+side+'/'+profile)

    connector_checker = 'tools/freecad/check_slim_connector_service.py'
    bound_hash(connector_checker, installation['connector_service_checker_sha256'])
    connector_service(installation['connector_service'], model, catalog, 'installation')
    connector = native_report('validation/revI-connector-service.json', source)
    bound_hash(connector_checker, connector['checker_sha256'])
    connector_service(connector, model, catalog, 'current native')
    for side in SIDES:
        old, current = installation['connector_service']['halves'][side], connector['halves'][side]
        require(old['retained_display_socket'] == current['retained_display_socket'] and
                old['retained_obstacles'] == current['retained_obstacles'], 'Connector/J2 service geometry changed after installation: '+side)

    expected_frames = {side+'-'+style for side in SIDES for style in styles}
    expected_decorated = {side+'-'+style for side in SIDES for style in DECORATED}
    require(set(model['frameVariants']) == expected_frames, 'Frame metadata coverage is incomplete')
    native_frames = installation['frames']['frames']
    require(set(native_frames) == expected_decorated, 'Flush material validation coverage is incomplete')
    for ident, frame in native_frames.items():
        require(frame['disjoint_interiors'] is True and frame['connected_solids'] == 1, 'Disconnected or overlapping frame: '+ident)
        require(frame['manufacturing_ready'] is False, 'Frame readiness must remain false')
        require(max(abs(frame[k]) for k in ('union_removed_volume_mm3', 'union_added_volume_mm3')) <= EPS,
                'Material union differs from the undecorated fallback: '+ident)
        require(max(frame['pair_intersections_mm3'].values(), default=0) <= EPS, 'Overlapping material interiors: '+ident)
        require(abs(frame['roof_mm']-roof) < 1e-6 and abs(frame['max_roof_relief_mm']) <= EPS, 'Raised decoration: '+ident)
        require(frame['minimum_backing_mm'] >= .8 and 0 < frame['inlay_depth_mm'] <= .4, 'Backing/depth requirement changed')
        require({p['role'] for p in frame['material_parts']} == ROLES, 'Missing native material role: '+ident)
        exported = {p['role']: p for p in model['frameVariants'][ident]['material_parts']}
        require(set(exported) == ROLES, 'Missing exported material role: '+ident)
        for part in frame['material_parts']:
            require(part['closed_mesh'] and part['volume_mm3'] > 0 and part['backing_missing_volume_mm3'] <= EPS,
                    'Open/empty/unsupported material: '+ident+'/'+part['role'])
            final = exported[part['role']]
            require(abs(final['volume_mm3']-part['volume_mm3']) <= EPS, 'Exported volume changed: '+ident)
            for extension in ('stl', 'step'):
                bound_hash('mechanical/revI/'+final[extension], final[extension+'_sha256'])

    mechanical = native_report('validation/revI-mechanical.json', source)
    bound_hash('tools/freecad/export_revI.py', mechanical['checker_sha256'])
    pruning = native_report('validation/revI-export-pruning.json', source)
    bound_hash('tools/freecad/check_export_pruning.py', pruning['checker_sha256'])
    bound_hash('tools/freecad/export_revI.py', pruning['exporter_sha256'])
    require(pruning['schema'] == 'flan36-export-pruning-audit-1' and pruning['passed'] is True and
            pruning['source_unchanged'] is True and pruning['exporter_unchanged'] is True and
            pruning['physical_acceptance'] is False, 'Current exporter pruning audit failed')
    require(set(pruning['halves']) == SIDES, 'Exporter pruning half coverage incomplete')
    for side, half in pruning['halves'].items():
        require(half['logical_pairs_checked'] == 1121 and half['logical_pair_counts'] == {
            'active':496, 'battery':62, 'frame':310, 'frame-usb':10,
            'case':180, 'case-frame':60, 'case-base-plate':3}, 'Exporter pruning pair coverage changed: '+side)
        require(not half['gate_selection_differences'] and not half['missed_intersections'],
                'Exporter pruning missed or changed a collision gate: '+side)
    require(set(mechanical['halves']) == SIDES, 'Mechanical half coverage is incomplete')
    coverage = []
    for side, half in mechanical['halves'].items():
        require(not half['collisions'] and set(half['frame_variants']) == styles, 'Mechanical frame failure: '+side)
        require(set(half['battery_variants']) == PROFILES, 'Mechanical battery coverage is incomplete')
        require(set(half['case_variants']) == set(catalog['case_styles']), 'Mechanical case coverage is incomplete')
        for case in half['case_variants'].values():
            require(case['closed_meshes'] and case['connected_solids'] and not case['component_collisions_mm3'], 'Case collision or open mesh')
        for style, frame in half['frame_variants'].items():
            require(frame['closed_mesh'] and not frame['component_collisions_mm3'] and frame['usb_envelope_collision_mm3'] <= EPS, 'Frame collision/open mesh: '+side+'/'+style)
            bounds = stl_bounds('mechanical/revI/'+side+'-frame-'+style+'.stl')
            require(bounds[5] <= roof+1e-4, 'Exported frame exceeds flush roof')
            sha('mechanical/revI/'+side+'-frame-'+style+'.step')
            for profile, battery in half['battery_variants'].items():
                require(not battery['component_collisions_mm3'], 'Battery collision: '+side+'/'+profile)
                # Every frame starts above both cells. This independent bound
                # proves their Cartesian combination, including wider 301230.
                require(battery['bounds_mm'][5] < bounds[2], 'Frame/battery combination needs an explicit collision check')
                coverage.append({'side':side, 'frame':style, 'battery':profile,
                                 'cell_to_frame_vertical_gap_mm':bounds[2]-battery['bounds_mm'][5]})
    require(len(coverage) == 40, 'Expected forty frame/battery combinations')
    require(set(model['batteryLeadProfiles']) == {s+'-'+p for s in SIDES for p in PROFILES}, 'Lead profile coverage is incomplete')
    for ident, wires in model['batteryLeadProfiles'].items():
        require(sorted(w['index'] for w in wires) == [0, 1], 'Lead pair missing: '+ident)
        for wire in wires:
            bound_hash('mechanical/revI/'+wire['stl'], wire['stl_sha256'])
            require(wire.get('color', '').startswith('#'), 'Native lead color missing')

    cases = native_report('validation/revI-cases.json', source)
    require(len(cases['measurements']) == 6 and cases['physical_acceptance'] is False, 'Case readback incomplete')
    bound_hash('tools/freecad/check_cases.py', cases['checker_sha256'])
    service = native_report('validation/revI-service.json', source)
    bound_hash('tools/freecad/check_revI_service.py', service['checker_sha256'])
    require(service['physical_acceptance'] is False and set(service['halves']) == SIDES, 'Service coverage/status incomplete')
    for side, half in service['halves'].items():
        require(set(half['frame_lift_paths']) == styles, 'Service check must cover all ten frames: '+side)
        for style, hits in half['frame_lift_paths'].items():
            require(not hits, 'Frame lift conflict: '+side+'/'+style)
        require(not half['pcb_lift_after_plate_modules_removed'] and not half['nominal_3mm_driver_shaft_collisions'], 'PCB/tool service conflict: '+side)
        cell_motion(half['cell_translation_bound_vs_leads_mm3'], side+' service')
    for coupon in service['coupons'].values():
        bound_hash(coupon['path'], coupon['sha256'])
    components = native_report('validation/revI-components.json', source)
    require(components['model_identity_without_reflection'] and components['switch_instances'] == 36, 'Commercial/switch model regression')
    native = native_report('validation/revI-freecad.json', source)
    for key in ('native_features_no_custom_proxy', 'configuration_roundtrip', 'mixed_battery_profiles_roundtrip',
                'mixed_cases_and_open_cover_roundtrip', 'reopened_customized_file', 'all_36_key_centres_unchanged',
                'invalid_configuration_rejected_atomically', 'source_file_unchanged'):
        require(native.get(key) is True, 'Native configuration regression: '+key)
    finishes = native_report('validation/revI-freecad-finishes.json', source)
    bound_hash('tools/freecad/check_finishes.py', finishes['checker_sha256'])
    require(finishes['passed'] and finishes['source_unchanged'] and finishes['saved_reopened_colors'] and finishes['json_body_override_roundtrip'], 'Native finish readback failed')
    require({r['side']+'-'+r['style'] for r in finishes['styles']} == expected_decorated, 'Native finish coverage incomplete')

    electrical = read('validation/revI-electrical.json')
    require(electrical['fabrication_ready'] is False and set(electrical['halves']) == SIDES, 'PCB study status/coverage changed')
    for side, result in electrical['halves'].items():
        bound_hash('hardware/revI/flan36-'+side+'.kicad_pcb', result['pcb_sha256'])
        require(not result['drc_violations'] and result['locked_original_keys'] == 18, 'New DRC/key regression')
        require(result['footprints_nets_uuid_models_preserved_except_explicit_PH_pad_and_reset_flip_changes'], 'Unexpected electrical mutation')
        require(result['slim_electronics']['reset_side'] == 'B.Cu', 'Bottom reset placement missing')
    bottom = native_report('validation/revI-bottom-reset-step.json', source)
    require(bottom['passed'] and bottom['physical_acceptance'] is False and set(bottom['halves']) == SIDES, 'Actual bottom STEP verification missing')
    bound_hash('tools/freecad/check_pcb_step_registration.py', bottom['checker_sha256'])
    bound_hash('tools/freecad/export_pcb_components.py', bottom['exporter_sha256'])
    calibration = bottom['calibration']
    require(calibration['passed'] and calibration['physical_acceptance'] is False, 'KiCad datum calibration incomplete')
    bound_hash('tools/freecad/check_pcb_step_registration.py', calibration['checker_sha256'])
    bound_hash('components/sources/SW_SPST_TL3342.step', calibration['source_step_sha256'])
    require(set(calibration['cases']) == {'front0', 'back0', 'back90', 'back180'}, 'Bottom angle/witness coverage incomplete')
    require(set(calibration['corrected_independent_cli_witness']) == {'front0', 'back90'}, 'Corrected CLI witness missing')
    for result in [*calibration['cases'].values(), *calibration['corrected_independent_cli_witness'].values()]:
        bound_hash(result['step'], result['step_sha256'])
        require(result['difference_mm3'] <= EPS, 'Calibration witness mismatch')
    params = model['parameter_values_mm']
    # Subtracting the nominal thickness introduces binary floating-point noise.
    datum = calibration['native_board_envelope_z_mm']
    expected_datum = [params['PCBTop']-params['PCBThickness'], params['PCBTop']]
    require(len(datum) == 2 and all(abs(a-b) <= 1e-8 for a,b in zip(datum, expected_datum)), 'Calibration refers to another native PCB datum')
    for side, result in bottom['halves'].items():
        bound_hash('hardware/revI/flan36-'+side+'.kicad_pcb', result['pcb_sha256'])
        require(result['reset_layer'] == 'B.Cu' and result['native_placement_difference_mm3'] <= EPS, 'Bottom reset is misregistered')
        require(result['actual_kicad_export_reimported'] is True, 'Calibration alone does not verify delivered reset')
        bound_hash(result['step_path'], result['step_sha256'])
        require(set(result['components']) == {'U1','J2','J1','SW1','SW2'}, 'Actual KiCad electronics coverage incomplete')
        for ref, component in result['components'].items():
            require(component['actual_kicad_export_reimported'] and component['native_placement_difference_mm3'] <= EPS, 'Actual KiCad component registration failed: '+side+'/'+ref)
            bound_hash(component['step_path'], component['step_sha256'])
            component_name = {'U1':'mcu', 'J2':'display', 'J1':'jst', 'SW1':'slider', 'SW2':'reset'}[ref]
            bound_hash('hardware/revI/models/'+side+'-'+component_name+'.step', component['local_model_sha256'])
        j2 = result['components']['J2']
        require(set(j2['native_components']) == {side+'-display', side+'-display-socket'}, 'Actual KiCad J2 must include display and retained socket: '+side)
        for ident, component in j2['native_components'].items():
            require(component['solid_count'] > 0 and component['native_placement_difference_mm3'] <= EPS, 'Actual KiCad J2 part mismatch: '+ident)
        socket = j2['retained_display_socket']
        require(socket['physical_acceptance'] is False and bool(socket['limitation']), 'J2 nominal dimensions must retain their qualification limit')
        require(socket['nominal_housing_height_mm'] == 5 and abs(socket['measured_native_housing_height_mm']-5) < 1e-5, 'J2 installed socket height differs from documented 5 mm')
        require(len(socket['native_housing_dimensions_mm']) == 3 and max(abs(a-b) for a,b in zip(socket['native_housing_dimensions_mm'], [13.2,3,5])) < 1e-5, 'J2 conservative body envelope changed')

    viewer = sha('docs/index.html')
    scene = read('build/viewer-scene.json')
    native_ids = [p['part_id'] for p in scene['parts'] if 'part_id' in p]
    require(len(native_ids) == len(set(native_ids)) and set(native_ids) == set(model['parts']), 'Viewer must show each native assembly part exactly once')
    expected_objects = len(model['parts']) + 36*3 + 8 + 2
    require(len(scene['parts']) == expected_objects, 'Viewer native/key/switch/foot/screen object coverage changed')
    for side in SIDES:
        socket = [p for p in scene['parts'] if p.get('part_id') == side+'-display-socket']
        require(len(socket) == 1 and socket[0]['group'] == 'connectors', 'Retained J2 missing from viewer: '+side)
    view = viewer_report('validation/revI-viewer.json', viewer)
    for item in view['sources']:
        bound_hash(item['path'], item['sha256'])
    ui = viewer_report('build/viewer-ui-check.json', viewer, 'viewer/check.cjs')
    require(ui['glb_objects'] == expected_objects and ui['glb_keycaps'] == 36, 'GLB part/key coverage changed')
    require(ui['ten_preview_cards'] and ui['glb_selected_vertices_exact'] and ui['small_320px_viewport'] and ui['about_measurements_match_model'], 'Viewer acceptance incomplete')
    themes = viewer_report('build/themes-print/ui.json', viewer, 'viewer/customize-check.cjs')
    require(themes['global_keycap_colors'] and themes['linked_colors_bidirectional'] and set(themes['new_frame_print_kits']) == DECORATED, 'Theme/print browser coverage incomplete')
    hexes = viewer_report('build/hex-check/result.json', viewer, 'viewer/hex-check.cjs')
    require(len(hexes['checks']) >= 7, 'HEX regression coverage incomplete')
    geometry = viewer_report('build/viewer-multicolor/geometry.json', viewer, 'viewer/finishes-check.cjs')
    bound_hash('build/viewer-scene.json', geometry['scene_sha256'])
    require(geometry['exact_native_material_volumes'] and geometry['no_raised_relief'] and len(geometry['checked']) == 20, 'Viewer material validation incomplete')
    leads = viewer_report('build/slim-flush/battery-viewer/result.json', viewer, 'viewer/battery-leads-check.cjs')
    require(leads['exact_native_lead_meshes'] and leads['exact_native_lead_colors'] and leads['stable_component_count'] == expected_objects, 'Viewer lead synchronization failed')
    require({r['name'] for r in leads['checked']} == {'adafruit', '301230', 'mixed'}, 'Lead UI profile coverage incomplete')
    require(leads['physical_polarity_verified'] is False, 'Wire colors cannot certify supplied-pack polarity')
    performance = viewer_report('build/viewer-sidebar/performance.json', viewer, 'viewer/performance.cjs')
    require(performance['smoke'] is True and performance['measurement_only'] is True and performance['baseline'] is False,
            'Current performance must be reported as a measurement, without a cross-version improvement claim')
    require(performance['scene_objects'] == expected_objects and set(performance['frame_choice']['styles']) == styles,
            'Performance measurement omits current geometry choices')
    require(performance['physical_phone_tested'] is False, 'Browser emulation is not a physical-phone test')
    kits = viewer_report('build/themes-print/print-validation.json', viewer, 'tools/check_print_kit.py')
    require(kits['passed'] and kits['no_manufacturing_acceptance'] and len(kits['kits']) == 9, 'Nine current print kits required')
    require({k['file'] for k in kits['kits']} == {'complete.zip', 'left-shells.zip'} | {s+'-shells.zip' for s in DECORATED}, 'Print kit style coverage incomplete')
    for kit in kits['kits']:
        bound_hash('build/themes-print/'+kit['file'], kit['zip_sha256'])
        for part in kit['parts']:
            require(part['stl_bytes_identical'] and part['native_material_surfaces_preserved'] and part['shared_registration'] and part['closed'], 'Print part verification failed')

    # Public receipts must be the checked local results, without retaining an
    # older successful run after this delivery changed the source.
    for current, public in (
        ('build/themes-print/ui.json', 'validation/revI-theme-customization.json'),
        ('build/themes-print/print-validation.json', 'validation/revI-print-kit.json'),
        ('build/hex-check/result.json', 'validation/revI-color-hex.json'),
        ('build/viewer-multicolor/geometry.json', 'validation/revI-flush-viewer.json'),
    ):
        bound_hash(public, sha(current))

    rendered = read('validation/revI-render.json')
    bound_hash('design/revI.json', rendered['model_sha256'])
    bound_hash('design/layout.json', rendered['layout_sha256'])
    bound_hash('tools/render_revI.py', rendered['renderer_sha256'])
    require(set(rendered['views']) == {'assembled', 'top', 'side', 'stack', 'detail', 'corner'}, 'Current native render coverage incomplete')
    for mesh in rendered['meshes']:
        bound_hash(mesh['path'], mesh['sha256'])
    for view, result in rendered['views'].items():
        bound_hash('docs/images/revI-'+view+'.png', result['image_sha256'])
    frame_render = read('validation/revI-frames-render.json')
    bound_hash('tools/render_frames.py', frame_render['renderer_sha256'])
    bound_hash('docs/images/revI-frames.png', frame_render['image_sha256'])
    for item in frame_render['sources']:
        bound_hash(item['path'], item['sha256'])
    case_render = viewer_report('validation/revI-cases-render.json', viewer, 'viewer/check.cjs')
    require(set(case_render['images']) == {'solid', 'rim', 'terrace', 'rim-open'}, 'Case render coverage incomplete')
    for name, digest in case_render['images'].items():
        bound_hash('docs/images/revI-case-'+name+'.png', digest)
    for image_source, image_target in (
        ('build/themes-print/themes-desktop.png', 'docs/images/revI-themes.png'),
        ('build/themes-print/nano-v2.png', 'docs/images/revI-nano-v2.png'),
    ):
        bound_hash(image_target, sha(image_source))
    documents = [ROOT/'README.md', ROOT/'ATTRIBUTION.md', ROOT/'CONTRIBUTING.md', *(ROOT/'docs').glob('*.md')]
    local_links = 0
    prospective_output_links = 0
    for path in documents:
        sha(path.relative_to(ROOT))
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if target.startswith(('https:', 'http:', '#', 'mailto:')):
                continue
            linked = path.parent/target.split('#')[0]
            if linked.resolve() == OUTPUT.resolve():
                # This receipt is created only after every check succeeds. Its
                # own documented link may be prospective on the first run;
                # no other missing artifact receives this bootstrap exception.
                prospective_output_links += 1
            else:
                require(linked.exists(), 'Broken local Markdown link: '+str(path.relative_to(ROOT))+' -> '+target)
            local_links += 1

    sha('tools/check_slim_flush_delivery.py')
    report = {'schema':'flan36-slim-flush-delivery-1', 'digital_update_accepted':True,
              'manufacturing_qualified':False, 'physical_acceptance':False,
              'native_source_sha256':source, 'viewer_sha256':viewer,
              'frame_top_mm':roof, 'decorated_frame_top_mm':roof,
              'coverage':coverage, 'decorated_variants':14, 'native_material_volumes':56,
              'print_kits':9, 'bottom_reset_actual_kicad_registration':True,
              'connector_continuous_housing_and_grip_sweeps':True,
              'retained_j2_sockets':2, 'socket_width_depth_and_engagement_qualified':False,
              'four_lead_analytic_bounds_stable_under_tessellation':True,
              'exporter_logical_collision_pairs_audited':2242,
              'wire_flex_validated':False,
              'fresh_native_and_viewer_renders':True, 'local_markdown_links_checked':local_links,
              'prospective_own_output_links':prospective_output_links,
              'limits':['Digital geometry: continuous nominal PH housing/grip sweeps and sampled frame/module extraction only.',
                        'J2 socket height follows the supplier; its 13.2 × 3 mm body width/depth, contacts and engagement remain assumptions.',
                        'Stock lead diameter, finished-pack dimensions and terminal engagement remain assumptions.',
                        'Flexible unplug motion, wire forces, measured polarity and electrical operation remain unqualified.',
                        'Printed fit, magnetic retention, RF, charging and PCB routing remain unqualified.'],
              'inputs':[{'path':p, 'sha256':h} for p,h in sorted(inputs.items())]}
    OUTPUT.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: current slim/flush digital delivery; 40 frame/battery combinations, 56 material volumes and 9 print kits. Physical acceptance remains open.')


if __name__ == '__main__':
    try:
        run()
    except (ValueError, KeyError, FileNotFoundError) as error:
        raise SystemExit('NOT ACCEPTED: '+str(error)) from error
