#!/usr/bin/env python3
"""Exercise adoption preflight and destination verification in temporary fixtures.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name('adopt_audit_repairs.py')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
A, B, C, D = (0., 0., 0.), (2., 1., 0.), (2., 1., 3.), (0., 0., 3.)
OLD_RECTANGLE = [(A, B, C), (A, C, D)]
NEW_RECTANGLE = [(A, B, D), (B, C, D)]


def write_mesh(path, triangles):
    data = bytearray(80) + struct.pack('<I', len(triangles))
    for triangle in triangles:
        data.extend(struct.pack('<12fH', 0., 0., 0.,
                                *(coordinate for point in triangle for coordinate in point), 0))
    path.write_bytes(data)


def exercise(mode):
    spec = importlib.util.spec_from_file_location('adoption_fixture', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        candidate, target = root / 'candidate', root / 'mechanical/revI'
        for directory in [candidate, target, root / 'design', root / 'validation']:
            directory.mkdir(parents=True, exist_ok=True)
        module.ROOT = root
        (target / 'Flan36.FCStd').write_bytes(b'baseline fixture')
        (candidate / 'Flan36.FCStd').write_bytes(b'candidate fixture')
        part = 'left-tray.stl'
        (candidate / part).write_bytes(b'verified mesh fixture')
        digest = sha(candidate / 'Flan36.FCStd')
        manifest = {part: sha(candidate / part)}
        if mode in ['rectangle_preserved', 'unrelated_rectangle_rejected']:
            untouched = ('left-frame-flan-body.stl' if mode == 'rectangle_preserved'
                         else 'left-case-solid-plate.stl')
            write_mesh(target / untouched, OLD_RECTANGLE)
            write_mesh(candidate / untouched, NEW_RECTANGLE)
            preserved_digest = sha(target / untouched)
            manifest[untouched] = sha(candidate / untouched)
        def write(name, value):
            (candidate / name).write_text(json.dumps(value))
        write('revI.json', {'fcstd_sha256': digest, 'inputs': [],
              'parts': {'left-tray': {'stl_sha256': manifest[part], 'visuals': []}},
              'frameVariants': {}, 'batteryLeadProfiles': {}, 'hotswap_model': {'visuals': []}})
        write('mechanical.json', {'source_sha256': digest, 'halves': {'left': {'collisions': []}}, 'exported_files': manifest})
        write('delivery.json', {'source_sha256': digest, 'passed': True,
              'baseline_sha256': sha(target / 'Flan36.FCStd')})
        for name in ['parameter-checks.json', 'hotswap.json']:
            write(name, {'source_sha256': digest, 'passed': True})
        write('relief.json', {'source_sha256':digest,'passed':True,'halves':{'left':{'socket_to_relieved_post_mm':.25,'minimum_pilot_web_mm':1.25}},'unrelated_parts_geometrically_unchanged':True})
        write('freecad.json', {'source_sha256':digest,'reopened_customized_file':True})
        if mode == 'tampered':
            (candidate / part).write_bytes(b'changed after export')
        if mode == 'unlisted':
            (candidate / 'left-diodes-extra.stl').write_bytes(b'unverified')
        before = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
        real_copy = module.shutil.copy2
        copies = []
        def copying(src, dst):
            copies.append(str(dst))
            result = real_copy(src, dst)
            if mode == 'copy_corruption' and Path(dst).name == part:
                Path(dst).write_bytes(b'corrupted destination')
            return result
        error = None
        with patch.object(sys, 'argv', [str(SOURCE), str(candidate)]), patch.object(module.shutil, 'copy2', copying):
            try:
                module.run()
            except AssertionError as exc:
                error = str(exc)
        if mode in ['valid', 'rectangle_preserved']:
            assert error is None, error
            assert sha(target / part) == manifest[part]
            receipt = json.loads((root / 'validation/revI-audit-adoption.json').read_text())
            assert receipt['passed']
            if mode == 'rectangle_preserved':
                assert sha(target / untouched) == preserved_digest
                assert str(target / untouched) not in copies
                assert receipt['preserved_meshes'] == [untouched]
                proof = receipt['preserved_rectangle_retriangulations']
                assert len(proof) == 1 and proof[0]['rectangles'] == 1
                assert proof[0]['preserved_sha256'] == preserved_digest
                assert proof[0]['candidate_sha256'] == manifest[untouched]
                assert proof[0]['coordinate_rounding'] is False
        else:
            expected = {'tampered': 'Changed after export', 'unlisted': 'Unverified export',
                        'copy_corruption': 'Adoption readback failed',
                        'unrelated_rectangle_rejected': 'Unrelated native mesh changed'}[mode]
            assert error and expected in error, (mode, error)
            assert not (root / 'validation/revI-audit-adoption.json').exists()
            if mode != 'copy_corruption':
                assert not copies
                assert before == {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
        print('PASS:', mode)


def rectangle_controls():
    spec = importlib.util.spec_from_file_location('rectangle_fixture', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    moved = (C[0], C[1] + .00001, C[2])
    controls = {
        'valid': NEW_RECTANGLE,
        'cyclic_order': [(B, D, A), (C, D, B)],
        'nonplanar': [(A, B, D), (B, (2., 1.125, 3.), D)],
        'moved_point_below_fast_precision': [(A, B, D), (B, moved, D)],
        'reversed_winding': [tuple(reversed(t)) for t in NEW_RECTANGLE],
        'one_reversed_face': [NEW_RECTANGLE[0], tuple(reversed(NEW_RECTANGLE[1]))],
        'duplicate': NEW_RECTANGLE + [NEW_RECTANGLE[0]],
        'overlap_and_hole': [(A, B, D), (A, C, D)],
        'missing_triangle': NEW_RECTANGLE[:1],
        'nonvertical_quad': [((0.,0.,0.),(2.,1.,0.),(0.,1.,0.)),
                             ((2.,1.,0.),(2.,2.,0.),(0.,1.,0.))],
    }
    with tempfile.TemporaryDirectory() as temp:
        old, new = Path(temp) / 'old.stl', Path(temp) / 'new.stl'
        # A non-rectangular unchanged face must survive as exact raw triangles.
        unchanged = [((10., 0., 0.), (11., 0., 0.), (10., 1., 0.))]
        write_mesh(old, OLD_RECTANGLE + unchanged)
        for name, triangles in controls.items():
            write_mesh(new, triangles + unchanged)
            before = sha(old)
            error = None
            try:
                result = module.rectangle_retriangulation(old, new)
            except AssertionError as exc:
                error = str(exc)
            if name in ['valid', 'cyclic_order']:
                assert error is None, error
                assert result['rectangles'] == 1 and result['identical_raw_triangles'] == 1
                assert result['changed_triangles_per_mesh'] == 2
                assert result['coordinate_rounding'] is False
            else:
                assert error, f'{name}: invalid mesh change was accepted'
            assert sha(old) == before
            print('PASS: rectangle', name)


if __name__ == '__main__':
    for mode in ['valid', 'tampered', 'unlisted', 'copy_corruption',
                 'rectangle_preserved', 'unrelated_rectangle_rejected']:
        exercise(mode)
    rectangle_controls()
