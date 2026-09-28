#!/usr/bin/env python3
"""Three actual themed revI frame exports, displayed separately for comparison.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import hashlib,json
import vtk
from frame_finishes import palette,rgb
ROOT=Path(__file__).resolve().parents[1]
model=json.loads((ROOT/'design/revI.json').read_text())
r=vtk.vtkRenderer();r.SetBackground(.929,.94,.918)
w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(1500,900);w.SetMultiSamples(0);w.AddRenderer(r);r.SetUseFXAA(True)
sources=[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in ['design/revI.json','design/frame-finishes.json','tools/frame_finishes.py']]
for i,style in enumerate(['handheld','tv','cyberpunk']):
 parts=model['frameVariants']['left-'+style]['material_parts']
 assert parts and any(part['role']=='body' for part in parts)
 for part in parts:
  color=rgb(palette(style)[part['role']])
  p=ROOT/'mechanical/revI'/part['stl'];sources.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  rd=vtk.vtkSTLReader();rd.SetFileName(str(p));rd.Update()
  n=vtk.vtkPolyDataNormals();n.SetInputConnection(rd.GetOutputPort());n.SetFeatureAngle(45);n.ConsistencyOn();n.AutoOrientNormalsOn();n.Update()
  mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(n.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mp);a.SetPosition(-111+40*i,0,0);a.GetProperty().SetColor(*color);r.AddActor(a)
 t=vtk.vtkTextActor();t.SetInput({'handheld':'HANDHELD','tv':'RETRO TV','cyberpunk':'CYBERPUNK'}[style]);t.SetPosition(210+430*i,170);t.GetTextProperty().SetFontSize(27);t.GetTextProperty().SetColor(.16,.25,.22);r.AddActor2D(t)
for text,y,size in [('FLAN36 / INTERCHANGEABLE FRAMES',805,35),('Three flush themes. Colors follow native recessed material volumes.',755,22),('Actual revI CAD exports. Nominal study; printed fit and fastening untested.',55,20)]:
 t=vtk.vtkTextActor();t.SetInput(text);t.SetPosition(100,y);t.GetTextProperty().SetFontSize(size);t.GetTextProperty().SetColor(.16,.25,.22);r.AddActor2D(t)
c=r.GetActiveCamera();c.ParallelProjectionOn();c.SetFocalPoint(52,-37,8);c.SetPosition(52,-140,170);c.SetViewUp(0,0,1);c.SetParallelScale(53);r.ResetCameraClippingRange();w.Render()
f=vtk.vtkWindowToImageFilter();f.SetInput(w);f.ReadFrontBufferOff();f.Update();p=ROOT/'docs/images/revI-frames.png';writer=vtk.vtkPNGWriter();writer.SetFileName(str(p));writer.SetInputConnection(f.GetOutputPort());writer.Write();w.Finalize()
(ROOT/'validation/revI-frames-render.json').write_text(json.dumps({'image_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sources':sources,'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'geometry_changed':False},indent=2)+'\n')
