#!/usr/bin/env python3
"""Register the already-selected R8 Hanafuda paths; never regenerate artwork.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    source='design/proposals/frame-redesign-r8/master.json';path=ROOT/source
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest=='291e9fb40634246b8a4f0733fed7e240ec94295adab2540a9e5445ea9057555e'
    art=json.loads(path.read_text())['styles']['hanafuda'];assert art['decision']=='SELECTED'
    def read(p):return json.loads((ROOT/p).read_text())
    def write(p,d):(ROOT/p).write_text(json.dumps(d,indent=2)+'\n')
    spec=read('design/frame-finishes.json')
    spec['styles']['hanafuda']={'label':'Hanafuda','description':art['note'],'colors':art['palette'],
        'labels':{'body':'Ivory card','detail':'Ink','accent':'Vermilion sun','secondary':'Pine green'},
        'features':[],'approved_master':'R4','approval_status':'approved','artwork_source':source,
        'artwork_source_sha256':digest,'construction':'Approved R8 paths and painter order; native roof-relative material partitions.'}
    write('design/frame-finishes.json',spec)
    catalog=read('keycaps/catalog.json');catalog['frame_styles']['hanafuda']='Hanafuda';write('keycaps/catalog.json',catalog)
    selection=read('design/frame-selection.json');assert 'hanafuda' in selection['selected']
    selection['viewer']['installed_styles']=list(selection['selected'])
    selection['integration']='All six selected designs installed from their approved paths; physical fit remains unqualified.'
    write('design/frame-selection.json',selection)
    from viewer_frame_selection import selected_catalog
    current=selected_catalog(catalog,spec,selection)['default_configuration']
    def canonical(value):
        if isinstance(value,dict):return {k:canonical(v) for k,v in value.items()}
        if isinstance(value,list):return [canonical(v) for v in value]
        return value.lower() if isinstance(value,str) and value.startswith('#') else value
    current=canonical(current)
    catalog['default_configuration']=current;write('keycaps/catalog.json',catalog)
    write('design/configurations/default.json',current)
    print('Registered exact approved Hanafuda artwork and aligned native/viewer Talavera default')
if __name__=='__main__':main()
