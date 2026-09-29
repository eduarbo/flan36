# Floor-mounted battery and level case

**Current R4 adjustment:** the frame and Level upper shell now reach **13.59 mm**. Glass remains at **13.39 mm**, recessed **0.20 mm**. A **0.40 mm** cover hides the display pins; the whole display mating chain moves 0.20 mm toward the frame center. [Approved frames and current verification](frames-extra.md).

The following dimensions describe the earlier Level installation and are retained as its history.
This prototype brings the **frame, display glass and Level upper shell to the same 13.39 mm plane**, lowering the frame by **1.41 mm** from the previous 14.8 mm design. Heights start at the case underside and exclude feet. The selected flat KLP caps still reach about **17.87 mm**, so overall keyboard height is unchanged; the switches and key positions have not moved.

![Actual Level CAD assembly](images/revI-level.png)

| Part | Previous Z | New Z |
|---|---:|---:|
| Battery underside | 2.00 mm | 1.40 mm, directly on the case floor |
| Battery cage roof | 6.20–6.80 mm | 5.60–6.20 mm |
| nice!nano PCB underside | 8.80 mm | 8.20 mm |
| nice!view PCB underside | 12.40 mm | 11.49 mm |
| Display glass top | 14.30 mm | 13.39 mm |
| Frame and Level upper shell | 14.80 mm frame | 13.39 mm |
| Selected flat KLP keycap top | 17.87 mm | 17.87 mm, unchanged |

The battery locator now has an open bottom. Its walls locate the cell; they add no layer below it. The cage feet stay captured under the PCB. Both Adafruit 1570 and 301230 retain their own cell and cable geometry. The stored cable loops descend with the cell and rise back to the unchanged battery connector.

## Level case

Choose **Level** in the case explorer. Its upper shell hides the switch housings from the sides and meets the display frame at the same height. The Piantor key centers, angles and outer silhouette remain unchanged.

The shell and original 1.3 mm switch-retaining plate form one removable part. It uses the same three plate screws, reached from above after removing the caps. The magnetic display frame remains independently removable. There are no new perimeter bosses or raised decorations.

The upper openings reserve all 28 currently admitted KLP variants and their allowed rotations over the full 3.5 mm travel envelope. The configurator still checks the chosen cap-to-cap and cap-to-frame arrangement. Thin intervening webs are merged into larger openings.

When **Match frame** is enabled, the Level upper shell, base and frame share a color. Turn it off to color them separately. Existing Solid, Color rim and Terrace options remain available.

## What makes the lower display possible

The nominal connector pair is **Samtec SLW-105-01-L-S + TLW-105-06-G-S**: a 4.57 mm socket and 1.52 mm header insulator create 6.09 mm board separation. The 2.67 mm mating post falls within the socket's published 2.16–2.92 mm insertion range. See the [SLW drawing](https://suddendocs.samtec.com/catalog_english/slw.pdf) and [TLW drawing](https://suddendocs.samtec.com/catalog_english/tlw_th.pdf).

The display's solder tails are modeled trimmed to 0.3 mm above its PCB, with a 0.5 mm solder envelope. A small open service well exposes that recessed contact row; it avoids a fragile roof directly over the joints. Local underside relief clears the display PCB. Decorative inlays retain their original backing requirement and stop where that backing is unavailable.

The [nice!view drawing](https://nicekeyboards.com/docs/nice-view/pinout-schematic/) places the contact row 1.3 mm from the end. The model now uses that datum, correcting the previous 2.4 mm misalignment with the socket.

**This is not a hardware-qualified connector substitution.** The finished nice!view hole diameter is not dimensioned in the available drawing. CAD retains its explicitly unmeasured 0.9 mm hole; the nominal 0.025-inch square post has a 0.898 mm diagonal, leaving no useful tolerance allowance. Measure actual hole and pin tolerances before choosing this pair. Do not enlarge or drill a purchased display based on this model. The stock 7 mm connector pair belongs to the previous taller stack.

13.39 mm was the initial Level prototype target, not a claim of an absolute physical minimum. Further reductions require a different qualified connector or module arrangement. Actual socket engagement, soldering, printed strength, battery insulation, cable flex and service forces still need a physical prototype. Both PCB studies remain unrouted; this geometry is not a finished build kit.

[Level geometry delivery](../validation/revI-level-delivery.json) is a historical receipt for the floor/Level installation. Its hashes identify that historical snapshot; the R4 adjustment supersedes its native and derived files. [Cap direction checks](../validation/revI-cap-rows.json) cover the subsequent orientation fix. [Earlier viewer reliability checks](../validation/revI-reliability.json) retain their original HTML hashes; the [approved-frame delivery](../validation/revI-approved-frames.json) binds the current viewer. Openings preserve cap travel, so parts of the switches can still be visible from above between keys; the Level perimeter conceals their bodies from the sides.

## Reproduce

Start from the preserved pre-level source at commit `9ab4b181f77d0f3ffc28bda0cb3c059006713c89`. Export that file into an ignored build directory, then run:

```sh
python3 tools/freecad/run_macos.py tools/freecad/install_level_stack.py \
  --source build/level-case/source/Flan36.FCStd \
  --output build/level-case/candidate/Flan36.FCStd
python3 tools/freecad/run_macos.py tools/freecad/check_level_stack.py \
  --source build/level-case/candidate/Flan36.FCStd \
  --output build/level-case/candidate/geometry-check.json
```

Use a new output directory. The installer preserves the input and checks native save/reopen, unchanged key meshes and transforms, and idempotence. A saved candidate alone is not acceptance. The delivery receipt records the subsequent collision, travel, service, export and viewer checks.

Follow the [CAD export and viewer commands](cad.md#rebuild-the-reference) after adopting an accepted candidate. Run `node viewer/level-check.cjs` before `python tools/check_print_kit.py` to include the Level shell kit alongside the nine existing kit checks. `python tools/check_level_delivery.py` reproduces the historical Level delivery binding only at that snapshot; newer viewer changes require their own scoped receipt. Use `node viewer/reliability-check.cjs` for the current viewer state transitions. After publication, `python tools/check_public_delivery.py COMMIT` checks the anonymous source archive and live viewer against that exact commit.

`build/level-case/` holds ignored, reproducible candidates, diagnostic logs and browser test output. The committed installer/checkers above recreate the delivery artifacts; the installation and review receipts preserve the decisions and superseded candidate findings.
