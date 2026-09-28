"""Measure actual cap edge heights relative to the home row, not preset labels.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import math
import struct
from pathlib import Path
import numpy as np


def stl_points(path):
    raw = Path(path).read_bytes()
    count = struct.unpack_from('<I', raw, 80)[0]
    dtype = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])
    return np.ndarray((count,), dtype=dtype, buffer=raw, offset=84)['vertices'].reshape(-1, 3).astype(float)


def assembled_points(points, key, turn, seating):
    """Source STL to native FreeCAD: X=layout X, Y=-layout Y, Z=height."""
    p = points.copy()
    p[:, 1] *= -1
    a = math.radians(key['angle'] + turn)
    c, s = math.cos(a), math.sin(a)
    p[:, :2] = p[:, :2] @ np.array([[c, s], [-s, c]])
    return p + [key['x'], -key['y'], seating]


def outward_rise_mm(points, key):
    """Positive means the outside edge is higher than the edge facing home."""
    assert key['row'] in (0, 2)
    local = points - [key['x'], -key['y'], 0]
    outward = 1 if key['row'] == 0 else -1
    middle = abs(local[:, 0]) < 4
    outer = local[middle & (local[:, 1] * outward > 4), 2]
    inner = local[middle & (local[:, 1] * outward < -4), 2]
    assert len(outer) and len(inner), 'Missing measured cap edges'
    return float(outer.max() - inner.max())
