#!/usr/bin/env python3
"""Check aggregate exit propagation without launching CAD, browsers or KiCad.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import ast
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'tools/audit_current.py'
spec = importlib.util.spec_from_file_location('audit_runner_controls', source)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
entry = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.If))
program = compile(ast.Module(body=[entry], type_ignores=[]), str(source), 'exec')
results = []
with tempfile.TemporaryDirectory() as temp:
    for status, expected in [(0, 0), (1, 1), ('timeout', 1)]:
        namespace = dict(vars(runner), __name__='__main__', OUT=Path(temp),
                         browser_checks=lambda: [{'name': 'synthetic-child',
                                                  'command': ['fixture'], 'exit_code': status}],
                         other_checks=lambda: [])
        try:
            exec(program, namespace)
        except SystemExit as exc:
            assert exc.code == expected, (status, exc.code)
        else:
            raise AssertionError('Entrypoint did not set aggregate exit status')
        assert json.loads((Path(temp) / 'checks.json').read_text())['results'][0]['exit_code'] == status
        results.append({'child_status': status, 'aggregate_exit': expected})
report = {'runner_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'synthetic_entrypoint_controls': results, 'passed': True}
(ROOT / 'validation/revI-audit-runner-controls.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS: successful, failed and timed-out children propagate through the actual entrypoint')
