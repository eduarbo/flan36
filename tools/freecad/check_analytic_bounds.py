"""Verify tessellation-independent bounds for the four stored Adafruit leads.

python3 tools/freecad/run_macos.py tools/freecad/check_analytic_bounds.py \
  --source mechanical/revI/Flan36.FCStd \
  --output validation/revI-analytic-bounds.json

Reads cached BRep members directly without opening or saving the native document.
Ordinary BoundBox is measured, not required to change: a source may already have
triangulation. The invariant is unchanged exact geometry and analytic bounds.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import FreeCAD
import Part

ROOT = Path(__file__).resolve().parents[2]
WIRE_NAMES = tuple(prefix + 'WireStudy' + str(index)
                   for prefix in ('L_', 'R_') for index in range(2))
DEFLECTIONS_MM = (0.2, 0.05, 0.01)
EPS = 1e-8


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounds(box):
    return [getattr(box, name) for name in
            ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')]


def max_delta(before, after):
    return max(abs(a - b) for a, b in zip(before, after))


def vertices(shape):
    return sorted(tuple(vertex.Point) for vertex in shape.Vertexes)


def check(source):
    source = Path(source)
    native = source.read_bytes()
    report = {
        'schema': 'flan36-analytic-bounds-regression-1',
        'source_file': source.name,
        'source_sha256': digest(native),
        'checker_sha256': digest(Path(__file__).read_bytes()),
        'freecad_version': '.'.join(FreeCAD.Version()[:3]),
        'scope': 'Read-only measurement regression; no physical fit acceptance.',
        'analytic_api': 'Shape.optimalBoundingBox(False, False)',
        'tolerance': {'distance_mm': EPS, 'volume_mm3': EPS, 'area_mm2': EPS},
        'ordinary_bounds_must_change': False,
        'physical_acceptance': False,
        'wires': {},
    }
    with ZipFile(source) as archive:
        xml = ET.fromstring(archive.read('Document.xml'))
        objects = {obj.get('name'): obj for obj in xml.find('ObjectData')}
        for name in WIRE_NAMES:
            prop = objects[name].find("./Properties/Property[@name='Shape']/Part")
            if prop is None or not prop.get('file'):
                raise ValueError('Missing stored BRep for ' + name)
            reference = Part.Shape()
            reference.importBrepFromString(archive.read(prop.get('file')).decode())
            assert reference.isValid() and len(reference.Solids) == 1, name
            analytic = bounds(reference.optimalBoundingBox(False, False))
            ordinary = bounds(reference.BoundBox)
            original_vertices = vertices(reference)
            trials = []
            for deflection in DEFLECTIONS_MM:
                # Independent geometry copy avoids sharing mesh caches with reference.
                shape = reference.copy(True, False)
                before = bounds(shape.BoundBox)
                mesh_vertices, mesh_faces = shape.tessellate(deflection)
                after = bounds(shape.BoundBox)
                optimal = bounds(shape.optimalBoundingBox(False, False))
                current_vertices = vertices(shape)
                same_vertex_count = len(original_vertices) == len(current_vertices)
                vertex_delta = (max((max_delta(a, b) for a, b in
                                     zip(original_vertices, current_vertices)), default=0.)
                                if same_vertex_count else None)
                symmetric_difference = reference.cut(shape).Volume + shape.cut(reference).Volume
                volume_delta = shape.Volume - reference.Volume
                area_delta = shape.Area - reference.Area
                optimal_delta = max_delta(analytic, optimal)
                passed = (shape.isValid() and len(shape.Solids) == 1
                          and same_vertex_count and vertex_delta <= EPS
                          and abs(volume_delta) <= EPS and abs(area_delta) <= EPS
                          and abs(symmetric_difference) <= EPS and optimal_delta <= EPS)
                trials.append({
                    'deflection_mm': deflection,
                    'mesh_vertices': len(mesh_vertices), 'mesh_triangles': len(mesh_faces),
                    'ordinary_bounds_before_mm': before,
                    'ordinary_bounds_after_mm': after,
                    'ordinary_bounds_max_change_mm': max_delta(before, after),
                    'analytic_bounds_after_mm': optimal,
                    'analytic_bounds_max_change_mm': optimal_delta,
                    'valid_after': shape.isValid(),
                    'volume_delta_mm3': volume_delta, 'area_delta_mm2': area_delta,
                    'symmetric_difference_mm3': symmetric_difference,
                    'vertex_count_preserved': same_vertex_count,
                    'vertex_max_change_mm': vertex_delta,
                    'passed': passed,
                })
            report['wires'][name] = {
                'stored_ordinary_bounds_mm': ordinary,
                'analytic_bounds_mm': analytic,
                'exact_volume_mm3': reference.Volume,
                'exact_area_mm2': reference.Area,
                'trials': trials,
                'passed': all(trial['passed'] for trial in trials),
            }
    report['source_unchanged'] = digest(source.read_bytes()) == report['source_sha256']
    report['passed'] = (report['source_unchanged']
                        and all(wire['passed'] for wire in report['wires'].values()))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'mechanical/revI/Flan36.FCStd')
    parser.add_argument('--output', type=Path, default=ROOT/'validation/revI-analytic-bounds.json')
    options, _ = parser.parse_known_args()
    result = check(options.source.resolve())
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(result, indent=2) + '\n')
    summary = {'passed': result['passed'], 'source_unchanged': result['source_unchanged'],
               'wire_count': len(result['wires']), 'trial_count': sum(len(w['trials']) for w in result['wires'].values()),
               'maximum_ordinary_bounds_change_mm': max(t['ordinary_bounds_max_change_mm'] for w in result['wires'].values() for t in w['trials']),
               'maximum_analytic_bounds_change_mm': max(t['analytic_bounds_max_change_mm'] for w in result['wires'].values() for t in w['trials'])}
    sys.__stdout__.write(json.dumps(summary, indent=2) + '\n')
    sys.__stdout__.flush()
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        os._exit(0 if result['passed'] else 1)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
