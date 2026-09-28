"""Synchronize revI's existing relative STEP references with the native models.

PCB footprints, nets, model references and historical revisions are never written.
Bottom mounting and KiCad's model-plane offsets are independently calibrated by
check_pcb_step_registration.py against actual CLI-exported STEP geometry.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import hashlib
import json
import os
import re
import sys

import FreeCAD as A
import Part

R = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def children(text):
    depth = 0
    quoted = escaped = False
    start = None
    for i, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '(':
            depth += 1
            if depth == 2:
                start = i
        elif char == ')':
            if depth == 2:
                yield text[start:i + 1]
            depth -= 1


def footprints(pcb):
    result = {}
    for block in children(Path(pcb).read_text()):
        if not block.startswith('(footprint '):
            continue
        ref = re.search(r'\(property\s+"Reference"\s+"([^\"]+)"', block)[1]
        fields = list(children(block))
        at = next(s for s in fields if s.startswith('(at '))
        values = [float(v) for v in at[4:-1].split()]
        layer = re.search(r'"([FB]\.Cu)"', next(s for s in fields if s.startswith('(layer ')))[1]
        result[ref] = {'block': block, 'pose': values + [0.] if len(values) == 2 else values, 'layer': layer}
    return result


def difference(first_shape, second_shape):
    # Match constituent solids first, preserving overlapping pad/body regions.
    remaining = list(second_shape.Solids)
    assert len(first_shape.Solids) == len(remaining), (len(first_shape.Solids), len(remaining))
    def bounds(shape):
        b = shape.cleaned().BoundBox
        return [getattr(b, k) for k in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]
    total = 0.
    for first in first_shape.Solids:
        box = bounds(first)
        def distance(second):
            return max(abs(x - y) for x, y in zip(box, bounds(second)))
        index = min(range(len(remaining)), key=lambda i: distance(remaining[i]))
        second = remaining.pop(index)
        assert distance(second) < 1e-5, (box, bounds(second), distance(second))
        total += first.cut(second, 1e-6).Volume + second.cut(first, 1e-6).Volume
    return total


def model_members(parts, side, part):
    """J2's existing model reference carries both removable and retained pieces."""
    members = [parts[side + '-' + part]]
    if part == 'display':
        members.append(parts[side + '-display-socket'])
    return members


def model_shape(members):
    return Part.makeCompound([solid for obj in members for solid in obj.Shape.Solids])


def model_colors(members):
    colors = []
    for obj in members:
        if obj.PartID.endswith('-display-socket'):
            # New retained housing and pins have separate native material objects.
            visual = list(obj.VisualParts)
            assert visual, (obj.Name, 'socket material objects missing')
            assert difference(obj.Shape, Part.makeCompound([v.Shape for v in visual])) < .001
            component_colors = []
            for item in visual:
                col = list(item.ViewObject.DiffuseColor)
                component_colors.extend(col if len(col) == len(item.Shape.Faces)
                                        else [item.ViewObject.ShapeColor] * len(item.Shape.Faces))
            # Part::Compound retains the Links/VisualParts ordering.
            assert list(obj.Links) == visual, (obj.Name, 'socket face material ordering')
            assert len(component_colors) == len(obj.Shape.Faces)
        else:
            col = list(obj.ViewObject.DiffuseColor)
            component_colors = col if len(col) == len(obj.Shape.Faces) else [obj.ViewObject.ShapeColor] * len(obj.Shape.Faces)
        colors.extend(component_colors)
    return colors


def member_readback(members, actual):
    """Match every native body's solids against the same combined STEP assembly."""
    def box(shape):
        b = shape.cleaned().BoundBox
        return [getattr(b, k) for k in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]
    remaining = list(actual.Solids)
    result = {}
    for obj in members:
        matched = []
        for solid in obj.Shape.Solids:
            expected = box(solid)
            assert remaining, (obj.PartID, 'missing native solid')
            index = min(range(len(remaining)), key=lambda i: max(abs(a - b) for a, b in zip(expected, box(remaining[i]))))
            matched.append(remaining.pop(index))
        delta = difference(obj.Shape, Part.makeCompound(matched))
        assert delta < .001, (obj.PartID, 'component body readback', delta)
        result[obj.PartID] = {'native_object': obj.Name, 'solid_count': len(matched),
                              'native_placement_difference_mm3': delta}
    assert not remaining, 'Unexpected bodies in combined STEP model'
    return result


def socket_status(obj):
    housing = [part for part in obj.VisualParts if part.Name.endswith('DisplaySocketHousing')]
    assert len(housing) == 1, (obj.PartID, 'retained socket housing missing')
    box = housing[0].Shape.cleaned().BoundBox
    level = obj.Document.getObject('LevelStackReceipt') is not None
    height = 4.57 if level else 5.
    assert abs(box.ZMin - 5.4) < 1e-5 and abs(box.ZLength - height) < 1e-5, (
        obj.PartID, 'nominal socket height', box.ZMin, box.ZLength)
    return {'nominal_housing_height_mm': height, 'measured_native_housing_height_mm': box.ZLength,
            'native_housing_dimensions_mm': [box.XLength, box.YLength, box.ZLength],
            'native_housing_bounds_mm': [getattr(box, k) for k in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')],
            'physical_acceptance': False,
            'height_source': 'https://suddendocs.samtec.com/catalog_english/slw.pdf' if level else 'https://typeractive.xyz/products/5-pin-sockets',
            'limitation': 'Samtec SLW/TLW nominal mating geometry; nice!view finished-hole fit, actual engagement and solder tolerances remain unqualified.' if level else 'Supplier states 5 mm socket height plus 2 mm display pin. Socket lateral body dimensions, contacts, engagement and tolerances remain nominal assumptions; geometry readback is not physical qualification.'}


def local_shape(shape, pose, layer, correction=0.):
    """Inverse of calibrated Rz(angle) Rx(180) bottom placement, never reflection."""
    assert layer in ('F.Cu', 'B.Cu')
    result = shape.copy()
    result.translate(A.Vector(-pose[0], pose[1], -(3.8 if layer == 'B.Cu' else 5.4)))
    result.rotate(A.Vector(), A.Vector(0, 0, 1), -pose[2])
    if layer == 'B.Cu':
        result.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
    result.translate(A.Vector(0, 0, correction))
    return result


def nominal_shape(shape, pose, layer, correction=0.):
    result = shape.copy()
    result.translate(A.Vector(0, 0, -correction))
    if layer == 'B.Cu':
        result.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
    result.rotate(A.Vector(), A.Vector(0, 0, 1), pose[2])
    result.translate(A.Vector(pose[0], -pose[1], 3.8 if layer == 'B.Cu' else 5.4))
    return result


def export(name, shape, colors, out, report, pose=None, layer=None, correction=0., reference=None, members=None):
    import ImportGui
    # Preserve analytic geometry and placement on constituent solids.
    shape = Part.makeCompound(shape.Solids)
    temp = A.newDocument('ModelExport')
    obj = temp.addObject('Part::Feature', 'Component')
    obj.Label, obj.Shape = name, shape
    obj.ViewObject.DiffuseColor = colors
    temp.recompute()
    path = out / (name + '.step')
    ImportGui.export([obj], str(path))
    A.closeDocument(temp.Name)
    loaded = A.newDocument('ModelReadback')
    ImportGui.insert(str(path), loaded.Name)
    loaded.recompute()
    items = [o for o in loaded.Objects if o.TypeId == 'Part::Feature' and not o.Shape.isNull()]
    leaves = []
    for item in items:
        leaf = item.Shape.copy()
        leaf.Placement = item.getGlobalPlacement()
        leaves.append(leaf)
    read = Part.makeCompound(leaves)
    delta = difference(shape, read)
    assert delta < .001, (name, 'STEP surface readback', delta)
    distinct = len({tuple(round(v, 3) for v in c[:3]) for item in items for c in item.ViewObject.DiffuseColor})
    expected = len({tuple(round(v, 3) for v in c[:3]) for c in colors})
    assert distinct == expected, (name, 'STEP colors', distinct, expected)
    def colored_area(sh, col):
        if len(col) == 1:
            col = list(col) * len(sh.Faces)
        assert len(sh.Faces) == len(col)
        areas = {}
        for face, color in zip(sh.Faces, col):
            key = tuple(round(v, 3) for v in color[:3])
            areas[key] = areas.get(key, 0) + face.Area
        return areas
    wanted, actual = colored_area(shape, colors), {}
    for item in items:
        for key, area in colored_area(item.Shape, item.ViewObject.DiffuseColor).items():
            actual[key] = actual.get(key, 0) + area
    assert actual.keys() == wanted.keys()
    area_error = max(abs(wanted[k] - actual[k]) for k in wanted)
    assert area_error < 1e-4, (name, 'STEP face material area', area_error)
    placed = difference(nominal_shape(read, pose, layer, correction), reference) if pose else 0.
    assert placed < .001, (name, 'nominal footprint registration', placed)
    report['models'][name] = {'path': str(path.relative_to(R)), 'sha256': sha(path),
        'import_difference_mm3': delta, 'native_placement_difference_mm3': placed,
        'distinct_colors': distinct, 'color_area_error_mm2': area_error,
        'footprint_pose_xy_deg': pose, 'footprint_layer': layer, 'local_z_correction_mm': correction}
    if members:
        report['models'][name]['native_components'] = member_readback(
            members, nominal_shape(read, pose, layer, correction))
        if len(members) > 1:
            report['models'][name]['retained_display_socket'] = socket_status(members[-1])
    A.closeDocument(loaded.Name)
    sys.__stdout__.write(name + ' verified\n')
    sys.__stdout__.flush()


def main():
    # Offscreen Qt is required for XCAF color export, but never opens a desktop window.
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        raise RuntimeError('Use tools/freecad/run_macos.py with its default offscreen platform')
    import FreeCADGui as G
    G.showMainWindow()
    G.getMainWindow().hide()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_pcb_step_registration import calibrate, board_settings, check
    source = R / 'mechanical/revI/Flan36.FCStd'
    digest = sha(source)
    work = R / 'build/slim-flush/pcb-step-registration'
    calibration = calibrate(work / 'calibration')
    native = A.openDocument(str(source))
    parts = {o.PartID: o for o in native.Objects if hasattr(o, 'PartID')}
    out = R / 'hardware/revI/models'
    report = {'source_sha256': digest, 'checker_sha256': sha(Path(__file__)),
              'models': {}, 'pcb_unchanged': {}, 'calibration': calibration,
              'scope': 'Colored local STEP readback plus actual KiCad CLI STEP assembly registration. Simplified nominal models, not physical fit or routing acceptance.',
              'physical_acceptance': False}
    for side in ('left', 'right'):
        pcb = R / f'hardware/revI/flan36-{side}.kicad_pcb'
        before = sha(pcb)
        assert board_settings(pcb)[1] == calibration['board_settings_sha256']
        fps = footprints(pcb)
        for ref, part in {'U1': 'mcu', 'J2': 'display', 'J1': 'jst', 'SW1': 'slider', 'SW2': 'reset'}.items():
            fp = fps[ref]
            block, pose, layer = fp['block'], fp['pose'], fp['layer']
            name = side + '-' + part
            assert '${KIPRJMOD}/models/' + name + '.step' in block
            assert layer == ('B.Cu' if ref == 'SW2' else 'F.Cu'), (name, layer)
            for field, expected in (('offset', [0, 0, 0]), ('rotate', [0, 0, 0]), ('scale', [1, 1, 1])):
                value = re.search(r'\(' + field + r'\s*\(xyz\s+([^)]*)\)', block)
                assert [float(v) for v in value[1].split()] == expected
            members = model_members(parts, side, part)
            reference = model_shape(members)
            correction = calibration['local_z_correction_mm'][layer]
            shape = local_shape(reference, pose, layer, correction)
            colors = model_colors(members)
            export(name, shape, colors, out, report, pose, layer, correction, reference,
                   members if part == 'display' else None)
        assert sha(pcb) == before
        report['pcb_unchanged'][side] = before
    A.closeDocument(native.Name)
    # Keep the historical filename and its conventional component-local axes.
    switch = A.openDocument(str(R / 'components/sources/SW_Kailh_Choc_V1.FCStd'))
    shapes, colors = [], []
    palette = {'Upper_Housing': (.816, .827, .796), 'Lower_Housing': (.141, .153, .161),
               'Pin_1': (.725, .624, .384), 'Pin_2': (.725, .624, .384), 'Stem': (.729, .251, .278)}
    for obj in switch.Objects:
        if obj.Label in palette:
            shape = obj.Shape.copy()
            shape.Placement = obj.getGlobalPlacement()
            shapes.append(shape)
            colors.extend([palette[obj.Label]] * len(shape.Faces))
    export('choc-envelope', Part.makeCompound(shapes), colors, out, report)
    A.closeDocument(switch.Name)
    assert sha(source) == digest
    report['actual_kicad_registration_receipt'] = 'validation/revI-bottom-reset-step.json'
    check(source, calibration, work / 'actual', R / report['actual_kicad_registration_receipt'])
    (R / 'validation/revI-pcb-component-models.json').write_text(json.dumps(report, indent=2) + '\n')
    sys.__stdout__.write('PASS: 11 colored relative STEP models; actual KiCad CLI registration checked for both electronics sets; PCB files unchanged\n')
    sys.__stdout__.flush()


if __name__ == '__main__':
    main()
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        os._exit(0)
