"""Apply viewer configurations to the open revI document; no custom proxies.
Used by the companion macro. Does not save over the user's document.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json,sys
from pathlib import Path
import FreeCAD as A
import Mesh
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from keycap_config import load,check,normalize
from frame_finishes import role,palette,rgb

def apply_finish(doc,cover,side,body,accents=None):
    if accents is None:accents=json.loads(getattr(cover,'PaletteAccents','{}'))
    colors=palette(cover.FrameStyle,body,accents)
    if not hasattr(cover,'PaletteAccents'):cover.addProperty('App::PropertyString','PaletteAccents','Flan36')
    cover.PaletteAccents=json.dumps({k:colors[k] for k in ['detail','accent','secondary']})
    roof=float(doc.Parameters.FrameTop)
    cover.ViewObject.ShapeColor=rgb(body)
    if getattr(cover,'MaterialParts',[]):
        from flush_frames import face_roles
        roles=face_roles(cover)
        assert len(roles)==len(cover.Shape.Faces),'Flush material faces are out of date'
        cover.ViewObject.DiffuseColor=[rgb(colors[r]) for r in roles]
        for part in cover.MaterialParts:
            part.ViewObject.ShapeColor=rgb(colors[part.ColorRole])
    else:
        cover.ViewObject.DiffuseColor=[rgb(colors[role(cover.FrameStyle,side,f.CenterOfMass.x,-f.CenterOfMass.y,f.CenterOfMass.z,roof)]) for f in cover.Shape.Faces]
    # The visible App::Link must inherit its source's per-face materials.
    doc.getObject(('L_' if side=='left' else 'R_')+'ActiveFrame').ViewObject.OverrideMaterial=False

def apply(doc,config):
    catalog=load();errors,clearance=check(config,catalog)
    if errors:raise ValueError('\n'.join(errors[:12]))
    config=normalize(config,catalog)
    if not doc or not all(doc.getObject(p+'ActiveFrame') for p in ['L_','R_']):raise ValueError('Open mechanical/revI/Flan36.FCStd first.')
    variants={v['id']:v for v in catalog['variants']};meshes={}
    for side,keys in catalog['layout'].items():
        for key in keys:
            ident=config['keycaps'][side][key['ref']]['variant'];v=variants[ident]
            if ident not in meshes:
                path=ROOT/v['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==v['sha256'],'Modified STL: '+ident
                mesh=Mesh.Mesh(str(path));mat=A.Matrix();mat.A22=-1;mesh.transform(mat);mesh.flipNormals();meshes[ident]=mesh
    doc.openTransaction('Flan36 configuration')
    try:
        for side,prefix in [('left','L_'),('right','R_')]:
            for key in catalog['layout'][side]:
                choice=config['keycaps'][side][key['ref']];v=variants[choice['variant']];obj=doc.getObject(prefix+key['ref'])
                obj.ViewObject.ShapeColor=rgb(choice['color']);obj.Mesh=meshes[v['id']];obj.KeycapVariant=v['id'];obj.CapRotation=choice['rotation_deg']
                obj.Placement=A.Placement(A.Vector(key['x'],-key['y'],v['seating_z_mm']),A.Rotation(A.Vector(0,0,1),key['angle']+choice['rotation_deg']))
            battery=next(o for o in doc.Objects if o.Name.startswith(prefix) and o.TypeId!='App::Link' and getattr(o,'BatteryStyle',None)==config['batteries'][side])
            doc.getObject(prefix+'ActiveBattery').setLink(battery)
            receipt=doc.getObject('SlimStackReceipt')
            if receipt:
                wires=json.loads(receipt.RecipeJSON)['halves'][side]['lead_objects'][config['batteries'][side]]
                for index,name in enumerate(wires):
                    link=doc.getObject(prefix+'ActiveBatteryLead'+str(index))
                    if not link or link.TypeId!='App::Link':
                        raise ValueError('Missing battery lead profile link: '+side)
                    link.setLink(doc.getObject(name))
                for obj in doc.Objects:
                    if obj.Name.startswith(prefix) and obj.TypeId!='App::Link' and hasattr(obj,'BatteryLeadStyle'):
                        obj.Visibility=False
            for o in doc.Objects:
                if hasattr(o,'BatteryStyle') and o.TypeId!='App::Link':o.Visibility=False
            doc.getObject(prefix+'ActiveBattery').Visibility=True
            case=config['cases'][side]
            for group,name in [('base','ActiveTray'),('plate','ActivePlate')]:
                link=doc.getObject(prefix+name);source=doc.getObject(prefix+'Case_'+case['style']+'_'+group);link.setLink(source);link.ViewObject.OverrideMaterial=False
                source.ViewObject.ShapeColor=rgb(case[group+'_color']);source.ViewObject.DiffuseColor=[rgb(case[group+'_color'])]*len(source.Shape.Faces)
            half=doc.getObject(prefix+'Half');half.DisplayCoverInstalled=case['cover']
            if not hasattr(half,'MatchFrameColor'):half.addProperty('App::PropertyBool','MatchFrameColor','Flan36')
            half.MatchFrameColor=case['match_frame']
            for o in doc.Objects:
                if o.Name.startswith(prefix) and hasattr(o,'CaseStyle'):o.Visibility=False
            doc.getObject(prefix+'ActiveTray').Visibility=True;doc.getObject(prefix+'ActivePlate').Visibility=True
            f=config['frames'][side];cover=next(o for o in doc.Objects if o.Name.startswith(prefix) and o.TypeId!='App::Link' and hasattr(o,'FrameStyle') and o.FrameStyle==f['style'])
            doc.getObject(prefix+'ActiveFrame').setLink(cover)
            apply_finish(doc,cover,side,f['color'],f['accents'])
            for o in doc.Objects:
                if o.Name.startswith(prefix) and hasattr(o,'FrameStyle'):o.Visibility=False
            doc.getObject(prefix+'ActiveFrame').Visibility=case['cover']
            for i in range(3):doc.getObject(prefix+'SteelTarget'+str(i)).Visibility=case['cover']
        doc.recompute()
        # Native boolean view providers remap face colors during recompute.
        # Apply the explicit palette after their geometry has settled.
        for side,prefix in [('left','L_'),('right','R_')]:
            f=config['frames'][side];apply_finish(doc,doc.getObject(prefix+'ActiveFrame').LinkedObject,side,f['color'],f['accents'])
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction();raise
    return clearance

def extract(doc):
    result={'schema':'flan36-config-1','revision':'I','keycaps':{},'frames':{},'batteries':{},'cases':{}}
    for side,prefix in [('left','L_'),('right','R_')]:
        hexcolor=lambda o:'#'+''.join(f'{round(v*255):02x}' for v in o.ViewObject.ShapeColor[:3])
        result['cases'][side]={'style':doc.getObject(prefix+'ActiveTray').LinkedObject.CaseStyle,'cover':doc.getObject(prefix+'Half').DisplayCoverInstalled,'base_color':hexcolor(doc.getObject(prefix+'ActiveTray').LinkedObject),'plate_color':hexcolor(doc.getObject(prefix+'ActivePlate').LinkedObject),'match_frame':getattr(doc.getObject(prefix+'Half'),'MatchFrameColor',False)}
        result['batteries'][side]=doc.getObject(prefix+'ActiveBattery').LinkedObject.BatteryStyle
        result['keycaps'][side]={o.KeyReference:{'variant':o.KeycapVariant,'rotation_deg':int(round(o.CapRotation.Value))%360,'color':hexcolor(o)} for o in doc.Objects if hasattr(o,'KeyReference') and o.Side==side}
        cover=doc.getObject(prefix+'ActiveFrame').LinkedObject
        color='#'+''.join(f'{round(v*255):02x}' for v in cover.ViewObject.ShapeColor[:3])
        result['frames'][side]={'style':cover.FrameStyle,'color':color,'accents':{k:v for k,v in palette(cover.FrameStyle,color,json.loads(getattr(cover,'PaletteAccents','{}'))).items() if k!='body'}}
    errors,_=check(result)
    if errors:raise ValueError('\n'.join(errors))
    return result
