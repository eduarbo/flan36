#!/usr/bin/env python3
"""Bind the sculpted-row correction to tested native and delivered viewer inputs.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='697807446a7f0e5e70a56aa240189dd8aa15f3cd'
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def run():
    native=read('build/cap-row-fix/native.json')
    browser=read('build/cap-row-fix/browser/result.json')
    ui=read('build/cap-row-fix/full-ui/build/viewer-ui-check.json')
    built=read('validation/revI-viewer.json')
    assert native['passed'] and browser['passed'] and not ui['runtime_errors']
    assert native['native_source_sha256']==sha('mechanical/revI/Flan36.FCStd')
    assert native['checker_sha256']==sha('tools/freecad/check_cap_rows.py')
    assert native['geometry_oracle_sha256']==sha('tools/keycap_row_geometry.py')
    assert browser['checker_sha256']==sha('viewer/cap-rows-check.cjs')
    assert browser['viewer_sha256']==ui['viewer_sha256']==built['viewer_sha256']==sha('docs/index.html')
    for item in built['sources']:assert sha(item['path'])==item['sha256'],item['path']
    assert not subprocess.check_output(['git','diff',BASE,'--','mechanical','hardware','keycaps','design/layout.json'],cwd=ROOT)
    changes={}
    for name in ['normal-sculpted','saddle-sculpted']:
        path=f'design/configurations/{name}.json'
        old=json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT))
        new=read(path);expected=json.loads(json.dumps(old));count=0
        for side,keys in read('design/layout.json')['halves'].items():
            for k in keys:
                if k['row'] not in (0,2):continue
                expected['keycaps'][side][k['ref']]['rotation_deg']=(old['keycaps'][side][k['ref']]['rotation_deg']+180)%360
                count+=1
        assert expected==new and count==20
        assert any(x['path']==path and x['sha256']==sha(path) for x in built['sources'])
        assert len(native['presets'][name]['measured_keys'])==20
        assert native['presets'][name]['reversed_negative_controls']==20
        assert len(browser['actual_glb_surface_measurements'][name])==20
        changes[name]={'rotations_changed':count,'sha256':sha(path)}
    sources=['design/layout.json','keycaps/catalog.json','tools/keycap_row_geometry.py',
        'tools/freecad/check_cap_rows.py','viewer/cap-rows-check.cjs','tools/check_cap_rows_delivery.py',
        'viewer/app.js','tools/build_viewer_revI.py']
    result={'schema':'flan36-cap-row-correction-1','accepted_digital_correction':True,
        'request':'Correct the reversed top and bottom sculpted cap rows shown by the user.',
        'source_commit':BASE,'cause':'Preset rotations were reversed; prior registration checked centers and configured transforms, not actual slope direction.',
        'correction':'Top row 180 degrees; bottom row 0 degrees, both halves and both sculpted presets.',
        'presets':changes,'source_meshes_seating_layout_and_hardware_unchanged':True,
        'native':native,'viewer':browser,
        'ui_regression':{'viewer_sha256':ui['viewer_sha256'],'runtime_errors':ui['runtime_errors'],'case_variants':ui['case_variants'],'glb_selected_vertices_exact':ui['glb_selected_vertices_exact']},
        'review':{'lenses':['constructive mechanics','adversarial reliability'],'baseline_unchanged_after_reviews':True,
            'agreement':'Correct preset rotations; retain literal saved/manual choices; use explicit targeted repair.',
            'dispositions':['World-space edge-height checks reject all forty reversed controls.',
                'Preset input hashes now prevent stale scene builds.',
                'An explicit repair changes only reversed non-90-degree Tilted finger caps, preserving other choices. No inferred storage migration.']},
        'images':{p:sha(p) for p in ['docs/images/revI-sculpted-normal.png','docs/images/revI-sculpted-saddle.png']},
        'inputs':[{'path':p,'sha256':sha(p)} for p in sources],'physical_acceptance':False,
        'reproduce':['python3 tools/freecad/run_macos.py tools/freecad/check_cap_rows.py','python tools/build_viewer_revI.py','node viewer/build.mjs','node viewer/cap-rows-check.cjs','node build/cap-row-fix/full-ui/viewer/check.cjs','python3 tools/check_cap_rows_delivery.py']}
    (ROOT/'validation/revI-cap-rows.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: corrected rows bound to saved native CAD, GLB vertices, current viewer and unchanged hardware')

if __name__=='__main__':run()
