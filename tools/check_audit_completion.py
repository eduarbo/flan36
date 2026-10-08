#!/usr/bin/env python3
"""Reject stale adoption/render evidence using isolated, non-CAD fixtures.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

SOURCE = Path(__file__).with_name('record_audit_completion.py')
SELECTED = ['talavera', 'gameboy', 'snes', 'phone', 'ipod', 'hanafuda']


def exercise(mode):
    spec = importlib.util.spec_from_file_location('completion_fixture', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        root = module.ROOT = Path(temp)

        def write(path, content):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content if isinstance(content, str) else json.dumps(content))

        def mutate(path, action):
            item = json.loads((root / path).read_text())
            action(item)
            write(path, item)

        def manifest(paths):
            return [{'path': path, 'sha256': module.sha(path)} for path in sorted(paths)]

        native = hashlib.sha256(b'native fixture').hexdigest()
        for script in ['adopt_audit_repairs', 'render_revI', 'render_frames', 'frame_finishes']:
            write(f'tools/{script}.py', 'isolated source fixture ' + script)
        model = {'fcstd_sha256': native,
                 'parts': {'left-display': {'visuals': [{'path': 'mechanical/revI/display.stl'}]}},
                 'frameVariants': {}, 'batteryLeadProfiles': {'left-1570': [], 'right-1570': []}}
        for side in ['left', 'right']:
            for style in SELECTED:
                model['frameVariants'][side + '-' + style] = {'material_parts': [
                    {'stl': f'{side}-frame-{style}-{role}.stl'}
                    for role in ['body', 'detail', 'accent', 'secondary']]}
        config = {'frames': {side: {'style': 'talavera'} for side in ['left', 'right']},
                  'batteries': {'left': '1570', 'right': '1570'},
                  'keycaps': {side: {'K01': {'variant': 'cap'}} for side in ['left', 'right']}}
        catalog = {'default_configuration': config, 'variants': [{'id': 'cap', 'path': 'keycaps/cap.stl'}]}
        layout = {'halves': {side: [{'ref': 'K01'}] for side in ['left', 'right']}}
        switches = {'choc-body': [{'path': 'components/body.stl'}], 'choc-stem': []}
        for path, data in [('design/revI.json', model), ('keycaps/catalog.json', catalog),
                           ('design/layout.json', layout), ('components/switches.json', switches),
                           ('design/frame-finishes.json', {'styles': SELECTED})]:
            write(path, data)
        assembly_paths = module.assembly_meshes(model, catalog, layout, switches)
        gallery_paths = {'design/revI.json', 'design/frame-finishes.json', 'tools/frame_finishes.py',
                         'mechanical/revI/display.stl'}
        gallery_paths.update('mechanical/revI/' + item['stl'] for style in SELECTED
                             for item in model['frameVariants']['left-' + style]['material_parts'])
        for path in assembly_paths | gallery_paths:
            if not (root / path).exists():
                write(path, 'isolated mesh fixture ' + path)
        views = {}
        for kind in module.ASSEMBLY_VIEWS:
            path = f'docs/images/revI-{kind}.png'
            write(path, 'isolated image fixture ' + kind)
            sides = ['left', 'right'] if kind in ['assembled', 'top'] else ['left']
            views[kind] = {'halves': sides, 'keys': len(sides) * 18,
                           'exploded': kind == 'stack', 'image_sha256': module.sha(path)}
        write('docs/images/revI-frame-gallery.png', 'isolated gallery fixture')
        adoption_path = 'validation/revI-audit-adoption.json'
        assembly_path = 'validation/revI-render.json'
        gallery_path = 'validation/revI-frames-render.json'
        write(adoption_path, {'passed': True, 'native_sha256': native,
                             'adopter_sha256': module.sha('tools/adopt_audit_repairs.py')})
        write(assembly_path, {'revision': 'I', 'model_sha256': module.sha('design/revI.json'),
                             'layout_sha256': module.sha('design/layout.json'),
                             'renderer_sha256': module.sha('tools/render_revI.py'),
                             'sources': manifest(module.ASSEMBLY_SOURCES),
                             'meshes': manifest(assembly_paths), 'views': views})
        write(gallery_path, {'styles': SELECTED, 'renderer_sha256': module.sha('tools/render_frames.py'),
                            'image_sha256': module.sha('docs/images/revI-frame-gallery.png'),
                            'sources': manifest(gallery_paths)})

        changes = {
            'adoption_failed': lambda: mutate(adoption_path, lambda d: d.update(passed=False)),
            'adoption_native': lambda: mutate(adoption_path, lambda d: d.update(native_sha256='stale')),
            'adopter_changed': lambda: write('tools/adopt_audit_repairs.py', 'changed'),
            'model_native': lambda: mutate('design/revI.json', lambda d: d.update(fcstd_sha256='stale')),
            'assembly_model': lambda: mutate(assembly_path, lambda d: d.update(model_sha256='stale')),
            'assembly_layout': lambda: mutate(assembly_path, lambda d: d.update(layout_sha256='stale')),
            'assembly_renderer': lambda: write('tools/render_revI.py', 'changed'),
            'assembly_color_source': lambda: mutate('keycaps/catalog.json', lambda d: d.update(color='changed')),
            'assembly_missing_source': lambda: mutate(assembly_path, lambda d: d['sources'].pop()),
            'assembly_duplicate_source': lambda: mutate(assembly_path, lambda d: d['sources'].append(d['sources'][0])),
            'assembly_mesh': lambda: write('mechanical/revI/left-tray.stl', 'changed'),
            'assembly_missing_mesh': lambda: mutate(assembly_path, lambda d: d['meshes'].pop()),
            'assembly_missing_view': lambda: mutate(assembly_path, lambda d: d['views'].pop('side')),
            'assembly_wrong_halves': lambda: mutate(assembly_path, lambda d: d['views']['side'].update(halves=['right'])),
            'assembly_wrong_keys': lambda: mutate(assembly_path, lambda d: d['views']['assembled'].update(keys=18)),
            'assembly_wrong_pose': lambda: mutate(assembly_path, lambda d: d['views']['stack'].update(exploded=False)),
            'assembly_image': lambda: write('docs/images/revI-side.png', 'changed'),
            'gallery_styles': lambda: mutate(gallery_path, lambda d: d.update(styles=SELECTED[:-1])),
            'gallery_renderer': lambda: write('tools/render_frames.py', 'changed'),
            'gallery_source': lambda: write('design/frame-finishes.json', 'changed'),
            'gallery_mesh': lambda: write('mechanical/revI/left-frame-hanafuda-detail.stl', 'changed'),
            'gallery_missing_mesh': lambda: mutate(gallery_path, lambda d: d['sources'].pop()),
            'gallery_image': lambda: write('docs/images/revI-frame-gallery.png', 'changed'),
        }
        if mode != 'valid':
            changes[mode]()
        error = None
        try:
            result = module.validate_presentation(native, SELECTED)
        except AssertionError as exc:
            error = str(exc)
        if mode == 'valid':
            assert error is None, error
            assert set(result) == {'adoption', 'revI-render', 'revI-frames-render'}
        else:
            assert error, f'{mode}: stale evidence was accepted'
        print('PASS:', mode)
        return list(changes)


if __name__ == '__main__':
    modes = exercise('valid')
    for mode in modes:
        exercise(mode)
    print(f'PASS: one valid and {len(modes)} stale/tampered presentation controls')
