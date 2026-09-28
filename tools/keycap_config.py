"""Pure-Python configuration checks shared by the build and FreeCAD macros.
Convex XY envelopes conservatively qualify configurations, not physical stem fit.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy, json, math
from frame_finishes import palette
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'keycaps/catalog.json'

def polygon(hull,key,turn):
    a=math.radians(-key['angle']-turn);c,s=math.cos(a),math.sin(a)
    return [[key['x']+x*c-y*s,key['y']+x*s+y*c] for x,y in hull]

def gap(a,b):
    """Largest separating-axis clearance. A conservative Euclidean lower bound."""
    boxgap=max(min(x for x,y in b)-max(x for x,y in a),min(x for x,y in a)-max(x for x,y in b),min(y for x,y in b)-max(y for x,y in a),min(y for x,y in a)-max(y for x,y in b))
    if boxgap>=.2:return boxgap
    result=boxgap
    for p in (a,b):
        for u,v in zip(p,p[1:]+p[:1]):
            dx,dy=v[0]-u[0],v[1]-u[1];length=math.hypot(dx,dy)
            if length<1e-8:continue
            nx,ny=-dy/length,dx/length
            aa=[x*nx+y*ny for x,y in a];bb=[x*nx+y*ny for x,y in b]
            result=max(result,min(bb)-max(aa),min(aa)-max(bb))
    return result

def load():return json.loads(CATALOG.read_text())

def default_config(catalog=None):
    c=catalog or load();return normalize(c['default_configuration'],c)

def normalize(config,catalog=None):
    c=catalog or load();result=copy.deepcopy(config);result['schema']='flan36-config-1'
    for side,keys in c['layout'].items():
        for key in keys:result['keycaps'][side][key['ref']].setdefault('color','#45967b' if key['row']==3 else '#e9dfc6')
    if 'cases' not in result:result['cases']={side:{'style':'solid','cover':True} for side in ['left','right']}
    for side in ['left','right']:
        case=result['cases'][side];style=c['case_styles'][case['style']]
        case.setdefault('base_color',style['base_color']);case.setdefault('plate_color',style['plate_color']);case.setdefault('match_frame',False)
        f=result['frames'][side];f['style']=c.get('retired_frame_styles',{}).get(f['style'],f['style']);colors=palette(f['style'],f['color'],f.get('accents'))
        f['accents']={k:colors[k] for k in ['detail','accent','secondary']}
    return result

def valid_color(v):return isinstance(v,str) and len(v)==7 and v[0]=='#' and all(x in '0123456789abcdefABCDEF' for x in v[1:])

def check(config,catalog=None):
    c=catalog or load();variants={v['id']:v for v in c['variants']};errors=[];shapes={};minimum=float('inf')
    if not isinstance(config,dict):return ['Choose a configuration object.'],None
    if config.get('schema') not in ('flan36-config-1','filo36-config-1') or config.get('revision')!='I':return ['Unsupported configuration format or revision.'],None
    if not isinstance(config.get('keycaps'),dict) or not isinstance(config.get('frames'),dict):return ['Both halves are required.'],None
    if set(config.get('keycaps',{}))!={'left','right'} or set(config.get('frames',{}))!={'left','right'}:return ['Both halves are required.'],None
    if not isinstance(config.get('batteries'),dict):return ['Select a battery for each half.'],None
    if set(config.get('batteries',{}))!={'left','right'}:return ['Select a battery for each half.'],None
    if 'cases' in config:
        cases=config['cases']
        if not isinstance(cases,dict) or set(cases)!={'left','right'}:return ['Select a case for each half.'],None
        for case in cases.values():
            if not isinstance(case,dict) or not isinstance(case.get('style'),str) or case.get('style') not in c['case_styles'] or type(case.get('cover')) is not bool:return ['Invalid case or display cover option.'],None
    for side in ['left','right']:
        case=config.get('cases',{}).get(side,{})
        for field in ['base_color','plate_color']:
            if field in case and not valid_color(case[field]):return ['Invalid case color.'],None
        if 'match_frame' in case and type(case['match_frame']) is not bool:return ['Invalid color link.'],None
        f=config['frames'][side]
        if not isinstance(f,dict):return ['Invalid frame.'],None
        if 'accents' in f:
            if not isinstance(f['accents'],dict) or any(k not in ['detail','accent','secondary'] or not valid_color(v) for k,v in f['accents'].items()):return ['Invalid frame accent color.'],None
        if case.get('match_frame') and case.get('style')=='level' and str(case.get('plate_color','')).lower()!=str(f.get('color','')).lower():return ['Linked Level shell and frame colors must match.'],None
        if case.get('match_frame') and str(case.get('base_color','')).lower()!=str(f.get('color','')).lower():return ['Linked rim and frame colors must match.'],None
    for side,keys in c['layout'].items():
        if not isinstance(config['batteries'][side],str) or config['batteries'][side] not in c['battery_profiles']:errors.append('Unknown battery profile.')
        if not isinstance(config['keycaps'][side],dict):return ['Missing keys or unknown positions.'],None
        if set(config['keycaps'][side])!={k['ref'] for k in keys}:return ['Missing keys or unknown positions.'],None
        f=config['frames'][side]
        if not isinstance(f.get('style'),str) or (f.get('style') not in c['frame_styles'] and f.get('style') not in c.get('retired_frame_styles',{})):errors.append('Unknown frame.')
        color=f.get('color','')
        if not valid_color(color):errors.append('Invalid frame color.')
        shapes[side]={}
        for k in keys:
            x=config['keycaps'][side][k['ref']]
            if not isinstance(x,dict):return ['Invalid keycap choice.'],None
            v=variants.get(x.get('variant')) if isinstance(x.get('variant'),str) else None;turn=x.get('rotation_deg')
            if 'color' in x and not valid_color(x['color']):return ['Invalid keycap color.'],None
            if not v or type(turn) not in (int,float) or turn not in v['rotations_deg'] or not v['qualified_reference_positions']:
                errors.append(f"{side} {k['ref']}: unqualified variant or orientation.");continue
            p=polygon(v['hull_xy_mm'],k,turn);shapes[side][k['ref']]=p
            d=gap(p,c['frame_envelopes'][side]);minimum=min(minimum,d)
            if d<c['minimum_clearance_mm']-1e-7:errors.append(f"{side} {k['ref']}: violates the frame clearance.")
        for i,(ref,a) in enumerate(shapes[side].items()):
            for other,b in list(shapes[side].items())[i+1:]:
                d=gap(a,b);minimum=min(minimum,d)
                if d<c['minimum_clearance_mm']-1e-7:errors.append(f'{side} {ref}/{other}: insufficient keycap clearance.')
    return errors,round(minimum,6) if math.isfinite(minimum) else None

if __name__=='__main__':
    import sys
    cfg=json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else default_config()
    errors,minimum=check(cfg);print(json.dumps({'errors':errors,'conservative_clearance_mm':minimum},ensure_ascii=False))
    raise SystemExit(bool(errors))
