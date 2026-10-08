"""Add nominal, datum-registered hot-swap sockets without changing PCB placement.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,re,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G,Part
from hotswap_geometry import local_socket
from export_pcb_components import footprints,children,export,difference
from check_pcb_step_registration import cli_export,sha
import flush_frames as F
ROOT=Path(__file__).resolve().parents[2]
def log(s):print(s,file=sys.__stdout__,flush=True)
def bounds(s):
    b=s.cleaned().BoundBox
    return [getattr(b,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
def colored_visuals(doc,prefix,group,nodes,source,colors):
    """One merged visual per material, not a draw call for every small chip."""
    old=list(getattr(group,'VisualParts',[]))
    if 'VisualParts' not in group.PropertiesList:group.addProperty('App::PropertyLinkList','VisualParts','Flan36')
    group.VisualParts=[]
    for o in old:doc.removeObject(o.Name)
    visuals=[]
    for i,color in enumerate(sorted(set(tuple(c) for c in colors))):
        faces=[]
        for node in nodes:
            for f,c in zip(source.Faces,colors):
                if tuple(c)==color:
                    placed=f.copy();placed.Placement=node.Placement.multiply(placed.Placement);faces.append(placed)
        o=doc.addObject('Part::Feature',prefix+'Visual'+str(i));o.Shape=Part.makeCompound(faces);o.ViewObject.ShapeColor=color[:3]
        doc.getObject(prefix[:2]+'Construction').addObject(o);o.Visibility=False;visuals.append(o)
    group.VisualParts=visuals

def run():
    argv=sys.argv[1:]
    while argv and not argv[0].startswith('--'):argv.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args(argv)
    G.showMainWindow();G.getMainWindow().hide();import ImportGui
    local,colors,datums=local_socket();assert len(colors)==len(local.Faces)
    calibration=json.loads((ROOT/'build/audit-fixes-20261007/candidate/diodes.json').read_text())['calibration']
    report={'datums':datums,'models':{},'halves':{},'physical_acceptance':False}
    step=local.copy();step.translate(A.Vector(0,0,-1.6+calibration['local_z_correction_mm']['F.Cu']))
    export('choc-hotswap',step,colors,ROOT/'hardware/revI/models',report)
    doc=A.openDocument(str(a.source));poses={p:A.Placement(doc.getObject(p+'Half').Placement) for p in ['L_','R_']}
    for p in poses:doc.getObject(p+'Half').Placement=A.Placement()
    doc.recompute();work=a.report.parent/'hotswap-step';work.mkdir(exist_ok=True)
    for side,prefix in [('left','L_'),('right','R_')]:
        board=ROOT/f'hardware/revI/flan36-{side}.kicad_pcb';before=board.read_text();fps=footprints(board);after=before;nodes=[]
        keys={r:v for r,v in fps.items() if r.startswith('K')};assert len(keys)==18
        for ref,fp in sorted(keys.items()):
            assert fp['layer']=='F.Cu';x,y,angle=fp['pose']
            holes=[]
            for pad in children(fp['block']):
                if pad.startswith('(pad ') and 'np_thru_hole' in pad:
                    xy=[float(v) for v in re.search(r'\(at\s+([^\)]+)\)',pad)[1].split()[:2]];holes.append(xy)
            for target in [(0,-5.95),(5,-3.75)]:assert any(max(abs(a-b) for a,b in zip(h,target))<1e-5 for h in holes),(ref,target)
            node=doc.addObject('Part::Feature',prefix+'Hotswap_'+ref);node.Shape=local.copy()
            node.Placement=A.Placement(A.Vector(x,-y,3.8),A.Rotation(A.Vector(0,0,1),angle));node.setExpression('Placement.Base.z','Parameters.PCBTop - 1.6 mm')
            node.ViewObject.DiffuseColor=colors;F.prop(node,'PCBReference','App::PropertyString',ref);nodes.append(node)
            doc.getObject(prefix+'Construction').addObject(node);node.Visibility=False
            model='(model "${KIPRJMOD}/models/choc-hotswap.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'
            existing=[m for m in children(fp['block']) if m.startswith('(model ') and 'choc-hotswap.step' in m]
            assert len(existing)<=1
            new=fp['block'].replace(existing[0],model) if existing else fp['block'][:-1].rstrip()+'\n'+model+'\n)'
            after=after.replace(fp['block'],new)
        board.write_text(after);post=footprints(board)
        scrub=lambda b:'\n'.join(x for x in children(b) if not x.startswith('(model '))
        for ref,fp in fps.items():
            assert scrub(fp['block'])==scrub(post[ref]['block'])
            oldmodels=[x for x in children(fp['block']) if x.startswith('(model ')]
            assert all(m in post[ref]['block'] for m in oldmodels)
        assert [x for x in children(before) if not x.startswith('(footprint ')]==[x for x in children(after) if not x.startswith('(footprint ')]
        group=doc.addObject('Part::Compound',prefix+'HotswapSockets');group.Links=nodes
        for name,kind,value in [('PartID','App::PropertyString',side+'-hotswap-sockets'),('DisplayName','App::PropertyString','18 × Kailh Choc hot-swap sockets'),('Layer','App::PropertyString','pcb'),('ViewerGroup','App::PropertyString','pcb'),('PrototypePrintable','App::PropertyBool',False),('ModelStatus','App::PropertyString',datums['qualification'])]:F.prop(group,name,kind,value)
        group.Label='18 × Kailh Choc hot-swap sockets';doc.getObject(prefix+'Half').addObject(group)
        colored_visuals(doc,prefix+'Hotswap',group,nodes,local,colors);doc.recompute()
        # Actual delivered PCB export also contains the pre-existing switch model.
        # Match every socket solid one-to-one; never accept a bounding box alone.
        actual=cli_export(board,work/(side+'.step'),'--no-board-body','--component-filter',','.join(keys));actual.translate(A.Vector(0,0,calibration['kicad_to_native_z_mm']))
        remaining=list(actual.Solids);matched=[]
        for solid in group.Shape.Solids:
            b=bounds(solid);dist=lambda s:max(abs(x-y) for x,y in zip(b,bounds(s)))
            index=min(range(len(remaining)),key=lambda i:dist(remaining[i]));assert dist(remaining[index])<1e-5
            matched.append(remaining.pop(index))
        delta=difference(group.Shape,Part.makeCompound(matched));assert delta<.001,(side,delta)
        record={'count':len(nodes),'socket_solids':len(matched),'actual_step_difference_mm3':delta,'actual_step_sha256':sha(work/(side+'.step')),
            'native_bounds_mm':bounds(group.Shape),'nominal_floor_gap_mm':1.95-1.4,
            'footprints_pads_nets_tracks_contours_unchanged':True,'pcb_sha256':sha(board)}
        report['halves'][side]=record;log(side+': 18 actual PCB socket poses registered; STEP difference '+str(delta))
        # Merge the already verified diode face visuals into three material groups.
        diode=doc.getObject(prefix+'Diodes');dnodes=list(diode.Links)
        d=A.newDocument('DiodeVisualSource');ImportGui.insert(str(ROOT/'components/sources/D_SOD-123.step'),d.Name);d.recompute()
        original=next(o for o in d.Objects if hasattr(o,'Shape') and o.Shape.Solids);ds=original.Shape.copy();dc=list(original.ViewObject.DiffuseColor)
        if len(dc)==1:dc*=len(ds.Faces)
        A.closeDocument(d.Name);A.setActiveDocument(doc.Name);colored_visuals(doc,prefix+'Diodes',diode,dnodes,ds,dc)
    for prefix,pose in poses.items():doc.getObject(prefix+'Half').Placement=pose
    doc.FrameArtworkOrientation.StylesJSON=json.dumps([*json.loads(doc.FrameArtworkOrientation.StylesJSON),'hanafuda'])
    marker=doc.addObject('App::DocumentObjectGroup','HotswapRegistration');F.prop(marker,'RecipeJSON','App::PropertyString',json.dumps(report,sort_keys=True));F.prop(marker,'SourceSHA256','App::PropertyString',datums['source_sha256'])
    doc.recompute();doc.save();A.closeDocument(doc.Name)
    reopened=A.openDocument(str(a.source));reopened.recompute()
    for p in ['L_','R_']:assert len(reopened.getObject(p+'HotswapSockets').Links)==18 and len(reopened.getObject(p+'HotswapSockets').Shape.Solids)==54
    A.closeDocument(reopened.Name)
    report.update(source_sha256=sha(a.source),native_saved_reopened=True,passed=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n');log('PASS: saved/reopened 36 nominal hot-swap sockets, both contact planes and actual KiCad STEP')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
