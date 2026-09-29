#!/usr/bin/env python3
"""Verify the current gallery and native approval source against committed bytes.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,concurrent.futures,datetime,hashlib,json,subprocess,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(commit,revision='R7'):
    commit=subprocess.check_output(['git','rev-parse',commit],cwd=ROOT,text=True).strip()
    folder='frame-redesign-'+revision.lower();namespace='docs/frame-proposals'+('/r7' if revision=='R7' else '')
    tree=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--',namespace],cwd=ROOT,text=True).splitlines()
    paths=[p for p in tree if not p.endswith('seam-comparison.png')]
    if 'docs/frame-proposals/index.html' not in paths:paths.insert(0,'docs/frame-proposals/index.html')
    paths+=['design/proposals/'+folder+'/'+p for p in ['master.json','Artwork-'+revision+'.FCStd','geometry-check.json']]
    def check(path):
        expected=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
        if path.startswith('docs/'):
            url='https://eduarbo.github.io/flan36/'+path.removeprefix('docs/')+'?rev='+commit
        else:url='https://raw.githubusercontent.com/eduarbo/flan36/'+commit+'/'+path
        request=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'Flan36-public-readback'})
        with urllib.request.urlopen(request,timeout=45) as response:actual=response.read();status=response.status
        digest=lambda b:hashlib.sha256(b).hexdigest()
        assert status==200 and digest(actual)==digest(expected),(path,'public bytes differ')
        return {'path':path,'url':url,'bytes':len(actual),'sha256':digest(actual),'matches_commit':True}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:assets=list(pool.map(check,paths))
    result={'schema_version':1,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':commit,
        'gallery_url':'https://eduarbo.github.io/flan36/frame-proposals/?rev='+commit,
        'checked_assets':len(assets),'assets':assets,'artwork_status':('HANAFUDA_SELECTED_MECHA_AND_KUMIKO_PENDING' if revision=='R7' else 'PROPOSALS_AWAITING_USER_APPROVAL'),'physical_acceptance':False}
    out=ROOT/('validation/revI-'+folder+'-public.json');out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:',len(assets),'public gallery/source files match',commit)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',default='HEAD');p.add_argument('--revision',choices=['R6','R7'],default='R7');a=p.parse_args();verify(a.commit,a.revision)
