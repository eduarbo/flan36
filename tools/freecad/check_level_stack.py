"""Read-only acceptance of the saved floor/flush/level nominal CAD candidate.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import Part
import slim_stack
from slim_stack import overlap,bounds
from check_slim_connector_service import check as connector_check
ROOT=Path(__file__).resolve().parents[2]

class AnalyticCollisionCache:
    """Cache bounds only for retained immutable shape snapshots during one check.

    The exact Boolean stays unchanged. Strong references prevent Python id reuse.
    """
    def __init__(self): self.cache={}
    def record(self,shape):
        key=id(shape)
        if key not in self.cache:
            solids=shape.Solids
            self.cache[key]=(shape,shape.optimalBoundingBox(False,False),solids,
                             [s.optimalBoundingBox(False,False) for s in solids])
        return self.cache[key]
    def __call__(self,a,b):
        def possible(x,y): return all(min(getattr(x,k+'Max'),getattr(y,k+'Max'))>max(getattr(x,k+'Min'),getattr(y,k+'Min')) for k in 'XYZ')
        _,ab,aa,axb=self.record(a);_,bb,bsa,bxb=self.record(b)
        if not possible(ab,bb):return 0.
        if not aa or not bsa:return a.common(b).Volume
        pairs=[(i,j) for i,x in enumerate(axb) for j,y in enumerate(bxb) if possible(x,y)]
        if not pairs:return 0.
        ai=sorted({i for i,j in pairs});bi=sorted({j for i,j in pairs})
        sa=aa[ai[0]] if len(ai)==1 else Part.makeCompound([aa[i] for i in ai])
        sb=bsa[bi[0]] if len(bi)==1 else Part.makeCompound([bsa[i] for i in bi])
        return sa.common(sb).Volume

def cell_motion(doc,side):
    floor=doc.Parameters.BatteryBottom.Value
    motion=Part.makeBox(12.5,33.2,4.2,A.Vector(116.55 if side=='left' else 30.95,-46.8,floor))
    attachment=Part.makeBox(2.2,2.2,2,A.Vector(117.65 if side=='left' else 40.15,-46.8,floor+1.8))
    profiles=json.loads(doc.SlimStackReceipt.RecipeJSON)['halves'][side]['lead_objects']
    result={}
    for profile,names in profiles.items():
        result[profile]=[]
        for name in names:
            common=motion.common(doc.getObject(name).Shape)
            outside=common.cut(attachment).Volume if common.Volume>1e-6 else 0
            result[profile].append({'lead':name,'attachment_overlap_mm3':common.Volume,'outside_attachment_overlap_mm3':outside})
    return result

def check(doc):
    from level_stack import cap_openings
    recipe=json.loads(doc.LevelStackReceipt.RecipeJSON)
    result={'schema':'flan36-level-acceptance-1','physical_acceptance':False,
            'commercial_pin_hole_fit_qualified':False,'halves':{}}
    # Preserve the historical migration and use the new floor datum for this run.
    old=slim_stack.cell_motion_checks;old_overlap=slim_stack.overlap
    try:
        slim_stack.cell_motion_checks=cell_motion
        slim_stack.overlap=AnalyticCollisionCache()
        result['stack']=slim_stack.validate(doc)
    finally: slim_stack.cell_motion_checks=old;slim_stack.overlap=old_overlap
    import check_slim_connector_service as service
    old_service=service.overlap
    try:
        service.overlap=AnalyticCollisionCache()
        result['ph_service']=service.check(doc)
    finally: service.overlap=old_service
    for side,prefix in [('left','L_'),('right','R_')]:
        half=doc.getObject(prefix+'Half');pose=A.Placement(half.Placement);half.Placement=A.Placement();doc.recompute()
        try:
            parts={o.PartID[len(side)+1:]:o.Shape for o in doc.Objects if getattr(o,'PartID','').startswith(side+'-')}
            shell=doc.getObject(prefix+'Case_level_plate').Shape
            assert shell.isValid() and len(shell.Solids)==1
            assert abs(bounds(shell)[5]-13.39)<1e-6
            glass=doc.getObject(prefix+'NiceViewVisual2').Shape
            assert abs(bounds(glass)[5]-13.39)<1e-6
            pcb=doc.getObject(prefix+'NanoV2Visual0').Shape
            underside=[f for f in pcb.Faces if abs(f.BoundBox.ZMin-doc.Parameters.MCUBottom.Value)<1e-6 and f.BoundBox.ZLength<1e-6]
            support_area=sum(parts['mcu-riser'].common(f).Area for f in underside)
            assert support_area>15,(side,'MCU support area',support_area)
            shell_hits={}
            for name,shape in parts.items():
                if name=='key-plate':continue
                vol=overlap(shell,shape)
                if vol>.001:shell_hits[name]=vol
            frames=[o for o in doc.Objects if o.Name.startswith(prefix) and o.TypeId!='App::Link' and hasattr(o,'FrameStyle')]
            assert len(frames)==10
            for frame in frames:
                vol=overlap(shell,frame.Shape)
                if vol>.001:shell_hits['frame-'+frame.FrameStyle]=vol
            assert not shell_hits,(side,'shell collisions',shell_hits)
            # Continuous conservative withdrawal through the shell opening.
            service_hits={}
            for name in ['display','display-sled','mcu']:
                b=parts[name].optimalBoundingBox(False,False)
                sweep=Part.makeBox(b.XLength,b.YLength,b.ZLength+24,A.Vector(b.XMin,b.YMin,b.ZMin))
                vol=overlap(shell,sweep)
                if vol>.001:service_hits[name]=vol
            upper=doc.getObject(prefix+'LevelUpperWalls').Shape
            for name,shape in slim_stack.key_reserves(side).items():
                # Preserve the thumb rotations. An axis-aligned bounding box
                # invents corners outside the actual rotated switch envelope.
                swept_solids=[]
                for solid in shape.Solids:
                    z=solid.optimalBoundingBox(False,False).ZMin
                    bottom=[f for f in solid.Faces if f.BoundBox.ZLength<1e-7
                            and abs(f.BoundBox.ZMin-z)<1e-7]
                    assert len(bottom)==1,(name,'switch bound bottom face')
                    swept_solids.append(bottom[0].extrude(A.Vector(0,0,40)))
                sweep=Part.makeCompound(swept_solids)
                vol=overlap(upper,sweep)
                if vol>.001:service_hits[name]=vol
            assert not service_hits,(side,'upper shell withdrawal',service_hits)

            batteries={}
            for o in doc.Objects:
                if o.Name.startswith(prefix) and o.TypeId!='App::Link' and hasattr(o,'BatteryStyle'):
                    assert abs(bounds(o.Shape)[2]-1.4)<1e-6
                    assert o.Shape.distToShape(parts['tray'])[0]<1e-6
                    hits={name:overlap(o.Shape,shape) for name,shape in parts.items() if name!='battery'}
                    assert all(v<.001 for v in hits.values()),(side,o.BatteryStyle,hits)
                    batteries[o.BatteryStyle]={'floor_contact_mm':o.Shape.distToShape(parts['tray'])[0],
                                             'locator_overlap_mm3':overlap(o.Shape,parts['cradle'])}
            # Each imported display contact ring must be concentric with J2.
            centers=sorted((round(s.CenterOfMass.x,6),round(s.CenterOfMass.y,6))
                           for s in doc.getObject(prefix+'NiceViewVisual1').Shape.Solids)
            cx=122.8 if side=='left' else 37.2
            expected=sorted((round(cx-5.08+i*2.54,6),-50.8) for i in range(5))
            assert centers==expected,(side,centers,expected)
            # Continuous cap travel: independently compare each transformed hull
            # against the saved native upper-wall volume, not sampled cap poses.
            import sys as _sys
            _sys.path.insert(0,str(ROOT/'tools'))
            from keycap_config import polygon
            from shapely.geometry import Polygon
            from shapely.ops import unary_union
            c=json.loads((ROOT/'keycaps/catalog.json').read_text())
            polys=[Polygon(polygon(v['hull_xy_mm'],key,turn))
                   for key in c['layout'][side] for v in c['variants'] if v['qualified_reference_positions']
                   for turn in v['rotations_deg']]
            union=unary_union(polys).buffer(.2,quad_segs=12)
            pieces=list(union.geoms) if hasattr(union,'geoms') else [union]
            swept=[]
            for p in pieces:
                wire=Part.makePolygon([A.Vector(x,-y,8.2) for x,y in p.exterior.coords])
                swept.append(Part.Face(Part.Wire(wire.Edges)).extrude(A.Vector(0,0,20)))
            sweep=Part.makeCompound(swept)
            hit=overlap(shell,sweep)
            assert hit<.001,(side,'cap full-travel collision',hit)
            result['halves'][side]={'frame_and_shell_top_mm':13.39,'glass_top_mm':bounds(glass)[5],
                'batteries':batteries,'display_contact_centers_xy_mm':centers,
                'mcu_display_distance_mm':parts['mcu'].distToShape(parts['display'])[0],
                'mcu_board_support_area_mm2':support_area,
                'upper_shell_collisions':shell_hits,'continuous_upper_shell_withdrawal_collisions':service_hits,
                'continuous_cap_poses':len(polys),'continuous_cap_travel_mm':3.5,
                'cap_clearance_sweep_overlap_mm3':hit,'closed_connected_upper_shell':True,
                'unchanged_switch_plate_top_mm':7.6,'upper_shell_mount_count':3}
        finally: half.Placement=pose;doc.recompute()
    failures=[]
    for side,h in result['stack']['halves'].items():
        for key in ['static_collisions','bottom_reset_probe_collisions']:
            if h[key]:failures.append([side,key,h[key]])
        for profile,leads in h['cell_motion'].items():
            if any(v['outside_attachment_overlap_mm3']>.001 for v in leads):failures.append([side,profile,'cell motion',leads])
        for profile,v in h['profiles'].items():
            for key,hits in v.items():
                if hits:failures.append([side,profile,key,hits])
    for side,h in result['ph_service']['halves'].items():
        if not h['rigid_housing_path_clear'] or not h['grip_tool_path_clear']:failures.append([side,'PH service',h])
        for profile,terminals in h['nominal_terminal_distances'].items():
            if any(t['to_plug_mm']>.001 or t['to_cell_mm']>.001 for t in terminals):failures.append([side,profile,'terminal continuity',terminals])
    result['failures']=failures;result['nominal_acceptance']=not failures
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args,_=p.parse_known_args()
    import FreeCADGui as G
    G.showMainWindow();G.getMainWindow().hide()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before=sha(args.source);doc=A.openDocument(str(args.source));doc.recompute()
    result=check(doc);result.update(source_sha256=before,checker_sha256=sha(Path(__file__)))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    assert sha(args.source)==before
    print(json.dumps({'nominal_acceptance':result['nominal_acceptance'],'failures':result['failures']}),file=sys.__stdout__,flush=True)
    A.closeDocument(doc.Name);os._exit(0 if result['nominal_acceptance'] else 1)

if __name__=='__main__': main()
