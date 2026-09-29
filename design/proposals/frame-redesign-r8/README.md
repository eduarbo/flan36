# R8 — selected frames + Evangelion

Six selected designs retain their exact paths and palettes: Talavera, Game Boy, SNES, Phone, iPod and Hanafuda. The six R7 Mecha/Kumiko candidates were rejected. **E1 / Evangelion Unit 01 is the only new proposal**, retaining M1's exact four-color palette.

`master.json` owns the millimetre paths, HEX values and painter order. SVGs, dimensioned sheets and `Artwork-R8.FCStd` use that same source. The native document contains the seven designs as named, independently visible groups. The E1 top and oblique renders come from actual review meshes.

The existing mechanical blank remains 24 × 56 mm, with a 13.90 × 30.50 mm aperture, 0.10 mm nominal glass clearance, 2.40 mm bezel and Z13.59 mm face. All details are flat color inlays. This is approval geometry, not a print release: slicing, bonding and physical fit are unqualified. No production assembly or main-viewer change is included. Hanafuda integration follows separately; the other five selected designs are already installed.

The reference link is recorded in the master. The Evangelion motif is an original geometric fan-art interpretation; it is not traced commercial artwork or an official collaboration.

## Reproduce

```sh
python3 tools/prepare_frame_redesign_r8.py
python3 tools/render_frame_artwork.py design/proposals/frame-redesign-r8
FLAN36_ARTWORK_REVIEW=frame-redesign-r8 python3 tools/freecad/run_macos.py tools/freecad/prepare_frame_artwork_review.py
FLAN36_ARTWORK_REVIEW=frame-redesign-r8 python3 tools/render_frame_artwork_review.py
python3 tools/build_frame_review_page.py
```

SVG rasterization uses `rsvg-convert`; FreeCAD supplies its runtime; the native renderer uses VTK. Ignored meshes in `build/frame-redesign-r8/geometry/` are reproducible from these commands. Validate exact source hashes, closed geometry, top-face equivalence and saved/reopened native state using `geometry-check.json`, `render-check.json` and `review-check.json`.

After publication: `python3 tools/check_frame_review_public.py --revision R8 --commit <published-commit>` verifies every current public gallery/source file against committed bytes.
