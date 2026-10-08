#!/usr/bin/env python3
"""Bind the October audit corrections to current native and browser evidence.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
from pathlib import Path
from audit_receipt_format import load_verified_receipt

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text())
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

ASSEMBLY_VIEWS = ('assembled', 'top', 'side', 'stack', 'detail', 'corner', 'level')
ASSEMBLY_SOURCES = {
    'design/revI.json', 'design/layout.json', 'keycaps/catalog.json',
    'components/switches.json', 'tools/render_revI.py',
}


def verify_manifest(items, expected, label):
    """A current hash is insufficient if a receipt silently omits an input."""
    paths = [item['path'] for item in items]
    assert len(paths) == len(set(paths)), f'{label}: duplicate source'
    assert set(paths) == set(expected), f'{label}: source inventory changed'
    for item in items:
        path = Path(item['path'])
        assert not path.is_absolute() and '..' not in path.parts, f'{label}: nonlocal source'
        assert sha(path) == item['sha256'], f'{label}: stale source {path}'


def assembly_meshes(model, catalog, layout, switches):
    """Expected files for the seven documented views, including the corner inset."""
    meshes = set()
    config = catalog['default_configuration']
    variants = {item['id']: item for item in catalog['variants']}

    def part(side, name):
        visuals = model['parts'].get(side + '-' + name, {}).get('visuals', [])
        meshes.update(visual['path'] for visual in visuals)
        if not visuals:
            meshes.add(f'mechanical/revI/{side}-{name}.stl')

    for side in ['left', 'right']:
        for name in ['tray', 'key-plate', 'pcb', 'diodes', 'hotswap-sockets',
                     'cradle', 'battery-retainer', 'battery', 'mcu-riser', 'mcu',
                     'mcu-sockets', 'display-socket', 'jst', 'reset', 'slider',
                     'display-sled', 'display']:
            part(side, name)
        for stem, numbers in [('washer', range(1, 4)), ('screw', range(1, 6)),
                              ('magnet', range(3)), ('frame-target', range(3))]:
            for number in numbers:
                part(side, f'{stem}-{number}')
        style = config['frames'][side]['style']
        meshes.update('mechanical/revI/' + item['stl']
                      for item in model['frameVariants'][side + '-' + style]['material_parts'])
        for lead in model['batteryLeadProfiles'][side + '-' + config['batteries'][side]]:
            part(side, f"battery-lead-{lead['index']}")
        for key in layout['halves'][side]:
            meshes.add(variants[config['keycaps'][side][key['ref']]['variant']]['path'])
    for name in ['case-rim-base', 'case-rim-plate', 'frame-' + config['frames']['left']['style']]:
        part('left', name)
    meshes.update(item['path'] for item in switches['choc-body'] + switches['choc-stem'])
    return meshes


def validate_presentation(native, selected):
    adoption = read('validation/revI-audit-adoption.json')
    assert adoption['passed'] is True, 'Adoption did not pass'
    assert adoption['native_sha256'] == native, 'Adoption native is stale'
    assert adoption['adopter_sha256'] == sha('tools/adopt_audit_repairs.py'), 'Adopter is stale'

    model, catalog, layout, switches = [read(path) for path in (
        'design/revI.json', 'keycaps/catalog.json', 'design/layout.json', 'components/switches.json')]
    assert model['fcstd_sha256'] == native, 'Rendered model is not the adopted native'
    render = read('validation/revI-render.json')
    assert render['revision'] == 'I'
    assert render['model_sha256'] == sha('design/revI.json'), 'Assembly model is stale'
    assert render['layout_sha256'] == sha('design/layout.json'), 'Assembly layout is stale'
    assert render['renderer_sha256'] == sha('tools/render_revI.py'), 'Assembly renderer is stale'
    verify_manifest(render['sources'], ASSEMBLY_SOURCES, 'Assembly inputs')
    verify_manifest(render['meshes'], assembly_meshes(model, catalog, layout, switches), 'Assembly meshes')
    assert set(render['views']) == set(ASSEMBLY_VIEWS), 'Assembly must contain all seven views'
    for kind in ASSEMBLY_VIEWS:
        item = render['views'][kind]
        sides = ['left', 'right'] if kind in ['assembled', 'top'] else ['left']
        assert item['halves'] == sides and item['keys'] == 18 * len(sides), f'{kind}: wrong assembly'
        assert item['exploded'] is (kind == 'stack'), f'{kind}: wrong pose'
        assert item['image_sha256'] == sha(f'docs/images/revI-{kind}.png'), f'{kind}: stale image'

    frames = read('validation/revI-frames-render.json')
    assert frames['styles'] == selected, 'Gallery must contain the six selected frames'
    assert frames['renderer_sha256'] == sha('tools/render_frames.py'), 'Gallery renderer is stale'
    gallery_sources = {'design/revI.json', 'design/frame-finishes.json', 'tools/frame_finishes.py'}
    for style in selected:
        gallery_sources.update('mechanical/revI/' + item['stl']
                               for item in model['frameVariants']['left-' + style]['material_parts'])
    gallery_sources.update(item['path'] for item in model['parts']['left-display']['visuals'])
    verify_manifest(frames['sources'], gallery_sources, 'Gallery inputs and meshes')
    assert frames['image_sha256'] == sha('docs/images/revI-frame-gallery.png'), 'Gallery image is stale'
    return {'adoption': adoption, 'revI-render': render, 'revI-frames-render': frames}


def run():
    native = sha('mechanical/revI/Flan36.FCStd')
    online, offline = sha('docs/index.html'), sha('docs/offline.html')
    evidence = {}
    for kind in ['parameters', 'delivery']:
        path = f'validation/revI-audit-{kind}.json'
        item, original = load_verified_receipt(ROOT / path) if kind == 'delivery' else (read(path), None)
        checked = original if original is not None else item
        assert checked['passed'] and checked['source_sha256'] == native, path
        assert checked['checker_sha256'] == sha('tools/freecad/check_audit_' + ('repairs' if kind == 'parameters' else 'delivery') + '.py')
        # Keep explicit path/digest lists in the published embedded evidence.
        evidence[kind] = item
    sockets = read('validation/revI-hotswap-registration.json')
    assert sockets['passed'] and sockets['source_sha256'] == native
    evidence['hotswaps'] = sockets
    relief=read('validation/revI-socket-clearance.json')
    assert relief['passed'] and relief['source_sha256']==native
    installer=(ROOT/'tools/freecad/install_socket_clearance.py').read_text()
    if relief['installer_sha256']!=sha('tools/freecad/install_socket_clearance.py'):
        correction=relief['receipt_path_correction']
        assert correction['old_expression']=='str(old_path.relative_to(ROOT))'
        assert correction['new_expression']=='str(old_path.resolve().relative_to(ROOT))'
        assert correction['current_installer_sha256']==sha('tools/freecad/install_socket_clearance.py')
        assert installer.count(correction['new_expression'])==1
        producing_code=installer.replace(correction['new_expression'],correction['old_expression'])
        assert hashlib.sha256(producing_code.encode()).hexdigest()==relief['installer_sha256']
    assert all(h['socket_to_relieved_post_mm']>=.25-1e-7 and h['minimum_pilot_web_mm']>=1.20 for h in relief['halves'].values())
    evidence['socket_support_relief']=relief
    native_config = read('validation/revI-freecad.json')
    assert native_config['source_sha256'] == native and native_config['reopened_customized_file']
    evidence['native_configuration'] = native_config
    _, mechanical = load_verified_receipt(ROOT / 'validation/revI-mechanical.json')
    assert mechanical['source_sha256'] == native
    assert all(not h['collisions'] for h in mechanical['halves'].values())
    assert mechanical['checker_sha256'] == sha('tools/freecad/export_revI.py')
    viewer = read('validation/revI-viewer.json')
    assert viewer['viewer_sha256'] == online and viewer['offline_sha256'] == offline
    for source in viewer['sources']:
        assert sha(source['path']) == source['sha256'], source['path']
    suite = read('build/audit-20261007/checks.json')
    assert suite['runner_sha256'] == sha('tools/audit_current.py')
    for source in suite['inputs']:
        assert sha(source['path']) == source['sha256'], source['path']
    assert {r['name'] for r in suite['results'] if r['exit_code'] != 0} == {'drc-left', 'drc-right'}
    pcb = {}
    for side in ['left', 'right']:
        drc = read('build/audit-20261007/drc-' + side + '.json')
        assert not drc['violations'] and len(drc['unconnected_items']) == 104
        pcb[side] = {'geometric_violations': 0, 'unconnected_items': 104,
                     'schematic_parity_items': len(drc['schematic_parity']),
                     'pcb_sha256': sha('hardware/revI/flan36-' + side + '.kicad_pcb')}
    browser = read('build/reliability-fix/browser.json')
    assert browser['passed'] and browser['online_sha256'] == online and browser['offline_sha256'] == offline
    evidence['browser'] = browser
    controls=read('validation/revI-audit-runner-controls.json')
    assert controls['passed'] and controls['runner_sha256']==sha('tools/audit_current.py')
    evidence['runner_controls']=controls
    for style in ['gameboy', 'hanafuda']:
        path = 'build/frame-orientation/viewer/' + style + '/result.json'
        item = read(path)
        assert item['viewer_sha256'] == offline, path
        assert not item.get('errors', []) and not item.get('runtime_errors', [])
        evidence['orientation_' + style] = item
    selected = read('design/frame-selection.json')['selected']
    assert selected == ['talavera', 'gameboy', 'snes', 'phone', 'ipod', 'hanafuda']
    evidence.update(validate_presentation(native, selected))
    sources = sorted({s['path'] for s in viewer['sources']} | {
        'validation/revI-socket-clearance.json', 'tools/freecad/install_socket_clearance.py',
        'tools/record_audit_completion.py', 'tools/audit_current.py', 'tools/check_audit_runner.py',
        'tools/audit_receipt_format.py', 'tools/check_audit_receipt_format.py',
        'tools/check_audit_adoption.py', 'tools/check_audit_completion.py',
        'validation/revI-audit-runner-controls.json',
        'tools/adopt_audit_repairs.py', 'tools/freecad/check_audit_repairs.py',
        'tools/freecad/check_audit_delivery.py', 'tools/freecad/check_revI.py',
        'validation/revI-audit-parameters.json', 'validation/revI-audit-delivery.json',
        'validation/revI-hotswap-registration.json', 'validation/revI-mechanical.json',
        'validation/revI-freecad.json', 'validation/revI-audit-adoption.json',
        'validation/revI-render.json', 'validation/revI-frames-render.json',
        'design/frame-selection.json',
    })
    report = {'schema': 1, 'scope': 'A1–A7 digital audit corrections and approved Hanafuda integration',
              'baseline_commit': 'b3e44990d9272327fef042439f1a6555eaae8c4f',
              'native_sha256': native, 'online_sha256': online, 'offline_sha256': offline,
              'selected_frames': selected, 'digital_corrections_passed': True,
              'full_fabrication_audit_passed': False, 'physical_acceptance': False,
              'pcb_readback': pcb, 'suite': suite, 'evidence': evidence,
              'sources': [{'path': p, 'sha256': sha(p)} for p in sources],
              'remaining': ['PCB routing and schematic parity', 'Integrated firmware',
                            'Purchased component dimensions, printed fits, retention and electrical operation'],
              'publication': 'Local acceptance only. Public readback is recorded separately after synchronization.'}
    (ROOT / 'validation/revI-audit-completion.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: source-bound digital audit corrections; fabrication remains unqualified')


if __name__ == '__main__':
    run()
