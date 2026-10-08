#!/usr/bin/env python3
"""Prepare disposable revI routing inputs without moving a component.

Run with KiCad Python. Canonical files are never overwritten by this tool.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]


def prepare(output, cli):
    output.mkdir(parents=True, exist_ok=True)
    reports = {}
    for side in ("left", "right"):
        name = f"flan36-{side}"
        source = ROOT / "hardware/revI" / name
        target = output / name
        if target.with_suffix(".kicad_pcb").exists():
            raise SystemExit(f"Refusing to overwrite {target}.kicad_pcb")
        for ext in (".kicad_sch", ".kicad_pro"):
            shutil.copyfile(source.with_suffix(ext), target.with_suffix(ext))
        netfile = output / f"netlist-{side}.xml"
        subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml",
                        "--output", str(netfile), str(source.with_suffix(".kicad_sch"))], check=True)
        xml = ET.parse(netfile).getroot()
        desired = {(node.get("ref"), node.get("pin")): net.get("name")
                   for net in xml.findall("./nets/net") for node in net.findall("node")}
        components = {c.get("ref"): c for c in xml.findall("./components/comp")}
        board = p.LoadBoard(str(source.with_suffix(".kicad_pcb")))
        assert not board.GetTracks(), "Do not reset routed work"
        nets = {n.GetNetname(): n for n in board.GetNetsByNetcode().values()}
        for name in sorted(set(desired.values())):
            if name not in nets:
                nets[name] = p.NETINFO_ITEM(board, name)
                board.Add(nets[name])
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            if ref not in components:
                assert ref in {"H1", "H2", "H3", "H4", "H5"}
                fp.SetBoardOnly(True)
                continue
            fp.SetValue(components[ref].findtext("value"))
            for pad in fp.Pads():
                name = desired.get((ref, pad.GetNumber()))
                if name:
                    old = pad.GetNetname()
                    assert not old or old.lstrip("/") == name.lstrip("/"), (ref, old, name)
                    pad.SetNet(nets[name])
        board.BuildConnectivity()
        p.SaveBoard(str(target.with_suffix(".kicad_pcb")), board)
        assert p.ExportSpecctraDSN(board, str(target.with_suffix(".dsn")))
        reports[side] = {"components": len(components), "net_nodes": len(desired),
                         "tracks": len(board.GetTracks()), "poses_changed": 0}
    for table in ("fp-lib-table", "sym-lib-table"):
        shutil.copyfile(ROOT / "hardware/revI" / table, output / table)
    (output / "libraries").symlink_to(ROOT / "hardware/revI/libraries", target_is_directory=True)
    (output / "preparation.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cli", default="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    args = parser.parse_args()
    prepare(args.output.resolve(), args.cli)
