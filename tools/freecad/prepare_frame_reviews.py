"""Save editable approval faces and renderable nominal frame candidates.
Never modifies or saves the production assembly.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import FreeCAD as A
import FreeCADGui as G
import Part,MeshPart
from frame_review_geometry import face,regions
ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build/display-seam/geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def log(s):print(s,file=sys.__stdout__,flush=True)
def bbox(s):
    b=s.BoundBox;return [b.XMin,-b.YMax,b.XMax,-b.YMin]
def prism(s,z0,z1):
    q=s.extrude(A.Vector(0,0,z1-z0));q.translate(A.Vector(0,0,z0));return q
def mesh(shape,path):
    m=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.10,Relative=False)
    assert m.isSolid(),path;m.write(str(path))
def run():
    BUILD.mkdir(parents=True,exist_ok=True);G.showMainWindow();G.getMainWindow().hide()
    source=Path(os.environ.get('FLAN36_REVIEW_SOURCE',ROOT/'mechanical/revI/Flan36.FCStd'));sourcehash=sha(source)
    src=A.openDocument(str(source));src.L_Half.Placement=A.Placement();src.R_Half.Placement=A.Placement();src.recompute()
    import flush_frames as F
    blank=F.find_smooth(src,'left').Shape.copy();blank.translate(A.Vector(-111,11,0))
    old=json.loads((ROOT/'design/proposals/frame-master-r4/master.json').read_text())
    original_window=face(old['aperture_commands'])
    glass=src.L_NiceViewVisual2.Shape.copy();glass.translate(A.Vector(-111,11,0))
    # Keep only the actual component solids as contextual geometry.
    context=[]
    for name in ['NiceViewVisual0','NiceViewVisual1','NiceViewVisual2','NiceViewVisual3','DisplayLedge0','DisplayLedge1','DisplayLedge2','DisplaySide0','DisplaySide1']:
        o=src.getObject('L_'+name)
        if o:
            s=o.Shape.copy();s.translate(A.Vector(-111,11,0));context.append((name,s))
            mesh(s,BUILD/(name+'.stl'))
    for folder,filename in [('display-seam-r1','Seam-candidate.FCStd'),('frame-redesign-r5','Artwork-R5.FCStd')]:
        out=ROOT/'design/proposals'/folder;master=json.loads((out/'master.json').read_text());digest=sha(out/'master.json')
        assert master['source_sha256']['mechanical/revI/Flan36.FCStd']==sourcehash
        doc=A.newDocument(folder.replace('-','_'));doc.Label='Flan36 · '+folder+' · PROPOSAL / NOT FOR PRINT'
        domain=face(master['outer_commands']).cut(face(master['aperture_commands']))
        xd=master['construction']['xy_domains'];relief=face(xd['relief_commands']);header=face(xd['header_commands'])
        zones={'ordinary':domain.cut(relief),'collar':relief.common(domain).cut(header),'cover':header.common(domain)}
        floors={'ordinary':13.19,'collar':12.725,'cover':13.19}
        added=original_window.cut(face(master['aperture_commands']))
        fill=[prism(added.common(zone),floors[k],13.59) for k,zone in zones.items() if added.common(zone).Area>1e-8]
        corrected=blank.multiFuse(fill).removeSplitter()
        assert corrected.isValid() and len(corrected.Solids)==1
        assert corrected.common(glass).Volume<1e-8
        report={'master_sha256':digest,'source_sha256':sourcehash,'physical_acceptance':False,'production_changed':False,'styles':{},
            'glass_clearance_mm':corrected.distToShape(glass)[0],'glass_interference_mm3':corrected.common(glass).Volume}
        assert abs(report['glass_clearance_mm']-.1)<1e-6
        for name,s in context:
            assert corrected.common(s).Volume<1e-6,(name,'candidate collision',corrected.common(s).Volume)
        for key,style in master['styles'].items():
            log('Checking '+folder+'/'+key);flat,features=regions(master,key)
            group=doc.addObject('App::Part',key);group.Label=style['label']+' · proposal'
            group.addProperty('App::PropertyString','MasterSHA256');group.MasterSHA256=digest
            group.addProperty('App::PropertyString','PaletteJSON');group.PaletteJSON=json.dumps(style['palette'])
            colored=[];parts={};record={'features':[],'roles':{}}
            for f,s in features:
                record['features'].append({'id':f['id'],'bounds_mm':bbox(s),'area_mm2':s.Area})
            for role,s in flat.items():
                node=doc.addObject('PartDesign::Feature',key+'_'+role+'_Plan');node.Shape=s;group.addObject(node)
                rgb=tuple(int(style['palette'][role][i:i+2],16)/255 for i in [1,3,5]);node.ViewObject.ShapeColor=rgb
                node.addProperty('App::PropertyString','CommandsJSON');node.CommandsJSON=json.dumps([f for f in style['features'] if f['color']==role])
                node.Visibility=False
                if role=='body':continue
                volumes=[]
                for zone,area in zones.items():
                    section=s.common(area)
                    if section.Area>1e-8:volumes.append(prism(section,floors[zone],13.59))
                if volumes:
                    shape=volumes[0].multiFuse(volumes[1:]) if len(volumes)>1 else volumes[0]
                    shape=shape.removeSplitter();parts[role]=shape;colored.append(shape)
            parts['body']=corrected.cut(Part.makeCompound(colored)).removeSplitter()
            full=Part.makeCompound(list(parts.values()))
            assert full.cut(corrected).Volume+corrected.cut(full).Volume<1e-5
            for role,s in parts.items():
                assert s.isValid() and s.Solids and all(t.isClosed() for t in s.Solids)
                for other,t in parts.items():
                    if role!=other:assert s.common(t).Volume<1e-6
                node=doc.addObject('PartDesign::Feature',key+'_'+role+'_ReviewSolid');node.Shape=s;group.addObject(node)
                node.addProperty('App::PropertyString','Purpose');node.Purpose='Nominal review solid; no approval, slice or physical qualification'
                node.ViewObject.ShapeColor=tuple(int(style['palette'][role][i:i+2],16)/255 for i in [1,3,5])
                mesh(s,BUILD/(folder+'-'+key+'-'+role+'.stl'))
                record['roles'][role]={'volume_mm3':s.Volume,'solids':len(s.Solids),'closed':True,'color':style['palette'][role]}
            # Native top partition must agree with the planar source, including logo holes.
            for role,s in parts.items():
                top=[]
                for q in s.Faces:
                    if abs(q.BoundBox.ZMin-13.59)<1e-6 and abs(q.BoundBox.ZMax-13.59)<1e-6:
                        t=q.copy();t.translate(A.Vector(0,0,-13.59));top.append(t)
                actual=Part.makeCompound(top);expected=flat[role]
                error=actual.cut(expected).Area+expected.cut(actual).Area
                assert error<.002,(key,role,error)
                record['roles'][role]['top_difference_mm2']=error
            report['styles'][key]=record
        doc.recompute();doc.saveAs(str(out/filename));A.closeDocument(doc.Name)
        reopened=A.openDocument(str(out/filename));assert all(o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape') and not o.Shape.isNull())
        A.closeDocument(reopened.Name);report['native_sha256']=sha(out/filename);report['saved_reopened']=True
        (out/'geometry-check.json').write_text(json.dumps(report,indent=2)+'\n')
    A.closeDocument(src.Name);assert sha(source)==sourcehash;log('PASS: exact proposals and candidates; production native unchanged')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
