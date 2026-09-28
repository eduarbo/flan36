"""Check sculpted profiles in saved/reopened native CAD using measured surfaces.
Run: python3 tools/freecad/run_macos.py tools/freecad/check_cap_rows.py
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy, hashlib, json, os, sys
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/freecad')]
from configuration import apply, extract
from keycap_config import load, check, normalize
from keycap_row_geometry import stl_points, assembled_points, outward_rise_mm

OUT = ROOT/'build/cap-row-fix'
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT/'mechanical/revI/Flan36.FCStd'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
catalog = load()
variants = {v['id']: v for v in catalog['variants']}
G.showMainWindow(); G.getMainWindow().hide()
doc = A.openDocument(str(source))
results = {}
for name in ['normal-sculpted', 'saddle-sculpted']:
    config = normalize(json.loads((ROOT/'design/configurations'/f'{name}.json').read_text()))
    errors, margin = check(config, catalog)
    assert not errors, errors
    old = copy.deepcopy(config)
    for side, keys in catalog['layout'].items():
        for key in keys:
            if key['row'] in (0, 2):
                old['keycaps'][side][key['ref']]['rotation_deg'] ^= 180
    # Collision/registration alone passed for the bad arrangement. The new
    # independent height-direction assertion must reject every reversed key.
    assert not check(old, catalog)[0]
    rejected = 0
    for side, keys in catalog['layout'].items():
        for key in keys:
            if key['row'] not in (0, 2): continue
            choice = old['keycaps'][side][key['ref']]
            variant = variants[choice['variant']]
            pts = assembled_points(stl_points(ROOT/variant['path']), key, choice['rotation_deg'], variant['seating_z_mm'])
            assert outward_rise_mm(pts, key) < -2.5
            rejected += 1
    # Unique colors and mixed components verify this is a full config roundtrip.
    for index, choice in enumerate(c for half in config['keycaps'].values() for c in half.values()):
        choice['color'] = '#'+format((index+1)*312709, '06x')
    config['batteries'] = {'left':'301230', 'right':'adafruit-1570'}
    config['cases']['left']['style'] = 'level'
    config['cases']['right']['style'] = 'rim'
    apply(doc, config)
    assert extract(doc) == config
    saved = OUT/f'{name}.FCStd'
    doc.saveAs(str(saved)); A.closeDocument(doc.Name)
    doc = A.openDocument(str(saved))
    assert extract(doc) == config
    measured = []
    for side, keys in catalog['layout'].items():
        for key in keys:
            obj = doc.getObject(('L_' if side=='left' else 'R_')+key['ref'])
            assert abs(obj.Placement.Base.x-key['x']) < 1e-6
            assert abs(obj.Placement.Base.y+key['y']) < 1e-6
            if key['row'] not in (0, 2): continue
            pts = np.array([[p.Vector.x,p.Vector.y,p.Vector.z] for p in obj.Mesh.Points])
            rise = outward_rise_mm(pts, key)
            assert rise > 2.5, (side, key['ref'], rise)
            measured.append({'side':side,'key':key['ref'],'outer_above_inner_mm':rise})
    # Explicit unusual rotations remain literal; no silent native migration.
    manual = copy.deepcopy(config)
    manual['keycaps']['left']['K01']['rotation_deg'] = 0
    apply(doc, manual); assert extract(doc) == manual
    results[name] = {'measured_keys':measured,'reversed_negative_controls':rejected,
        'minimum_clearance_mm':margin,'saved_reopened':True,'custom_colors_and_components_preserved':True,
        'manual_rotation_preserved':True}
A.closeDocument(doc.Name)
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
report = {'passed':True,'native_source_sha256':source_hash,'canonical_native_unchanged':True,
    'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'geometry_oracle_sha256':hashlib.sha256((ROOT/'tools/keycap_row_geometry.py').read_bytes()).hexdigest(),
    'presets':results,'physical_acceptance':False}
(OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: 40 saved native cap directions; 40 reversed controls rejected; literal custom rotations retained',flush=True)
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':
    sys.__stdout__.flush(); os._exit(0)
