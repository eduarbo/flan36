#!/usr/bin/env python3
"""Bind current viewer acceptance to its exact sources. Does not qualify hardware."""
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
base=ROOT/'build/reliability-fix'
checks={
 'configuration_contract':read('build/reliability-fix/contract.json'),
 'legacy_schema_restore':read('build/reliability-fix/rebrand-config.json'),
 'browser':read('build/reliability-fix/browser.json'),
 'loading':read('build/reliability-fix/loading.json'),
 'full_ui':json.loads((base/'full-ui.log').read_text()),
 'cap_rows':read('build/reliability-fix/cap-rows/result.json'),
 'hex':read('build/hex-check/result.json'),
 'key_colors':read('build/keycolors/acceptance.json'),
}
online=sha('docs/index.html');offline=sha('docs/offline.html')
assert checks['browser']['passed'] and checks['browser']['online_sha256']==online and checks['browser']['offline_sha256']==offline
assert checks['loading']['summary']['online']['sha256']==online and checks['loading']['summary']['offline']['sha256']==offline
for name in ['full_ui','cap_rows','hex','key_colors']:
 assert checks[name]['viewer_sha256']==offline,name
 assert not checks[name].get('runtime_errors',[]),name
assert checks['cap_rows']['passed']
viewer=read('validation/revI-viewer.json')
assert viewer['viewer_sha256']==online and viewer['offline_sha256']==offline
native=next(p for p in ROOT.glob('mechanical/revI/*.FCStd'))
expected='1c9d3db85b360fea61ed891d6262d0b49055a3fde4ac0912038c96a59ded84cd'
assert hashlib.sha256(native.read_bytes()).hexdigest()==expected
sources=sorted({item['path'] for item in viewer['sources']}|{str(p.relative_to(ROOT)) for p in (ROOT/'viewer').glob('*.js')}|{'tools/keycap_config.py','viewer/config-contract-check.cjs','viewer/reliability-check.cjs','viewer/loading-check.cjs','viewer/public-check.cjs','viewer/check.cjs','viewer/cap-rows-check.cjs','viewer/hex-check.cjs','viewer/keycolors-check.cjs','viewer/rebrand-check.cjs','tools/record_viewer_reliability.py','tools/check_public_delivery.py'})
report={'schema':1,'baseline_commit':'4d17638357f200a53fe4d6baddc9753209019ca6','scope':'GR01–07, related palette persistence, view continuity, session undo, named JSON snapshots, online loading and complete offline exports. Digital viewer acceptance; no new hardware qualification.','online_sha256':online,'offline_sha256':offline,'printing':viewer['printing'],'native_fcstd_sha256':expected,'native_geometry_changed':False,'sources':[{'path':p,'sha256':sha(p)} for p in sources],'checks':checks,'independent_review':{'lenses':['constructive domain','adversarial reliability'],'reviewed_snapshot':'4d17638357f200a53fe4d6baddc9753209019ca6','inputs_unchanged_before_implementation':True,'agreement':'Both recommended the bounded route; each material finding became an acceptance requirement. Root implemented. No unresolved objection to that route.'},'publication':'Verify the pushed commit using tools/check_public_delivery.py and viewer/public-check.cjs. This receipt records local acceptance, not a claim of publication.'}
(ROOT/'validation/revI-reliability.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('PASS: current online/offline artifacts, all acceptance reports and unchanged native geometry are bound')
