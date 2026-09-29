# Display seam correction

The R4 opening was 14.50 mm wide while the modeled PCB is 14.00 mm wide. Each side exposed a 0.25 mm band beyond the PCB. The approval drawing incorrectly painted the whole opening dark, hiding that geometry. Its north/south glass gaps were also unequal: 0.30 / 0.50 mm.

The seam-only correction uses local aperture **[5.05, 7.55, 18.95, 38.05] mm**: 13.90 × 30.50 mm, centered on the existing glass, with 0.10 mm nominal clearance. The five approved ScreenField paths use an exact 2.40 mm outward offset, bounds **[2.65, 5.15, 21.35, 40.45] mm**, R2.40. Every other approved motif and HEX value remains unchanged. The display, PCB, connector chain, battery, MCU, case height and mounting datums do not move.

The original R4 master remains immutable. The [correction master](proposals/display-seam-r1/master.json) records the separate delta. Its old display translation is explicitly historical and already applied. The installer changes only WindowMargin and the glass-window Y datum, then rebuilds the approved color partitions. The six R5 designs remain proposals.

Two independent reviews agreed to the bounded nominal correction after inspecting exact candidate geometry, source hashes and actual mesh renders. Both retained the limitation that 0.10 mm assembly clearance and 0.05 mm projected PCB coverage are not measured manufacturing tolerances or a guarantee of invisibility at every oblique corner. The second-round production checks are acceptance requirements, not worker-certified completion.

The prevention change is a real-footprint display preview plus candidate geometry that rejects clipping, glass interference and color partition drift. The current-versus-candidate render includes normal, 30°, 45° and 60° views. No opaque plane is painted over missing physical material.

## Reproduce

Use the pre-correction source from commit `04e1b4637645c2529e35a5e8c1727a4df1578059`. Do not overwrite production files to reconstruct proposals.

```sh
mkdir -p build/display-seam/source
git show 04e1b4637645c2529e35a5e8c1727a4df1578059:mechanical/revI/Flan36.FCStd > build/display-seam/source/Flan36.FCStd
export FLAN36_REVIEW_SOURCE="$PWD/build/display-seam/source/Flan36.FCStd"
python3 tools/prepare_display_seam_proposal.py
python3 tools/prepare_frame_redesign_r5.py
python3 tools/freecad/run_macos.py tools/freecad/prepare_frame_reviews.py
python tools/render_frame_reviews.py
python3 tools/build_frame_review_page.py
python3 tools/freecad/run_macos.py tools/freecad/install_display_seam.py \
  --source build/display-seam/source/Flan36.FCStd \
  --output build/display-seam/reproduced/Flan36.FCStd
FLAN36_EXPORT_OUT=build/display-seam/reproduced \
FLAN36_EXPORT_METADATA=build/display-seam/reproduced/revI.json \
FLAN36_EXPORT_REPORT=build/display-seam/reproduced/mechanical.json \
python3 tools/freecad/run_macos.py tools/freecad/export_revI.py
python3 tools/freecad/run_macos.py tools/freecad/check_approved_frames.py \
  --source build/display-seam/reproduced/Flan36.FCStd \
  --report build/display-seam/reproduced/geometry.json
```

FreeCAD, VTK and the SVG renderer are required as documented in the CAD workflow. Generated review meshes, logs and candidate exports in ignored `build/display-seam/` are reproducible with these commands. Current review evidence and final delivery receipts live in `design/proposals/` and `validation/`; rebuilding a frozen proposal should be done in a disposable checkout and compared geometrically because native archive metadata can vary.

After exporting the current assembly and rebuilding the viewer, run `node viewer/display-seam-check.cjs` with the Playwright settings in the [CAD guide](../docs/cad.md). It captures the actual frame, glass and support ledges from the front and an oblique angle, and checks the proposal link. Inspect both images in `build/display-seam/viewer/`; the script does not substitute a pixel assertion for visual or physical fit acceptance. Run the collection and 3MF checks in the [frame guide](../docs/frames-extra.md) for camera/configuration continuity and registered print volumes.
