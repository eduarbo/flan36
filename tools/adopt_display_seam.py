#!/usr/bin/env python3
"""Adopt only validated seam-dependent exports; preserve all other source files.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import collections,hashlib,json,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def facets(path):
    raw=path.read_bytes();n=struct.unpack_from('<I',raw,80)[0];assert len(raw)==84+50*n
    return collections.Counter(raw[i:i+50] for i in range(84,len(raw),50))
def run():
    source=Path(sys.argv[1]).resolve();target=ROOT/'mechanical/revI'
    install=read(source/'installation.json');meta=read(source/'revI.json');mechanical=read(source/'mechanical.json');geometry=read(source/'geometry.json')
    assert all(install[k] for k in ['saved_reopened_recomputed','configuration_unchanged','cap_geometry_unchanged','excluded_artwork_xy_unchanged','unrelated_parts_unchanged'])
    assert install['source_sha256']==sha(target/'Flan36.FCStd')
    assert install['output_sha256']==meta['fcstd_sha256']==mechanical['source_sha256']==geometry['source_sha256']==sha(source/'Flan36.FCStd')
    assert geometry['passed'] and len(geometry['frames'])==len(install['frames'])==len(meta['frameVariants'])==22
    assert all(not h['collisions'] for h in mechanical['halves'].values())
    assert all(sha(ROOT/i['path'])==i['sha256'] for i in meta['inputs'])
    def allowed(name):
        if name=='Flan36.FCStd':return True
        return any(name.startswith(s+'-frame-') or name in [s+'-electronics-lid.stl',s+'-electronics-lid.step',s+'-assembly.step'] for s in ['left','right'])
    preserved=[]
    for p in source.glob('*.stl'):
        if not allowed(p.name):
            assert (target/p.name).is_file() and facets(p)==facets(target/p.name),('Unexpected unrelated mesh change',p.name)
            preserved.append(p.name)
    # Check the final file set before writing any production artifact. Equivalent
    # facets alone do not authorize relabeling preserved bytes with a new hash.
    def final_path(name):return (source if allowed(name) else target)/name
    for name,part in meta['parts'].items():
        assert sha(final_path(name+'.stl'))==part['stl_sha256'],('Part hash mismatch before adoption',name)
    for variant in meta['frameVariants'].values():
        for part in variant['material_parts']:
            for kind in ['stl','step']:
                assert sha(final_path(part[kind]))==part[kind+'_sha256'],('Material hash mismatch before adoption',part[kind])
    adopted=[]
    for p in sorted(source.iterdir()):
        if p.suffix not in ['.stl','.step','.FCStd'] or not allowed(p.name):continue
        if not (target/p.name).exists() or sha(p)!=sha(target/p.name):shutil.copy2(p,target/p.name);adopted.append(p.name)
    for src,dst in [('revI.json','design/revI.json'),('mechanical.json','validation/revI-mechanical.json'),('installation.json','validation/revI-display-seam-native.json'),('geometry.json','validation/revI-display-seam-geometry.json')]:shutil.copy2(source/src,ROOT/dst)
    for name,part in meta['parts'].items():assert sha(target/(name+'.stl'))==part['stl_sha256']
    for variant in meta['frameVariants'].values():
        for part in variant['material_parts']:
            assert sha(target/part['stl'])==part['stl_sha256'] and sha(target/part['step'])==part['step_sha256']
    report={'source_sha256':install['source_sha256'],'native_sha256':meta['fcstd_sha256'],'adopted_files':adopted,'unchanged_meshes':preserved}
    (ROOT/'validation/revI-display-seam-adoption.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Adopted',len(adopted),'seam-dependent exports; preserved',len(preserved),'unrelated meshes')
if __name__=='__main__':run()
