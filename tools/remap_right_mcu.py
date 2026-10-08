#!/usr/bin/env python3
"""Apply the reviewed five-net right MCU remap to a disposable schematic.
Preserves symbol, wire and label UUIDs. Requires sexpdata. GPL-3.0-or-later.
"""
import argparse
from pathlib import Path
import sexpdata as sx


def tag(node, name):
    return isinstance(node, list) and node and str(node[0]) == name


def child(node, name):
    return next(n for n in node if tag(n, name))


def remap(source, dest):
    assert source.resolve() != dest.resolve() and not dest.exists()
    tree = sx.loads(source.read_text())
    u = next(n for n in tree if tag(n, "symbol") and any(tag(q,"property") and q[1:3]==["Reference","U1"] for q in n))
    ux,uy,angle = child(u,"at")[1:]; assert angle == 0
    lib = next(n for n in child(tree,"lib_symbols") if tag(n,"symbol") and n[1]==child(u,"lib_id")[1])
    pins = {}
    for unit in lib:
        if tag(unit,"symbol"):
            for pin in unit:
                if tag(pin,"pin"):
                    x,y,_=child(pin,"at")[1:]
                    pins[child(pin,"number")[1]]=[round(ux+x,5),round(uy-y,5)]
    def at(node): return [round(float(v),5) for v in child(node,"at")[1:3]]
    for old,new,net in [("D2","D21","ROW0"),("D3","D20","ROW1"),("D4","D19","ROW2"),("D5","D18","ROW3"),("D6","D15","COL0")]:
        a,b=pins[old],pins[new];assert a[1]==b[1]
        wire=next(n for n in tree if tag(n,"wire") and child(n,"pts")[1][1:]==a)
        far=child(wire,"pts")[2][1:]
        label=next(n for n in tree if tag(n,"label") and n[1]==net and at(n)==far)
        nc=next(n for n in tree if tag(n,"no_connect") and at(n)==b)
        child(wire,"pts")[1][1:]=b
        endpoint=[round(b[0]+2.54,5),b[1]]
        child(wire,"pts")[2][1:]=endpoint
        child(label,"at")[1:3]=endpoint
        child(nc,"at")[1:3]=a
    dest.write_text(sx.dumps(tree)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);p.add_argument("destination",type=Path)
    a=p.parse_args();remap(a.source,a.destination)
