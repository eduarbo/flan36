#!/usr/bin/env python3
"""Render front and oblique views of actual CAD for reference comparison.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,json,hashlib
from pathlib import Path
import vtk
from frame_finishes import FINISHES,rgb
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--native-dir',type=Path,default=ROOT/'mechanical/revI');p.add_argument('--out-dir',type=Path,default=ROOT/'docs/images/frames');a=p.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
a.native_dir=a.native_dir.resolve()
model=json.loads((ROOT/'design/revI.json').read_text());sources={}
def actor(r,path,color):
 sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
 rd=vtk.vtkSTLReader();rd.SetFileName(str(path));rd.Update();n=vtk.vtkPolyDataNormals();n.SetInputConnection(rd.GetOutputPort());n.SetFeatureAngle(45);n.ConsistencyOn();n.AutoOrientNormalsOn();m=vtk.vtkPolyDataMapper();m.SetInputConnection(n.GetOutputPort());o=vtk.vtkActor();o.SetMapper(m);o.GetProperty().SetColor(*rgb(color));o.GetProperty().SetAmbient(.7);o.GetProperty().SetDiffuse(.3);o.GetProperty().SetSpecular(0);r.AddActor(o)
for style in ['tape','orbit','manga','talavera']:
 t=FINISHES['styles'][style];w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(720,820);w.SetMultiSamples(0)
 for i in range(2):
  r=vtk.vtkRenderer();r.SetViewport(i/2,0,(i+1)/2,1);r.SetBackground(.947,.947,.915);r.SetUseFXAA(True);w.AddRenderer(r)
  for role,color in t['colors'].items():actor(r,a.native_dir/f'left-frame-{style}-{role}.stl',color)
  for visual in model['parts']['left-display']['visuals']:actor(r,ROOT/visual['path'],visual['color'])
  c=r.GetActiveCamera();c.ParallelProjectionOn();c.SetFocalPoint(123,-39,11);c.SetPosition((123,-39,240) if i==0 else (210,-95,230));c.SetViewUp(0,1,0);c.SetParallelScale(34);r.ResetCameraClippingRange()
 w.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.SetInputBufferTypeToRGB();f.ReadFrontBufferOff();f.Update();out=a.out_dir/(style+'.png');wr=vtk.vtkPNGWriter();wr.SetFileName(str(out));wr.SetInputConnection(f.GetOutputPort());wr.Write();w.Finalize()
(ROOT/'validation/revI-frame-detail-renders.json').write_text(json.dumps(dict(sources=sources,renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),physical_acceptance=False),indent=2)+'\n')
print('Rendered four reference comparisons from native parts')
