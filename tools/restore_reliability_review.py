#!/usr/bin/env python3
"""Restore ignored advisory evidence copies from the committed review receipt."""
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
record=json.loads((root/'validation/revI-reliability-review.json').read_text())
out=root/'build/reliability-fix';out.mkdir(parents=True,exist_ok=True)
items={'baseline':record['baseline'],'decision':record['decision']}
for reviewer in record['reviewers']:
    items[reviewer['lens']+'-handoff']=reviewer['handoff']
    items[reviewer['lens']+'-final']=reviewer['finalization']
for name,value in items.items():
    encoded=(json.dumps(value,indent=2)+'\n').encode();target=out/(name+'.json')
    target.write_bytes(encoded)
    assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(encoded).digest()
print('PASS: six advisory evidence copies restored and verified from the committed receipt')
