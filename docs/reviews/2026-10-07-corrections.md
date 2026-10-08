# October audit corrections

This correction set addresses the seven findings in the [original audit](2026-10-07.md). The source-bound reports below determine acceptance. The keyboard remains a digital prototype: PCB routing, integrated firmware and physical acceptance are still outstanding.

| Finding | Correction | Verification |
|---|---|---|
| A1 · Display dependencies | Board, glass, header, retained socket and structural reliefs follow the same display datum. | Both halves at +1 mm, including saved/reopened CAD. |
| A2 · Window edits | Color volumes intersect the current frame blank; an old fixed opening cannot protrude into the edited window. | 0.10 and 0.30 mm margins across all six designs. |
| A3 · Inlay depth | Ordinary inlays follow the roof and retain 0.40 mm depth. | Roof raised 0.40 mm; backing checked from actual faces. |
| A4 · USB access | A local clearance cut removes the obstruction from all four case bases. | USB insertion envelope against every base, plate and frame. |
| A5 · Missing underside parts | All 36 diodes and 36 hot-swap sockets are registered to the actual PCB footprints. | Native intersections, exact socket distances and real KiCad STEP readback. |
| A6 · Stale checks | Current selectors, dimensions and legacy defaults are tested; the aggregate runner fails on child failures or timeouts. | Native and browser suites, negative runner probes. |
| A7 · Stale presentation | Current dimensions, six approved designs and the selected native default drive the documentation and renders. | Source hashes, rendered CAD and public viewer readback. |

Hanafuda uses its approved R8 paths and solid palette. No retired design is restored. Right-hand artwork keeps the same reading direction, while structural corners retain their handed fit. The 36 keycap meshes and poses, including the F/J homing variants, are preserved.

The socket datum uses both mounting bores and four coplanar faces on its two metal terminals. It places the nominal socket bottom at **Z1.95 mm**, **0.55 mm** above the floor. The first candidate failed the right K30 clearance gate at the internal H3 support. The corrected local relief measures **0.2500001 mm** from K30 to that support on both halves.

| H3 support measurement | Left | Right |
|---|---:|---:|
| Previous K30 gap | 0.136281 mm | 0.047739 mm |
| Minimum remaining material around pilot | 1.336281 mm | 1.247739 mm |
| Bearing area removed | 0.108848 mm² | 0.256669 mm² |

The [relief report](../../validation/revI-socket-clearance.json) verifies the saved/reopened result, preserved outer contour, floor, pilot location and stack height, and unchanged geometry for 66 other assembly objects, including all 108 socket solids. All four case bases receive the local correction; the relief removes material only from H3. These are nominal CAD measurements. Purchased-part, solder and printed fit remain unqualified (`physical_acceptance: false`).

## Evidence

- [Native parameter checks](../../validation/revI-audit-parameters.json)
- [Saved assembly and clearances](../../validation/revI-audit-delivery.json)
- [Hot-swap source and actual STEP registration](../../validation/revI-hotswap-registration.json)
- [Local H3 support relief](../../validation/revI-socket-clearance.json)
- [All case/frame collisions](../../validation/revI-mechanical.json)
- [Source-preserving adoption](../../validation/revI-audit-adoption.json)
- [Viewer and publication checks](../../validation/revI-audit-completion.json)

## Reproduce

Use the pinned runtimes described in the [CAD guide](../freecad.md), from the repository root in a disposable checkout with an empty `build/audit-fixes-20261007/`. The immutable baseline is commit `b3e44990d9272327fef042439f1a6555eaae8c4f`. These scripts also add relative diode/socket models to the existing PCB studies; keep manually edited CAD and routed boards outside this reconstruction.

The paths below are intentional: socket installation and delivery validation read diode calibration from **`build/audit-fixes-20261007/candidate/diodes.json`**. Do not rename that path independently.

```sh
mkdir -p build/audit-fixes-20261007/final
git show b3e44990d9272327fef042439f1a6555eaae8c4f:mechanical/revI/Flan36.FCStd > build/audit-fixes-20261007/baseline.FCStd
python3 tools/integrate_hanafuda.py
python3 tools/freecad/run_macos.py tools/freecad/install_audit_repairs.py \
  --source build/audit-fixes-20261007/baseline.FCStd \
  --output build/audit-fixes-20261007/candidate/Flan36.FCStd
python3 tools/freecad/run_macos.py tools/freecad/install_diode_models.py \
  --source build/audit-fixes-20261007/candidate/Flan36.FCStd \
  --report build/audit-fixes-20261007/candidate/diodes.json
cp build/audit-fixes-20261007/candidate/Flan36.FCStd build/audit-fixes-20261007/final/Flan36.FCStd
python3 tools/freecad/run_macos.py tools/freecad/install_hotswap_models.py \
  --source build/audit-fixes-20261007/final/Flan36.FCStd \
  --report build/audit-fixes-20261007/final/hotswap.json
python3 tools/freecad/run_macos.py tools/freecad/install_socket_clearance.py \
  --source build/audit-fixes-20261007/final/Flan36.FCStd \
  --output build/audit-fixes-20261007/clearance/Flan36.FCStd \
  --report build/audit-fixes-20261007/clearance/relief.json
python3 tools/freecad/run_macos.py tools/freecad/check_audit_repairs.py \
  --source build/audit-fixes-20261007/clearance/Flan36.FCStd \
  --report build/audit-fixes-20261007/clearance/parameter-checks.json
python3 tools/freecad/run_macos.py tools/freecad/check_revI.py \
  --source build/audit-fixes-20261007/clearance/Flan36.FCStd \
  --report build/audit-fixes-20261007/clearance/freecad.json
python3 tools/freecad/run_macos.py tools/freecad/check_audit_delivery.py \
  --source build/audit-fixes-20261007/clearance/Flan36.FCStd \
  --baseline build/audit-fixes-20261007/baseline.FCStd \
  --report build/audit-fixes-20261007/clearance/delivery.json
FLAN36_EXPORT_OUT=build/audit-fixes-20261007/clearance \
FLAN36_EXPORT_METADATA=build/audit-fixes-20261007/clearance/revI.json \
FLAN36_EXPORT_REPORT=build/audit-fixes-20261007/clearance/mechanical.json \
  python3 tools/freecad/run_macos.py tools/freecad/export_revI.py
python3 tools/freecad/run_macos.py tools/freecad/export_hotswap_visual.py \
  --directory build/audit-fixes-20261007/clearance \
  --metadata build/audit-fixes-20261007/clearance/revI.json
```

The relief installer preserves the `final/` candidate. Its new `hotswap.json` explicitly inherits registration evidence only after unchanged socket geometry and PCB hashes are verified. Parameter, configuration, complete-assembly clearance and export checks run against the new `clearance/` source. The exporter records file hashes; shared socket visuals must be generated afterward.

Before adoption, the destination native file must still match the extracted baseline. Adoption checks every required report against the candidate hash, rejects altered exports, preserves equivalent unrelated meshes and verifies copied files:

```sh
python3 tools/check_audit_adoption.py
# In this disposable checkout only: restore the required adoption baseline.
cp build/audit-fixes-20261007/baseline.FCStd mechanical/revI/Flan36.FCStd
python3 tools/adopt_audit_repairs.py build/audit-fixes-20261007/clearance
python3 tools/check_audit_receipt_format.py
python3 tools/audit_receipt_format.py
python3 tools/audit_receipt_format.py --check
python tools/build_viewer_revI.py
node viewer/build.mjs
python tools/render_revI.py
python tools/render_frames.py
python3 tools/check_audit_runner.py
python3 tools/check_audit_completion.py
python3 tools/audit_current.py
```

Published receipt digest maps use ordered `path` / `sha256` records. Their provenance preserves the original producer-byte hash; verification must reconstruct those bytes exactly. The generating reports under `build/` remain unchanged.

The full audit intentionally exits nonzero while either PCB remains unrouted. Review its per-check results: only the two DRC routing gates may fail for this digital correction set. Run the [current browser checks](../cad.md#color-and-frame-update-checks), both `gameboy` and `hanafuda` with `FLAN36_FRAME_STYLE=STYLE node viewer/frame-orientation-check.cjs`, and the loading checks. Run `tools/record_audit_completion.py` only after native, browser and render checks pass. Following authorized synchronization, use `python3 tools/check_public_delivery.py COMMIT` and `node viewer/public-check.cjs COMMIT` for public readback. Temporary candidates, profiles, downloads and screenshots are ignored, reproducible artifacts.

## Why these defects escaped

Some geometry depended on fixed reference heights while the documented parameters remained editable; several checks also targeted retired designs. The correction tests changed and combined parameter states, preserved source artwork, actual PCB STEP registration and current downloadable geometry. Registering the missing sockets also exposed the right K30 support conflict; the local relief keeps that correction separate from the exterior contour. Adoption rejects post-validation file changes and verifies copied files before recording success. Physical qualification remains a separate gate.
