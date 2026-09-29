#!/usr/bin/env python3
"""Current collection: six selected designs and one Evangelion proposal.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib, html, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'design/proposals/frame-redesign-r8'
OUT=ROOT/'docs/frame-proposals'

def run(css):
    master=json.loads((SOURCE/'master.json').read_text())
    check=json.loads((SOURCE/'geometry-check.json').read_text())
    digest=hashlib.sha256((SOURCE/'master.json').read_bytes()).hexdigest()
    assert check['master_sha256']==digest and check['saved_reopened']
    dest=OUT/'r8';dest.mkdir(parents=True,exist_ok=True)
    assets=['evangelion.png','native-review.png','native-top.png']+[k+ext for k in master['styles'] for ext in ['-preview.svg','-card.png','-dimensioned.png','.svg']]
    for name in assets:shutil.copy2(SOURCE/name,dest/name)
    base='https://github.com/eduarbo/flan36/blob/main/design/proposals/frame-redesign-r8/'
    def palette(s):
        return '<div class="palette">'+''.join(f'<span><i style="background:{c}"></i><code>{c}</code></span>' for c in s['palette'].values())+'</div>'
    def preview(key):
        label=html.escape(master['styles'][key]['label'])
        return f'<a class="preview" href="r8/{key}-card.png" aria-label="Enlarge {label}"><img src="r8/{key}-preview.svg" width="240" height="560" alt="{label}, exact frame artwork" loading="lazy"></a>'
    def links(key):
        return f'<nav aria-label="{html.escape(master["styles"][key]["label"])} files"><a href="r8/{key}-dimensioned.png">Dimensions</a><a href="r8/{key}.svg" download>1:1 SVG ↓</a></nav>'
    cards=''
    for key in master['decisions']['retained']:
        s=master['styles'][key]
        state='In the current assembly' if s.get('integration')=='INSTALLED' else 'Selected · integration pending'
        cards+=f'<article id="{key}" data-state="selected">{preview(key)}<div class="status">{state}</div><h2>{html.escape(s["label"])}</h2>{palette(s)}{links(key)}</article>'
    s=master['styles']['evangelion']
    extra='.proposal{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,1.2fr);gap:36px;align-items:center;background:#eee9f4;border-radius:20px;padding:32px}.proposal .preview{height:540px;margin:0}.proposal .palette{max-width:430px}.proposal h2{font-size:32px}.proposal .status{color:#64517e}.native{max-width:700px;display:block;margin:20px auto}.retained{margin-top:52px}.retained>p{max-width:780px;margin-bottom:24px}@media(max-width:650px){.proposal{grid-template-columns:1fr;padding:24px;gap:24px}.proposal .preview{height:460px}.proposal h2{font-size:28px}}'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Selected frames + Evangelion · Flan36</title><style>{css}{extra}</style></head><body><main>
<a class="back" href="../">← 3D explorer</a><header><div class="status">R8 · six selected designs · one new proposal</div><h1>Your frame collection.</h1><p>The approved designs stay. One new Evangelion direction uses the purple and lime palette you liked in M1.</p></header>
<section class="proposal" id="evangelion" data-state="proposed">{preview('evangelion')}<div><div class="status">E1 · awaiting your approval</div><h2>Evangelion / Unit 01</h2><p>{html.escape(s['note'])}</p>{palette(s)}{links('evangelion')}<nav><a href="r8/native-review.png">3D close-up</a><a href="{base}Artwork-R8.FCStd">FreeCAD review</a></nav><p class="small">24 × 56 mm. Solid colors. Flush inlays. This artwork is a proposal; approval comes before installation in the keyboard.</p></div></section>
<section class="retained" aria-labelledby="selected"><h2 id="selected">The selected designs</h2><p>Talavera, Game Boy, SNES, Phone, iPod and Hanafuda retain their exact paths and palettes. All six Mecha and Kumiko candidates from R7 were rejected and are excluded from this selection.</p><div class="grid">{cards}</div></section>
<section class="notes"><h2>Exact artwork, editable geometry.</h2><p>The drawing and the native review use the same millimetre paths and HEX colors. The frame face stays at Z13.59 mm, with a uniform 2.40 mm screen bezel and the current 13.90 × 30.50 mm opening.</p><nav><a href="{base}master.json">Dimensions &amp; HEX source</a><a href="r8/native-top.png">Native top view</a><a href="{base}geometry-check.json">Geometry checks</a></nav><details><summary>Printing and reference</summary><p>The design targets a 0.4 mm nozzle and 0.2 mm layers. Features, bonding and physical fit still need slicing and a sample print. No decoration rises above the frame face. The LCD content in the flat preview is illustrative.</p><p>Original fan-art interpretation of <a href="https://www.goodsmile.com/en/product/59101/MODEROID%2BEvangelion%2BUnit-01">Evangelion Unit-01</a>. The M1 palette is preserved exactly; no commercial image or logo was traced.</p><p>This page records artwork selection. Hanafuda still awaits production integration. The main keyboard assembly and explorer remain unchanged in this proposal round.</p></details><p class="hash">Master SHA256: {digest}</p></section>
</main></body></html>'''
    (OUT/'index.html').write_text(page)
    print('Built R8 gallery: six selected designs and one Evangelion proposal')
