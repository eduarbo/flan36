"""Nominal service checks and small fit coupons from the actual revI solids.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,os,sys
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
import Part,MeshPart
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/freecad'))
from slim_stack import overlap, cell_motion_checks
G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(ROOT/'mechanical/revI/Flan36.FCStd'));doc.recompute()
def log(*args):sys.__stdout__.write(' '.join(map(str,args))+'\n');sys.__stdout__.flush()
def volume(a,b):
    return overlap(a,b)
steps=[0,.1,.2,.3,.5,.75,1,1.5,2,3,4,5,6,8,10,12,16,24]
report={'scope':'Nominal CAD only; sampled release path, not a physical fit/force test','frame_lift_samples_mm':steps,'halves':{},'coupons':{},'physical_acceptance':False}
for side,prefix in [('left','L_'),('right','R_')]:
    assembly=doc.getObject(prefix+'Half');assembly.Placement=A.Placement();doc.recompute()
    shapes={o.PartID[len(side)+1:]:o.Shape for o in doc.Objects if hasattr(o,'PartID') and o.PartID.startswith(side+'-')}
    static={k:s for k,s in shapes.items() if k!='electronics-lid' and not k.startswith('frame-target-')}
    checks={}
    for obj in [o for o in doc.Objects if hasattr(o,'FrameStyle') and o.TypeId!='App::Link' and o.Name.startswith(prefix)]:
        moving=Part.makeCompound([obj.Shape]+[s for k,s in shapes.items() if k.startswith('frame-target-')])
        hits=[]
        for dz in steps:
            moved=moving.copy();moved.translate(A.Vector(0,0,dz))
            for name,fixed in static.items():
                v=volume(moved,fixed)
                if v>.001:hits.append({'lift_mm':dz,'part':name,'volume_mm3':v})
        checks[obj.FrameStyle]=hits
        assert not hits,(side,obj.FrameStyle,hits)
        log(side,obj.FrameStyle,'sampled frame lift clear')
    cage=shapes['battery-retainer'].copy();cage.translate(A.Vector(0,0,.2))
    captured=volume(cage,shapes['pcb']);assert captured>.01,(side,'cage is not captured by PCB')
    # Both profiles include a continuous lead attached to the terminal region.
    # Only that explicit join may meet the cell-motion bound; free lead storage
    # must remain outside it. This does not qualify flexible unplugging.
    movement=cell_motion_checks(doc,side)
    for profile, leads in movement.items():
        assert len(leads)==2
        assert all(item['outside_attachment_overlap_mm3']<=.001 for item in leads),(side,profile,movement)
    # A rigid enclosed insert cannot leave either pocket by straight translation.
    capture={}
    for i in range(3):
        for part,host in [('magnet-'+str(i),'tray'),('frame-target-'+str(i),'electronics-lid')]:
            original=shapes[part]
            hits=[]
            for direction in [A.Vector(1,0,0),A.Vector(-1,0,0),A.Vector(0,1,0),A.Vector(0,-1,0),A.Vector(0,0,1),A.Vector(0,0,-1)]:
                moved=original.copy();moved.translate(direction.multiply(.3))
                hits.append(round(volume(moved,shapes[host]),6))
            assert min(hits)>.001,(side,part,'open insert pocket',hits)
            capture[part]=hits
    pcb_lift=[]
    for dz in steps:
        moved=shapes['pcb'].copy();moved.translate(A.Vector(0,0,dz))
        for name in ['tray','battery-retainer','cradle','battery','magnet-0','magnet-1','magnet-2']:
            v=volume(moved,shapes[name])
            if v>.001:pcb_lift.append({'lift_mm':dz,'part':name,'volume_mm3':v})
    assert not pcb_lift,(side,'PCB release after screws/modules removed',pcb_lift)
    driver_hits=[]
    for mount in json.loads((ROOT/'design/revI-mounts.json').read_text())['left']:
        x,y=mount['xy'];x=x if side=='left' else 160-x
        driver=Part.makeCylinder(1.5,25,A.Vector(x,-y,mount['seat_z']+mount['head_height']))
        # Remove caps and frame first; remove plate after its three screws,
        # before accessing the two short PCB screws below its lower edge.
        for name,shape in shapes.items():
            if name=='electronics-lid' or name.startswith(('frame-target-','screw-')):continue
            if mount['id'] in ['H4','H5'] and name=='key-plate':continue
            v=volume(driver,shape)
            if v>.001:driver_hits.append({'mount':mount['id'],'part':name,'volume_mm3':v})
    assert not driver_hits,(side,'nominal 3 mm driver shaft blocked',driver_hits)
    report['halves'][side]={'pcb_lift_after_plate_modules_removed':pcb_lift,'nominal_3mm_driver_shaft_collisions':driver_hits,'frame_lift_paths':checks,'cage_capture_overlap_at_0_2mm_lift_mm3':captured,'cell_translation_bound_vs_leads_mm3':movement,'six_direction_insert_capture_mm3':capture}
    if side=='left':
        # Extract the production interface, without scaling or changing its gap.
        x,y=122.8,-64.7
        post=shapes['tray'].common(Part.makeCylinder(1.86,5.3,A.Vector(x,y,1.4)))
        base=post.fuse(Part.makeBox(12,12,1.4,A.Vector(x-6,y-6,0)))
        top=shapes['electronics-lid'].common(Part.makeCylinder(1.86,5.3,A.Vector(x,y,6.3)))
        top=top.fuse(Part.makeBox(12,12,1.2,A.Vector(x-6,y-6,11.6)))
        thread=shapes['tray'].common(Part.makeCylinder(1.81,2.4,A.Vector(57,-20.5,1.4)))
        thread=thread.fuse(Part.makeBox(12,12,1.4,A.Vector(51,-26.5,0)).cut(Part.makeCylinder(.85,2,A.Vector(57,-20.5,-.1))))
        for name,shape in [('magnet-base',base),('magnet-frame',top),('m2-thread',thread)]:
            assert shape.isValid() and len(shape.Solids)==1,(name,'invalid coupon')
            mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.03,AngularDeflection=.12,Relative=False);assert mesh.isSolid()
            p=ROOT/'mechanical/revI'/('coupon-'+name+'.stl');mesh.write(str(p));shape.exportStep(str(p.with_suffix('.step')))
            report['coupons'][name]={'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
report['source_sha256']=hashlib.sha256((ROOT/'mechanical/revI/Flan36.FCStd').read_bytes()).hexdigest()
report['checker_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(ROOT/'validation/revI-service.json').write_text(json.dumps(report,indent=2)+'\n')
log('PASS: sampled frame release, captive inserts, captive battery cage, cell/lead separation and closed coupons')
A.closeDocument(doc.Name)
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':
    sys.__stdout__.flush();sys.__stderr__.flush();os._exit(0)
