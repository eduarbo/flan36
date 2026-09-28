#!/usr/bin/env python3
"""Reproducible nominal105 mm leads including the cell-end return bend.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json, math
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def planar_length(points,radius=1.5):
    return sum(math.dist(a,b) for a,b in zip(points,points[1:]))-(len(points)-2)*radius*(2-math.pi/2)
def route(index,battery):
    shift=.8*index;end=45.3 if battery=='adafruit-1570' else 44.8
    points=[[118.2+shift,47.4],[118.2+shift,22],[127.5+shift,22],[127.5+shift,28],[120.6+shift,28],[120.6+shift,43],[127.,43],[127.,47.6],[130.6,47.6],[130.6,54.1],[115.3,54.1],[115.3,59.2-2*index],[117.2,59.2-2*index]]
    total=planar_length(points)+(47.4-end)+math.pi*1.5
    extension=(105-total)/2;points[1][1]-=extension;points[2][1]-=extension
    return {'cell_end':[118.2+shift,end,4.2+.8*index],'return_center_y':47.4,'return_radius':1.5,'storage_z':7.2+.8*index,'control_points':points,'length_mm':round(planar_length(points)+(47.4-end)+math.pi*1.5,9)}
v={'schema':'flan36-wire-route-3','units':'mm','diameter':.6,'minimum_bend_radius_mm':1.5,'centerline_length_mm':105,'profiles':{b:[route(i,b) for i in range(2)] for b in ['adafruit-1570','301230']},'status':'Nominal continuous cell-end to mated PHR-2 leads including rear return bend. Stock105 mm lead length retained. 0.6 mm insulation diameter and inferred cell/plug terminals require measurement; not supplier tolerance or physical-fit certification.','release':'Lift frame, then lift display and support together. Bottom-open support relief leaves wires stationary. Leads detour around the retained J2 socket end. Remove MCU before straight5 mm sideways PH unplug and24 mm lift; flexing leads require a physical service trial.'}
for routes in v['profiles'].values():
    for r in routes:assert abs(r['length_mm']-105)<1e-7
if __name__=='__main__':
    (R/'design/revI-wire-study.json').write_text(json.dumps(v,indent=2)+'\n');print('Two105 mm nominal continuous routes per battery;0.6 mm insulation;R1.5 minimum.')
