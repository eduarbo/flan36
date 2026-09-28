"""Build the editable revI study using only native FreeCAD features.

Run with FreeCAD's Python (see docs/freecad.md). Opening/recomputing the saved
FCStd does not need this script, CadQuery, StepUp, or any custom Python proxy.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
import math
import sys
from pathlib import Path

import FreeCAD as A
import FreeCADGui as G
import Part
import Sketcher
import Mesh

def progress(*args, **kwargs):
    sys.__stdout__.write(" ".join(map(str,args))+"\n"); sys.__stdout__.flush()
print=progress

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'mechanical/revI'
OUT.mkdir(parents=True, exist_ok=True)
import faulthandler
faulthandler.enable()
G.showMainWindow()
print('GUI ready',flush=True)
doc = A.newDocument('Flan36_revI')
doc.Label = 'Flan36 · revI · editable study'
doc.Comment = 'GPL-3.0-or-later; Piantor/beekeeb, KLP Lame/braindefender CC-BY-SA-4.0. Nominal study, not manufacturing release.'
layout = json.loads((ROOT / 'design/layout.json').read_text())
profiles = json.loads((ROOT / 'design/revI-profiles.json').read_text())
params = doc.addObject('Spreadsheet::Sheet', 'Parameters')
params.Label = '00 · Parameters (edit column B)'
values = [
    ('Floor', 1.4, 'Base floor'), ('PlateThickness', 1.3, 'Plate thickness'),
    ('PlateBottom', 6.3, 'Plate bottom Z'), ('PCBTop', 5.4, 'PCB top'),
    ('PCBThickness', 1.6, 'PCB thickness'), ('MCUShiftY', 7.5, 'Controller shift toward thumbs'),
    ('MCUBottom', 8.8, 'Controller PCB bottom'),
    ('DisplayShiftY', 2.4, 'Display shift toward thumbs'),
    ('DisplayBottom', 14.2, 'Display PCB bottom'),
    ('BatteryShiftY', 2.0, 'Battery shift toward thumbs'), ('BatteryBottom', 2.0, 'Cell bottom'),
    ('FrameTop', 16.6, 'Frame top height'),
    ('FrameRoof', 1.2, 'Frame roof thickness'), ('WindowMargin', .4, 'Clearance per glass side'),
    ('SlotClearance', .10, 'Cage/opening clearance PER SIDE'),
]
cells = {}
for row, (alias, number, note) in enumerate(values, 2):
    params.set(f'A{row}', alias); params.set(f'B{row}', f'{number} mm')
    params.setAlias(f'B{row}', alias); params.set(f'C{row}', note); cells[alias] = f'B{row}'
params.set('A1', 'Parameter'); params.set('B1', 'Value'); params.set('C1', 'Purpose')
params.setColumnWidth('A', 165); params.setColumnWidth('B', 95); params.setColumnWidth('C', 290)
params.setStyle('A1:C1', 'bold'); params.setBackground('B2:B16', (0.84, .95, .88))
doc.recompute()
print('Parameters ready',flush=True)
frame_profiles=json.loads((ROOT/'design/revI-frame-profiles.json').read_text())
sys.path.insert(0,str(ROOT/'tools'));from keycap_config import load,default_config,check
sys.path.insert(0,str(ROOT/'tools/freecad'));import components
import extra_frames
extension_spec=extra_frames.load_spec(ROOT)
catalog=load();configuration=default_config(catalog);assert not check(configuration,catalog)[0]
variants={v['id']:v for v in catalog['variants']}
finals = {}
metadata = {'revision': 'I', 'units': 'mm', 'coordinate_system': 'FreeCAD X=KiCad X, Y=-KiCad Y; PCB top=5.4 mm',
            'manufacturing_ready': False, 'parameters': cells, 'halves': {}, 'parts': {}}


def expr(obj, prop, expression):
    obj.setExpression(prop, expression)


for side in ('left', 'right'):
    print('Building',side,flush=True)
    prefix = 'L_' if side == 'left' else 'R_'
    assembly = doc.addObject('App::Part', prefix + 'Half')
    assembly.Label = '01 · Left' if side == 'left' else '02 · Right'
    history = doc.addObject('App::DocumentObjectGroup', prefix + 'Construction')
    history.Label = 'Construction · sketches and operations'; assembly.addObject(history)
    finished = []
    mx = lambda x: x if side == 'left' else 160 - x

    def add(typ, name):
        obj = doc.addObject(typ, prefix + name); history.addObject(obj); return obj

    def box(name, x0, y0, x1, y1, z, height, shift=None):
        obj = add('Part::Box', name)
        obj.Length = x1 - x0; obj.Width = y1 - y0; obj.Height = height
        obj.Placement.Base = A.Vector(x0 if side == 'left' else 160 - x1, -y1, z)
        if shift:
            expr(obj, 'Placement.Base.y', f'-{y1} mm - Parameters.{shift}')
        return obj

    def cyl(name, x, y, z, radius, height):
        o = add('Part::Cylinder', name); o.Radius = radius; o.Height = height
        o.Placement.Base = A.Vector(mx(x), -y, z); return o

    def sketch(name, points, plane='XY', rail=False):
        s = add('Sketcher::SketchObject', name)
        # Native lines and arcs: the visible corner count is the control polygon,
        # not the tessellation needed for STL/PCB export.
        arcs=None
        if points==profiles[side]['outer'] and plane=='XY':
            vec=lambda p:A.Vector(p[0],-p[1],0)
            for segment in profiles[side]['outer_segments']:
                if segment['kind']=='bezier':
                    geometry=Part.BezierCurve();geometry.setPoles([vec(p) for p in segment['poles']]);geometry=geometry.toBSpline()
                elif segment['kind']=='arc':geometry=Part.Arc(vec(segment['start']),vec(segment['mid']),vec(segment['end']))
                else:geometry=Part.LineSegment(vec(segment['start']),vec(segment['end']))
                j=s.addGeometry(geometry,False);s.addConstraint(Sketcher.Constraint('Block',j))
            return s
        if points==profiles[side]['outer']:arcs=profiles[side]['outer_arcs']
        elif points==frame_profiles[side]['outer']:arcs=frame_profiles[side]['outer_arcs']
        elif points==frame_profiles[side]['bevel']:arcs=frame_profiles[side]['bevel_arcs']
        elif points==frame_profiles[side]['facet']:arcs=frame_profiles[side]['facet_arcs']
        if arcs and plane=='XY':
            vec=lambda p:A.Vector(p[0],-p[1],0)
            for i,a in enumerate(arcs):
                j=s.addGeometry(Part.Arc(vec(a['start']),vec(a['mid']),vec(a['end'])),False)
                s.addConstraint(Sketcher.Constraint('Block',j))
                j=s.addGeometry(Part.LineSegment(vec(a['end']),vec(arcs[(i+1)%len(arcs)]['start'])),False)
                s.addConstraint(Sketcher.Constraint('Block',j))
            return s
        vectors = [A.Vector(x, -y, 0) for x, y in points] if plane == 'XY' else [A.Vector(y, z, 0) for y,z in points]
        for a,b in zip(vectors, vectors[1:] + vectors[:1]):
            i = s.addGeometry(Part.LineSegment(a, b), False)
            if not rail:s.addConstraint(Sketcher.Constraint('Block', i))
        if rail:
            for i,v in enumerate(vectors):
                s.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%len(vectors),1))
                s.addConstraint(Sketcher.Constraint('DistanceX',i,1,v.x))
                c=s.addConstraint(Sketcher.Constraint('DistanceY',i,1,v.y))
                if v.y in (16.6,15.4):s.setExpression(f'Constraints[{c}]','Parameters.FrameTop' + (' - 1.2 mm' if v.y==15.4 else ''))
        return s

    def extrude(name, points, z, height):
        s = sketch(name + 'Sketch', points)
        e = add('Part::Extrusion', name); e.Base = s; e.Dir = A.Vector(0,0,1)
        e.LengthFwd = height; e.Solid = True; e.Placement.Base.z = z
        return e

    def fuse(name, objects):
        o = add('Part::MultiFuse', name); o.Shapes = objects; o.Refine = True; return o

    def cut(name, base, tool):
        o = add('Part::Cut', name); o.Base = base; o.Tool = tool; o.Refine = True; return o

    def done(name, obj, label, group, color, printable=False):
        assembly.addObject(obj); finished.append(obj)
        obj.Label = label
        obj.addProperty('App::PropertyString', 'PartID', 'Flan36'); obj.PartID = side + '-' + name
        obj.addProperty('App::PropertyString', 'Layer', 'Flan36'); obj.Layer = group
        obj.addProperty('App::PropertyBool', 'PrototypePrintable', 'Flan36'); obj.PrototypePrintable = printable
        obj.addProperty('App::PropertyString', 'ModelStatus', 'Flan36'); obj.ModelStatus = 'Nominal study; physical fit untested'
        view=obj.LinkedObject.ViewObject if obj.TypeId=='App::Link' else obj.ViewObject
        view.ShapeColor = color; view.LineColor = (.13,.18,.17)
        if hasattr(obj,'VisualFaceColors'):view.DiffuseColor=[tuple(c) for c in json.loads(obj.VisualFaceColors)]
        finals[side + '-' + name] = obj
        return obj

    print(side,'helpers ready',flush=True)
    # Native sketch/extrusion/boolean history; stored source contour is editable.
    outer = extrude('OuterPad', profiles[side]['outer'], 0, 6.3)
    cavity = extrude('Cavity', profiles[side]['inner'], 1.4, 8)
    expr(cavity, 'Placement.Base.z', 'Parameters.Floor')
    tray = cut('TrayShell', outer, cavity)
    magnetic=json.loads((ROOT/'design/revI-magnets.json').read_text())
    mount_data=json.loads((ROOT/'design/revI-mounts.json').read_text())
    mounts=[m['xy'] for m in mount_data['left']]
    radii=[m['post_radius'] for m in mount_data['left']]
    holes = []
    for i, ((x,y),radius) in enumerate(zip(mounts,radii),1):
        pillar = cyl('Pillar'+str(i),x,y,1.4,radius,2.4)
        expr(pillar, 'Placement.Base.z', 'Parameters.Floor')
        expr(pillar, 'Height', 'Parameters.PCBTop - Parameters.PCBThickness - Parameters.Floor')
        tray = fuse('TrayPillar'+str(i), [tray,pillar])
        tray = cut('TrayDrill'+str(i),tray,cyl('Pilot'+str(i),x,y,-.1,.85,4.2))
        if i<=3:
            washer = cut('Washer'+str(i),cyl('Spacer'+str(i),x,y,5.4,radius,.9),cyl('SpacerHole'+str(i),x,y,5.3,1.15,1.1))
            done('washer-'+str(i),washer,'Washer '+str(i),'fasteners',(.54,.57,.54),True)
        holes.append(cyl('BoardDrill'+str(i),x,y,3.7,1.1,2))
        tray=cut('WasherSeat'+str(i),tray,cyl('WasherSeatTool'+str(i),x,y,5.4,radius+.1,1.0))
    for i,m in enumerate(mount_data['left'],1):
        x,y=m['xy'];seat=m['seat_z'];length=m['length']
        screw=fuse('Screw'+str(i),[cyl('Shaft'+str(i),x,y,seat-length,1,length),cyl('Head'+str(i),x,y,seat,m['head_diameter']/2,m['head_height'])])
        done('screw-'+str(i),screw,'M2 x '+str(length)+' · low head','fasteners',(.24,.26,.25))
    for i,(x,y) in enumerate(magnetic['stations_left']):
        post=cyl('MagnetPost'+str(i),x,y,1.4,1.85,4.9)
        locator=cyl('MagnetLocator'+str(i),x,y,6.3,1.4,.3)
        tray=fuse('TrayMagnetPost'+str(i),[tray,post,locator])
        tray=cut('MagnetPocket'+str(i),tray,cyl('MagnetPocketTool'+str(i),x,y,3.1,1.15,3.2))
        magnet=cyl('Magnet'+str(i),x,y,3.2,1,3)
        done('magnet-'+str(i),magnet,'Captive magnet 2 x 3 mm','fasteners',(.57,.6,.62))
        target=cyl('SteelTarget'+str(i),x,y,7.1,1,4)
        done('frame-target-'+str(i),target,'Captive steel pin 2 x 4 mm','lid',(.53,.56,.58))
        holes.append(cyl('MagnetBoardDrill'+str(i),x,y,3.7,2.05,2))
    power_slot = box('PowerAccess',128.3,55.4,140,63.9,5.1,4.1)
    tray = cut('TrayPowerCut',tray,power_slot)
    # Case variants derive from this shared structural tray.

    plate_pad=extrude('PlatePad',profiles[side]['outer'],6.3,1.3)
    plate_tool=extrude('PlateFrameTool',profiles[side]['plate_frame_clearance'],6.2,1.5)
    expr(plate_pad,'Placement.Base.z','Parameters.PlateBottom');expr(plate_pad,'LengthFwd','Parameters.PlateThickness')
    expr(plate_tool,'Placement.Base.z','Parameters.PlateBottom - 0.1 mm');expr(plate_tool,'LengthFwd','Parameters.PlateThickness + 0.2 mm')
    plate=cut('PlateFrameClearance',plate_pad,plate_tool)
    for key in layout['halves'][side]:
        angle = -math.radians(key['angle']); points=[]
        for x,y in [(-7,-7),(7,-7),(7,7),(-7,7)]:
            points.append((key['x']+x*math.cos(angle)-y*math.sin(angle),key['y']+x*math.sin(angle)+y*math.cos(angle)))
        plate=cut('Plate_'+key['ref'],plate,extrude('SwitchCut_'+key['ref'],points,5.5,4))
    for i,(x,y) in enumerate(mounts[:3],1):plate=cut('PlateDrill'+str(i),plate,cyl('PlateHole'+str(i),x,y,5.5,1.15,4))
    for i,(x,y) in enumerate(mounts[3:],4):plate=cut('PlateHeadRelief'+str(i),plate,cyl('PlateHeadTool'+str(i),x,y,5.3,2.15,1.45))
    case_catalog=json.loads((ROOT/'design/cases.json').read_text())
    # Shared interfaces, native booleans and explicit interchangeable source bodies.
    ring=cut('RimRing',extrude('RimOuter',profiles[side]['outer'],6.3,1.3),
             extrude('RimInner',profiles[side]['rim_inner'],6.2,1.5))
    ring=cut('RimFrameClearance',ring,plate_tool)
    rim_tray=fuse('RimTray',[tray,ring])
    rim_plate=add('Part::MultiCommon','RimPlate')
    rim_plate.Shapes=[plate,extrude('InsetPlateEnvelope',profiles[side]['rim_inset'],6.2,1.5)]
    rim_plate.Refine=True
    terrace=tray
    for j,z in enumerate(case_catalog['geometry_mm']['terrace_band_bottoms']):
        band=cut('TerraceBand'+str(j),extrude('TerraceOuter'+str(j),profiles[side]['outer'],z,.6),
                 extrude('TerraceInner'+str(j),profiles[side]['terrace_inset'],z-.1,.8))
        terrace=cut('TerraceCut'+str(j),terrace,band)
    sources={'solid':(tray,plate),'rim':(rim_tray,rim_plate),'terrace':(terrace,plate)}
    for style,pair in sources.items():
        for group,source in zip(('base','plate'),pair):
            # Separate native compounds allow shared plate geometry without conflicting styles.
            variant=add('Part::Compound','Case_'+style+'_'+group);variant.Links=[source]
            variant.addProperty('App::PropertyString','CaseStyle','Flan36');variant.CaseStyle=style
            variant.addProperty('App::PropertyString','CaseGroup','Flan36');variant.CaseGroup=group
            variant.Label=case_catalog['styles'][style]['label']+' · '+group
            color=case_catalog['styles'][style][group+'_color']
            variant.ViewObject.ShapeColor=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
    for group,part_id in [('base','tray'),('plate','key-plate')]:
        active=doc.addObject('App::Link',prefix+('ActiveTray' if group=='base' else 'ActivePlate'))
        active.setLink(doc.getObject(prefix+'Case_'+('solid' if configuration['cases'][side]['style']=='level' else configuration['cases'][side]['style'])+'_'+group))
        done(part_id,active,('Base' if group=='base' else 'Plate')+' · interchangeable','base' if group=='base' else 'plate',(.145,.205,.207),True)
        active.LinkedObject.ViewObject.ShapeColor=tuple(int(case_catalog['styles'][configuration['cases'][side]['style']][group+'_color'][i:i+2],16)/255 for i in (1,3,5))
        active.ViewObject.OverrideMaterial=False
    assembly.addProperty('App::PropertyBool','DisplayCoverInstalled','Flan36')
    assembly.DisplayCoverInstalled=True

    pcb=extrude('PCBPad',profiles[side]['pcb_outline'],3.8,1.6)
    expr(pcb,'LengthFwd','Parameters.PCBThickness');expr(pcb,'Placement.Base.z','Parameters.PCBTop - Parameters.PCBThickness')
    slot=box('BatteryOpening',116.55,12,129.05,45.6,3.6,2.2,'BatteryShiftY')
    expr(slot,'Length','12.3 mm + 2 * Parameters.SlotClearance')
    expr(slot,'Placement.Base.x',('116.65 mm - Parameters.SlotClearance' if side=='left' else '31.05 mm - Parameters.SlotClearance'))
    pcb=cut('PCBBatteryOpening',pcb,slot)
    for i,h in enumerate(holes,1):pcb=cut('PCBMount'+str(i),pcb,h)
    drills_path=ROOT/'design/revF-drills.json'
    if drills_path.exists():
        drills=[]
        for i,d0 in enumerate(json.loads(drills_path.read_text())[side]):
            d=dict(d0)
            if d['ref'] in ['J1','SW1']:d['y']+=2
            if d['ref']=='SW1':d['x']+=-1.6 if side=='left' else 1.6
            if d['ref'].startswith('H'):continue
            o=add('Part::Cylinder','PadDrill'+str(i));o.Radius=d['radius'];o.Height=2
            o.Placement.Base=A.Vector(d['x'],-d['y'],3.7)
            if d['ref']=='U1':expr(o,'Placement.Base.y',f'{7.5-d["y"]} mm - Parameters.MCUShiftY')
            if d['ref']=='J2':expr(o,'Placement.Base.y',f'{2.4-d["y"]} mm - Parameters.DisplayShiftY')
            drills.append(o)
        tool=add('Part::Compound','DrillTools');tool.Links=drills
        pcb=cut('PCBAllDrills',pcb,tool)
    done('pcb',pcb,'PCB · unrouted placement','pcb',(.10,.34,.25))

    print(side,'case and PCB defined',flush=True)
    # Cradle walls stay BELOW the PCB. Only the pouch and narrow cage cross
    # the aperture. Wide cage feet are positively captured underneath the PCB.
    cradle=box('CradleOuter',115.8,11.6,129.8,46.1,1.4,2.25,'BatteryShiftY')
    cavity=box('CradleCavity',116.55,12.4,129.05,45.6,2,3,'BatteryShiftY')
    expr(cavity,'Placement.Base.z','Parameters.BatteryBottom')
    cradle=cut('CradleHollow',cradle,cavity)
    for i,(y0,y1) in enumerate([(12.05,13.05),(44.55,45.55)]):
        cradle=cut('CageSeat'+str(i),cradle,box('CageSeatTool'+str(i),115.7,y0,129.9,y1,2.9,1,'BatteryShiftY'))
    done('cradle',cradle,'Low insulating saddle · walls below PCB','supports',(.44,.57,.52),True)
    cells={}
    for ident,spec in json.loads((ROOT/'design/batteries.json').read_text())['profiles'].items():
        w,l,h=[spec[k] for k in ['width','length','height']]
        raw=box('RawCell_'+ident.replace('-','_'),122.8-w/2,28.6-l/2,122.8+w/2,28.6+l/2,2,h,'BatteryShiftY')
        expr(raw,'Placement.Base.z','Parameters.BatteryBottom')
        # App::Link replaces a source object's Placement. A native compound
        # retains the placed cell in its shape, keeping every profile registered.
        o=add('Part::Compound','Cell_'+ident.replace('-','_'));o.Links=[raw]
        o.addProperty('App::PropertyString','BatteryStyle','Flan36');o.BatteryStyle=ident
        o.Label=spec['label'];cells[ident]=o
    activecell=doc.addObject('App::Link',prefix+'ActiveBattery');activecell.setLink(cells['adafruit-1570'])
    done('battery',activecell,'Battery · Adafruit 1570 or 301230','battery',(.72,.75,.74))
    keeper_members=[
        box('KeeperA',116.65,12.25,128.95,13.0,6.2,.6,'BatteryShiftY'),
        box('KeeperB',116.65,44.65,128.95,45.35,6.2,.6,'BatteryShiftY'),
        box('KeeperSideA',116.65,12.25,117.25,45.35,6.2,.6,'BatteryShiftY'),
        box('KeeperSideB',128.35,12.25,128.95,45.35,6.2,.6,'BatteryShiftY')]
    for i,(y0,y1) in enumerate([(12.25,12.85),(44.75,45.35)]):
        keeper_members.append(box('CageEnd'+str(i),116.65,y0,128.95,y1,3,3.4,'BatteryShiftY'))
        keeper_members.append(box('CageFoot'+str(i),115.9,y0,129.7,y1,3,.65,'BatteryShiftY'))
    keeper=fuse('BatteryKeeper',keeper_members)
    # Cable exit through the rear end; roof is a rigid stop clear of the pouch.
    keeper=cut('KeeperCableExit',keeper,box('KeeperCableTool',120.8,44.55,124.8,45.55,4.5,1.3,'BatteryShiftY'))
    done('battery-retainer',keeper,'Rigid cage · feet captured below PCB','supports',(.44,.57,.52),True)

    bars=[]
    for i,(a,b) in enumerate([(112.9,114),(131.6,132.7)]):
        bar=box('Riser'+str(i),a,8,b,41,5.4,3.4,'MCUShiftY');expr(bar,'Height','Parameters.MCUBottom - Parameters.PCBTop');bars.append(bar)
    bars.append(box('RiserBridge',112.9,40,132.7,41,5.4,.8,'MCUShiftY'))
    # Raised scalloped shelves support the narrower nominal v2 PCB without
    # crossing the socket bodies or the 1.05 mm underside solder-pad reserve.
    for i,(a,b) in enumerate([(112.9,114.7),(130.9,132.7)]):
        ledge=box('RiserLedge'+str(i),a,8,b,40,8.1,.7,'MCUShiftY')
        expr(ledge,'Placement.Base.z','Parameters.MCUBottom - .7 mm')
        for j in range(-1,12):
            hole=cyl('RiserPadReserve'+str(i)+'_'+str(j),115.18 if i==0 else 130.42,9.8+j*2.54,8.0,1.05,1)
            expr(hole,'Placement.Base.y',f'-{9.8+j*2.54} mm - Parameters.MCUShiftY')
            expr(hole,'Placement.Base.z','Parameters.MCUBottom - .8 mm');ledge=cut('RiserScallop'+str(i)+'_'+str(j),ledge,hole)
        bars.append(ledge)
    done('mcu-riser',fuse('Riser',bars),'Controller support · scalloped PCB ledges','supports',(.31,.43,.39),True)
    module=components.install(doc,history,prefix+'NanoV2','nice!nano v2 · nominal reconstruction',components.nano(),(mx(122.8),-6.1,8.8),'MCUShiftY','Parameters.MCUBottom')
    done('mcu',module,'nice!nano v2 · nominal reconstruction','mcu',(.045,.049,.053))
    sock=[]
    for i,x in enumerate([115.18,130.42]):sock.append(box('Socket'+str(i),x-.9,8.53,x+.9,39.01,5.4,2.413,'MCUShiftY'))
    socketcompound=add('Part::Compound','MCUSockets');socketcompound.Links=sock
    done('mcu-sockets',socketcompound,'Controller sockets · reference','connectors',(.16,.21,.18))

    sled=box('DisplayPost',115.4,46.4,130.2,50.4,5.4,8.8,'DisplayShiftY')
    expr(sled,'Height','Parameters.DisplayBottom - Parameters.PCBTop')
    sled=cut('HeaderRelief',sled,box('HeaderReliefTool',116.2,46.9,129.4,49.9,5.3,2.95,'DisplayShiftY'))
    # Commercial display contact order remains left-to-right on BOTH halves.
    for i in range(5):
        h=add('Part::Cylinder','DisplayContact'+str(i));h.Radius=.42;h.Height=12
        h.Placement.Base=A.Vector(mx(122.8)-5.08+2.54*i,-50.8,5.2)
        expr(h,'Placement.Base.y','-48.4 mm - Parameters.DisplayShiftY');sled=cut('SledHole'+str(i),sled,h)
    members=[sled]
    for i,b in enumerate([(115,13.1,116.3,50.4),(129.3,13.1,130.6,50.4),(115,13.1,130.6,14.1)]):
        o=box('DisplayLedge'+str(i),*b,13.8,.4,'DisplayShiftY');expr(o,'Placement.Base.z','Parameters.DisplayBottom - .4 mm');members.append(o)
    for i,b in enumerate([(115,13.1,115.55,50.4),(130.05,13.1,130.6,50.4)]):
        o=box('DisplaySide'+str(i),*b,13.8,1.6,'DisplayShiftY');expr(o,'Placement.Base.z','Parameters.DisplayBottom - .4 mm');members.append(o)
    sledsolid=fuse('DisplaySled',members)
    sledsolid=cut('SledCableTunnel',sledsolid,box('SledCableTunnelTool',120.3,48.5,125.3,53.2,6.7,1.8))
    sledsolid=cut('SledCableCrossing',sledsolid,box('SledCableCrossingTool',115.3,52.2,125.3,53.5,6.7,1.8))
    done('display-sled',sledsolid,'Removable display support','supports',(.32,.43,.39),True)
    screen=components.install(doc,history,prefix+'NiceView','nice!view · nominal geometry',components.niceview(),(mx(122.8),-13.6,14.2),'DisplayShiftY','Parameters.DisplayBottom')
    done('display',screen,'nice!view · nominal geometry','display',(.07,.14,.11))
    done('jst',box('JST',112.5,56.2,119.1,62.5,5.4,8.5),'JST · relocated reference','connectors',(.85,.83,.73))
    for ident,filename,x,y,angle in [('reset','SW_SPST_TL3342.step',123,59.5,0),('slider','SW_SPDT_PCM12.step',130.9,59.65,90 if side=='left' else -90)]:
        shape,parts=components.standard(filename);rot=A.Rotation(A.Vector(0,0,1),angle)
        transformed=[]
        for title,part,color in parts:
            part=part.copy();part.rotate(A.Vector(0,0,0),A.Vector(0,0,1),angle);transformed.append((title,part,color))
        shape=shape.copy();shape.rotate(A.Vector(0,0,0),A.Vector(0,0,1),angle)
        obj=components.install(doc,history,prefix+ident.title()+'Model',ident,transformed,(mx(x),-y,5.4),whole=shape,whole_colors=components._facecolors[filename])
        done(ident,obj,filename.removesuffix('.step')+' · KiCad model','connectors',(.45,.47,.5))


    # The source route includes cell-to-plug transitions for both profiles.
    # slim_stack.apply below installs the active battery/lead links together.
    import slim_stack
    wire_spec=json.loads((ROOT/'design/revI-wire-study.json').read_text())
    for n,route in enumerate(wire_spec['profiles']['adafruit-1570']):
        obj=add('Part::Feature','WireStudy'+str(n))
        obj.Shape=slim_stack.wire_shape(route,side=='right')
        done('battery-lead-'+str(n),obj,'105 mm battery lead · nominal continuous route','connectors',(.62,.18,.16) if n==0 else(.18,.19,.20))

    print(side,'electronics defined',flush=True)
    # Interchangeable opaque covers. Same PCB/mount centers and independent sled.
    # Three native ruled lofts share one cavity, screen aperture and service cuts.
    cavity=extrude('FrameInside',frame_profiles[side]['inner'],6.2,9.2)
    expr(cavity,'LengthFwd','Parameters.FrameTop - Parameters.FrameRoof - 6.2 mm')
    window=box('GlassWindow',115.55,18.25,130.05,49.35,15.3,5)
    expr(window,'Length','13.7 mm + 2 * Parameters.WindowMargin')
    expr(window,'Width','30.3 mm + 2 * Parameters.WindowMargin')
    expr(window,'Placement.Base.x',('115.95 mm - Parameters.WindowMargin' if side=='left' else '30.35 mm - Parameters.WindowMargin'))
    expr(window,'Placement.Base.y','-46.55 mm - Parameters.DisplayShiftY - Parameters.WindowMargin')
    expr(window,'Placement.Base.z','Parameters.DisplayBottom + .9 mm')
    usb_access=box('USBPlugAccess',116.3,8,129.3,20,6.2,5.6)
    mcu_clearance=box('MCUCornerClearance',113,3.9,132.6,40.6,6.2,6.5,'MCUShiftY')
    expr(mcu_clearance,'Placement.Base.z','Parameters.MCUBottom - 2.6 mm')
    reset_access=cyl('ResetToolAccess',123,59.5,7.8,1.4,12)
    styles={}
    for style,label in catalog['frame_styles'].items():
        if style in extension_spec['styles']:continue
        if style in ('bevel','facet'):
            sections=[]
            for j,(z,contour) in enumerate([(6.3,'outer'),(15.4,'outer'),(16.6,style)]):
                sk=sketch('Frame_'+style+'_Section'+str(j),frame_profiles[side][contour]);sk.Placement.Base.z=z
                if j==1:expr(sk,'Placement.Base.z','Parameters.FrameTop - Parameters.FrameRoof')
                if j==2:expr(sk,'Placement.Base.z','Parameters.FrameTop')
                sections.append(sk)
            loft=add('Part::Loft','Frame_'+style+'_Loft');loft.Sections=sections;loft.Solid=True;loft.Ruled=True
        else:
            # Constant sections are extrusions. Redundant identical arc loft
            # sections can fail later boolean recomputes when FrameTop changes.
            loft=extrude('Frame_'+style+'_Pad',frame_profiles[side]['outer'],6.3,10.3)
            expr(loft,'LengthFwd','Parameters.FrameTop - 6.3 mm')
        cover=cut('Frame_'+style+'_Hollow',loft,cavity)
        cover=cut('Frame_'+style+'_Window',cover,window)
        cover=cut('Frame_'+style+'_USB',cover,usb_access)
        cover=cut('Frame_'+style+'_Micro',cover,mcu_clearance)
        cover=cut('Frame_'+style+'_Power',cover,power_slot)
        cover=cut('Frame_'+style+'_Reset',cover,reset_access)
        # Distinct printable themes. Relief is fused into the roof, stays inside
        # the common XY envelope and adds only 0.6 mm. Controls are decorative.
        relief=[]
        def badge_box(tag,x0,y0,x1,y1):
            b=box('Theme_'+style+'_'+tag,x0,y0,x1,y1,16.5,.7)
            expr(b,'Placement.Base.z','Parameters.FrameTop - .1 mm');relief.append(b)
        def badge_disc(tag,x,y,r):
            b=cyl('Theme_'+style+'_'+tag,x,y,16.5,r,.7)
            expr(b,'Placement.Base.z','Parameters.FrameTop - .1 mm');relief.append(b)
        if style=='handheld':
            badge_box('DpadH',113.7,54,120.1,56)
            badge_box('DpadV',115.9,51.8,117.9,58.2)
            badge_disc('ButtonA',129.3,53.5,1.65)
            badge_disc('ButtonB',125.7,56.1,1.65)
            for i in range(3):badge_box('Speaker'+str(i),119+i*2.2,63,120+i*2.2,65.3)
        elif style=='tv':
            # Portrait CRT-inspired bezel, sized around the actual LCD opening.
            badge_box('BezelLeft',113.8,16.8,115.55,50.8)
            badge_box('BezelRight',130.05,16.8,131.8,50.8)
            badge_box('BezelTop',113.8,16.8,131.8,18.25)
            badge_box('BezelBottom',113.8,49.35,131.8,50.8)
            badge_disc('Tuning',128.9,55.1,2.15)
            for i in range(4):badge_box('Speaker'+str(i),114.2,52.6+i*1.5,120,53.3+i*1.5)
        elif style=='cyberpunk':
            for i in range(3):
                badge_box('Vent'+str(i),113.4+i*2.7,52,114.6+i*2.7,56.9)
            badge_box('TraceA',126.8,51.8,132.5,52.6)
            badge_box('TraceB',131.7,52.6,132.5,58.1)
            badge_box('TraceC',126.8,57.3,132.5,58.1)
            badge_box('Panel',119.5,63.2,124.2,65.5)
            badge_disc('Node',128.1,61,1)
        if relief:
            cover=fuse('Frame_'+style+'_Relief',[cover]+relief)
            cover=cut('Frame_'+style+'_ThemeWindow',cover,window)
            cover=cut('Frame_'+style+'_ThemeReset',cover,reset_access)
        for i,(x,y) in enumerate(magnetic['stations_left']):
            cover=fuse('Frame_'+style+'_MagnetBoss'+str(i),[cover,cyl('Frame_'+style+'_Boss'+str(i),x,y,6.3,1.85,5.3)])
            cover=cut('Frame_'+style+'_Register'+str(i),cover,cyl('Frame_'+style+'_RegisterTool'+str(i),x,y,6.2,1.6,.6))
            cover=cut('Frame_'+style+'_SteelPocket'+str(i),cover,cyl('Frame_'+style+'_SteelPocketTool'+str(i),x,y,7,1.1,4.2))
        for i,(x,y) in enumerate(mounts[3:],4):
            cover=cut('Frame_'+style+'_HeadRelief'+str(i),cover,cyl('Frame_'+style+'_HeadTool'+str(i),x,y,5.3,2.15,1.45))
        cover.Label='Frame · '+label+' · variant'
        cover.addProperty('App::PropertyString','FrameStyle','Flan36');cover.FrameStyle=style
        cover.ViewObject.ShapeColor=(.16,.25,.23);styles[style]=cover
    styles.update(extra_frames.build_for_half(doc,side,smooth=styles['smooth'],history=history,spec=extension_spec))
    active=doc.addObject('App::Link',prefix+'ActiveFrame');active.setLink(styles[configuration['frames'][side]['style']])
    done('electronics-lid',active,'Magnetic frame · vertical lift','lid',tuple(int(configuration['frames'][side]['color'][i:i+2],16)/255 for i in (1,3,5)),True)

    print(side,'frame defined; recompute BEFORE meshes',flush=True)
    doc.recompute()
    print(side,'solid recompute complete',flush=True)
    # Keycaps remain the original KLP meshes; mirrored local Y is the KiCad/CAD
    # coordinate conversion, not a redesign of the keycap.
    keygroup=doc.addObject('App::DocumentObjectGroup',prefix+'Keys');keygroup.Label='Keycaps · Piantor centers and angles';assembly.addObject(keygroup)
    for key in layout['halves'][side]:
        choice=configuration['keycaps'][side][key['ref']];v=variants[choice['variant']]
        o=doc.addObject('Mesh::Feature',prefix+key['ref']); keygroup.addObject(o)
        mesh=Mesh.Mesh(str(ROOT/v['path'])); mat=A.Matrix();mat.A22=-1;mesh.transform(mat);mesh.flipNormals();o.Mesh=mesh
        o.Placement=A.Placement(A.Vector(key['x'],-key['y'],v['seating_z_mm']),A.Rotation(A.Vector(0,0,1),key['angle']+choice['rotation_deg']))
        o.Label='KLP '+key['ref'];o.ViewObject.ShapeColor=tuple(int(choice['color'][i:i+2],16)/255 for i in (1,3,5))
        for prop,value in [('KeycapVariant',v['id']),('KeyReference',key['ref']),('Side',side),('Source','KLP Lame / braindefender / CC-BY-SA-4.0 / unchanged mesh; nominal stem-tip datum')]:
            o.addProperty('App::PropertyString',prop,'Flan36');setattr(o,prop,value)
        o.addProperty('App::PropertyAngle','CapRotation','Flan36');o.CapRotation=choice['rotation_deg']
    print(side,'recomputing',flush=True)
    doc.recompute()
    print(side,'recomputed',flush=True)
    for o in history.Group:o.Visibility=False
    for o in finished:o.Visibility=True
    history.Visibility=False
    metadata['halves'][side]={'mount_holes':[[mx(x),y] for x,y in mounts], 'mount_tops_z':[m['seat_z'] for m in mount_data['left']],
        'outer':profiles[side]['outer'],'pcb_outline':profiles[side]['pcb_outline'],
        'battery_opening':[mx(116.55) if side=='left' else mx(129.05),14,mx(129.05) if side=='left' else mx(116.55),47.6],
        'display_header':{'x':mx(122.8)-5.08,'y':50.8}, 'electronics_cover':profiles[side]['hood']}
    if side=='right':assembly.Placement.Base.x=161

doc.recompute()
from switch_instances import ensure
ensure(doc)
import slim_stack,level_stack,flush_frames
from configuration import apply as apply_configuration
slim_stack.apply(doc)
level_stack.apply(doc)
flush_frames.apply(doc)
apply_configuration(doc,configuration)
A.setActiveDocument(doc.Name)
G.activeDocument().activeView().viewTop();G.activeDocument().activeView().fitAll()
doc.saveAs(str(OUT/'Flan36.FCStd'))
(ROOT/'design/revI.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Saved native editable FreeCAD assembly:',OUT/'Flan36.FCStd',flush=True)
exec(compile((ROOT/'tools/freecad/export_revI.py').read_text(),str(ROOT/'tools/freecad/export_revI.py'),'exec'))

import os
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':
    sys.__stdout__.flush();sys.__stderr__.flush();os._exit(0)
