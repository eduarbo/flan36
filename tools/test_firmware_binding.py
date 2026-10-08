#!/usr/bin/env python3
"""Reject stale firmware in a disposable copy; preserve published artifacts.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import check_firmware
import firmware_inputs

ROOT = Path(__file__).resolve().parents[1]


def test(zephyr):
    copy = ROOT / 'build/firmware-binding-test'
    if copy.exists(): shutil.rmtree(copy)
    copy.mkdir()
    for path in firmware_inputs.sources():
        target = copy / path; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/path,target)
    for v in ('left','right','right-no-display'):
        directory=copy/'build'/('firmware-'+v)/'zephyr'; directory.mkdir(parents=True)
        for name in ('zmk.uf2','zephyr.dts','.config'):
            shutil.copyfile(ROOT/'build'/('firmware-'+v)/'zephyr'/name,directory/name)
        shutil.copyfile(ROOT/'build'/('firmware-'+v)/'build-attestation.json',directory.parent/'build-attestation.json')
    shutil.copytree(ROOT/'firmware/uf2',copy/'firmware/uf2')
    (copy/'validation').mkdir()
    shutil.copyfile(ROOT/'validation/revI-firmware.json',copy/'validation/revI-firmware.json')
    protected=list((copy/'firmware/uf2').glob('*'))+[copy/'validation/revI-firmware.json']
    before={str(p.relative_to(copy)):firmware_inputs.sha(p) for p in protected}
    check_firmware.ROOT=copy;firmware_inputs.ROOT=copy
    cases=[]
    for path,mutate,expected in (
        (copy/'firmware/config/flan36.keymap',lambda b:b.replace(b'&kp Q',b'&kp W',1),'Sources changed since build'),
        (copy/'build/firmware-right-no-display/zephyr/zmk.uf2',lambda b:b[:-1]+bytes([b[-1]^1]),'Build outputs changed'),
    ):
        original=path.read_bytes(); changed=mutate(original); assert changed != original
        path.write_bytes(changed)
        try:
            try: check_firmware.verify(zephyr, publish=True)
            except AssertionError as error: assert expected in str(error), error
            else: raise AssertionError('Stale firmware accepted')
            assert before == {str(p.relative_to(copy)):firmware_inputs.sha(p) for p in protected}
            cases.append({'mutation':str(path.relative_to(copy)),'rejected':True,'published_artifacts_unchanged':True})
        finally: path.write_bytes(original)
    (ROOT/'validation/revI-firmware-negative.json').write_text(json.dumps({'cases':cases,'isolated_copy':True},indent=2)+'\n')
    print('PASS: changed key binding and altered final-variant binary rejected; publication unchanged')


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--zephyr',type=Path,required=True)
    test(ap.parse_args().zephyr)
