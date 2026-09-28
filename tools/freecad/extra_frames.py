"""Four native flush frame themes, shared by the installer and full generator.

Compatibility entry points delegate to the common seven-style co-print recipe.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
from pathlib import Path

import flush_frames

OWNER = 'flan36-frame-extensions-1'
STYLES = ('cartridge', 'arcade', 'mecha', 'kintsugi')
BOUND_KEYS = flush_frames.BOUNDS


def load_spec(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    spec = json.loads((root / 'design/frame-extensions.json').read_text())
    if spec['schema'] != OWNER or tuple(spec['styles']) != STYLES:
        raise ValueError('Unexpected extension schema or style set')
    if spec['decoration_mode'] != 'flush-co-print' or spec['max_relief_mm'] != 0:
        raise ValueError('Only flush co-print frame themes are supported')
    flush_frames.load_spec(root)
    return spec


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb(hexcolor):
    return flush_frames.rgb(hexcolor)


def fingerprint(shape):
    return hashlib.sha256(shape.exportBrepToString().encode('utf-8')).hexdigest()


def property_value(obj, name, type_id, value):
    return flush_frames.prop(obj, name, type_id, value)


def find_smooth(doc, side):
    return flush_frames.find_smooth(doc, side)


def validate_variant(doc, side, smooth, variant, spec=None):
    return flush_frames.validate_variant(doc, side, smooth, variant)


def build_for_half(doc, side, smooth=None, history=None, spec=None, validate=True):
    """Return the same four FrameStyle objects using actual flush color solids."""
    load_spec()
    objects, _ = flush_frames.build_styles(doc, side, smooth=smooth,
                                          styles=STYLES, validate=validate)
    return objects
