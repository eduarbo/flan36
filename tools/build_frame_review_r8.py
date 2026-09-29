#!/usr/bin/env python3
"""Current collection: only the six selected designs.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib, html, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'design/proposals/frame-redesign-r8'
OUT=ROOT/'docs/frame-proposals'

def run(css):
    selection=json.loads((ROOT/'design/frame-selection.json').read_text())
    master=json.loads((SOURCE/'master.json').read_text())
    check=json.loads((SOURCE/'geometry-check.json').read_text())
    digest=hashlib.sha256((SOURCE/'master.json').read_bytes()).hexdigest()
    assert check['master_sha256']==digest==selection['preview_master_sha256'] and check['saved_reopened']
    assert selection['status']=='APPROVED_ONLY' and not selection['pending_proposals']
    keys=selection['selected']
    assert all(master['styles'][key]['decision']=='SELECTED' for key in keys)
    dest=OUT/'r8';dest.mkdir(parents=True,exist_ok=True)
    assets=[k+ext for k in keys for ext in ['-preview.svg','-card.png','-dimensioned.png','.svg']]
    for name in assets:shutil.copy2(SOURCE/name,dest/name)
    # Only the explicitly rejected public previews are retired. Historical source stays intact.
    for name in ['evangelion.png','evangelion-card.png','evangelion-dimensioned.png','evangelion-preview.svg','evangelion.svg','native-review.png','native-top.png']:
        (dest/name).unlink(missing_ok=True)
    base='https://github.com/eduarbo/flan36/blob/main/design/'
    def palette(s):
        return '<div class="palette">'+''.join(f'<span><i style="background:{c}"></i><code>{c}</code></span>' for c in s['palette'].values())+'</div>'
    def preview(key):
        label=html.escape(master['styles'][key]['label'])
        return f'<a class="preview" href="r8/{key}-card.png" aria-label="Enlarge {label}"><img src="r8/{key}-preview.svg" width="240" height="560" alt="{label}, exact frame artwork" loading="lazy"></a>'
    def links(key):
        return f'<nav aria-label="{html.escape(master["styles"][key]["label"])} files"><a href="r8/{key}-dimensioned.png">Dimensions</a><a href="r8/{key}.svg" download>1:1 SVG ↓</a></nav>'
    cards=''
    for key in keys:
        s=master['styles'][key]
        state='In the current assembly' if s.get('integration')=='INSTALLED' else 'Selected · integration pending'
        cards+=f'<article id="{key}" data-state="selected">{preview(key)}<div class="status">{state}</div><h2>{html.escape(s["label"])}</h2>{palette(s)}{links(key)}</article>'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Selected frames · Flan36</title><style>{css}</style></head><body><main>
<a class="back" href="../">← 3D explorer</a><header><div class="status">Six selected designs</div><h1>Your frame collection.</h1><p>Talavera, Game Boy, SNES, Phone, iPod and Hanafuda. The approved artwork and palettes stay exactly as selected.</p></header>
<section aria-label="Selected designs"><div class="grid">{cards}</div></section>
<section class="notes"><h2>Exact artwork, editable geometry.</h2><p>The previews use the approved millimetre paths and HEX colors. The frame face stays at Z13.59 mm, with a uniform 2.40 mm screen bezel and the current 13.90 × 30.50 mm opening.</p><nav><a href="{base}frame-selection.json">Selection record</a></nav><details><summary>Printing and integration</summary><p>The design targets a 0.4 mm nozzle and 0.2 mm layers. Features, bonding and physical fit still need slicing and a sample print. No decoration rises above the frame face. The LCD content in the previews is illustrative.</p><p>Hanafuda still awaits production integration. The main keyboard assembly and explorer remain unchanged by this selection update.</p></details></section>
</main></body></html>'''
    (OUT/'index.html').write_text(page)
    print('Built gallery: six selected designs, no pending proposals')
