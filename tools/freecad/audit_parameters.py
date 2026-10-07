"""Read-only native edit/USB probes for the 2026-10-07 audit.
Run with tools/freecad/run_macos.py; never saves the source document.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

import FreeCAD as A
import Part

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/audit-20261007'


def bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return [float(getattr(b, k)) for k in ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]


def run():
    source = ROOT / 'mechanical/revI/Flan36.FCStd'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    doc = A.openDocument(str(source))
    for prefix in ('L_', 'R_'):
        doc.getObject(prefix + 'Half').Placement = A.Placement()
    doc.recompute()
    params = doc.Parameters
    # USB access is a separate baseline test. Freeze these solids before edits.
    usb_sources = {o.Name: o.Shape.copy() for o in doc.Objects if any(o.Name == prefix + 'Case_' + style + '_' + part for prefix in ['L_', 'R_'] for style in ['solid', 'rim', 'terrace', 'level'] for part in ['base', 'plate'])}
    names = ['NiceViewVisual0', 'NiceViewVisual1', 'NiceViewVisual2', 'GlassWindow',
             'SlimDisplayMaleSpacer', 'SlimDisplayMaleContacts', 'SlimDisplaySocketHousing',
             'SlimDisplaySocketPins', 'LevelDisplaySolderReserve', 'LevelDisplayPCBRelief',
             'LevelHeaderServiceWell']
    targets = [doc.getObject('L_' + n) for n in names] + [doc.L_FlushFrame_talavera_Final, doc.L_FrameInside]

    def recompute_probe():
        # Recompute these objects and their dependencies, without rebuilding all
        # hidden historical frame bodies. The source is never saved.
        doc.recompute(targets)

    def snapshot():
        result = {}
        for side, prefix in [('left', 'L_')]:
            glass = doc.getObject(prefix + 'NiceViewVisual2').Shape
            objects = {n: bounds(doc.getObject(prefix + n).Shape) for n in names}
            frames = {}
            for style in ['talavera']:
                obj = doc.getObject(prefix + 'FlushFrame_' + style + '_Final')
                frame = obj.Shape
                blank = obj.SmoothSource.Shape
                mats = {}
                for material in obj.MaterialParts:
                    mats[material.ColorRole] = {'bounds_mm': bounds(material.Shape), 'valid': material.Shape.isValid()}
                frames[style] = {
                    'glass_gap_mm': frame.distToShape(glass)[0],
                    'glass_collision_mm3': frame.common(glass).Volume,
                    'outside_blank_mm3': frame.cut(blank).Volume,
                    'missing_from_blank_mm3': blank.cut(frame).Volume,
                    'bounds_mm': bounds(frame), 'valid': frame.isValid(), 'materials': mats,
                    'ordinary_inlay': {o.Name: bounds(o.Shape) for o in doc.Objects if o.Name.startswith(prefix + 'FlushFrame_' + style + '_R4_') and o.Name.endswith('_ordinary')},
                    'cavity_bounds_mm': bounds(doc.getObject(prefix + 'FrameInside').Shape),
                }
            result[side] = {'objects': objects, 'frames': frames}
        return result

    report = {'source_sha256': digest, 'physical_acceptance': False,
              'initial_parameters_mm': {k: getattr(params, k).Value for k in
                                        ['DisplayShiftY', 'FrameTop', 'FrameRoof', 'WindowMargin', 'MCUBottom']}}
    print('Opened source; beginning left Talavera parameter probes', file=sys.__stdout__, flush=True)
    report['baseline'] = snapshot()
    print('Baseline measured', file=sys.__stdout__, flush=True)
    for name, value in [('DisplayShiftY', 3.4), ('WindowMargin', .3), ('FrameTop', 13.99)]:
        original = getattr(params, name).Value
        params.set(params.getCellFromAlias(name), str(value) + ' mm')
        recompute_probe()
        report[name] = {'value_mm': value, 'snapshot': snapshot()}
        params.set(params.getCellFromAlias(name), str(original) + ' mm')
        recompute_probe()
        (OUT / 'native-parameters-progress.json').write_text(json.dumps(report, indent=2) + '\n')
        print('Probed', name, file=sys.__stdout__, flush=True)

    report['usb_envelope'] = {}
    for side, prefix, x in [('left', 'L_', 116.8), ('right', 'R_', 31.2)]:
        plug = Part.makeBox(12, 20, 5, A.Vector(x, -18.8, params.MCUBottom.Value - 2.1))
        checks = {}
        for style in ['solid', 'rim', 'terrace', 'level']:
            for part in ['base', 'plate']:
                obj = doc.getObject(prefix + 'Case_' + style + '_' + part)
                common = usb_sources[obj.Name].common(plug)
                checks[style + '-' + part] = {'collision_mm3': common.Volume,
                    'collision_bounds_mm': bounds(common) if common.Volume > 1e-8 else None}
        report['usb_envelope'][side] = {'bounds_mm': bounds(plug), 'cases': checks}
        print('USB baseline checked', side, file=sys.__stdout__, flush=True)
    A.closeDocument(doc.Name)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    report['source_unchanged'] = True
    report['checker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'native-parameters.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Audit probes completed; native source unchanged', file=sys.__stdout__, flush=True)


if __name__ == '__main__':
    try:
        run()
    except Exception:
        traceback.print_exc(file=sys.__stderr__)
        sys.__stderr__.flush()
        os._exit(1)
    os._exit(0)
