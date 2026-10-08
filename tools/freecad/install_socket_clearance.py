"""Relieve only the K30-facing segment of the H3 support on both halves.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,math,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G,Part
from check_audit_delivery import min_distance,shape_digest
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(s):print(s,file=sys.__stdout__,flush=True)
def empty(s):return not(s.Faces or s.Edges or s.Vertexes)
def equivalent(a,b):
    if shape_digest(a)==shape_digest(b):return 'identical serialized BRep'
    def solid_only(s):
        return s.ShapeType=='Solid' or (s.ShapeType in ('Compound','CompSolid') and all(solid_only(c) for c in s.childShapes()))
    assert a.isValid() and b.isValid() and solid_only(a) and solid_only(b)
    aa=list(a.Solids);bb=[(v,v.optimalBoundingBox(False,False)) for v in b.Solids];assert aa and len(aa)==len(bb)
    # A bijection of equal solids proves equal compounds. Pair by spatial
    # bounds, then require both exact Boolean differences to be empty. This
    # avoids an unnecessary all-to-all Boolean over 54 disconnected sockets.
    keys=['XMin','YMin','ZMin','XMax','YMax','ZMax']
    for old in aa:
        bounds=old.optimalBoundingBox(False,False)
        distance=lambda pair:max(abs(getattr(bounds,k)-getattr(pair[1],k)) for k in keys)
        i=min(range(len(bb)),key=lambda i:distance(bb[i]));pair=bb.pop(i);new=pair[0]
        assert distance(pair)<1e-6,('Optimal solid bounds differ',distance(pair),bounds,pair[1])
        if shape_digest(old)!=shape_digest(new):
            ab=old.cut(new);ba=new.cut(old)
            assert empty(ab) and empty(ba),('Nonempty bidirectional solid difference',ab.Volume,ba.Volume)
    return 'empty bidirectional Boolean difference for all '+str(len(aa))+' matched solids'
def run():
    argv=sys.argv[1:]
    while argv and not argv[0].startswith('--'):argv.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args(argv)
    digest=sha(a.source);assert a.source.resolve()!=a.output.resolve();assert not a.output.exists()
    G.showMainWindow();G.getMainWindow().hide();doc=A.openDocument(str(a.source));doc.recompute()
    poses={p:A.Placement(doc.getObject(p+'Half').Placement) for p in ['L_','R_']}
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute();report={'parent_source_sha256':digest,'installer_sha256':sha(__file__),'halves':{},'physical_acceptance':False}
    unchanged={o.Name:o.Shape.copy() for o in doc.Objects if hasattr(o,'Shape') and getattr(o,'PartID','') and not o.PartID.endswith('-tray')}
    unchanged_hashes={name:shape_digest(doc.getObject(name).Shape) for name in unchanged}
    socket_hashes={p:shape_digest(doc.getObject(p+'HotswapSockets').Shape) for p in poses}
    for side,prefix in [('left','L_'),('right','R_')]:
        history=doc.getObject(prefix+'Construction');pillar=doc.getObject(prefix+'Pillar3');pilot=doc.getObject(prefix+'Pilot3');socket=doc.getObject(prefix+'Hotswap_K30')
        assert abs(pillar.Radius.Value-2.3)<1e-8 and abs(pilot.Radius.Value-.85)<1e-8
        center=A.Vector(pillar.Placement.Base);before=min_distance([socket],pillar.Shape)
        point=A.Vector(*before['witness']['socket_point_mm']);n=A.Vector(point.x-center.x,point.y-center.y,0);n.normalize();angle=math.degrees(math.atan2(n.y,n.x));t=A.Vector(-n.y,n.x,0)
        # Use an exact supporting plane of the full plastic solid, not a fitted
        # bounding box of the socket. Metal is independently checked afterward.
        plastic=socket.Shape.Solids[0].copy();plastic.rotate(center,A.Vector(0,0,1),-angle)
        support=plastic.optimalBoundingBox(False,False).XMin-center.x;plane=support-.25
        assert plane-pilot.Radius.Value>=1.20
        box=doc.addObject('Part::Box',prefix+'SocketH3Halfspace');box.Length=10;box.Width=10
        box.Placement=A.Placement(center+n*plane-t*5,A.Rotation(A.Vector(0,0,1),angle))
        box.setExpression('Placement.Base.z','Parameters.Floor');box.setExpression('Height','Parameters.PCBTop - Parameters.PCBThickness - Parameters.Floor');history.addObject(box)
        relief=doc.addObject('Part::Common',prefix+'SocketH3Relief');relief.Base=pillar;relief.Tool=box;relief.Refine=True;history.addObject(relief);doc.recompute([relief])
        assert relief.Shape.isValid() and len(relief.Shape.Solids)==1
        actual_web=relief.Shape.distToShape(pilot.Shape)[0];assert actual_web>=1.20
        cut_post=pillar.Shape.cut(relief.Shape);assert cut_post.isValid() and len(cut_post.Solids)==1
        gap=socket.Shape.distToShape(cut_post)[0];assert gap>=.25-1e-7,(side,gap)
        top=pillar.Shape.BoundBox.ZMax
        removed_area=sum(f.Area for f in relief.Shape.Faces if abs(f.BoundBox.ZMin-top)<1e-7 and abs(f.BoundBox.ZMax-top)<1e-7)
        changes={}
        for style in ['solid','rim','terrace']:
            base=doc.getObject(prefix+'Case_'+style+'_base');old=base.Shape.copy();assert len(base.Links)==1
            cut=doc.addObject('Part::Cut',prefix+'SocketH3_'+style);cut.Base=base.Links[0];cut.Tool=relief;cut.Refine=True;history.addObject(cut);base.Links=[cut];doc.recompute([base])
            removed=old.common(relief.Shape)
            assert abs(old.Volume-base.Shape.Volume-removed.Volume)<1e-5
            assert base.Shape.isValid() and len(base.Shape.Solids)==1
            assert empty(removed.cut(pillar.Shape))
            assert removed.BoundBox.ZMin>=float(doc.Parameters.Floor)-1e-7
            assert removed.common(pilot.Shape).Volume<1e-8
            changes[style]={'removed_mm3':removed.Volume,'added_mm3':0,'valid_single_solid':True,'removal_confined_to_pillar3':True}
            cut.Visibility=False
        box.Visibility=False;relief.Visibility=False;doc.recompute()
        assert doc.getObject(prefix+'Case_level_base').Links==[doc.getObject(prefix+'Case_solid_base')]
        assert abs(doc.getObject(prefix+'Case_level_base').Shape.Volume-doc.getObject(prefix+'Case_solid_base').Shape.Volume)<1e-8
        report['halves'][side]={'old_socket_to_post_mm':before['distance_mm'],'normal_xy':[n.x,n.y],'support_plane_radius_mm':plane,'socket_to_relieved_post_mm':gap,'minimum_pilot_web_mm':actual_web,'thread_envelope_web_mm':plane-1,'bearing_area_removed_mm2':removed_area,'bearing_area_remaining_mm2':math.pi*(2.3**2-.85**2)-removed_area,'changes':changes,'floor_exterior_pilot_center_height_preserved':True}
        log(side+': socket gap '+str(gap)+'; pilot web '+str(actual_web)+'; bearing removed '+str(removed_area))
    for name,d in unchanged_hashes.items():assert shape_digest(doc.getObject(name).Shape)==d,('Unrelated part changed',name)
    for prefix,h in socket_hashes.items():assert shape_digest(doc.getObject(prefix+'HotswapSockets').Shape)==h
    marker=doc.addObject('App::DocumentObjectGroup','SocketH3Clearance');marker.addProperty('App::PropertyString','RecipeJSON');marker.RecipeJSON=json.dumps(report,sort_keys=True)
    for prefix,pose in poses.items():doc.getObject(prefix+'Half').Placement=pose
    doc.recompute();a.output.parent.mkdir(parents=True,exist_ok=True);doc.saveAs(str(a.output));A.closeDocument(doc.Name)
    # Compare independent reopened files, not shapes whose tessellation caches
    # participated in the construction probes above.
    original=A.openDocument(str(a.source))
    for p in poses:original.getObject(p+'Half').Placement=A.Placement()
    original.recompute()
    unchanged_hashes={name:shape_digest(original.getObject(name).Shape) for name in unchanged}
    unchanged={name:original.getObject(name).Shape.copy() for name in unchanged}
    A.closeDocument(original.Name)
    doc=A.openDocument(str(a.output));doc.recompute();assert not any('Invalid' in o.State for o in doc.Objects)
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute()
    comparisons={}
    for name,d in unchanged.items():
        comparisons[name]='identical serialized BRep' if shape_digest(doc.getObject(name).Shape)==unchanged_hashes[name] else equivalent(d,doc.getObject(name).Shape)
        log('Reopened part unchanged: '+name+' / '+comparisons[name])
    for p in poses:
        for style in ['level','solid','rim','terrace']:
            obj=doc.getObject(p+'Case_'+style+'_base');assert obj.Shape.isValid() and len(obj.Shape.Solids)==1
        assert p+'HotswapSockets' in comparisons
    A.closeDocument(doc.Name);assert sha(a.source)==digest
    report.update(source_sha256=sha(a.output),saved_reopened=True,unrelated_parts_geometrically_unchanged=True,unchanged_part_comparisons=comparisons,passed=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    # This is explicit evidence reuse only for unchanged socket/PCB registration.
    # Parameters, delivery clearances and exports are freshly checked separately.
    old_path=a.source.parent/'hotswap.json';old=json.loads(old_path.read_text());assert old['passed'] and old['source_sha256']==digest
    for side in ['left','right']:assert old['halves'][side]['pcb_sha256']==sha(ROOT/f'hardware/revI/flan36-{side}.kicad_pcb')
    old['inherited_registration']={'report_path':str(old_path.resolve().relative_to(ROOT)),'report_sha256':sha(old_path),'native_sha256':digest,'basis':'Unchanged socket BRep before save and exact matched-solid equivalence after reopen, unchanged PCB hashes; only local case support subtraction','parent_socket_brep_sha256':socket_hashes,'saved_socket_equivalence':{p:comparisons[p+'HotswapSockets'] for p in poses},'relief_report_sha256':sha(a.report)}
    old['source_sha256']=sha(a.output);(a.output.parent/'hotswap.json').write_text(json.dumps(old,indent=2)+'\n')
    log('PASS: localized H3 relief, unchanged components, saved/reopened candidate')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
