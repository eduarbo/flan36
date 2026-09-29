#!/usr/bin/env python3
"""Compare real seam geometry and six review solids. No artificial hole fill.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,math
from pathlib import Path
import vtk
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/display-seam/geometry'
def label(ren,t,x,y,size=18):
    a=vtk.vtkTextActor();a.SetInput(t);a.SetPosition(x,y);a.GetTextProperty().SetFontSize(size);a.GetTextProperty().SetColor(.14,.22,.20);ren.AddActor2D(a)
def actor(ren,path,color,translate=None):
    rd=vtk.vtkSTLReader();rd.SetFileName(str(path));rd.Update()
    data=rd.GetOutputPort()
    if translate:
        t=vtk.vtkTransform();t.Translate(*translate);f=vtk.vtkTransformPolyDataFilter();f.SetTransform(t);f.SetInputConnection(data);data=f.GetOutputPort()
    m=vtk.vtkPolyDataMapper();m.SetInputConnection(data);a=vtk.vtkActor();a.SetMapper(m)
    rgb=[int(color[i:i+2],16)/255 for i in [1,3,5]];a.GetProperty().SetColor(*rgb);a.GetProperty().SetAmbient(.75);a.GetProperty().SetDiffuse(.25);a.GetProperty().SetSpecular(0);ren.AddActor(a)
def display(ren):
    for p in sorted(BUILD.glob('*.stl')):
        name=p.stem
        if name.startswith('NiceViewVisual'):
            color={'NiceViewVisual0':'#0B0C0E','NiceViewVisual1':'#C8A956','NiceViewVisual2':'#303836','NiceViewVisual3':'#BEC8AD'}[name];actor(ren,p,color)
        elif name.startswith(('DisplayLedge','DisplaySide')):actor(ren,p,'#F1E6CA')
def camera(ren,elevation=0,azimuth=0,scale=33):
    c=ren.GetActiveCamera();c.ParallelProjectionOn();c.SetFocalPoint(12,-28,12)
    a=math.radians(azimuth);t=math.radians(elevation)
    c.SetPosition(12+180*math.sin(t)*math.cos(a),-28+180*math.sin(t)*math.sin(a),12+180*math.cos(t));c.SetViewUp(0,1,0);c.SetParallelScale(scale);ren.ResetCameraClippingRange()
def renderer(win,view):
    r=vtk.vtkRenderer();r.SetViewport(*view);r.SetBackground(.965,.962,.94);r.SetUseFXAA(True);win.AddRenderer(r);return r
def save(win,path):
    win.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(win);f.SetInputBufferTypeToRGB();f.ReadFrontBufferOff();f.Update()
    w=vtk.vtkPNGWriter();w.SetFileName(str(path));w.SetInputConnection(f.GetOutputPort());w.Write();win.Finalize()
def run():
    master=json.loads((ROOT/'design/proposals/display-seam-r1/master.json').read_text());p=master['styles']['talavera']['palette']
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1600,1040);win.SetMultiSamples(0)
    header=renderer(win,[0,.90,1,1]);label(header,'DISPLAY SEAM / ACTUAL GEOMETRY',30,62,28);label(header,'Top: current 14.50 mm opening. Bottom: 13.90 mm candidate. Same stack height.',30,28,20)
    views=[(0,0),(30,0),(45,45),(60,135)]
    for row,kind in enumerate(['current','candidate']):
        for col,(e,a) in enumerate(views):
            r=renderer(win,[col/4,.04+(1-row)*.43,(col+1)/4,.04+(2-row)*.43])
            for role,color in p.items():
                path=ROOT/'mechanical/revI'/('left-frame-talavera-'+role+'.stl') if kind=='current' else BUILD/('display-seam-r1-talavera-'+role+'.stl')
                actor(r,path,color,[-111,11,0] if kind=='current' else None)
            display(r);camera(r,e,a,34);label(r,kind.upper()+' / '+str(e)+' deg',15,12,17)
    footer=renderer(win,[0,0,1,.04]);label(footer,'Real PCB, glass and support ledges. Nominal 0.10 mm clearance; oblique corner leakage and physical fit are not qualified.',20,12,17)
    save(win,ROOT/'design/proposals/display-seam-r1/comparison.png')
    master=json.loads((ROOT/'design/proposals/frame-redesign-r5/master.json').read_text())
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1680,990);win.SetMultiSamples(0)
    header=renderer(win,[0,.90,1,1]);label(header,'FLAN36 / SIX REDESIGNS',35,56,30);label(header,'Actual nominal review solids. Exact JSON curves and colors. Awaiting artwork approval.',35,20,20)
    for i,(key,s) in enumerate(master['styles'].items()):
        col=i%3;row=i//3;r=renderer(win,[col/3,.04+(1-row)*.43,(col+1)/3,.04+(2-row)*.43])
        for role,color in s['palette'].items():
            path=BUILD/('frame-redesign-r5-'+key+'-'+role+'.stl')
            if path.exists():actor(r,path,color)
        display(r);camera(r,12,180,33);label(r,s['label'].upper(),25,14,22)
    footer=renderer(win,[0,0,1,.04]);label(footer,'24 x 56 mm / face Z13.59 / candidate opening 13.90 x 30.50 mm / no raised artwork / not a print release',30,12,17)
    save(win,ROOT/'design/proposals/frame-redesign-r5/native-review.png')
    sources=[ROOT/'tools/render_frame_reviews.py',*BUILD.glob('*.stl')]
    report={'renderer':'VTK, actual exported review solids','artificial_aperture_fill':False,'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'images':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'design/proposals/display-seam-r1/comparison.png',ROOT/'design/proposals/frame-redesign-r5/native-review.png']}}
    (ROOT/'design/proposals/frame-redesign-r5/render-check.json').write_text(json.dumps(report,indent=2)+'\n');print('Rendered actual seam and six review assemblies')
if __name__=='__main__':run()
