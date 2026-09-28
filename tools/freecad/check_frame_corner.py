"""Check the actual shared USB-side corner, including the former mismatch.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import Part

ROOT = Path(__file__).resolve().parents[2]
G.showMainWindow();G.getMainWindow().hide()
doc = A.openDocument(str(ROOT/'mechanical/revI/Flan36.FCStd'))
profiles = json.loads((ROOT/'design/revI-profiles.json').read_text())
frames = json.loads((ROOT/'design/revI-frame-profiles.json').read_text())
rows = []
for side, prefix in [('left', 'L_'), ('right', 'R_')]:
    doc.getObject(prefix+'Half').Placement = A.Placement()
    doc.recompute()
    index = profiles[side]['control_vertices'].index([135 if side == 'left' else 25, 11])
    expected = profiles[side]['outer_arcs'][index]
    assert all(math.dist(expected[k], frames[side]['outer_arcs'][1][k]) < 1e-8 for k in expected)
    center = A.Vector(132.6 if side == 'left' else 27.4, -13.4, 0)
    # Actual saved native case sketch, extruded only as a comparison envelope.
    envelope = Part.Face(doc.getObject(prefix+'OuterPadSketch').Shape.Wires[0]).extrude(A.Vector(0, 0, 20))
    region = Part.makeBox(5, 6, 20, A.Vector(131 if side == 'left' else 24, -16, 0))
    for obj in [o for o in doc.Objects if o.Name.startswith(prefix) and hasattr(o, 'FrameStyle') and o.TypeId != 'App::Link']:
        shape = obj.Shape
        assert shape.isValid() and len(shape.Solids) == 1
        matching = []
        for edge in shape.Edges:
            curve = edge.Curve
            if not isinstance(curve, Part.Circle):
                continue
            c = curve.Center
            if abs(curve.Radius-2.4) < 1e-7 and math.hypot(c.x-center.x, c.y-center.y) < 1e-7:
                if abs(edge.Length-math.pi*2.4/2) < 1e-6:
                    matching.append(edge)
        assert matching, (side, obj.FrameStyle, 'shared analytic quarter circle missing')
        outside = shape.common(region).cut(envelope).Volume
        assert outside < 1e-6, (side, obj.FrameStyle, outside)
        rows.append({'side': side, 'style': obj.FrameStyle, 'radius_mm': 2.4, 'outside_case_corner_mm3': outside})
    # Old R1.2 outer corner has material at this XY point; new case does not.
    old_mid = A.Vector(134.648528137 if side == 'left' else 25.351471863, -11.351471863, 8)
    assert not envelope.isInside(old_mid, 1e-7, True), 'Former mismatch not rejected'
report = {'source_sha256': hashlib.sha256((ROOT/'mechanical/revI/Flan36.FCStd').read_bytes()).hexdigest(),
          'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'shared_corner_checks': rows, 'previous_corner_rejected': True,
          'scope': 'Native corner geometry; physical fit remains untested'}
(ROOT/'validation/revI-frame-corner.json').write_text(json.dumps(report, indent=2)+'\n')
sys.__stdout__.write(f'PASS: {len(rows)} native frame corners coincide with the case; former mismatch rejected\n')
sys.__stdout__.flush()
if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
    os._exit(0)
