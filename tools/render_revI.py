#!/usr/bin/env python3
"""Render generated revI CAD and unchanged KLP meshes. No retouching or geometry edits.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
from pathlib import Path
import vtk

ROOT=Path(__file__).resolve().parents[1]
layout=json.loads((ROOT/'design/layout.json').read_text())
catalog=json.loads((ROOT/'keycaps/catalog.json').read_text());variants={v['id']:v for v in catalog['variants']};cfg=catalog['default_configuration']
m=json.loads((ROOT/'design/revI.json').read_text())
switches=json.loads((ROOT/'components/switches.json').read_text())
used={};views={};IMAGE_DIR=ROOT/'docs/images';IMAGE_DIR.mkdir(exist_ok=True)


def render(kind):
    ren=vtk.vtkRenderer();ren.SetBackground(.929,.933,.918)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(2400,1500);win.SetMultiSamples(0);win.AddRenderer(ren)
    ren.SetUseFXAA(True)
    cache={}
    def mesh(path):
        if path not in cache:
            used[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            rd=vtk.vtkSTLReader();rd.SetFileName(str(ROOT/path));rd.Update()
            if path.startswith('mechanical/revI/'):
                t=vtk.vtkTransform();t.Scale(1,-1,1)
                f=vtk.vtkTransformPolyDataFilter();f.SetTransform(t);f.SetInputData(rd.GetOutput());f.Update()
                rev=vtk.vtkReverseSense();rev.SetInputData(f.GetOutput());rev.ReverseCellsOn();rev.ReverseNormalsOn();rev.Update()
                rd=rev
            norms=vtk.vtkPolyDataNormals();norms.SetInputData(rd.GetOutput());norms.SetFeatureAngle(45);norms.ConsistencyOn();norms.AutoOrientNormalsOn();norms.Update()
            mp=vtk.vtkPolyDataMapper();mp.SetInputData(norms.GetOutput());cache[path]=mp
        return cache[path]
    def actor(mp,xyz,color,rz=0,rx=0,opacity=1):
        a=vtk.vtkActor();a.SetMapper(mp);a.RotateX(rx);a.RotateZ(rz);a.SetPosition(*xyz)
        p=a.GetProperty();p.SetColor(*color);p.SetAmbient(.20);p.SetDiffuse(.78);p.SetSpecular(.1);p.SetSpecularPower(32);p.SetInterpolationToPhong();p.SetOpacity(opacity);ren.AddActor(a);return a
    def part(side,name,color,dz=0,dx=0):
        visuals=m['parts'].get(side+'-'+name,{}).get('visuals',[])
        if visuals:return [actor(mesh(v['path']),(offset+dx,0,dz),tuple(int(v['color'][i:i+2],16)/255 for i in (1,3,5))) for v in visuals]
        return actor(mesh(f'mechanical/revI/{side}-{name}.stl'),(offset+dx,0,dz),color)
    def primitive(source,xyz,color,rz=0,rx=0):
        source.Update();mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(source.GetOutputPort());return actor(mp,xyz,color,rz,rx)
    def cube(x,y,z,w,d,h,color,rz=0):
        s=vtk.vtkCubeSource();s.SetXLength(w);s.SetYLength(d);s.SetZLength(h);return primitive(s,(x,y,z),color,rz)
    def cylinder(x,y,z,r,h,color):
        s=vtk.vtkCylinderSource();s.SetRadius(r);s.SetHeight(h);s.SetResolution(36);return primitive(s,(x,y,z),color,rx=90)
    rgb=lambda color:tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
    style=catalog['case_styles'][cfg['cases']['left']['style']]
    body=rgb(cfg['cases']['left'].get('base_color',style['base_color']));plate_color=rgb(cfg['cases']['left'].get('plate_color',style['plate_color']));cover=rgb(cfg['frames']['left']['color'])
    sides=['left'] if kind in ['side','stack','detail','corner','level'] else ['left','right']
    for side in sides:
        offset=0 if side=='left' else 161
        stack=kind=='stack';lid_dx=32 if stack else 0;lid_dz=13 if stack else 0
        if kind=='corner':
            part(side,'case-rim-base',(.64,.12,.23));part(side,'case-rim-plate',plate_color)
            part(side,'frame-'+cfg['frames'][side]['style'],(.64,.12,.23))
        else:
            part(side,'tray',body);part(side,'key-plate',plate_color)
            colors={'body':cfg['frames'][side]['color'],**cfg['frames'][side]['accents']}
            for volume in m['frameVariants'][side+'-'+cfg['frames'][side]['style']]['material_parts']:
                actor(mesh('mechanical/revI/'+volume['stl']),(offset+lid_dx,0,lid_dz),rgb(colors[volume['role']]))
        part(side,'pcb',(.10,.32,.26))
        part(side,'diodes',(.14,.15,.16))
        part(side,'hotswap-sockets',(.23,.23,.23))
        part(side,'cradle',(.30,.38,.39),10 if stack else 0)
        part(side,'battery-retainer',(.30,.38,.39),15 if stack else 0)
        part(side,'battery',(.67,.70,.71),10 if stack else 0)
        part(side,'mcu-riser',(.26,.32,.33),25 if stack else 0)
        part(side,'mcu',(.07,.15,.16),25 if stack else 0)
        part(side,'mcu-sockets',(.05,.06,.062))
        part(side,'display-socket',(.05,.06,.062))
        part(side,'jst',(.88,.865,.815));part(side,'reset',(.25,.26,.27));part(side,'slider',(.16,.16,.17))
        part(side,'display-sled',(.25,.33,.34),45 if stack else 0)
        part(side,'display',(.055,.075,.073),45 if stack else 0)
        for i in range(1,4):part(side,f'washer-{i}',(.35,.37,.37))
        for i in range(1,6):part(side,f'screw-{i}',(.25,.28,.26))
        for i in range(3):
            part(side,f'magnet-{i}',(.56,.59,.60))
            part(side,f'frame-target-{i}',(.56,.59,.60),lid_dz,lid_dx)
        for lead in m['batteryLeadProfiles'][side+'-'+cfg['batteries'][side]]:
            part(side,f"battery-lead-{lead['index']}",rgb(lead['color']))
        # Reflective screen artwork is illustrative, not a live hardware readback.
        bounds=m['parts'][side+'-display']['bounds_mm'];cx=(bounds[0]+bounds[3])/2;hy=m['halves'][side]['display_header']['y'];dz=45 if stack else 0
        screen_z=m['parameter_values_mm']['DisplayBottom']+1.915
        glass=vtk.vtkPlaneSource();glass.SetOrigin(offset+cx-5.372,hy-29.54,screen_z+dz);glass.SetPoint1(offset+cx+5.372,hy-29.54,screen_z+dz);glass.SetPoint2(offset+cx-5.372,hy-4.26,screen_z+dz)
        primitive(glass,(0,0,0),(.73,.79,.725))
        entries=[('BASE',hy-26,1.36),('BLE',hy-18,1.55),('L',hy-8,2.15)] if side=='left' else [('LINK',hy-26,1.36),('BAT',hy-18,1.55),('R',hy-8,2.15)]
        for text,y,scale in entries:
            src=vtk.vtkVectorText();src.SetText(text);src.Update();mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(src.GetOutputPort())
            a=actor(mp,(offset+cx-4.75,y,screen_z+.025+dz),(.08,.15,.12),rx=180);a.SetScale(scale,scale,scale)
        for key in layout['halves'][side]:
            for v in switches['choc-body']+switches['choc-stem']:
                actor(mesh(v['path']),(offset+key['x'],key['y'],5.4),rgb(v['color']),rz=-key['angle'])
            choice=cfg['keycaps'][side][key['ref']];v=variants[choice['variant']]
            actor(mesh(v['path']),(offset+key['x'],key['y'],v['seating_z_mm']),rgb(choice['color']),rz=-key['angle']-choice['rotation_deg'])
        for x,y in [(26,26),(57,15),(28,70),(125,83)]:
            cylinder(offset+(x if side=='left' else 160-x),y,-.6,3,1.2,(.055,.067,.07))
    floor=vtk.vtkPlaneSource();floor.SetOrigin(-600,-600,-1.21);floor.SetPoint1(900,-600,-1.21);floor.SetPoint2(-600,800,-1.21)
    primitive(floor,(0,0,0),(.929,.933,.918))
    ren.AutomaticLightCreationOff()
    for pos,intensity in [((-80,15,350),.80),((390,150,220),.35),((160,-180,180),.30)]:
        light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(*pos);light.SetFocalPoint(150,40,0);light.SetIntensity(intensity);ren.AddLight(light)
    # KiCad Y-down -> world coordinates, repairing handedness for normal lighting.
    actors=ren.GetActors();actors.InitTraversal()
    for _ in range(actors.GetNumberOfItems()):
        a=actors.GetNextActor();pose=vtk.vtkTransform();pose.Scale(1,-1,1);pose.Concatenate(a.GetMatrix())
        tf=vtk.vtkTransformPolyDataFilter();tf.SetTransform(pose);a.GetMapper().Update();tf.SetInputData(a.GetMapper().GetInput());tf.Update()
        rev=vtk.vtkReverseSense();rev.SetInputConnection(tf.GetOutputPort());rev.ReverseCellsOn();rev.ReverseNormalsOff();rev.Update()
        mp=vtk.vtkPolyDataMapper();mp.SetInputData(rev.GetOutput());a.SetMapper(mp);a.SetPosition(0,0,0);a.SetOrientation(0,0,0);a.SetScale(1,1,1)
    def label(text,x,y,size,color=(.14,.24,.22)):
        a=vtk.vtkTextActor();a.SetInput(text);a.SetPosition(x,y);p=a.GetTextProperty();p.SetFontFamilyToArial();p.SetFontSize(size);p.SetColor(*color);ren.AddActor2D(a)
    titles={'assembled':'FLAN36  /  REV I','top':'FLAN36  /  TOP VIEW','side':'FLAN36  /  SIDE PROFILE','stack':'FLAN36  /  REMOVABLE STACK','detail':'FLAN36  /  CONTOUR + MAGNETIC FRAMES','corner':'FLAN36  /  SHARED CORNER','level':'FLAN36  /  LEVEL CASE'}
    if kind!='corner':label(titles[kind],105,1380,44)
    sub=('Left half  /  KLP LAME  /  Orthographic profile' if kind=='side' else '36 keys  /  KLP LAME  /  Two nice!view displays  /  24 mm bay') if kind!='stack' else 'Adafruit 1570 or 301230. Captured battery cage and magnetic frame.'
    sub='Contour / Original thumb angles / Local tangent corners' if kind=='detail' else sub
    if kind=='level':sub=f"Frame + upper shell / {m['parameter_values_mm']['FrameTop']:g} mm / Glass recessed 0.20 mm"
    if kind=='corner':sub='Color rim + selected frame / Shared R2.4 corner / Actual CAD meshes'
    if kind!='corner':label(sub,108,1334,25,(.37,.44,.41))
    label('RevI CAD study. Wiring, final connectors, fit and operation remain untested.',108,60,24,(.36,.42,.39))
    cam=ren.GetActiveCamera();cam.ParallelProjectionOn()
    if kind=='assembled':focal=(160,-44,7);pos=(182,-255,360);up=(0,0,1);scale=99
    elif kind=='top':focal=(160,-43,5);pos=(160,-43,450);up=(0,1,0);scale=99
    elif kind=='side':focal=(78,-38,8);pos=(350,-38,8);up=(0,0,1);scale=53
    elif kind=='detail':focal=(115,-45,7);pos=(115,-45,450);up=(0,1,0);scale=68
    elif kind=='corner':focal=(127,-18,8);pos=(180,65,48);up=(0,0,1);scale=17
    elif kind=='level':focal=(79,-43,8);pos=(160,-220,180);up=(0,0,1);scale=58
    else:focal=(88,-39,28);pos=(225,-270,205);up=(0,0,1);scale=70
    cam.SetFocalPoint(*focal);cam.SetPosition(*pos);cam.SetViewUp(*up);cam.SetParallelScale(scale);ren.ResetCameraClippingRange();win.Render()
    if kind=='side':
        label(f"Level shell + frame: {m['parameter_values_mm']['FrameTop']:g} mm / Glass: {m['parameter_values_mm']['DisplayBottom']+1.9:g} mm",105,1235,29)
        label('Heights above base; feet add 1.2 mm. Switch retention plate remains at 7.6 mm.',105,170,24,(.37,.44,.41))
    if kind=='stack':
        label('nice!view  /  nice!nano  /  LiPo 100 mAh',105,1230,27)
        label('PCB with battery opening; unrouted',105,170,24,(.37,.44,.41))
    win.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(win);f.SetInputBufferTypeToRGB();f.ReadFrontBufferOff();f.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(IMAGE_DIR/f'revI-{kind}.png'));writer.SetInputConnection(f.GetOutputPort());writer.Write();win.Finalize()
    views[kind]={'keys':18*len(sides),'halves':sides,'exploded':kind=='stack','image_sha256':hashlib.sha256((IMAGE_DIR/f'revI-{kind}.png').read_bytes()).hexdigest()}
    print(kind,'rendered',flush=True)


for kind in ['assembled','top','side','stack','detail','corner','level']:render(kind)
receipt={'revision':'I','model_sha256':hashlib.sha256((ROOT/'design/revI.json').read_bytes()).hexdigest(),
         'layout_sha256':hashlib.sha256((ROOT/'design/layout.json').read_bytes()).hexdigest(),
         'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'sources':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in
                    ['design/revI.json','design/layout.json','keycaps/catalog.json','components/switches.json','tools/render_revI.py']],
         'meshes':[{'path':p,'sha256':h} for p,h in used.items()],
         'views':views,'geometry_source':'generated CAD, no image retouching',
         'illustrative':['component envelopes','feet','screen artwork','unmeasured cap stem-tip datum Z=11.7'],
         'unresolved':['battery cable routing','routed PCB','purchased component tolerances','physical fit and tests']}
(ROOT/'validation/revI-render.json').write_text(json.dumps(receipt,indent=2)+'\n')
