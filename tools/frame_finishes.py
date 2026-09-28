"""Shared palette for solid-owned flush co-print materials.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
from pathlib import Path
FINISHES=json.loads((Path(__file__).resolve().parents[1]/'design/frame-finishes.json').read_text())


def role(style,side,x,y,height,roof=None,material_role=None):
    """Compatibility adapter. Geometry consumers must pass the owning solid role.

    Plain/legacy callers receive body rather than inventing painted zones. Native
    frame consumers use FrameFaceRoles; exports use MaterialParts/ColorRole.
    """
    if material_role is not None and material_role not in FINISHES['roles']:
        raise ValueError('Unknown frame material role: '+str(material_role))
    return material_role or 'body'

def palette(style,body=None,accents=None):
    result=dict(FINISHES['styles'].get(style,{}).get('colors',{'body':'#304d4e'}))
    if body:result['body']=body
    for name in ['detail','accent','secondary']:result[name]=(accents or {}).get(name,result.get(name,result['body']))
    return result

def rgb(color):return tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
