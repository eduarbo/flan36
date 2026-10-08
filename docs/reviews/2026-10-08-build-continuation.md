# Build continuation

The original outcome is a buildable, slim, completely wireless 36-key split with the retained Piantor key poses, Choc hot-swap, removable electronics, nice!nano v2, low-power displays, both battery envelopes and printable KLP Lamé caps/cases/approved frames. Finishing the digital audit does not finish that outcome.

Source: Eduardo's continued build request, including “si no has terminado, por que vuelves a parar?” on 2026-10-08. Starting point: `fe8c7fdc1b13b8eac6383c3315af8e749b1b8d4c`.

Required outcomes:

1. **Electrical candidate:** preserve all component poses, holes and contours; reconcile schematic/PCB; route both halves; verify every physical pad, semantic matrix, ERC and DRC without disconnected nets. Preserve exact source-bound fabrication outputs.
2. **Firmware:** pinned and rebuildable ZMK; left central/right peripheral, custom SPI, 36 physical key mappings, both displays and the optional right without a display. Inspect compiled DTS/configuration and valid UF2 blocks.
3. **Build package:** concise English assembly, BOM/alternatives, exact files and acceptance procedure; no presentation that implies unperformed physical tests passed.
4. **Physical acceptance:** measured supplied connectors/packs, printed fit and retention, assembled continuity, all keys, display recovery, BLE, safe charging and measured sleep/active current. This remains separate from CAD, routing and compilation and requires actual parts.

Two independent read-only reviews agreed that the existing topology can proceed without moving components. Their principal conditions and source baseline are recorded in [the electrical decision](../../design/reviews/electronics-20261008/decision.json). Firmware uses the verified stable ZMK revision instead of inheriting an unpinned current branch.

Work stays in disposable `build/electronics-20261008/` candidates until the affected checks pass. Historical audit receipts remain historical; new routed-board evidence must identify its own source hashes. The canonical FreeCAD assembly, key positions and selected frame artwork are preserved.

## Verified delivery

Both canonical boards now pass KiCad 10.0.6 DRC, ERC and schematic parity with no unconnected items. Each has 247 physical pads checked, 18 key positions and two copper layers. All original footprint/pad geometry, model references and 676 outline/cutout segments per half match the baseline. The FreeCAD assembly remains unchanged.

The reviewed right-only MCU remap moves rows 0–3 to D21/D20/D19/D18 and column 0 to D15. This avoids routing five signals around the battery opening's 0.55 mm north bridge; it does not widen the case or weaken the original rules. D2–D6 are explicit NC on the right. The matching source and three firmware images use the same per-half pin map.

Independent readback also parsed the emitted Gerbers and drills: each half's 676 outline segments, 91 plated holes and 97 non-plated holes match the PCB; drill serialization is within 0.0005 mm. ZIP readback checks every member and its bound source. [Routing](../../validation/revI-routing.json) · [Fabrication](../../validation/revI-fabrication.json).

All three ZMK variants were rebuilt from 39 clean pinned repositories and the qualified compiler, with source checks before/after each build. Actual DTS/config/UF2 readback verifies the 36-position transform, half roles, GPIO, SPI, screen variants, sleep and firmware address bounds. [Firmware evidence](../../validation/revI-firmware.json) · [Two-reviewer disposition](../../design/reviews/electronics-20261008/firmware-final/decision.json).

## Bugs caught and prevention

- The old PCB values/net names and five mechanical-only footprints disagreed with schematic parity. They now match the authoritative netlist, including every duplicate physical pad. A deliberately wrong duplicate pad is rejected.
- Router import rounded four diode positions per half by at most 0.000046 mm. Exact baseline coordinates were restored and DRC rerun. Edge comparison ignores generated UUIDs and decimal formatting, while preserving exact numeric geometry.
- Initial routing reduced local neck widths and approached cutouts too closely. The accepted boards use at least 0.20 mm everywhere, original 0.20/0.50 mm clearances and no new exclusions. Independent DRC validates the serialized result, not the router's success message.
- Existing firmware validation could describe an old binary using current source hashes. Build-time attestations now bind sources, dependency/compiler identity and actual outputs. Both an edited key binding and a corrupted last-variant binary are rejected before publication.
- Current guides and viewer status now refer to routed candidates. Historical receipts retain their original hashes and observations.

[PCB negative controls](../../validation/revI-routing-negative.json) · [Firmware negative controls](../../validation/revI-firmware-negative.json). The existing Level viewer smoke check passed after the status-text update; its themes, native print bytes, 3MF and frame heights remain unchanged.

## Still required for the original outcome

Digital delivery is complete when its source and packages are synchronized and read back publicly. A buildable, physically accepted keyboard still requires measured supplied connectors/cells, printed fit/retention, assembled continuity and all keys/displays, BLE, charging and current tests. The exact next physical step and acceptance criteria are in [Build](../build.md#hardware-acceptance). No hardware test, purchase, flashing or physical printing is represented as completed here.
