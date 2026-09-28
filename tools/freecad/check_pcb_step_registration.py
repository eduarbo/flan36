"""Calibrate KiCad's actual STEP placement and check the delivered PCB models.

Run with run_macos.py; --calibrate-only needs no GUI. Calibration copies only
board stack settings and uses the committed TL3342 plus an asymmetric witness.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import FreeCAD as A
import Part

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
KICAD = Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
NATIVE_BOTTOM = 3.8
NATIVE_TOP = 5.4


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(shape):
    b = shape.cleaned().BoundBox
    return [getattr(b, k) for k in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]


def cli_export(board, output, *flags):
    command = [str(KICAD), 'pcb', 'export', 'step', '-f', '-o', str(output), *flags, str(board)]
    result = subprocess.run(command, text=True, capture_output=True)
    output.with_suffix('.log').write_text(result.stdout + result.stderr)
    if result.returncode or not output.is_file():
        raise RuntimeError(f'KiCad STEP export failed: {output.with_suffix(".log")}')
    shape = Part.read(str(output))
    assert shape.Solids and shape.isValid(), str(output)
    return shape


def board_settings(board):
    from export_pcb_components import children
    blocks = list(children(board.read_text()))
    general = next(b for b in blocks if b.startswith('(general'))
    thickness = float(re.search(r'\(thickness\s+([\d.]+)\)', general)[1])
    assert abs(thickness - (NATIVE_TOP - NATIVE_BOTTOM)) < 1e-8, thickness
    setup = next(b for b in blocks if b.startswith('(setup'))
    stackup = next((b for b in children(setup) if b.startswith('(stackup')), '')
    # These are the complete inputs controlling the board's vertical stack.
    signature = hashlib.sha256((str(thickness) + stackup).encode()).hexdigest()
    header = '\n'.join(b for b in blocks if any(b.startswith('(' + k) for k in
                        ('version ', 'general', 'layers', 'setup')))
    return header, signature


def calibrate(output, board=None):
    from export_pcb_components import difference
    board = board or ROOT / 'hardware/revI/flan36-left.kicad_pcb'
    output.mkdir(parents=True, exist_ok=True)
    header, settings_hash = board_settings(board)
    source = ROOT / 'components/sources/SW_SPST_TL3342.step'
    nominal = Part.read(str(source))
    witness = Part.makeBox(.7, 1.1, 1.3, A.Vector(8, 3, 2))
    compound = Part.makeCompound([*nominal.Solids, witness])
    model = output / 'tl3342-with-witness.step'
    compound.exportStep(str(model))
    edges = '\n'.join(f'(gr_line (start {a} {b}) (end {c} {d}) '
                       '(stroke (width 0.05) (type default)) (layer "Edge.Cuts"))'
                       for a, b, c, d in ((0, 0, 60, 0), (60, 0, 60, 40),
                                         (60, 40, 0, 40), (0, 40, 0, 0)))
    results = {}
    for name, layer, angle in (('front0', 'F.Cu', 0), ('back0', 'B.Cu', 0),
                                ('back90', 'B.Cu', 90), ('back180', 'B.Cu', 180)):
        pcb = output / (name + '.kicad_pcb')
        pcb.write_text('(kicad_pcb\n' + header + '\n' + edges +
                       f'\n(footprint "Calibration" (layer "{layer}") (at 20 20 {angle}) '
                       '(property "Reference" "SW2" (at 0 0) (layer "F.SilkS") '
                       '(effects (font (size 1 1) (thickness .15)))) '
                       f'(model {json.dumps(str(model))} (offset (xyz 0 0 0)) '
                       '(scale (xyz 1 1 1)) (rotate (xyz 0 0 0))))\n)\n')
        path = output / (name + '.step')
        exported = cli_export(pcb, path, '--no-board-body', '--component-filter', 'SW2')
        expected = compound.copy()
        if layer == 'B.Cu':
            expected.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
        expected.rotate(A.Vector(), A.Vector(0, 0, 1), angle)
        # Measure only Z translation. Independent witness constrains X/Y/rotation.
        def center_z(shape):
            return sum(s.CenterOfMass.z * s.Volume for s in shape.Solids) / sum(s.Volume for s in shape.Solids)
        z = center_z(exported) - center_z(expected)
        expected.translate(A.Vector(20, -20, z))
        delta = difference(expected, exported)
        assert delta < .001, (name, delta)
        results[name] = {'layer': layer, 'angle_deg': angle, 'model_origin_z_mm': z,
                         'difference_mm3': delta, 'step_sha256': sha(path),
                         'step': str(path.relative_to(ROOT))}
    body_path = output / 'board-only.step'
    body = cli_export(output / 'front0.kicad_pcb', body_path, '--board-only')
    b = bounds(body)
    shift = (NATIVE_BOTTOM + NATIVE_TOP - b[2] - b[5]) / 2
    corrections = {
        'F.Cu': NATIVE_TOP - shift - results['front0']['model_origin_z_mm'],
        'B.Cu': results['back0']['model_origin_z_mm'] + shift - NATIVE_BOTTOM,
    }
    for name in ('back90', 'back180'):
        assert abs(results[name]['model_origin_z_mm'] - results['back0']['model_origin_z_mm']) < 1e-7
    corrected_checks = {}
    for name, layer, angle in (('front0', 'F.Cu', 0), ('back90', 'B.Cu', 90)):
        corrected_model = output / (name + '-corrected-model.step')
        corrected = compound.copy()
        corrected.translate(A.Vector(0, 0, corrections[layer]))
        corrected.exportStep(str(corrected_model))
        pcb = output / (name + '-corrected.kicad_pcb')
        pcb.write_text((output / (name + '.kicad_pcb')).read_text().replace(
            json.dumps(str(model)), json.dumps(str(corrected_model))))
        path = output / (name + '-corrected.step')
        actual = cli_export(pcb, path, '--no-board-body', '--component-filter', 'SW2')
        actual.translate(A.Vector(0, 0, shift))
        expected = compound.copy()
        if layer == 'B.Cu':
            expected.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
        expected.rotate(A.Vector(), A.Vector(0, 0, 1), angle)
        expected.translate(A.Vector(20, -20, NATIVE_BOTTOM if layer == 'B.Cu' else NATIVE_TOP))
        delta = difference(expected, actual)
        assert delta < .001, (name, 'corrected independent CLI witness', delta)
        corrected_checks[name] = {'difference_mm3': delta, 'step_sha256': sha(path),
                                  'step': str(path.relative_to(ROOT))}
    report = {'schema': 'flan36-kicad-step-calibration-1', 'passed': True,
              'checker_sha256': sha(Path(__file__)), 'source_step_sha256': sha(source),
              'kicad_version': subprocess.check_output([str(KICAD), 'version'], text=True).strip(),
              'board_settings_sha256': settings_hash, 'cases': results,
              'corrected_independent_cli_witness': corrected_checks,
              'bottom_rotation': 'Rz(footprint angle) * Rx(180 degrees)',
              'board_dielectric_z_mm': [b[2], b[5]], 'native_board_envelope_z_mm': [NATIVE_BOTTOM, NATIVE_TOP],
              'dielectric_vs_native_thickness_difference_mm': (NATIVE_TOP - NATIVE_BOTTOM) - (b[5] - b[2]),
              'kicad_to_native_z_mm': shift, 'local_z_correction_mm': corrections,
              'datum_policy': 'One board-midplane registration. Local component Z compensation cancels measured KiCad model standoff against the simplified native total-board envelope. Dielectric-only body is not asserted equal to that envelope.',
              'physical_acceptance': False}
    (output / 'calibration.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def check(source, calibration, output, receipt):
    from export_pcb_components import (difference, footprints, sha as digest,
        model_members, model_shape, member_readback, socket_status)
    output.mkdir(parents=True, exist_ok=True)
    before = digest(source)
    doc = A.openDocument(str(source))
    parts = {o.PartID: o for o in doc.Objects if hasattr(o, 'PartID')}
    report = {'schema': 'flan36-bottom-reset-step-1', 'passed': False,
              'source_sha256': before, 'checker_sha256': sha(Path(__file__)),
              'exporter_sha256': sha(Path(__file__).with_name('export_pcb_components.py')),
              'calibration': calibration, 'halves': {}, 'physical_acceptance': False}
    for side in ('left', 'right'):
        pcb = ROOT / f'hardware/revI/flan36-{side}.kicad_pcb'
        pcb_hash = sha(pcb)
        assert board_settings(pcb)[1] == calibration['board_settings_sha256']
        fps = footprints(pcb)
        assert fps['SW2']['layer'] == 'B.Cu'
        reset_bounds = bounds(parts[side + '-reset'].Shape)
        reset_x, reset_y, reset_angle = fps['SW2']['pose']
        assert abs(reset_angle) < 1e-8
        expected_reset_bounds = [reset_x - 3.2, -reset_y - 2.6, 2.26,
                                 reset_x + 3.2, -reset_y + 2.6, NATIVE_BOTTOM]
        assert max(abs(a - b) for a, b in zip(reset_bounds, expected_reset_bounds)) < 1e-5, (
            side, 'native bottom reset datum', reset_bounds, expected_reset_bounds)
        checks = {}
        for ref, part in {'U1': 'mcu', 'J2': 'display', 'J1': 'jst', 'SW1': 'slider', 'SW2': 'reset'}.items():
            path = output / (side + '-' + part + '.step')
            actual = cli_export(pcb, path, '--no-board-body', '--component-filter', ref)
            actual.translate(A.Vector(0, 0, calibration['kicad_to_native_z_mm']))
            members = model_members(parts, side, part)
            native = model_shape(members)
            delta = difference(native, actual)
            assert delta < .001, (side, ref, delta)
            checks[ref] = {'layer': fps[ref]['layer'], 'native_placement_difference_mm3': delta,
                           'actual_kicad_export_reimported': True,
                           'step_path': str(path.relative_to(ROOT)), 'step_sha256': sha(path),
                           'local_model_sha256': sha(ROOT / f'hardware/revI/models/{side}-{part}.step'),
                           'native_bounds_mm': bounds(native), 'registered_kicad_bounds_mm': bounds(actual)}
            if part == 'display':
                checks[ref]['native_components'] = member_readback(members, actual)
                checks[ref]['retained_display_socket'] = socket_status(members[-1])
            print(f'Actual KiCad STEP registration: {side}-{part} verified', flush=True)
        assert sha(pcb) == pcb_hash
        reset = checks['SW2']
        report['halves'][side] = {'pcb_sha256': pcb_hash, 'reset_layer': 'B.Cu',
                                 **reset, 'components': checks}
    A.closeDocument(doc.Name)
    assert digest(source) == before
    report['passed'] = True
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    return report


def check_j2_fixture(output):
    """Isolated color/body roundtrip; does not qualify the final native assembly."""
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        raise RuntimeError('Use run_macos.py with its default offscreen platform')
    import FreeCADGui as G
    import export_pcb_components as exporter
    G.showMainWindow()
    G.getMainWindow().hide()
    output.mkdir(parents=True, exist_ok=True)
    doc = A.newDocument('J2Fixture')
    def feature(name, shape, color, part_id=None):
        obj = doc.addObject('Part::Feature', name)
        obj.Shape = shape
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.DiffuseColor = [color] * len(shape.Faces)
        if part_id:
            obj.addProperty('App::PropertyString', 'PartID')
            obj.PartID = part_id
        return obj
    display = feature('Display', Part.makeBox(14, 36, 1, A.Vector(115.8, -52.8, 12.4)),
                      (.1, .5, .2), 'left-display')
    housing = feature('L_SlimDisplaySocketHousing', Part.makeBox(13.2, 3, 5, A.Vector(116.2, -52.3, 5.4)), (.12, .12, .12))
    pins = feature('L_SlimDisplaySocketPins', Part.makeCompound([
        Part.makeCylinder(.2, 10.4, A.Vector(117.72 + i * 2.54, -50.8, 2)) for i in range(5)]), (.8, .7, .2))
    socket = doc.addObject('Part::Compound', 'Socket')
    socket.Links = [housing, pins]
    socket.addProperty('App::PropertyString', 'PartID')
    socket.PartID = 'left-display-socket'
    socket.addProperty('App::PropertyLinkList', 'VisualParts')
    socket.VisualParts = socket.Links
    doc.recompute()
    parts = {obj.PartID: obj for obj in (display, socket)}
    members = exporter.model_members(parts, 'left', 'display')
    reference = exporter.model_shape(members)
    pose = [117.72, 50.8, 0]
    report = {'scope': 'Synthetic J2 exporter fixture only; final native and actual PCB checks remain separate.',
              'physical_acceptance': False, 'checker_sha256': sha(Path(__file__)),
              'exporter_sha256': sha(Path(exporter.__file__)), 'models': {}}
    exporter.export('fixture-display', exporter.local_shape(reference, pose, 'F.Cu', -.04),
                    exporter.model_colors(members), output, report, pose, 'F.Cu', -.04, reference, members)
    entry = report['models']['fixture-display']
    assert set(entry['native_components']) == set(parts)
    assert entry['distinct_colors'] == 3
    assert entry['retained_display_socket']['measured_native_housing_height_mm'] == 5
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    A.closeDocument(doc.Name)


def main():
    args = sys.argv[1:]
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        args = args[args.index(str(Path(__file__).resolve())) + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibrate-only', action='store_true')
    parser.add_argument('--j2-fixture', action='store_true', help='Run only the isolated J2 colored STEP roundtrip')
    parser.add_argument('--source', type=Path, default=ROOT / 'mechanical/revI/Flan36.FCStd')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/slim-flush/pcb-step-registration')
    options = parser.parse_args(args)
    output = options.output.resolve()
    if options.j2_fixture:
        check_j2_fixture(output / 'j2-fixture')
        return
    calibration = calibrate(output / 'calibration')
    if not options.calibrate_only:
        check(options.source.resolve(), calibration, output / 'actual', ROOT / 'validation/revI-bottom-reset-step.json')
    print(json.dumps({'passed': True, 'calibrate_only': options.calibrate_only,
                      'local_z_correction_mm': calibration['local_z_correction_mm']}), flush=True)


if __name__ == '__main__':
    main()
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        os._exit(0)
