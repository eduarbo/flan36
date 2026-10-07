"""Cross-check current revI schematic nets, PCB associations and model coverage.
Run using KiCad's Python (pcbnew); no PCB/schematic is saved.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/audit-20261007'
OUT.mkdir(parents=True, exist_ok=True)
CLI = os.environ.get('FLAN36_KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
report = {}
for side in ['left', 'right']:
    schematic = ROOT / f'hardware/revI/flan36-{side}.kicad_sch'
    netlist = OUT / f'netlist-{side}.xml'
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(netlist), str(schematic)], check=True)
    board = p.LoadBoard(str(schematic.with_suffix('.kicad_pcb')))
    root = ET.parse(netlist).getroot()
    desired = {(x.get('ref'), x.get('pin')): net.get('name').lstrip('/') for net in root.findall('./nets/net') for x in net.findall('node')}
    actual = {(f.GetReference(), q.GetNumber()): q.GetNetname().lstrip('/') for f in board.GetFootprints() for q in f.Pads() if q.GetNetname()}
    mismatches = [(key, want, actual.get(key)) for key, want in desired.items() if not want.startswith('unconnected-') and actual.get(key) != want]
    mismatches += [(key, desired.get(key), value) for key, value in actual.items() if desired.get(key) != value]
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    comps = root.findall('./components/comp')
    report[side] = {
        'net_nodes': len(desired), 'normalized_net_mismatches': mismatches,
        'symbol_path_mismatches': [c.get('ref') for c in comps if not fps[c.get('ref')].GetPath().AsString().endswith('/'+c.findtext('tstamps'))],
        'diodes': [{'ref': f.GetReference(), 'layer': board.GetLayerName(f.GetLayer()), 'models': len(f.Models()),
                    'xy_mm': [p.ToMM(f.GetPosition().x), p.ToMM(f.GetPosition().y)]} for f in fps.values() if f.GetReference().startswith('D')],
        'tracks': len(board.GetTracks()), 'extra_footprints': [f for f in fps if f not in [c.get('ref') for c in comps]],
    }
(OUT / 'electrical-crosscheck.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({side: {k: v for k, v in data.items() if k != 'diodes'} for side, data in report.items()}, indent=2))
