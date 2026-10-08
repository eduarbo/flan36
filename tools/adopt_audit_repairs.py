#!/usr/bin/env python3
"""Adopt only verified audit-related CAD exports and preserve unrelated mesh bytes.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import collections,hashlib,json,math,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
ACTIVE={'talavera','gameboy','snes','phone','ipod','hanafuda'}
RETIRED_RECTANGLE_FILES={f'{side}-frame-{style}{suffix}.stl'
                       for side in ['left','right']
                       for style in ['flan','tape','orbit','manga','nes','walkman']
                       for suffix in ['', '-body']}
def mesh_signature(path):
    data=path.read_bytes();count=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*count,path
    result=collections.Counter()
    for start in range(84,len(data),50):
        v=struct.unpack_from('<9f',data,start+12)
        # Cyclic order is irrelevant; winding is retained and normals derive from it.
        xyz=[tuple(round(x,4) for x in v[i:i+3]) for i in (0,3,6)]
        result[min(tuple(xyz[i:]+xyz[:i]) for i in range(3))]+=1
    return result

def raw_triangles(path):
    """Retain the exact binary STL float32 coordinates and oriented winding."""
    data=path.read_bytes();count=struct.unpack_from('<I',data,80)[0]
    assert len(data)==84+50*count,path
    result=collections.Counter()
    for start in range(84,len(data),50):
        values=struct.unpack_from('<9f',data,start+12)
        assert all(math.isfinite(value) for value in values),('Nonfinite mesh vertex',path)
        points=[tuple(values[i:i+3]) for i in (0,3,6)]
        result[min(tuple(points[i:]+points[:i]) for i in range(3))]+=1
    return result

def vertical_rectangles(triangles):
    """Prove each unmatched pair tiles one vertical rectangle exactly once."""
    grouped=collections.defaultdict(list)
    for triangle,count in triangles.items():
        assert count==1 and len(set(triangle))==3,'Duplicate or degenerate unmatched triangle'
        xy=tuple(sorted({point[:2] for point in triangle}));z=tuple(sorted({point[2] for point in triangle}))
        assert len(xy)==2 and len(z)==2,'Unmatched face is not a vertical rectangle triangle'
        grouped[(xy,z)].append(triangle)
    rectangles={}
    for key,pair in grouped.items():
        assert len(pair)==2,'Rectangle must have exactly two triangles'
        first,second=pair;xy,z=key
        corners={(x,y,height) for x,y in xy for height in z}
        assert set(first)|set(second)==corners,'Rectangle corners do not match'
        shared=set(first)&set(second)
        assert len(shared)==2,'Rectangle triangles must share one diagonal'
        a,b=sorted(shared)
        assert a[:2]!=b[:2] and a[2]!=b[2],'Shared edge is not the rectangle diagonal'
        edges=collections.Counter((triangle[i],triangle[(i+1)%3])
                                  for triangle in pair for i in range(3))
        assert edges[(a,b)]==edges[(b,a)]==1,'Internal diagonal winding differs'
        del edges[(a,b)];del edges[(b,a)]
        assert len(edges)==4 and set(edges.values())=={1},'Overlapping rectangle faces'
        following={start:end for start,end in edges}
        assert len(following)==4 and len(set(following.values()))==4,'Broken oriented rectangle boundary'
        boundary=[min(corners)]
        for _ in range(3):boundary.append(following[boundary[-1]])
        assert len(set(boundary))==4 and following[boundary[-1]]==boundary[0],'Open rectangle boundary'
        rectangles[key]=(tuple(boundary),tuple(sorted(shared)))
    return rectangles

def rectangle_retriangulation(old,new):
    """Only opposite diagonals of identical raw, oriented rectangles may differ."""
    before,after=raw_triangles(old),raw_triangles(new)
    common=before&after
    left,right=vertical_rectangles(before-common),vertical_rectangles(after-common)
    assert left and left.keys()==right.keys(),'Rectangle inventories differ'
    for key,(boundary,diagonal) in left.items():
        assert boundary==right[key][0],'Oriented rectangle boundaries differ'
        assert diagonal!=right[key][1],'Retriangulation must use the opposite diagonal'
    return {'method':'raw_float32_vertical_rectangle_opposite_diagonal',
            'rectangles':len(left),'changed_triangles_per_mesh':2*len(left),
            'identical_raw_triangles':sum(common.values()),'coordinate_rounding':False,
            'preserved_sha256':sha(old),'candidate_sha256':sha(new)}

def run():
    source=Path(sys.argv[1]).resolve();target=ROOT/'mechanical/revI'
    meta=read(source/'revI.json');mechanical=read(source/'mechanical.json');delivery=read(source/'delivery.json');parameters=read(source/'parameter-checks.json');hotswap=read(source/'hotswap.json');relief=read(source/'relief.json');configuration=read(source/'freecad.json')
    digest=sha(source/'Flan36.FCStd')
    assert digest==meta['fcstd_sha256']==mechanical['source_sha256']==delivery['source_sha256']==parameters['source_sha256']==hotswap['source_sha256']==relief['source_sha256']==configuration['source_sha256']
    assert all(x['passed'] for x in [delivery,parameters,hotswap,relief])
    assert configuration['reopened_customized_file']
    assert all(h['socket_to_relieved_post_mm']>=.25-1e-7 and h['minimum_pilot_web_mm']>=1.20 for h in relief['halves'].values())
    assert relief['unrelated_parts_geometrically_unchanged']
    assert delivery['baseline_sha256']==sha(target/'Flan36.FCStd')
    assert all(not h['collisions'] for h in mechanical['halves'].values())
    assert all(sha(ROOT/i['path'])==i['sha256'] for i in meta['inputs'])
    # Reject post-export changes before rewriting hashes for byte-preserved meshes.
    manifest=mechanical['exported_files'];assert manifest
    for name,digest_expected in manifest.items():assert sha(source/name)==digest_expected,('Changed after export',name)
    for visual in meta['hotswap_model']['visuals']:assert sha(source/Path(visual['path']).name)==visual['sha256']
    for name,part in meta['parts'].items():assert sha(source/(name+'.stl'))==part['stl_sha256']
    for variant in meta['frameVariants'].values():
        for part in variant['material_parts']:
            for ext in ['stl','step']:assert sha(source/part[ext])==part[ext+'_sha256']
    for entries in meta['batteryLeadProfiles'].values():
        for item in entries:assert sha(source/item['stl'])==item['stl_sha256']
    def allowed(name):
        if name=='Flan36.FCStd' or name in ['component-hotswap-0.stl','component-hotswap-1.stl']:return True
        for side in ['left','right']:
            if name in [side+'-assembly.step',side+'-tray.stl',side+'-tray.step',side+'-electronics-lid.stl',side+'-electronics-lid.step']:return True
            if name.startswith(side+'-diodes') or name.startswith(side+'-hotswap-sockets'):return True
            if any(name in [f'{side}-case-{c}-base.stl',f'{side}-case-{c}-base.step'] for c in ['solid','rim','terrace','level']):return True
            if any(name.startswith(side+'-frame-'+s+'.') or name.startswith(side+'-frame-'+s+'-') for s in ACTIVE):return True
        return False
    expected_files={'Flan36.FCStd':digest,**manifest,**{Path(v['path']).name:v['sha256'] for v in meta['hotswap_model']['visuals']}}
    candidates=[p for p in sorted(source.iterdir()) if p.suffix in ['.stl','.step','.FCStd'] and allowed(p.name)]
    for p in candidates:
        assert p.name in expected_files,('Unverified export',p.name)
        assert sha(p)==expected_files[p.name],('Changed before adoption',p.name)
    preserved=[];retriangulated=[]
    for p in source.glob('*.stl'):
        if not allowed(p.name):
            old=target/p.name;assert old.is_file(),('Missing unrelated native mesh',p.name)
            if mesh_signature(old)!=mesh_signature(p):
                assert p.name in RETIRED_RECTANGLE_FILES,('Unrelated native mesh changed',p.name)
                proof=rectangle_retriangulation(old,p)
                retriangulated.append({'file':p.name,**proof})
            preserved.append(p.name)
    def final_path(name):return (source if allowed(name) else target)/name
    # Preserved equivalent meshes retain original serialized bytes and their hash.
    for name,part in meta['parts'].items():
        part['stl_sha256']=sha(final_path(name+'.stl'))
        for v in part['visuals']:assert final_path(Path(v['path']).name).exists()
    for variant in meta['frameVariants'].values():
        for part in variant['material_parts']:
            for ext in ['stl','step']:part[ext+'_sha256']=sha(final_path(part[ext]))
    for entries in meta['batteryLeadProfiles'].values():
        for item in entries:item['stl_sha256']=sha(final_path(item['stl']))
    adopted=[]
    for p in candidates:
        if not (target/p.name).exists() or sha(p)!=sha(target/p.name):shutil.copy2(p,target/p.name);adopted.append(p.name)
    for p in candidates:assert sha(target/p.name)==expected_files[p.name],('Adoption readback failed',p.name)
    (ROOT/'design/revI.json').write_text(json.dumps(meta,indent=2)+'\n')
    for src,dst in [('mechanical.json','revI-mechanical.json'),('delivery.json','revI-audit-delivery.json'),('parameter-checks.json','revI-audit-parameters.json'),('hotswap.json','revI-hotswap-registration.json'),('relief.json','revI-socket-clearance.json'),('freecad.json','revI-freecad.json')]:shutil.copy2(source/src,ROOT/'validation'/dst)
    for name,part in meta['parts'].items():assert sha(target/(name+'.stl'))==part['stl_sha256']
    report={'baseline_sha256':delivery['baseline_sha256'],'native_sha256':digest,'adopter_sha256':sha(__file__),'adopted_files':adopted,'preserved_meshes':preserved,'unchanged_mesh_comparison_precision_mm':.0001,'preserved_rectangle_retriangulations':retriangulated,'passed':True,'physical_acceptance':False}
    (ROOT/'validation/revI-audit-adoption.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Adopted',len(adopted),'audit-related files; preserved',len(preserved),'unrelated meshes')
if __name__=='__main__':run()
