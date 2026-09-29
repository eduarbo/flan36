#!/usr/bin/env python3
"""Adopt the validated right artwork and preserve unrelated export bytes.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import collections
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def facets(path):
    raw = path.read_bytes()
    assert len(raw) == 84 + 50 * struct.unpack_from('<I', raw, 80)[0]
    return collections.Counter(raw[i:i+50] for i in range(84, len(raw), 50))


def run():
    source = Path(sys.argv[1]).resolve()
    target = ROOT / 'mechanical/revI'
    install = read(source / 'installation.json')
    meta = read(source / 'revI.json')
    mechanical = read(source / 'mechanical.json')
    original = read(ROOT / 'design/revI.json')
    styles = read(ROOT / 'design/frame-selection.json')['viewer']['installed_styles']
    assert set(install['frames']) == set(styles)
    for key in ['saved_reopened_recomputed', 'configuration_preserved',
                'left_materials_and_nonframe_parts_preserved', 'structural_blank_preserved',
                'all_right_decorative_roles_equal_translated_left',
                'former_mirrored_artwork_rejected', 'document_context_replay']:
        assert install[key], key
    assert install['source_sha256'] == sha(target / 'Flan36.FCStd')
    assert install['output_sha256'] == meta['fcstd_sha256'] == mechanical['source_sha256'] == sha(source / 'Flan36.FCStd')
    assert all(not half['collisions'] for half in mechanical['halves'].values())
    assert all(sha(ROOT / item['path']) == item['sha256'] for item in meta['inputs'])

    def allowed(name):
        return name in ['Flan36.FCStd', 'right-assembly.step', 'right-electronics-lid.stl',
                        'right-electronics-lid.step'] or any(
            name.startswith('right-frame-' + style + '.') or
            name.startswith('right-frame-' + style + '-') for style in styles)

    preserved, order_only = [], []
    for path in source.glob('*.stl'):
        if allowed(path.name):
            continue
        old = target / path.name
        assert old.is_file(), path.name
        if sha(path) != sha(old):
            assert facets(path) == facets(old), ('Unexpected mesh change', path.name)
            order_only.append(path.name)
        preserved.append(path.name)
    # Original STEP headers are retained for all unaffected designs. Their recorded
    # material hashes must continue to describe those exact retained files.
    for key in meta['frameVariants']:
        if key not in ['right-' + style for style in styles]:
            meta['frameVariants'][key] = original['frameVariants'][key]
    for name, part in meta['parts'].items():
        path = (source if allowed(name + '.stl') else target) / (name + '.stl')
        assert sha(path) == part['stl_sha256'], ('Part hash mismatch', name)
    for variant in meta['frameVariants'].values():
        for material in variant['material_parts']:
            for kind in ['stl', 'step']:
                name = material[kind]
                assert sha((source if allowed(name) else target) / name) == material[kind + '_sha256']

    adopted = []
    for path in sorted(source.iterdir()):
        if path.suffix in ['.stl', '.step', '.FCStd'] and allowed(path.name):
            if sha(path) != sha(target / path.name):
                shutil.copy2(path, target / path.name)
                adopted.append(path.name)
    (ROOT / 'design/revI.json').write_text(json.dumps(meta, indent=2) + '\n')
    for src, dst in [('mechanical.json', 'revI-mechanical.json'),
                     ('installation.json', 'revI-frame-orientation-native.json')]:
        shutil.copy2(source / src, ROOT / 'validation' / dst)
    assert sha(target / 'Flan36.FCStd') == install['output_sha256']
    report = dict(native_sha256=install['output_sha256'], adopted_files=adopted,
                  unrelated_stls_preserved=sorted(preserved),
                  identical_facets_different_enumeration=sorted(order_only),
                  source_inputs_verified=True)
    (ROOT / 'validation/revI-frame-orientation-adoption.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Adopted', len(adopted), 'files; preserved', len(preserved), 'unrelated meshes')


if __name__ == '__main__':
    run()
