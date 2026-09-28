#!/usr/bin/env python3
"""Anonymous archive and Pages readback for an already published commit.
Does not publish, create releases or change remote state.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import hashlib,json,subprocess,sys,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'build/revI';out.mkdir(parents=True,exist_ok=True)
commit=sys.argv[1] if len(sys.argv)>1 else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
url='https://codeload.github.com/eduarbo/flan36/zip/'+commit
path=out/'public-source.zip'
with urllib.request.urlopen(url,timeout=60) as remote,path.open('wb') as local:
    while data:=remote.read(1048576):local.write(data)
expected={}
for entry in subprocess.check_output(['git','ls-tree','-rz',commit],cwd=ROOT).split(b'\0'):
    if not entry:continue
    meta,name=entry.split(b'\t',1);mode,kind,digest=meta.split();assert kind==b'blob'
    expected[name.decode()]=digest.decode()
with zipfile.ZipFile(path) as archive:
    prefix=archive.namelist()[0].split('/')[0]+'/'
    actual={n[len(prefix):] for n in archive.namelist() if not n.endswith('/')}
    assert actual==set(expected),'Archive file set differs from committed source'
    for name,digest in expected.items():
        raw=archive.read(prefix+name)
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==digest,name
print('Anonymous archive verified:',len(expected),'files',flush=True)
pageurl='https://eduarbo.github.io/flan36/'
html=urllib.request.urlopen(pageurl+'?rev='+commit,timeout=60).read()
assert hashlib.sha1(b'blob '+str(len(html)).encode()+b'\0'+html).hexdigest()==expected['docs/index.html'],'Pages is not yet the published source revision'
extra={}
viewer_receipt=json.loads(subprocess.check_output(['git','show',commit+':validation/revI-viewer.json'],cwd=ROOT))
for name in ['docs/offline.html',viewer_receipt['printing']['path']]:
    raw=urllib.request.urlopen(pageurl+name.removeprefix('docs/')+'?rev='+commit,timeout=60).read()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected[name],name
    extra[name]=hashlib.sha256(raw).hexdigest()
report={'additional_published_assets':extra,'source_commit':commit,'archive_files_verified':len(expected),'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages_url':pageurl,'pages_matches_committed_html':True,'viewer_sha256':hashlib.sha256(html).hexdigest(),'authenticated_requests':False,'method':'All archive entries matched against Git blob IDs; public Pages bytes matched the committed viewer.'}
(out/'public-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
