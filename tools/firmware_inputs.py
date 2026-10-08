#!/usr/bin/env python3
"""Bind clean, pinned build inputs to actual compiled firmware outputs.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    paths = list((ROOT / 'firmware/config').rglob('*'))
    paths += [ROOT / p for p in ('design/layout.json', 'design/pinmap.json', 'design/key-order.json',
        'firmware/west-frozen.yml', 'firmware/dependencies.json', 'tools/build_firmware.sh',
        'tools/firmware_inputs.py', 'tools/check_firmware.py')]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths) if p.is_file()}


def source_records():
    # Explicit fields keep public file checksums distinct from credential fields.
    return [{'path': path, 'sha256': digest} for path, digest in sources().items()]


def capture():
    workspace = Path(os.environ['FLAN36_ZMK_WORKSPACE']).resolve()
    west = os.environ.get('FLAN36_WEST', 'west')
    active = subprocess.check_output([west, 'list', '-f', '{name}\t{path}'], cwd=workspace, text=True)
    pins = {p['name']: p for p in json.loads((ROOT / 'firmware/dependencies.json').read_text())}
    dependencies = {}
    for line in active.strip().splitlines():
        name, rel = line.split('\t'); expected = pins[name]
        assert rel == expected['path'], (name, 'unexpected dependency path')
        directory = workspace / rel
        head = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        assert head == expected['revision'], (name, 'dependency revision differs')
        assert not subprocess.check_output(['git', '-C', str(directory), 'status', '--porcelain']), (name, 'dirty dependency')
        dependencies[name] = {'path': rel, 'revision': head, 'clean': True}
    assert {'manifest','zephyr','cmsis','hal_nordic','lvgl','tinycrypt'} <= dependencies.keys()
    prefix = os.environ['CROSS_COMPILE']
    compiler = Path(prefix + 'gcc')
    # This is the verified compiler used for the distributed candidates.
    assert sha(compiler) == '7528680ad6078c1d2dd67a414fca656e5d78e56e7bc31f422a849bb15a7db04a', 'Unqualified compiler'
    toolchain = {name: sha(prefix + name) for name in ('gcc','as','ld','objcopy')}
    for name in ('cc1','libgcc.a','libc.a'):
        option = '-print-prog-name=' if name == 'cc1' else '-print-file-name='
        path = subprocess.check_output([str(compiler), option + name], text=True).strip()
        toolchain[name] = sha(path)
    toolchain['version'] = subprocess.check_output([str(compiler),'--version'], text=True).splitlines()[0]
    for name in ('cmake','ninja'):
        toolchain[name + '_version'] = subprocess.check_output([name,'--version'], text=True).splitlines()[0]
    return {'sources': source_records(), 'dependencies': dependencies, 'toolchain': toolchain}


def outputs(variant):
    directory = ROOT / 'build' / ('firmware-' + variant) / 'zephyr'
    return {name: sha(directory / name) for name in ('zmk.uf2','zephyr.dts','.config')}


def verify_attestation(variant):
    receipt = ROOT / 'build' / ('firmware-' + variant) / 'build-attestation.json'
    data = json.loads(receipt.read_text())
    assert data['inputs']['sources'] == source_records(), (variant, 'Sources changed since build')
    assert data['outputs'] == outputs(variant), (variant, 'Build outputs changed')
    assert data['variant'] == variant and data['inputs_unchanged_after_build'] is True
    return data


if __name__ == '__main__':
    mode, variant = sys.argv[1:]
    assert variant in ('left','right','right-no-display')
    temp = ROOT / 'build/firmware-attestation'; temp.mkdir(parents=True, exist_ok=True)
    before = temp / (variant + '-inputs.json')
    if mode == 'start':
        # Remove prior successful evidence before attempting a new build.
        (ROOT / 'build' / ('firmware-' + variant) / 'build-attestation.json').unlink(missing_ok=True)
        before.write_text(json.dumps(capture(), indent=2)+'\n')
    elif mode == 'finish':
        inputs = json.loads(before.read_text())
        assert inputs == capture(), 'Build inputs changed during compilation'
        data = {'variant': variant, 'inputs': inputs, 'inputs_unchanged_after_build': True, 'outputs': outputs(variant)}
        (ROOT / 'build' / ('firmware-' + variant) / 'build-attestation.json').write_text(json.dumps(data, indent=2)+'\n')
    else:
        raise SystemExit('Expected start or finish')
