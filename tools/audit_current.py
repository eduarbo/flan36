#!/usr/bin/env python3
"""Run the bounded October 2026 audit without rebuilding product artifacts.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/audit-20261007'
OUT.mkdir(parents=True, exist_ok=True)
KICAD = os.environ.get('FLAN36_KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')


def run(name, command):
    start = time.monotonic()
    with (OUT / (name + '.log')).open('w') as log:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=360)
            status = result.returncode
        except subprocess.TimeoutExpired:
            status = 'timeout'
    record = dict(name=name, command=command, exit_code=status,
                  elapsed_seconds=round(time.monotonic()-start, 2))
    print(name, status, flush=True)
    return record


def browser_checks():
    names = ['reliability', 'frame-collection', 'frame-orientation', 'keycolors',
             'hex', 'cap-rows', 'battery-leads', 'display-seam']
    return [run(name, ['node', 'viewer/' + name + '-check.cjs']) for name in names]


def other_checks():
    results = [run('layout', ['python3', 'tools/check_layout.py'])]
    for name in ['config-contract', 'finishes', 'flush-print', 'level']:
        results.append(run(name, ['node', 'viewer/' + name + '-check.cjs']))
    for side in ['left', 'right']:
        for kind, verb, ext in [('pcb', 'drc', 'kicad_pcb'), ('sch', 'erc', 'kicad_sch')]:
            name = verb + '-' + side
            command = [KICAD, kind, verb, '--format', 'json', '--severity-all',
                       '--exit-code-violations', '--output', str(OUT / (name + '.json'))]
            if kind == 'pcb':
                command.append('--schematic-parity')
            results.append(run(name, command + ['hardware/revI/flan36-' + side + '.' + ext]))
    return results


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(browser_checks), pool.submit(other_checks)]
        results = [r for future in futures for r in future.result()]
    report = dict(snapshot=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  results=results, physical_acceptance=False)
    (OUT / 'checks.json').write_text(json.dumps(report, indent=2) + '\n')
