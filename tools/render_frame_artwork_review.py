#!/usr/bin/env python3
"""Render the R6 approval solids and actual display context, without re-rendering history.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json
from pathlib import Path
import vtk
from render_frame_reviews import actor,camera,label,renderer,save
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/frame-redesign-r6/geometry'
OUT=ROOT/'design/proposals/frame-redesign-r6'
def run():
    master=json.loads((OUT/'master.json').read_text())
    check=json.loads((OUT/'geometry-check.json').read_text())
    digest=hashlib.sha256((OUT/'master.json').read_bytes()).hexdigest()
    assert check['master_sha256']==digest and check['saved_reopened']
    files=[]
    for view,tilt in [('native-review',18),('native-top',0)]:
        win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1680,1700);win.SetMultiSamples(0)
        header=renderer(win,[0,.935,1,1]);label(header,'FLAN36 / R6 REVIEW SOLIDS',32,64,32)
        label(header,'Actual geometry, fixed mechanical blank, flush color volumes. Artwork awaiting approval.',32,23,21)
        for i,(key,s) in enumerate(master['styles'].items()):
            col=i%3;row=i//3
            r=renderer(win,[col/3,.035+(1-row)*.45,(col+1)/3,.035+(2-row)*.45])
            for role,color in s['palette'].items():
                p=BUILD/(key+'-'+role+'.stl')
                if p.exists():actor(r,p,color)
            for p in sorted(BUILD.glob('NiceViewVisual*.stl')):
                color={'NiceViewVisual0':'#0B0C0E','NiceViewVisual1':'#C8A956','NiceViewVisual2':'#303836','NiceViewVisual3':'#BEC8AD'}[p.stem]
                actor(r,p,color)
            for p in sorted(BUILD.glob('Display*.stl')):actor(r,p,s['palette']['body'])
            camera(r,tilt,180,32);label(r,s['label'].upper(),25,14,24)
        footer=renderer(win,[0,0,1,.035]);label(footer,'24 x 56 mm / Z13.59 face / 13.90 x 30.50 opening / exact master paths / not a print release',25,17,19)
        path=OUT/(view+'.png');save(win,path);files.append(path)
    sources=[OUT/'master.json',OUT/'geometry-check.json',ROOT/'tools/render_frame_artwork_review.py',ROOT/'tools/render_frame_reviews.py',*sorted(BUILD.glob('*.stl'))]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'renderer':'VTK, actual exported review solids','master_sha256':digest,'artificial_aperture_fill':False,
        'sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},'images':{str(p.relative_to(ROOT)):sha(p) for p in files}}
    (OUT/'render-check.json').write_text(json.dumps(report,indent=2)+'\n');print('Rendered R6 actual review assemblies in oblique and top views')
if __name__=='__main__':run()
