# Editable CAD and 3D files

**[Editing guide](freecad.md)** · **[3D configurator](https://eduarbo.github.io/flan36/)** · **[Configuration format and examples](customize.md)**

The current mechanical source is [`mechanical/revI/Flan36.FCStd`](../mechanical/revI/Flan36.FCStd). It contains both halves, native sketches/operations, editable parameters and 36 original KLP meshes. Commercial modules use [nominal component models](../components/README.md); some connectors remain dimensional reserves. The matching revI KiCad studies use the chosen contour and internal battery/magnet clearances. The specified auxiliary/mounting footprints move, J1 uses a 2 mm side-entry PH footprint, and SW2 moves to the underside; all key transforms and nets are preserved.

| Nominal measure | Revision I |
|---|---:|
| Frame and Level shell height | 13.59 mm, including flush decoration |
| Display glass | 13.39 mm; recessed 0.20 mm |
| Display opening | 13.90 × 30.50 mm; 0.10 mm nominal glass clearance |
| Battery underside / case floor top | 1.4 mm |
| Selected flat KLP keycap top | About 17.87 mm, unchanged |
| Key plate top | 7.6 mm |
| Electronics bay | 24 mm |
| Case width × depth, each half | 116.75 × 94.57 mm |
| Case control corners / radius | 21 / locally bounded tangent arcs |
| Exposed finger switch-to-rim margin | 4.75 mm |
| Battery aperture | 12.5 × 34.4 mm plus local rear lead notch |
| North overhang past adjacent cap | 0 mm nominal |

The frame is **1.21 mm lower** than the previous 14.8 mm design; this does not reduce the selected keycaps' overall height. The [Samtec display connection](level-stack.md#what-makes-the-lower-display-possible) remains a dimensional candidate with unmeasured nice!view hole tolerances. Heights exclude the illustrative 1.2 mm feet. USB is only 0.045 mm behind the adjacent keycap’s north edge: this is a nominal alignment, not a physical tolerance guarantee.

## Files

- `mechanical/revI/Flan36.FCStd`: editable assembly.
- `mechanical/revI/*-case-{solid,rim,terrace,level}-{base,plate}.{step,stl}`: [four real case variants](cases.md).
- `mechanical/revI/*-assembly.step`: installed solid parts per half; no KLP mesh bodies.
- `mechanical/revI/*-frame-{flan,tape,orbit,manga,talavera,gameboy,nes,snes,phone,walkman,ipod}.{step,stl}`: all interchangeable cover styles.
- `mechanical/revI/*-frame-*-{body,detail,accent,secondary}.{step,stl}`: registered flush color volumes.
- `mechanical/revI/*.step`, `*.stl`: individual prototype parts and identified envelopes.
- `mechanical/revI/*-battery-{adafruit-1570,301230}.stl`: selectable nominal cell envelopes.
- `mechanical/revI/coupon-*.{step,stl}`: actual magnetic/thread interface samples.
- `keycaps/variants/`: all 38 unchanged Choc-stem KLP files, including unqualified study variants.
- `keycaps/catalog.json`: provenance, actual stem axes, convex envelopes and qualification.
- `design/configurations/`: default and two sculpted preset examples.
- `hardware/revI/`: two KiCad projects, schematic/PCB placement, local libraries and models; **unrouted**.
- `docs/images/revI-*.png`: renders calculated from exported meshes.
- Viewer: lighter online page, complete self-contained offline HTML, active-configuration GLB and JSON downloads. See the [viewer guide](viewer.md).

Parts retain assembly coordinates. Screw envelopes and nominal engagement are modeled; physical fits, printing orientation and final slicing settings are not qualified. Historical revE/revF/revG/revH sources and receipts remain available for comparison. To rebuild an older viewer, use its historical Git commit; the current shared viewer code targets revI.

## Rebuild the reference

For the isolated migration from the preserved source, use the [floor/level reproduction commands](level-stack.md#reproduce). This keeps manual edits and the published source intact.

For the current frame-only update and validation, use the [seam correction commands](../design/display-seam-implementation.md#reproduce). They preserve the stack and write an isolated candidate. The [six R5 proposals](frame-proposals.md) are separate editable review files awaiting artwork approval.

To refresh exports from the saved reference without rebuilding or overwriting its FCStd, run `python3 tools/freecad/run_macos.py tools/freecad/export_revI.py`, then rebuild the renders and viewer below. The exporter records current provenance separately from the preserved historical export record.

These commands overwrite generated revI reference files. **Do not run them over a source you edited by hand.** Use a separate checkout for reconstruction and keep custom FCStd files elsewhere.

Tested tooling: FreeCAD 1.1.3, KiCad 10.0.6, StepUp 13.1.7 (package metadata 11.09.6), Python with `tools/requirements-render.txt`, and Node dependencies fixed in `viewer/package-lock.json`.

```sh
python -m pip install -r tools/requirements-render.txt
npm ci --prefix viewer
python3 tools/freecad/run_macos.py tools/freecad/export_revI.py
python3 tools/freecad/run_macos.py tools/freecad/check_approved_frames.py \
  --source mechanical/revI/Flan36.FCStd --report build/approved-r4/geometry.json
python tools/render_revI.py
python tools/render_frames.py
python tools/build_viewer_revI.py
node viewer/build.mjs
node viewer/config-contract-check.cjs
node viewer/finishes-check.cjs
node viewer/flush-print-check.cjs
node viewer/frame-collection-check.cjs
node viewer/reliability-check.cjs
python3 tools/check_approved_3mf.py
python3 tools/check_approved_frames.py
```

Browser checks need Playwright and its Chromium runtime; set `FLAN36_PLAYWRIGHT_MODULE` and `FLAN36_BROWSER` when using an existing installation. The resulting ignored `build/frame-collection/` files are reproducible with the commands above. Checks must pass and their recorded source hashes must match the generated artifacts. Historical delivery scripts and receipts describe their pinned snapshots, not the current collection.

To reconstruct the pre-R4 PCB without replacing existing work, use `python3 tools/build_revI_pcb.py --output build/lcd-curve/hardware` with a new empty destination and compare its two PCB files. The source remains the immutable revH placement. The approved R4 J2 translation is a separate guarded migration in `tools/update_approved_display_pcb.py`; its receipt records the final coordinates.

For a fresh PCB reconstruction, run `python3 tools/build_revI_pcb.py` only when `hardware/revI/` does not exist. Run KiCad CLI DRC for both boards with JSON outputs at `build/revI/drc-left.json` and `drc-right.json`, then run `tools/check_revI_pcb.py` with KiCad Python. It checks the explicitly allowed footprint changes, preserved keys/nets and exact new outline, and writes the actual pad polygons. Then run `python tools/check_revI_outline.py` to measure every pad-to-edge clearance. Run these PCB checks before the final delivery check.

The macOS helper uses an existing FreeCAD installation. It disables optional `flatmesh` only in its subprocess because that installed extension crashes on import; it does not modify application preferences. The helper defaults to offscreen Qt. Current checks use offscreen GUI support to preserve native appearance without showing a window. On other systems, run the scripts through the equivalent installed FreeCAD Python environment.

After an authorized publication, `python3 tools/check_public_delivery.py COMMIT_SHA` checks an anonymous full source ZIP against every Git blob and compares public Pages with that commit. Its ZIP and receipt are reproducible under `build/revI/`; it does not publish anything.

The current frame check inspects all 22 saved frame bodies and compares the ten approved top faces against the exact master and the frozen native planar artifact. The earlier height and service studies retain their historical scope. The R4 readback checks the translated contacts, PCB drills and guides; the exporter checks nominal assembled collisions and cap travel. Neither study qualifies a physical assembly. `build/corner-stack/` contains ignored regenerable logs and staging for these commands.

The browser check needs Playwright and a Chromium-compatible browser. Set `FLAN36_PLAYWRIGHT_MODULE` and `FLAN36_BROWSER` if they are not on the usual path. It tests the generated file with HTTP(S) requests blocked; `FLAN36_VIEWER_URL` instead selects the published URL.

The native configuration test also uses the scoped subprocess exit after its assertions, file writes and save/reopen readback to avoid the same Qt teardown crash. It does not suppress failed assertions or change installed FreeCAD.

The catalog build verifies SHA-256 and Git blob hashes of every pinned upstream STL. The geometry exporter checks closed printable solids, pair intersections, all four case pairs, both cell variants and all eleven cover variants against components and a nominal USB plug corridor. The case checker measures the actual saved solids at the side bands, floor and raised-rim joint. The separate keycap checker includes complete-configuration envelopes and a travel/plate bound. The service checker samples frame lift, checks closed insert capture, cage capture and the cell-motion bound against lead paths. These tests do not measure force or print tolerances. Source hashes and results are under `validation/revI-*`.

`build/` is ignored and reproducible: native save/reopen trials come from `check_revI.py`; screenshots, test GLB/JSON and UI receipts from `viewer/check.cjs`; the viewer scene from `build_viewer_revI.py`. Source generations should be compared geometrically because STEP/FCStd metadata may vary. DRC JSON and pad polygons regenerate with the PCB checks above; service coupons regenerate with `check_revI_service.py`. The rim checker rejects the retained former contour, measures 216 preserved finger/outer-thumb normal samples, verifies native local tangent arcs and LCD-aligned flanks in the actual plate solids, and compares mirrored tray/plate volumes. `tools/check_revI_fasteners.py` clips actual KLP triangles to each screw-height travel slab for all 756 qualified reference choices. `build/case-variants/`, `build/lcd-curve/` and `build/uniform-contour/` contain reproducible logs/staging from these commands; review decisions are retained in the public receipt. The disposable contour study and reference copy in `build/case-variants/` are removed after acceptance; case screenshots and selected JSON/GLB regenerate with `viewer/check.cjs`. `viewer/performance.cjs` regenerates the current interaction timing receipt under `build/viewer-sidebar/`; `viewer/finishes-check.cjs` checks triangle/material identity. The native finish checker saves its current readback under `build/viewer-multicolor/freecad.json`. On macOS offscreen Qt, it verifies native face colors and save/reopen without calling OpenGL screenshot capture; the receipt marks that capture as unavailable. VTK renders and browser material checks provide separate visual QA.

## PCB exchange

The existing relative STEP references in `hardware/revI/models/` use the current nominal nano, display, connector, power/reset switch and Choc geometry. Their colors and footprint registration are checked by exporting and reimporting all 11 models. The bottom reset uses an explicitly flipped component transform, verified against actual KiCad CLI assembly exports. [Bottom-side registration](../validation/revI-bottom-reset-step.json) · [Model readback](../validation/revI-pcb-component-models.json).

RevI updates the board contour, battery opening and magnetic-station cutouts. `tools/build_revI_pcb.py` copies the historical unrouted source and refuses to overwrite existing work. Readback permits the specified H1/H3/H4/H5, J1, SW1 and SW2 changes, including the explicit PH pad geometry and bottom reset flip. It checks preserved nets, UUIDs, relative model references and all 36 locked keys. The verified StepUp procedure and coordinate alignment are described in [the editing guide](freecad.md#3-inspect-the-pcb-with-stepup). To rerun the historical exchange test on temporary copies:

```sh
python3 tools/freecad/run_macos.py tools/freecad/check_stepup.py
```

Then run `tools/check_stepup_readback.py` with KiCad’s Python. The StepUp harness exits its own GUI subprocess after saving because that runtime crashes during Qt teardown; independent KiCad readback is required. The test must change only the example opening edge, without altering key positions, pads, connectivity or the outer contour.

`tools/sync_pcb_study.py` resets reference placement; it is not an automatic synchronizer for hand-edited designs. Never use it to discard routing. The current contour/DRC receipt is [revI-electrical.json](../validation/revI-electrical.json); the full schematic/netlist validation is retained as historical [revF-electrical.json](../validation/revF-electrical.json).

## Remaining hardware work

The updated opening and rear lead notch must pass the configured 0.5 mm copper-to-edge rule. Both boards have **zero geometric DRC violations and 104 unconnected items each**. They remain unrouted; do not order them as finished PCBs.

Exact cable terminals, sockets/contact lengths, magnetic retention, printed fits, keycap insertion, screw access with real tools, RF, charging and consumption still need verification. [Revision review](revI-review.md).

The historical `tools/check_rebrand.py` command applies only to its identity-only snapshot. The September 23 identity migration preserves the original geometry. Native metadata and current filenames use Flan36; previous generation receipts keep their original source hashes. [Rename checks](../validation/rebrand-file-map.json) bind the previous snapshot to the current files.

## Color and frame update checks

The isolated [floor/Level installer](level-stack.md#reproduce) preserves its source and verifies the permitted changes before adoption. The color and print checks run after rebuilding the viewer:

```sh
node viewer/keycolors-check.cjs
node viewer/capture-customization.cjs
node viewer/customize-check.cjs
node viewer/hex-check.cjs
node viewer/finishes-check.cjs
node viewer/battery-leads-check.cjs
node viewer/flush-print-check.cjs
node viewer/performance.cjs --smoke
python3 tools/check_approved_3mf.py
python3 tools/check_approved_frames.py
python3 tools/freecad/run_macos.py tools/freecad/check_keycolors.py
python3 tools/freecad/run_macos.py tools/freecad/check_approved_frames.py \
  --source mechanical/revI/Flan36.FCStd --report build/approved-r4/geometry.json
```

`build/keycolors/` and `build/themes-print/` are ignored, reproducible test outputs: JSON/GLB downloads, palette collections, print ZIPs, screenshots and a native save/reopen copy. Native frame comparisons are included in `install_level_stack.py`; the earlier slim/flush installer and raised-frame sources are historical. The [mount study](slim-mount-study.md) produces separately named experimental geometry and a measured report under `build/`.

The [approved R4 frame implementation](frames-extra.md) supersedes the 13.39 mm shared-roof snapshot. The [slim/flush delivery receipt](../validation/revI-slim-flush.json) records the previous 14.8 mm stack and its nine print kits. It does not establish acceptance of the current 13.59 mm R4 update; use the current installation, geometry and export/viewer readbacks in the [approved-frame guide](frames-extra.md). The older `check_frame_collection.py`, `check_level_stack.py` and `check_print_kit.py` describe their historical geometries and palettes. Previous [customization](../validation/revI-customization.json) and [Label-only identity](../validation/revI-document-label.json) receipts retain their historical hashes. These digital checks do not qualify the keyboard for manufacturing.
