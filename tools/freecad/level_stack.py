"""Floor-mounted cell, flush display and removable level upper shell.

Nominal CAD prototype: commercial hole tolerances and physical assembly are
unqualified. Apply after the immutable slim_stack migration, before flush_frames.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import math
from pathlib import Path
import FreeCAD as A
import Part
from slim_stack import bounds, overlap, visible

ROOT = Path(__file__).resolve().parents[2]
V = A.Vector
TARGETS = {'BatteryBottom': 1.4, 'MCUBottom': 8.2,
           'DisplayBottom': 11.49, 'FrameTop': 13.39}
ROW_Y = 50.8
POST = .025 * 25.4


def stamp():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def input_stamps():
    paths=['tools/freecad/components.py','design/revI-wire-study.json','design/layout.json']
    result={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    variants=json.loads((ROOT/'keycaps/catalog.json').read_text())['variants']
    result['keycap_geometry']=hashlib.sha256(json.dumps(variants,sort_keys=True).encode()).hexdigest()
    return result


def rounded_path(points, radius=1.5):
    """Continuous 3D circular fillets; radius is geometric, not XY projection."""
    edges, last = [], points[0]
    for a, b, c in zip(points, points[1:], points[2:]):
        u, v = b-a, c-b
        u.normalize(); v.normalize()
        theta = math.acos(max(-1., min(1., u.dot(v))))
        if theta < 1e-8:
            continue
        trim = radius * math.tan(theta/2)
        assert (b-a).Length > trim and (c-b).Length > trim
        start, end = b-u*trim, b+v*trim
        inward = v-u*u.dot(v); inward.normalize()
        center = start+inward*radius
        middle = (start-center)+(end-center); middle.normalize()
        middle = center+middle*radius
        if (start-last).Length > 1e-8:
            edges.append(Part.makeLine(last, start))
        edges.append(Part.Arc(start, middle, end).toShape())
        last = end
    edges.append(Part.makeLine(last, points[-1]))
    return edges


def wire(route, right=False):
    """Lower stored wire but keep the PH terminal fixed, with a 3D ramp."""
    def vec(x, y, z): return V(160-x if right else x, -y, z)
    x, y, z = route['cell_end']; z -= .6
    cy, rr, sz = route['return_center_y'], route['return_radius'], route['storage_z']-.6
    start, turn_start, turn_end = vec(x,y,z), vec(x,cy,z), vec(x,cy,sz)
    initial = [Part.makeLine(start,turn_start),
               Part.Arc(turn_start,vec(x,cy+rr,z+rr),turn_end).toShape()]
    def path(adjustment):
        points=[]
        for i,(px,py) in enumerate(route['control_points']):
            if i in (1,2): py += adjustment
            # Rise along the outboard rear leg after clearing the MCU.
            pz=sz if i <= 8 else sz+.6
            points.append(vec(px,py,pz))
        return Part.Wire(initial+rounded_path(points))
    raw=path(0); adjustment=(raw.Length-105)/2
    spine=path(adjustment)
    assert abs(spine.Length-105)<1e-6, spine.Length
    circle=Part.Wire([Part.makeCircle(.3,start,turn_start-start)])
    shape=spine.makePipeShell([circle],True,False)
    assert shape.isValid() and len(shape.Solids)==1
    return shape, {'length_mm':spine.Length,'bend_radius_mm':1.5,
                   'cell_terminal_mm':list(start),'plug_terminal_mm':list(points_end(route,right)),
                   'storage_z_mm':sz,'coil_y_adjustment_mm':adjustment}


def points_end(route,right):
    x,y=route['control_points'][-1]
    return V(160-x if right else x,-y,route['storage_z'])


def cap_openings(side):
    """Union every admitted variant/orientation at every position, all travel.

    The complete XY hull is conservative for every Z during 3.5 mm travel.
    Morphological closing removes thin webs, and interior islands are filled.
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    from keycap_config import polygon
    catalog=json.loads((ROOT/'keycaps/catalog.json').read_text())
    variants=[v for v in catalog['variants'] if v['qualified_reference_positions']]
    polys=[Polygon(polygon(v['hull_xy_mm'],key,turn))
           for key in catalog['layout'][side] for v in variants for turn in v['rotations_deg']]
    exact=unary_union(polys)
    opening=exact.buffer(.25,quad_segs=8).buffer(.6,quad_segs=8).buffer(-.6,quad_segs=8)
    pieces=list(opening.geoms) if hasattr(opening,'geoms') else [opening]
    # Fill islands and simplify outward only, never removing cap clearance.
    pieces=[Polygon(p.exterior).simplify(.015,preserve_topology=True).buffer(.02,quad_segs=4) for p in pieces]
    merged=unary_union(pieces)
    assert merged.covers(exact.buffer(.2,quad_segs=4))
    return merged, {'admitted_variants':len(variants),'poses':len(polys),
                    'travel_mm':catalog['study_travel_mm'],'minimum_xy_clearance_mm':.2,
                    'minimum_pressed_mesh_z_mm':catalog['minimum_pressed_mesh_z_mm']}


def finish_clearances(doc):
    """Retain full-height ledges outside socket bodies and relieve the wire exit."""
    for side,prefix in [('left','L_'),('right','R_')]:
        mx=lambda x:x if side=='left' else 160-x
        for i,(x0,x1) in enumerate([(112.9,114.18),(131.42,132.7)]):
            o=doc.getObject(prefix+'RiserLedge'+str(i))
            o.Length=x1-x0;o.Placement.Base.x=min(mx(x0),mx(x1))
        if doc.getObject(prefix+'LevelCradleCableExit'):continue
        old=next(o for o in doc.Objects if getattr(o,'PartID','')==side+'-cradle')
        tool=doc.addObject('Part::Box',prefix+'LevelCradleCableTool')
        tool.Length=2.3;tool.Width=1.;tool.Height=1.
        tool.Placement.Base=V(min(mx(117.55),mx(119.85)),-47.6,3.15)
        doc.getObject(prefix+'Construction').addObject(tool)
        cut=doc.addObject('Part::Cut',prefix+'LevelCradleCableExit');cut.Base=old;cut.Tool=tool;cut.Refine=True
        for prop in ['PartID','DisplayName','ViewerGroup','PrototypePrintable','Layer','ModelStatus']:
            if hasattr(old,prop):
                cut.addProperty(old.getTypeIdOfProperty(prop),prop,'Flan36')
                setattr(cut,prop,getattr(old,prop));old.removeProperty(prop)
        cut.Label=old.Label;cut.ViewObject.ShapeColor=old.ViewObject.ShapeColor
        doc.getObject(prefix+'Half').addObject(cut)
        visible(old,False);visible(tool,False);visible(cut,True)


def apply(doc):
    existing=doc.getObject('LevelStackReceipt')
    if existing:
        record=json.loads(existing.RecipeJSON)
        if record['generator_sha256']!=stamp():
            raise ValueError('Changed level recipe: regenerate from preserved pre-level native source')
        if record['inputs_sha256']!=input_stamps():
            raise ValueError('Level geometry inputs changed; regenerate the candidate')
        if any(abs(getattr(doc.Parameters,k).Value-v)>1e-8 for k,v in TARGETS.items()):
            raise ValueError('Level parameters were edited; revalidate this custom stack before reapplying the reference recipe')
        return record
    import components
    params=doc.Parameters
    for alias,value in TARGETS.items(): params.set(params.getCellFromAlias(alias),f'{value} mm')
    report={'schema':'flan36-level-stack-1','generator_sha256':stamp(),'inputs_sha256':input_stamps(),
            'parameters_mm':TARGETS,'frame_reduction_mm':1.41,'physical_acceptance':False,
            'niceview_hole_diameter_mm':.9,'niceview_hole_status':'Unmeasured nominal; toleranced pin fit must be verified, never enlarge a purchased board on this evidence.',
            'display_pair':{'socket':'SLW-105-01-L-S','header':'TLW-105-06-G-S',
              'separation_mm':6.09,'female_height_mm':4.57,'male_insulator_mm':1.52,
              'post_mm':POST,'post_diagonal_mm':POST*math.sqrt(2),'insertion_mm':2.67,
              'allowed_insertion_mm':[2.16,2.92],'tail_trim_above_display_mm':.3,
              'solder_envelope_above_display_mm':.5,'fixed_socket_tail_mm':2.92,'qualification':'Nominal mating geometry only'},
            'halves':{}}
    routes=json.loads((ROOT/'design/revI-wire-study.json').read_text())
    old_recipe=json.loads(doc.SlimStackReceipt.RecipeJSON)
    for side,prefix in [('left','L_'),('right','R_')]:
        history=doc.getObject(prefix+'Construction')
        def add(kind,name):
            o=doc.addObject(kind,prefix+'Level'+name);history.addObject(o);return o
        def feature(name,shape):
            o=add('Part::Feature',name);o.Shape=shape;return o
        def box(name,x,y,z,w,d,h):
            o=add('Part::Box',name);o.Length=w;o.Width=d;o.Height=h;o.Placement.Base=V(x,y,z);return o
        def part(ident): return next(o for o in doc.Objects if getattr(o,'PartID','')==side+'-'+ident)
        cx=122.8 if side=='left' else 37.2
        part('cradle').Label='Battery locator · open bottom, cell on case floor'
        for name in ['KeeperA','KeeperB','KeeperSideA','KeeperSideB']:
            doc.getObject(prefix+name).setExpression('Placement.Base.z','Parameters.BatteryBottom + 4.2 mm')
        for name in ['CageEnd0','CageEnd1']:
            doc.getObject(prefix+name).setExpression('Height','Parameters.BatteryBottom + 1.4 mm')
        doc.getObject(prefix+'KeeperCableTool').Placement.Base.z=3.2
        # Correct the vendor connector row: 16.1 + (36 - 1.3) = 50.8.
        for i,(_,shape,color) in enumerate(components.niceview()):
            o=doc.getObject(prefix+'NiceViewVisual'+str(i));old=A.Placement(o.Placement)
            o.Shape=shape;o.Placement=old
            o.setExpression('Placement.Base.y','-13.7 mm - Parameters.DisplayShiftY')
        window=doc.getObject(prefix+'GlassWindow')
        window.setExpression('Placement.Base.y','-46.65 mm - Parameters.DisplayShiftY - Parameters.WindowMargin')
        # Fixed socket with explicit insertion cavities; nominal square posts.
        housing=Part.makeBox(12.7,2.54,4.57,V(cx-6.35,-ROW_Y-1.27,5.4))
        fixed=[]; moving=[]; solder=[]
        for i in range(5):
            x=cx-5.08+i*2.54
            well=Part.makeBox(.85,.85,3.05,V(x-.425,-ROW_Y-.425,6.92))
            housing=housing.cut(well)
            fixed.append(Part.makeCylinder(.3,4.44,V(x,-ROW_Y,2.48)))
            moving.append(Part.makeBox(POST,POST,5.49,V(x-POST/2,-ROW_Y-POST/2,7.30)))
            # Solder reserve deliberately stays above the board and out of the hole.
            solder.append(Part.makeCylinder(.8,.5,V(x,-ROW_Y,12.49)).cut(
                Part.makeBox(POST,POST,.6,V(x-POST/2,-ROW_Y-POST/2,12.48))))
        doc.getObject(prefix+'SlimDisplaySocketHousing').Shape=housing
        doc.getObject(prefix+'SlimDisplaySocketPins').Shape=Part.makeCompound(fixed)
        part('display-socket').Label='Samtec SLW-105 · nominal 4.57 mm socket'
        part('display-socket').ModelStatus='SLW/TLW nominal mating; finished nice!view hole and retention unqualified'
        male=doc.getObject(prefix+'SlimDisplayMaleSpacer')
        male.setExpression('Placement.Base.z',None);male.Placement=A.Placement()
        plastic=Part.makeBox(12.7,2.48,1.52,V(cx-6.35,-ROW_Y-1.24,9.97))
        for i in range(5):
            x=cx-5.08+i*2.54
            plastic=plastic.cut(Part.makeBox(POST,POST,1.6,V(x-POST/2,-ROW_Y-POST/2,9.95)))
        male.Shape=plastic
        male.setExpression('Placement.Base.z','Parameters.DisplayBottom - 11.49 mm')
        contacts=doc.getObject(prefix+'SlimDisplayMaleContacts')
        contacts.setExpression('Placement.Base.z',None);contacts.Placement=A.Placement();contacts.Shape=Part.makeCompound(moving)
        contacts.setExpression('Placement.Base.z','Parameters.DisplayBottom - 11.49 mm')
        joins=feature('DisplaySolderReserve',Part.makeCompound(solder));joins.ViewObject.ShapeColor=(.65,.68,.7)
        joins.setExpression('Placement.Base.z','Parameters.DisplayBottom - 11.49 mm')
        screen=part('display');screen.Links=[*screen.Links,joins];screen.VisualParts=[*screen.VisualParts,joins]
        colors=[tuple(o.ViewObject.ShapeColor[:3]) for o in screen.VisualParts for _ in o.Shape.Faces]
        screen.VisualFaceColors=json.dumps(colors);screen.ViewObject.DiffuseColor=colors
        # Keep 1.2 mm nominal roof and .8 mm backing policy. Undercut only the
        # PCB region; backed-inlay masks automatically omit unsupported details.
        relief=box('DisplayPCBRelief',cx-7.95,-53.0,10.9,15.9,37.9,1.825)
        relief.setExpression('Placement.Base.z','Parameters.DisplayBottom - .59 mm')
        well=box('HeaderServiceWell',cx-6.85,-52.6,10.9,13.7,3.5,4)
        well.setExpression('Placement.Base.z','Parameters.DisplayBottom - .59 mm')
        tools=add('Part::MultiFuse','FrameCavities');tools.Shapes=[doc.getObject(prefix+'FrameInside'),relief,well]
        for style in ['smooth','bevel','facet']:
            hollow=doc.getObject(prefix+'Frame_'+style+'_Hollow')
            if hollow is not None:hollow.Tool=tools
        # Rebuild continuous battery routes; fixed PH contacts do not descend.
        wire_report={}
        for profile,names in old_recipe['halves'][side]['lead_objects'].items():
            wire_report[profile]=[]
            for route,name in zip(routes['profiles'][profile],names):
                shape,receipt=wire(route,side=='right');o=doc.getObject(name);o.Shape=shape
                wire_report[profile].append(receipt)
        # Reuse the exact native outer contour. A removable upper shell fuses
        # into the existing 1.3 mm switch-retaining plate and its three screws.
        opening,cap_report=cap_openings(side)
        hole_nodes=[]
        pieces=list(opening.geoms) if hasattr(opening,'geoms') else [opening]
        for i,poly in enumerate(pieces):
            pts=[V(x,-y,0) for x,y in poly.exterior.coords]
            face=Part.Face(Part.Wire(Part.makePolygon(pts).Edges))
            o=feature('CapSweep'+str(i),face.extrude(V(0,0,25)));o.Placement.Base.z=7.6;hole_nodes.append(o)
        # A full-height copy of the existing frame clearance also preserves the
        # original 0.2 mm seam, magnetic frame independence and USB access.
        frame_tool=doc.getObject(prefix+'PlateFrameTool')
        frame_cut=add('Part::Extrusion','UpperFrameClearance');frame_cut.Base=frame_tool.Base
        frame_cut.Dir=V(0,0,1);frame_cut.LengthFwd=20;frame_cut.Solid=True;frame_cut.Placement.Base.z=7.6
        hole_nodes.append(frame_cut)
        for i in range(1,4):
            old=doc.getObject(prefix+'PlateHole'+str(i));tool=add('Part::Cylinder','DriverAccess'+str(i))
            tool.Radius=2.1;tool.Height=20;tool.Placement.Base=V(old.Placement.Base.x,old.Placement.Base.y,7.6);hole_nodes.append(tool)
        cuts=add('Part::MultiFuse','UpperOpenings');cuts.Shapes=hole_nodes
        outer=add('Part::Extrusion','UpperContour');outer.Base=doc.getObject(prefix+'PlatePad').Base
        outer.Dir=V(0,0,1);outer.Solid=True;outer.Placement.Base.z=7.6
        outer.setExpression('LengthFwd','Parameters.FrameTop - 7.6 mm')
        upper=add('Part::Cut','UpperWalls');upper.Base=outer;upper.Tool=cuts;upper.Refine=True
        solid=doc.getObject(prefix+'Case_solid_plate').Links[0]
        shell=add('Part::MultiFuse','UpperShell');shell.Shapes=[solid,upper];shell.Refine=True
        for group,source in [('base',doc.getObject(prefix+'Case_solid_base')),('plate',shell)]:
            o=doc.addObject('Part::Compound',prefix+'Case_level_'+group);history.addObject(o);o.Links=[source]
            o.addProperty('App::PropertyString','CaseStyle','Flan36');o.CaseStyle='level'
            o.addProperty('App::PropertyString','CaseGroup','Flan36');o.CaseGroup=group
            o.Label='Level · '+('base' if group=='base' else 'removable upper shell')
            o.ViewObject.ShapeColor=(.19,.30,.30)
        report['halves'][side]={'wires':wire_report,'caps':cap_report,
            'header_row_mm':ROW_Y,'display_origin_y_mm':16.1,'display_local_row_mm':34.7}
        for o in history.Group: visible(o,False)
    finish_clearances(doc)
    doc.recompute()
    for side,prefix in [('left','L_'),('right','R_')]:
        shell=doc.getObject(prefix+'Case_level_plate')
        assert len(shell.Shape.Solids)==1 and shell.Shape.isValid(),(side,'upper shell')
        assert abs(bounds(shell.Shape)[5]-TARGETS['FrameTop'])<1e-6
        report['halves'][side].update(upper_shell_volume_mm3=shell.Shape.Volume,upper_shell_bounds_mm=bounds(shell.Shape))
    report['local_clearances']={'mcu_ledge_socket_gap_mm':.1,'cradle_wire_exit_floor_z_mm':3.15,
        'purpose':'Clear lowered socket bodies and the retained continuous battery lead; no height increase.'}
    receipt=doc.addObject('App::DocumentObjectGroup','LevelStackReceipt')
    receipt.addProperty('App::PropertyString','RecipeJSON','Flan36');receipt.RecipeJSON=json.dumps(report,sort_keys=True)
    doc.recompute()
    return report
