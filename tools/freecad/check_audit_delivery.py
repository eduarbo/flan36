"""Validate saved audit delivery against the source baseline and actual PCBs.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,copy,hashlib,json,math,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G,Part
from export_pcb_components import footprints,children,difference
from check_pcb_step_registration import cli_export
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
# This predecessor used the identical exact distance solver below. Its completed
# measurements remain valid when every non-checker input is unchanged.
CHECKPOINT_PREDECESSOR='4b9078c4eeddbab764608bcb8f77291dc53264610a8a756b4ea6813f67f96789'
def log(s):print(s,file=sys.__stdout__,flush=True)
def shape_digest(shape):
    # Exact serialized BRep identity, including placement; no bbox-only reuse.
    return hashlib.sha256(shape.exportBrepToString().encode()).hexdigest()

def min_distance(nodes,b):
    pairs=[]
    # For disjoint parts (checked separately by the volume-intersection gate),
    # solid-to-boundary distance equals solid-to-solid distance. Face boxes
    # prune distant case walls without repeatedly searching the whole shell.
    aa=[(node.Name,getattr(node,'PCBReference',''),i,x,x.BoundBox)
        for node in nodes for i,x in enumerate(node.Shape.Solids)]
    bb=[(i,y,y.BoundBox) for i,y in enumerate(b.Faces)]
    for name,ref,i,x,u in aa:
        for j,y,v in bb:
            lower=math.sqrt(sum(max(getattr(u,k+'Min')-getattr(v,k+'Max'),getattr(v,k+'Min')-getattr(u,k+'Max'),0)**2 for k in 'XYZ'))
            pairs.append((lower,name,ref,i,j,x,y))
    best=float('inf');witness=None;evaluated=0
    for lower,name,ref,i,j,x,y in sorted(pairs,key=lambda i:i[0]):
        if lower>=best-1e-7:break
        distance,points,_=x.distToShape(y);evaluated+=1
        if distance<best:
            best=distance;v,w=points[0]
            witness={'socket_object':name,'pcb_reference':ref,'socket_solid_index':i,
                     'target_face_index':j,'socket_point_mm':[v.x,v.y,v.z],
                     'target_point_mm':[w.x,w.y,w.z]}
    assert math.isfinite(best) and witness
    return {'distance_mm':best,'witness':witness,'exact_face_pairs_evaluated':evaluated,
            'bounding_box_pairs':len(pairs)}

def included_distance(nodes,shape,parent,parent_shape):
    """Distance lower bound by set inclusion, upper bound by a retained witness."""
    assert shape.Solids and shape.isValid() and all(s.isClosed() for s in shape.Solids)
    assert parent_shape.Solids and parent_shape.isValid() and all(s.isClosed() for s in parent_shape.Solids)
    residual=shape.cut(parent_shape)
    proof={'parent_target_object':parent['target_object'],
           'parent_distance_mm':parent['distance_mm'],
           'subset_difference_null':residual.isNull(),
           'subset_difference_empty':not (residual.Faces or residual.Edges or residual.Vertexes),
           'subset_difference_volume_mm3':residual.Volume,
           'subset_difference_area_mm2':residual.Area,
           'subset_difference_solid_count':len(residual.Solids)}
    # Demand an actually empty result, not a small positive residual volume.
    if not proof['subset_difference_empty']:
        log('Set inclusion not established: '+str(proof));return None
    point=A.Vector(*parent['witness']['target_point_mm']);vertex=Part.Vertex(point)
    nearest=None
    for i,face in enumerate(shape.Faces):
        box=face.BoundBox
        lower=math.sqrt(sum(max(getattr(box,k+'Min')-getattr(point,k.lower()),getattr(point,k.lower())-getattr(box,k+'Max'),0)**2 for k in 'XYZ'))
        if lower>1e-7:continue
        d=vertex.distToShape(face)[0]
        if d<1e-7:nearest=(i,d);break
    if nearest is None:
        log('Prior witness absent from included boundary');return None
    result=copy.deepcopy(parent)
    result.pop('reused_identical_brep',None)
    result['witness']['target_face_index']=nearest[0]
    proof['retained_boundary_witness_distance_mm']=nearest[1]
    proof['closed_valid_solids']=True
    result['inclusion_proof']=proof
    result['distance_method']='exact set inclusion plus retained boundary witness'
    result.pop('exact_face_pairs_evaluated',None);result.pop('bounding_box_pairs',None)
    return result

def write_report(path,report):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)

def run():
    argv=sys.argv[1:]
    while argv and not argv[0].startswith('--'):argv.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args(argv)
    G.showMainWindow();G.getMainWindow().hide()
    before=A.openDocument(str(args.baseline));before.recompute()
    caps={o.Name:(o.Mesh.Topology,str(o.Placement)) for o in before.Objects if o.Name.startswith(('L_K','R_K')) and hasattr(o,'Mesh')};assert len(caps)==36
    A.closeDocument(before.Name);doc=A.openDocument(str(args.source));doc.recompute()
    assert doc.AuditRepairs20261007.SourceSHA256==sha(args.baseline)
    assert not any('Invalid' in o.State or o.TypeId.endswith('Python') for o in doc.Objects)
    delta=0
    for name,(old,pose) in caps.items():
        node=doc.getObject(name);new=node.Mesh.Topology;assert new[1]==old[1] and len(new[0])==len(old[0]) and str(node.Placement)==pose
        delta=max(delta,max((a-b).Length for a,b in zip(old[0],new[0])))
    assert delta<1e-5
    from configuration import extract
    from keycap_config import normalize
    assert extract(doc)==normalize(json.loads((ROOT/'design/configurations/default.json').read_text()))
    for prefix in ['L_','R_']:doc.getObject(prefix+'Half').Placement=A.Placement()
    doc.recompute();report={'source_sha256':sha(args.source),'baseline_sha256':sha(args.baseline),'checker_sha256':sha(__file__),'keycaps':{'count':36,'max_vertex_delta_mm':delta,'placements_unchanged':True},'halves':{},'native_saved_reopened':True,'configuration_matches_default':True,'physical_acceptance':False}
    work=args.report.parent/'delivery-step';work.mkdir(exist_ok=True)
    calibration_path=ROOT/'build/audit-fixes-20261007/candidate/diodes.json'
    calibration=json.loads(calibration_path.read_text())['calibration']
    bound_paths=[args.source,args.baseline,Path(__file__),calibration_path,
        ROOT/'design/configurations/default.json',ROOT/'hardware/revI/models/diode-sod123.step',
        ROOT/'tools/keycap_config.py',ROOT/'tools/frame_finishes.py',ROOT/'keycaps/catalog.json',
        *[ROOT/f'hardware/revI/flan36-{s}.kicad_pcb' for s in ['left','right']],
        *[Path(__file__).with_name(s+'.py') for s in
          ['export_pcb_components','check_pcb_step_registration','configuration']]]
    inputs={str(path.resolve().relative_to(ROOT)):sha(path) for path in bound_paths}
    report['inputs_sha256']=inputs;report['passed']=False
    checkpoint=args.report.with_suffix('.checkpoint.json')
    if checkpoint.exists():
        previous=json.loads(checkpoint.read_text())
        old_inputs=previous.get('inputs_sha256',{})
        checker_key=str(Path(__file__).resolve().relative_to(ROOT))
        predecessor=(previous.get('checker_sha256')==CHECKPOINT_PREDECESSOR and
            old_inputs.get(checker_key)==CHECKPOINT_PREDECESSOR and
            {k:v for k,v in old_inputs.items() if k!=checker_key}==
            {k:v for k,v in inputs.items() if k!=checker_key})
        if old_inputs==inputs or predecessor:
            report['halves']=previous['halves'];log('Resuming exact source-bound delivery checkpoint')
            if predecessor:
                report['checkpoint_predecessor_sha256']=CHECKPOINT_PREDECESSOR
                for half in report['halves'].values():
                    for record in half.get('distance_witnesses',{}).values():
                        record['producing_checker_sha256']=CHECKPOINT_PREDECESSOR
    distance_cache={}
    for half in report['halves'].values():
        for record in half.get('distance_witnesses',{}).values():
            distance_cache[record['exact_geometry_cache_key']]=record
    for side,prefix in [('left','L_'),('right','R_')]:
        group=doc.getObject(prefix+'HotswapSockets');diodes=doc.getObject(prefix+'Diodes');assert len(group.Links)==len(diodes.Links)==18
        half=report['halves'].setdefault(side,{'distance_witnesses':{}})
        group_hash=shape_digest(group.Shape)
        def measured(name,obj,included_in=None):
            if name in half['distance_witnesses']:
                result=half['distance_witnesses'][name]
                log(side+' reused checkpoint socket distance / '+name+': '+str(result['distance_mm']))
                return result['distance_mm']
            cache_key=group_hash+':'+shape_digest(obj.Shape)
            result=None
            if cache_key in distance_cache:
                result=copy.deepcopy(distance_cache[cache_key]);result['reused_identical_brep']=True
            elif included_in:
                parent_name,parent_obj=included_in
                log(side+' proving '+name+' subset of '+parent_name)
                result=included_distance(group.Links,obj.Shape,half['distance_witnesses'][parent_name],parent_obj.Shape)
            if result is None:result=min_distance(group.Links,obj.Shape)
            result['exact_geometry_cache_key']=cache_key
            result['producing_checker_sha256']=sha(__file__)
            distance_cache[cache_key]=result
            result['target_object']=obj.Name
            half['distance_witnesses'][name]=result
            write_report(checkpoint,report)
            log(side+' socket distance / '+name+': '+str(result['distance_mm'])+'; '+str(result['witness']))
            return result['distance_mm']
        distance={}
        for part in ['pcb','tray','key-plate','diodes','mcu-sockets','jst','reset','slider','cradle','battery-retainer','mcu-riser']:
            other=next(o for o in doc.Objects if getattr(o,'PartID','')==side+'-'+part)
            distance[part]=measured(part,other)
        cases={}
        for style in ['level','solid','rim','terrace']:
            for layer in ['base','plate']:
                obj=doc.getObject(prefix+'Case_'+style+'_'+layer)
                included=('solid-'+layer,doc.getObject(prefix+'Case_solid_'+layer)) if style=='terrace' else None
                cases[style+'-'+layer]=measured(style+'-'+layer,obj,included)
                assert cases[style+'-'+layer]>.05,(side,style,layer,cases)
                if layer=='base' and doc.getObject('SocketH3Clearance'):
                    assert cases[style+'-'+layer]>=.25-1e-7,(side,style,'corrected support clearance',cases)
        if doc.getObject('SocketH3Clearance'):
            relief=doc.getObject(prefix+'SocketH3Relief').Shape
            web=relief.distToShape(doc.getObject(prefix+'Pilot3').Shape)[0]
            assert web>=1.20,(side,'saved pilot web',web)
            half['saved_support_pilot_web_mm']=web
        board=ROOT/f'hardware/revI/flan36-{side}.kicad_pcb';fps=footprints(board)
        refs=sorted(r for r in fps if r.startswith('D'));actual=cli_export(board,work/(side+'-diodes.step'),'--no-board-body','--component-filter',','.join(refs));actual.translate(A.Vector(0,0,calibration['kicad_to_native_z_mm']))
        diode_delta=difference(diodes.Shape,actual);assert diode_delta<.001
        # Every diode and socket must appear in the renderer's compact material groups.
        for obj in [group,diodes]:
            actual_area=sum(v.Shape.Area for v in obj.VisualParts);assert abs(actual_area-obj.Shape.Area)<1e-4,(obj.Name,actual_area,obj.Shape.Area)
            assert len(obj.VisualParts)<=3
        half.update({'minimum_hotswap_distances_mm':distance,'minimum_hotswap_case_distances_mm':cases,'diodes':{'count':18,'actual_step_difference_mm3':diode_delta},'hotswap_count':18,'pcb_sha256':sha(board),'visual_surface_area_complete':True})
        write_report(checkpoint,report)
        log(side+': saved components, current PCB diode registration, exact minimum socket clearances verified')
    assert inputs=={str(path.resolve().relative_to(ROOT)):sha(path) for path in bound_paths},'A source-bound input changed during validation'
    report['passed']=True;write_report(args.report,report);write_report(checkpoint,report);A.closeDocument(doc.Name)
    log('PASS: both halves, 36 unchanged caps, current PCB diodes, all exact socket distances')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
