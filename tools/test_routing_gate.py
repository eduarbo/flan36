#!/usr/bin/env python3
"""Reject wrong duplicate pads and broken routes in disposable PCB copies.
Run with KiCad Python. SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
from pathlib import Path
import shutil
import subprocess

import pcbnew as p
from check_routed_pcb import ROOT, verify

CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'


def test():
    root=ROOT/'build/routing-negative'; root.mkdir(parents=True,exist_ok=True)
    receipt=ROOT/'validation/revI-routing.json'; before=receipt.read_bytes(); cases=[]
    for kind in ('one-duplicate-pad','disconnected-row'):
        directory=root/kind; directory.mkdir(exist_ok=True)
        for side in ('left','right'):
            for ext in ('kicad_pcb','kicad_pro','kicad_sch'):
                name=f'flan36-{side}.{ext}';shutil.copyfile(ROOT/'hardware/revI'/name,directory/name)
        path=directory/'flan36-left.kicad_pcb';board=p.LoadBoard(str(path))
        if kind=='one-duplicate-pad':
            fp=next(f for f in board.GetFootprints() if f.GetReference()=='K01')
            pads=[q for q in fp.Pads() if q.GetNumber()=='1']; assert len(pads)>1
            net=next(n for n in board.GetNetsByNetcode().values() if n.GetNetname()=='/COL2')
            pads[0].SetNet(net)
        else:
            tracks=[t for t in board.GetTracks() if t.GetNetname()=='/ROW0']; assert tracks
            for track in tracks:board.Remove(track)
        p.SaveBoard(str(path),board)
        try: verify(directory,directory/'checks',CLI)
        except AssertionError as error:
            assert kind=='one-duplicate-pad' and 'K01' in str(error),error
        except subprocess.CalledProcessError:
            assert kind=='disconnected-row'
            drc=json.loads((directory/'checks/drc-left.json').read_text());assert drc['unconnected_items']
        else: raise AssertionError('Broken PCB accepted')
        assert receipt.read_bytes()==before
        cases.append({'mutation':kind,'rejected':True,'canonical_receipt_unchanged':True})
    (ROOT/'validation/revI-routing-negative.json').write_text(json.dumps({'cases':cases,'isolated_copy':True},indent=2)+'\n')
    print('PASS: one mismatched duplicate pad and a disconnected row rejected')


if __name__=='__main__':test()
