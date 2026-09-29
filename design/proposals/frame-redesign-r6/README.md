# R6 — six new directions

**Proposed, not approved.** This revision responds to the rejection of R5 and the request to reinvent its six designs. It replaces the proposed art direction, not the installed frame artwork.

| Proposed design | Deferred slot | Reference |
| --- | --- | --- |
| Caramelo | Flan | Caramel glaze and the existing outline logo |
| Lucha | Tape | Mexican wrestling mask |
| Hanafuda | Orbit | Japanese card landscape, sun and mountain |
| Mecha | Manga | Original robot faceplate |
| Cartucho 8 | NES | Retro game cartridge |
| Terminal | Walkman | Compact terminal and return key |

The 24 × 56 mm blank, 13.90 × 30.50 mm display opening, 0.10 mm nominal glass clearance, 2.40 mm screen bezel and Z13.59 mm face remain fixed. No stack, mounting, assembly, theme or main viewer change is included.

`master.json` owns literal millimetre paths, painter order and HEX colors. The 1:1 SVGs, dimensioned sheets and `Artwork-R6.FCStd` use those exact paths. Each material is a complementary volume with a flush top face. The FreeCAD document arranges six named groups in a grid; each has hidden planar sources and visible review solids. `geometry-check.json` records exact source-to-solid agreement, clipping, save/reopen and display clearance. Native images use actual review meshes. LCD text in flat previews is illustrative.

Approval fixes these shapes and palettes. These files are not a print release: 0.4 mm nozzle / 0.2 mm layers remain a target, with thin tips, bonding, toolpaths and physical fit unqualified.

Reproduce from the repository root:

```sh
python3 tools/prepare_frame_redesign_r6.py
python3 tools/render_frame_artwork.py design/proposals/frame-redesign-r6
python3 tools/freecad/run_macos.py tools/freecad/prepare_frame_artwork_review.py
python3 tools/render_frame_artwork_review.py
python3 tools/build_frame_review_page.py
```

SVG rasterization needs `rsvg-convert`; FreeCAD supplies its own Python; native image rendering needs VTK. The ignored `build/frame-redesign-r6/geometry/` meshes are reproducible from the committed source using the commands above. Validate regeneration through the geometry receipt, the master binding and visual comparison of the images. Proposal derivation requires the production source hash recorded in `master.json`.
