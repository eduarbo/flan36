"""Build exact approval solids on the current mechanical blank, without installing artwork.
Usage: python3 tools/freecad/run_macos.py tools/freecad/prepare_frame_artwork_review.py
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
OUT=ROOT/'design/proposals/frame-redesign-r6'
BUILD=ROOT/'build/frame-redesign-r6/geometry'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def log(s):print(s,file=sys.__stdout__,flush=True)
def prism(s,z0,z1):
    q=s.extrude(A.Vector(0,0,z1-z0));q.translate(A.Vector(0,0,z0));return q
def mesh(shape,path):
    m=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.10,Relative=False)
    assert m.isSolid(),path;m.write(str(path))
def run():
    BUILD.mkdir(parents=True,exist_ok=True);G.showMainWindow();G.getMainWindow().hide()
    master=json.loads((OUT/'master.json').read_text());digest=sha(OUT/'master.json')
    source=ROOT/'mechanical/revI/Flan36.FCStd';sourcehash=sha(source)
    assert master['source_sha256']['mechanical/revI/Flan36.FCStd']==sourcehash
    src=A.openDocument(str(source));src.L_Half.Placement=A.Placement();src.R_Half.Placement=A.Placement();src.recompute()
    import flush_frames as F
    blank=F.find_smooth(src,'left').Shape.copy();blank.translate(A.Vector(-111,11,0))
    glass=src.L_NiceViewVisual2.Shape.copy();glass.translate(A.Vector(-111,11,0))
    context=[]
    for name in ['NiceViewVisual0','NiceViewVisual1','NiceViewVisual2','NiceViewVisual3','DisplayLedge0','DisplayLedge1','DisplayLedge2','DisplaySide0','DisplaySide1']:
        o=src.getObject('L_'+name)
        if o:
            s=o.Shape.copy();s.translate(A.Vector(-111,11,0));context.append((name,s));mesh(s,BUILD/(name+'.stl'))
    doc=A.newDocument('Flan36_R6_Review');doc.Label='Flan36 R6 artwork · proposal, not for print'
    domain=face(master['outer_commands']).cut(face(master['aperture_commands']))
    xd=master['construction']['xy_domains'];relief=face(xd['relief_commands']);header=face(xd['header_commands'])
    zones={'ordinary':domain.cut(relief),'collar':relief.common(domain).cut(header),'cover':header.common(domain)}
    top=master['common']['frame_face_z_mm']
    floors={'ordinary':top-master['construction']['ordinary_inlay_depth_mm'],'collar':master['common']['relief_top_z_mm'],'cover':top-.4}
    assert blank.isValid() and len(blank.Solids)==1 and abs(blank.BoundBox.ZMax-top)<1e-6
    assert blank.common(glass).Volume<1e-8
    report={'master_sha256':digest,'source_sha256':sourcehash,'physical_acceptance':False,'production_changed':False,'styles':{},
        'glass_clearance_mm':blank.distToShape(glass)[0],'glass_interference_mm3':blank.common(glass).Volume,
        'review_method':'Literal planar paths partition the current unmodified mechanical blank; no aperture patch or height change.'}
    assert abs(report['glass_clearance_mm']-.1)<1e-6
    for name,s in context:assert blank.common(s).Volume<1e-6,(name,'candidate collision',blank.common(s).Volume)
    for key,style in master['styles'].items():
        log('Checking R6/'+key);flat,features=regions(master,key)
        group=doc.addObject('App::Part',key);group.Label=style['label']+' · proposal'
        group.addProperty('App::PropertyString','MasterSHA256');group.MasterSHA256=digest
        group.addProperty('App::PropertyString','PaletteJSON');group.PaletteJSON=json.dumps(style['palette'])
        colored=[];parts={};record={'features':[],'roles':{}}
        for f,s in features:
            b=s.BoundBox;record['features'].append({'id':f['id'],'bounds_mm':[b.XMin,-b.YMax,b.XMax,-b.YMin],'area_mm2':s.Area})
        for role,s in flat.items():
            node=doc.addObject('PartDesign::Feature',key+'_'+role+'_Plan');node.Shape=s;group.addObject(node)
            rgb=tuple(int(style['palette'][role][i:i+2],16)/255 for i in [1,3,5]);node.ViewObject.ShapeColor=rgb
            node.addProperty('App::PropertyString','CommandsJSON');node.CommandsJSON=json.dumps([f for f in style['features'] if f['color']==role]);node.Visibility=False
            if role=='body':continue
            volumes=[]
            for zone,area in zones.items():
                section=s.common(area)
                if section.Area>1e-8:volumes.append(prism(section,floors[zone],top))
            if volumes:
                shape=volumes[0].multiFuse(volumes[1:]) if len(volumes)>1 else volumes[0]
                shape=shape.removeSplitter();parts[role]=shape;colored.append(shape)
        parts['body']=blank.cut(Part.makeCompound(colored)).removeSplitter()
        full=Part.makeCompound(list(parts.values()))
        assert full.cut(blank).Volume+blank.cut(full).Volume<1e-5
        for role,s in parts.items():
            assert s.isValid() and s.Solids and all(t.isClosed() for t in s.Solids)
            for other,t in parts.items():
                if role!=other:assert s.common(t).Volume<1e-6
            node=doc.addObject('PartDesign::Feature',key+'_'+role+'_ReviewSolid');node.Shape=s;group.addObject(node)
            node.addProperty('App::PropertyString','Purpose');node.Purpose='Nominal review solid; not approved, sliced or physically qualified'
            node.ViewObject.ShapeColor=tuple(int(style['palette'][role][i:i+2],16)/255 for i in [1,3,5])
            mesh(s,BUILD/(key+'-'+role+'.stl'))
            record['roles'][role]={'volume_mm3':s.Volume,'solids':len(s.Solids),'closed':True,'color':style['palette'][role]}
            faces=[]
            for q in s.Faces:
                if abs(q.BoundBox.ZMin-top)<1e-6 and abs(q.BoundBox.ZMax-top)<1e-6:
                    t=q.copy();t.translate(A.Vector(0,0,-top));faces.append(t)
            actual=Part.makeCompound(faces);expected=flat[role]
            error=actual.cut(expected).Area+expected.cut(actual).Area
            assert error<.002,(key,role,error)
            record['roles'][role]['top_difference_mm2']=error
        # Arrange six independently selectable candidates rather than overlapping them.
        index=list(master['styles']).index(key)
        group.Placement.Base=A.Vector((index%3)*34,-(index//3)*66,0)
        report['styles'][key]=record
    doc.recompute();G.activeDocument().activeView().viewAxonometric();G.activeDocument().activeView().fitAll()
    doc.saveAs(str(OUT/'Artwork-R6.FCStd'));A.closeDocument(doc.Name)
    reopened=A.openDocument(str(OUT/'Artwork-R6.FCStd'))
    assert all(o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape') and not o.Shape.isNull())
    A.closeDocument(reopened.Name);report['native_sha256']=sha(OUT/'Artwork-R6.FCStd');report['saved_reopened']=True
    (OUT/'geometry-check.json').write_text(json.dumps(report,indent=2)+'\n')
    A.closeDocument(src.Name);assert sha(source)==sourcehash;log('PASS: six exact review solids; current mechanical assembly unchanged')
if __name__=='__main__':
    try:run()
    except Exception:traceback.print_exc(file=sys.__stderr__);sys.__stderr__.flush();os._exit(1)
    os._exit(0)
