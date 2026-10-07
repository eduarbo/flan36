"""Verify current source receipts, local documentation targets and BOM URLs.
Network checks only read public URLs; no downloads are redistributed.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import base64
import concurrent.futures
import gzip
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/audit-20261007'
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(url):
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Flan36 documentation audit'}, method='HEAD')
        with urllib.request.urlopen(request, timeout=25) as response:
            return {'url': url, 'status': response.status, 'resolved_url': response.url}
    except Exception as error:
        return {'url': url, 'error': str(error)}


html = (ROOT / 'docs/index.html').read_text()
packed = re.search(r'<script id="scene-data" type="application/octet-stream">(.*?)</script>', html, re.S)[1]
scene = json.loads(gzip.decompress(base64.b64decode(packed)))
(OUT / 'runtime-catalog.json').write_text(json.dumps(scene['catalog']))
receipt = json.loads((ROOT / 'validation/revI-viewer.json').read_text())
stale = [x['path'] for x in receipt['sources'] if sha(ROOT / x['path']) != x['sha256']]
local_missing = []
documents = [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md')), ROOT / 'components/README.md']
for doc in documents:
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        target = target.strip('<>')
        if ':' in target or target.startswith('#'):
            continue
        path = urllib.parse.unquote(target.split('#')[0])
        if path and not (doc.parent / path).exists():
            local_missing.append({'document': str(doc.relative_to(ROOT)), 'target': target})
urls = sorted(set(re.findall(r'https://[^\s)"<>]+', (ROOT / 'docs/parts.md').read_text())))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    links = list(pool.map(link, urls))
render = json.loads((ROOT / 'validation/revI-render.json').read_text())
manifest = json.loads((ROOT / 'sources/manifest.json').read_text())
pinned = dict(manifest['files'])
pinned.update({k: v['sha256'] for k, v in manifest['license_sources'].items()})
for file, key in [('components/sources.json', 'assets'), ('keycaps/variants-source.json', 'files')]:
    pinned.update({v['path']: v['sha256'] for v in json.loads((ROOT / file).read_text())[key]})
render_stale = [v['path'] for v in render['meshes'] if sha(ROOT / v['path']) != v['sha256']]
report = {'viewer_source_count': len(receipt['sources']), 'stale_viewer_sources': stale,
          'online_matches_receipt': sha(ROOT / 'docs/index.html') == receipt['viewer_sha256'],
          'offline_matches_receipt': sha(ROOT / 'docs/offline.html') == receipt['offline_sha256'],
          'local_documents_checked': len(documents), 'local_missing_targets': local_missing,
          'bom_links': links, 'active_frames': scene['catalog']['frame_styles'],
          'native_catalog_frames': json.loads((ROOT / 'keycaps/catalog.json').read_text())['frame_styles'],
          'render_metadata_matches': sha(ROOT / 'design/revI.json') == render['model_sha256'],
          'stale_render_meshes': render_stale,
          'pinned_source_count': len(pinned), 'modified_pinned_sources': [p for p, h in pinned.items() if sha(ROOT / p) != h],
          'physical_acceptance': False}
(OUT / 'assets.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'bom_links'}, indent=2))
print('BOM links:', len(links), 'unresolved HEAD responses:', sum('error' in x for x in links))
