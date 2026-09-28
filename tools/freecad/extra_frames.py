"""Compatibility helpers for the current native frame collection.

Legacy entry points delegate to the canonical co-print recipe.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
from pathlib import Path

import flush_frames

OWNER = 'flan36-frame-extensions-1'
STYLES = flush_frames.STYLES
BOUND_KEYS = flush_frames.BOUNDS


def load_spec(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    return flush_frames.load_spec(root)


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
    """Return the current FrameStyle objects using actual flush color solids."""
    load_spec()
    objects, _ = flush_frames.build_styles(doc, side, smooth=smooth,
                                          styles=STYLES, validate=validate)
    return objects
