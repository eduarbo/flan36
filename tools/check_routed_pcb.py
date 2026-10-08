#!/usr/bin/env python3
"""Read every physical pad and independently check the routed revI boards.
Run with KiCad Python. SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pcbnew as p
from check_layout import read_sexpr

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "fe8c7fdc1b13b8eac6383c3315af8e749b1b8d4c"


def geometry(board):
    result = {}
    for fp in board.GetFootprints():
        pads = []
        for q in fp.Pads():
            pads.append((q.m_Uuid.AsString(), q.GetNumber(), q.GetPosition().x, q.GetPosition().y,
                         q.GetOrientationDegrees(), q.GetSize().x, q.GetSize().y,
                         q.GetDrillSize().x, q.GetDrillSize().y, q.GetShape(), q.GetAttribute(),
                         q.GetLayerSet().FmtHex()))
        result[fp.GetReference()] = {"uuid": fp.m_Uuid.AsString(),
            "xy": [fp.GetPosition().x, fp.GetPosition().y], "angle": fp.GetOrientationDegrees(),
            "layer": fp.GetLayer(), "locked": fp.IsLocked(), "symbol": fp.GetPath().AsString(),
            "pads": sorted(pads), "models": [m.m_Filename for m in fp.Models()]}
    return result


def edges(path):
    tree = read_sexpr(path.read_text())
    # KiCad adds missing UUIDs and removes trailing decimal zeroes when saving.
    # Compare exact decimal geometry, independent of those serialization changes.
    def canonical(node):
        if isinstance(node, list):
            return tuple(canonical(c) for c in node if not (isinstance(c, list) and c[0] == "uuid"))
        try:
            return str(Decimal(node).normalize())
        except InvalidOperation:
            return node
    return sorted(repr(canonical(n)) for n in tree if isinstance(n, list) and n[0].startswith("gr_")
                  and any(isinstance(c, list) and c[:2] == ["layer", "Edge.Cuts"] for c in n))


def verify(directory, output, cli):
    output.mkdir(parents=True, exist_ok=True)
    result = {"schema": "flan36-routed-pcb-1", "baseline": BASELINE,
              "kicad_version": p.GetBuildVersion(), "physical_acceptance": False, "halves": {}}
    pinmap = json.loads((ROOT / "design/pinmap.json").read_text())["halves"]
    layout = json.loads((ROOT / "design/layout.json").read_text())["halves"]
    for side in ("left", "right"):
        name = f"flan36-{side}"
        board_path = directory / (name + ".kicad_pcb")
        sch_path = board_path.with_suffix(".kicad_sch")
        original = output / (name + "-baseline.kicad_pcb")
        original.write_bytes(subprocess.check_output(["git", "show", f"{BASELINE}:hardware/revI/{name}.kicad_pcb"], cwd=ROOT))
        board = p.LoadBoard(str(board_path)); old = p.LoadBoard(str(original))
        assert geometry(board) == geometry(old), "Component/pad/pose/model mutation"
        assert edges(board_path) == edges(original), "Outline or aperture changed"
        assert board.GetTracks(), "Unrouted study is not accepted"
        assert board.GetCopperLayerCount() == 2
        netfile = output / (name + "-netlist.xml")
        subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(netfile), str(sch_path)], check=True)
        root = ET.parse(netfile).getroot()
        expected = {(node.get("ref"), node.get("pin")): net.get("name")
                    for net in root.findall("./nets/net") for node in net.findall("node")}
        fps = {f.GetReference(): f for f in board.GetFootprints()}
        physical_pads = 0
        for fp in fps.values():
            for pad in fp.Pads():
                physical_pads += 1
                assert pad.GetNetname() == expected.get((fp.GetReference(), pad.GetNumber()), ""), (
                    side, fp.GetReference(), pad.GetNumber(), pad.m_Uuid.AsString())
        for key in layout[side]:
            ref = key["ref"]; diode = "D" + ref[1:]
            assert expected[ref, "1"] == f'/COL{key["col"]}'
            assert expected[ref, "2"] == expected[diode, "2"] == f"/{ref}_A"
            assert expected[diode, "1"] == f'/ROW{key["row"]}'
        pins = {"D0": "DISP_SCK", "D1": "DISP_MOSI", "D14": "DISP_CS", "RAW": "BAT_SW", "VCC": "VCC", "RST": "RESET"}
        pins.update({f"D{x}": f"ROW{i}" for i, x in enumerate(pinmap[side]["rows"])})
        pins.update({f"D{x}": f"COL{i}" for i, x in enumerate(pinmap[side]["cols"])})
        for pad, net in pins.items(): assert expected["U1", pad] == "/"+net
        for i, net in enumerate(("DISP_MOSI", "DISP_SCK", "VCC", "GND", "DISP_CS"), 1):
            assert expected["J2", str(i)] == "/"+net
        for ref, pad, net in [("J1","1","BAT_PLUS"),("J1","2","GND"),("SW1","1","BAT_PLUS"),("SW1","2","BAT_SW"),("SW2","1","RESET"),("SW2","2","GND")]:
            assert expected[ref,pad] == "/"+net
        counts = {}
        for kind, check, source in (("pcb", "drc", board_path), ("sch", "erc", sch_path)):
            report = output / f"{check}-{side}.json"
            command = [cli, kind, check, "--format", "json", "--severity-all", "--exit-code-violations", "-o", str(report)]
            if kind == "pcb": command += ["--schematic-parity", "--all-track-errors"]
            subprocess.run(command + [str(source)], check=True)
            data = json.loads(report.read_text())
            if kind == "pcb":
                assert not data["violations"] and not data["unconnected_items"] and not data["schematic_parity"]
                counts.update(drc_violations=0, unconnected_items=0, schematic_parity=0)
            else:
                assert not any(s["violations"] for s in data["sheets"])
                counts["erc_violations"] = 0
        widths = [p.ToMM(t.GetWidth()) for t in board.GetTracks() if not isinstance(t,p.PCB_VIA)]
        assert min(widths) >= .2 - 1e-7
        result["halves"][side] = {**counts, "components": len(fps), "physical_pads_checked": physical_pads,
            "matrix_keys": 18, "tracks_and_vias": len(board.GetTracks()), "minimum_track_mm": min(widths),
            "poses_pads_models_and_outline_preserved": True,
            "pcb_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
            "schematic_sha256": hashlib.sha256(sch_path.read_bytes()).hexdigest(),
            "rules_sha256": hashlib.sha256(board_path.with_suffix(".kicad_pro").read_bytes()).hexdigest()}
    (ROOT / "validation/revI-routing.json").write_text(json.dumps(result, indent=2)+"\n")
    print("PASS: both boards connected; all physical pads, semantic matrix and unchanged geometry verified")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory", type=Path, default=ROOT/"hardware/revI")
    ap.add_argument("--output", type=Path, default=ROOT/"build/routing-validation")
    ap.add_argument("--cli", default="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    a=ap.parse_args(); verify(a.directory.resolve(), a.output.resolve(), a.cli)
