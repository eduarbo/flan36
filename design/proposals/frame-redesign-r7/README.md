# R7 — Hanafuda retained, Mecha and Kumiko alternatives

Hanafuda's R6 paths and palette are retained exactly following the user's selection. **M1–M3 and K1–K3 are proposals, not approved artwork.** Caramelo, Lucha, Cartucho 8 and Terminal were rejected; the old Mecha was rejected for redesign. Their historical files remain in R6, not in the active selection.

| Code | Direction | Family |
| --- | --- | --- |
| H | Hanafuda — selected, unchanged | Retained |
| M1 | Recon — purple scout armor | Mecha |
| M2 | Reactor — pale armor and cyan core | Mecha |
| M3 | Hangar — industrial service hatch | Mecha |
| K1 | Asanoha — radial leaf lattice | Kumiko |
| K2 | Kikko — hexagonal lattice | Kumiko |
| K3 | Kasane — original diagonal lattice | Kumiko |

`master.json` owns millimetre coordinates, solid HEX palettes and painter order. The 1:1 SVGs, dimensioned sheets and `Artwork-R7.FCStd` use these exact paths. Review solids are material partitions of the existing blank: 24 × 56 mm, 13.90 × 30.50 mm opening, 0.10 mm nominal glass clearance, 2.40 mm bezel, face at Z13.59 mm. No mounting, stack, PCB or production viewer change is included.

The native review arranges the six candidates in two rows and selected Hanafuda below. Toggle named groups or material solids to inspect them. `geometry-check.json` validates closed solids, no overlaps or clipping, exact top surfaces and save/reopen. Kumiko strips have 0.80–0.85 mm nominal widths; this is a colored-inlay interpretation, not functional wooden joinery. Slicing and physical fit remain unqualified.

Pattern references are recorded in the master. The geometry is original, not traced from commercial work. Kasane is the name of this original diagonal composition, not a claim that it is a historical pattern.

Reproduce from the repository root:

```sh
python3 tools/prepare_frame_redesign_r7.py
python3 tools/render_frame_artwork.py design/proposals/frame-redesign-r7
FLAN36_ARTWORK_REVIEW=frame-redesign-r7 python3 tools/freecad/run_macos.py tools/freecad/prepare_frame_artwork_review.py
FLAN36_ARTWORK_REVIEW=frame-redesign-r7 python3 tools/render_frame_artwork_review.py
python3 tools/build_frame_review_page.py
```

SVG rasterization needs `rsvg-convert`, FreeCAD supplies its runtime, and native rendering needs VTK. Ignored review meshes under `build/frame-redesign-r7/geometry/` are reproduced by these commands. Validate with the geometry receipt, master hashes and visual comparison. After publication, run `python3 tools/check_frame_review_public.py --revision R7 --commit <published-commit>` for exact public readback.
