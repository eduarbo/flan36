"""Share one exact nominal socket mesh across all 36 viewer placements.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A,FreeCADGui as G,Part,MeshPart
from hotswap_geometry import local_socket
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
    args=sys.argv[1:]
    while args and not args[0].startswith('--'):args.pop(0)
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--metadata',type=Path);a=p.parse_args(args);out=a.directory.resolve()
    metadata=a.metadata or (ROOT/'design/revI.json' if out==ROOT/'mechanical/revI' else out/'revI.json')
    G.showMainWindow();G.getMainWindow().hide();meta=json.loads(metadata.read_text());assert meta['fcstd_sha256']==sha(out/'Flan36.FCStd')
    shape,colors,datums=local_socket();visuals=[]
    for i,color in enumerate(sorted(set(tuple(c) for c in colors))):
        part=Part.makeCompound([f for f,c in zip(shape.Faces,colors) if tuple(c)==color]);name='component-hotswap-'+str(i)+'.stl'
        mesh=MeshPart.meshFromShape(Shape=part,LinearDeflection=.035,AngularDeflection=.15,Relative=False);mesh.write(str(out/name))
        visuals.append({'name':'Socket body' if i==0 else 'Socket contacts','path':'mechanical/revI/'+name,'color':'#'+''.join(f'{round(c*255):02x}' for c in color[:3]),'sha256':sha(out/name),'triangles':mesh.CountFacets})
    doc=A.openDocument(str(out/'Flan36.FCStd'));poses={}
    for side,prefix in [('left','L_'),('right','R_')]:
        poses[side]=[]
        nodes=doc.getObject(prefix+'HotswapSockets').Links;assert len(nodes)==18
        for node in nodes:
            p=node.Placement;expected=shape.copy();expected.Placement=p
            # Native instance references exactly the same source geometry; verify
            # placement and measured extents without rebuilding or moving it.
            b=expected.optimalBoundingBox(False,False);n=node.Shape.optimalBoundingBox(False,False)
            assert max(abs(getattr(b,k)-getattr(n,k)) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax'])<1e-6
            yaw,pitch,roll=p.Rotation.getYawPitchRoll();assert abs(pitch)+abs(roll)<1e-7
            poses[side].append({'reference':node.PCBReference,'position_mm':[p.Base.x,p.Base.z,-p.Base.y],'angle_deg':yaw})
    A.closeDocument(doc.Name)
    meta['hotswap_model']={'visuals':visuals,'instances':poses,'source_registration':datums,'geometry_reused':True,'physical_acceptance':False}
    source='tools/freecad/export_hotswap_visual.py';meta['inputs']=[i for i in meta['inputs'] if i['path']!=source];meta['inputs'].append({'path':source,'sha256':sha(ROOT/source)})
    metadata.write_text(json.dumps(meta,indent=2)+'\n');print('PASS: one shared two-material socket mesh; all 36 saved native placements read back',file=sys.__stdout__,flush=True)
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
