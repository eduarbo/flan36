#!/usr/bin/env python3
"""Render the current native material solids in a compact comparison gallery.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import argparse,hashlib,json
import vtk
from frame_finishes import palette,rgb,FINISHES
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--native-dir',type=Path,default=ROOT/'mechanical/revI');parser.add_argument('--output',type=Path,default=ROOT/'docs/images/revI-frame-gallery.png');parser.add_argument('--report',type=Path,default=ROOT/'validation/revI-frames-render.json');parser.add_argument('--approved-only',action='store_true');args=parser.parse_args()
args.native_dir=args.native_dir.resolve()
model=json.loads((ROOT/'design/revI.json').read_text());styles={k:v for k,v in FINISHES['styles'].items() if not args.approved_only or v.get('approval_status')=='approved'}
columns=5 if args.approved_only else 6;rows=1 if args.approved_only else 2
win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(1600,1000) if args.approved_only else win.SetSize(1920,1220);win.SetMultiSamples(0)
footer=vtk.vtkRenderer();footer.SetViewport(0,0,1,.04);footer.SetBackground(.947,.947,.915);win.AddRenderer(footer)
sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['design/revI.json','design/frame-finishes.json','tools/frame_finishes.py']}
def label(ren,text,x,y,size,color=(.18,.24,.22)):
 a=vtk.vtkTextActor();a.SetInput(text);a.SetPosition(x,y);a.GetTextProperty().SetFontSize(size);a.GetTextProperty().SetColor(*color);a.GetTextProperty().SetFontFamilyToArial();ren.AddActor2D(a)
def actor(ren,path,color):
 p=ROOT/path
 candidate=args.native_dir/p.name
 if candidate.exists():p=candidate
 sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 rd=vtk.vtkSTLReader();rd.SetFileName(str(p));rd.Update()
 normals=vtk.vtkPolyDataNormals();normals.SetInputConnection(rd.GetOutputPort());normals.SetFeatureAngle(45);normals.ConsistencyOn();normals.AutoOrientNormalsOn()
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetColor(*rgb(color));a.GetProperty().SetAmbient(.75);a.GetProperty().SetDiffuse(.25);a.GetProperty().SetSpecular(0);ren.AddActor(a)
for i,(style,theme) in enumerate(styles.items()):
 col=i%columns;row=i//columns;r=vtk.vtkRenderer();r.SetViewport(col/columns,.04+(rows-1-row)*(.86/rows),(col+1)/columns,.04+(rows-row)*(.86/rows));r.SetBackground(.947,.947,.915);r.SetUseFXAA(True);win.AddRenderer(r)
 for part in model['frameVariants']['left-'+style]['material_parts']:actor(r,'mechanical/revI/'+part['stl'],theme['colors'][part['role']])
 for visual in model['parts']['left-display']['visuals']:actor(r,visual['path'],visual['color'])
 label(r,theme['label'],25,22,23)
 camera=r.GetActiveCamera();camera.ParallelProjectionOn();camera.SetFocalPoint(123,-39,11);camera.SetPosition(123,-47,240);camera.SetViewUp(0,1,0);camera.SetParallelScale(36);r.ResetCameraClippingRange()
r=vtk.vtkRenderer();r.SetViewport(0,.90,1,1);r.SetBackground(.947,.947,.915);win.AddRenderer(r);label(r,'FLAN36 / APPROVED R4' if args.approved_only else 'FLAN36 / FRAME COLLECTION',45,52 if args.approved_only else 65,34);label(r,'Five approved designs. Corrected display seam. Solid colors. 13.59 mm face.' if args.approved_only else '5 approved designs; 6 existing designs with new proposals awaiting approval.',45,25,23)
if not args.approved_only:
 r=vtk.vtkRenderer();r.SetViewport(5/6,.04,1,.47);r.SetBackground(.947,.947,.915);win.AddRenderer(r);label(r,'FLUSH COLOR',15,260,23);label(r,'0.4 mm co-print inlays',15,222,20);label(r,f"{model['parameter_values_mm']['FrameTop']:.2f} mm shared roof",15,190,20);label(r,'Editable native CAD',15,158,20);label(r,'Prototype / fit untested',15,105,18)
win.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(win);f.SetInputBufferTypeToRGB();f.ReadFrontBufferOff();f.Update();p=args.output;p.parent.mkdir(parents=True,exist_ok=True);w=vtk.vtkPNGWriter();w.SetFileName(str(p));w.SetInputConnection(f.GetOutputPort());w.Write();win.Finalize()
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(dict(image_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sources=[dict(path=p,sha256=h) for p,h in sources.items()],renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),geometry_changed=False,styles=list(styles)),indent=2)+'\n')
print('Rendered',len(styles),'native frames')
