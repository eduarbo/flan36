# Previous slim stack and flush frames

This page records the 14.8 mm reference at commit `9ab4b18`. The current [floor-mounted, level-stack prototype](level-stack.md) places the glass at 13.39 mm and, after the R4 frame adjustment, the frame at 13.59 mm. The dimensions and receipts below remain historical evidence.

The revised stack targets a **14.8 mm frame roof**, compared with 16.6 mm for the previous plain frame and 17.2 mm for raised decoration. These are heights from the case underside, excluding feet. The selected flat KLP caps still reach about **17.87 mm**: lowering the electronics does not lower the keys.

| Change | Purpose |
|---|---|
| Display PCB underside at 12.4 mm | Gives a nominal 7 mm separation above the keyboard PCB |
| nice!nano PCB underside at 8.8 mm | Preserves the controller/socket arrangement |
| Battery moved 0.8 mm toward USB, without rotation | Leaves space for the rear lead return while supporting both cell profiles |
| Rotated side-entry JST PH header and PHR-2 plug | Provides a lateral release path beside the retained display connector |
| Fixed 5 mm display socket and moving 2 mm male spacer | Accounts for both halves of the removable display connection |
| TL3342 reset below the PCB | Frees the crowded top surface; a recessed Ø2.8 mm hole provides tool access |
| Open-bottom cable reliefs | Lets the display and sled lift off the nominal stationary wires |
| 0.4 mm flush color volumes | Keeps each motif level with the roof, with at least 0.8 mm nominal backing |

The case outline, 36 key positions and angles, magnetic frame interface and existing structural screws remain unchanged. Every base receives the underside reset access. Adafruit 1570 and 301230 retain separate cell and lead geometry in FreeCAD, the viewer and GLB exports.

## Appearance and printing

All seven decorative styles—Handheld, Retro TV, Cyberpunk, Cartridge, Arcade, Mecha and Kintsugi—use real complementary material volumes. No decorative part rises above the roof. Smooth, Bevel and Facet were the plain options at that revision. The [current collection](frames-extra.md) replaces these designs.

Choose a style and palette in the [configurator](https://eduarbo.github.io/flan36/), then download its print kit. Multipart 3MF and individual material STLs keep the colors registered to the same origin. Assign actual filaments in your slicer. Use compatible colors of the same material and test their bonding before a full print.

The complete single-material STL has a continuous plain surface because the inlays fill their recesses. The `*-body.stl` file exposes the recesses. Separate press-fit inserts are **not** qualified. [Themes and print workflow](themes-printing.md).

## Access sequence

1. Lift off the magnetic frame.
2. Lift the display, male header and sled together from the open-bottom cable reliefs.
3. Remove the controller to expose the battery connector. The display socket stays on the PCB.
4. Grip the battery plug housing from above, slide it 5 mm toward the keys, then lift it clear. Release the loose cable bends as needed.
5. With the battery disconnected, remove the structural fasteners and battery cage.

The connector check uses continuous rigid sweeps for a 5 mm unplug stroke, 24 mm lift and a thin gripping-tool reserve. It includes the retained socket and key bounds. These checks cannot establish the force, wire flexibility or reliable manual unplugging of a real harness. Do not pull on the wires to disconnect the battery. The underside reset stays recessed and is reached with a narrow blunt tool.

## What this proves

The delivery check uses analytic geometry bounds, independent of display-mesh triangulation, and covers both halves, ten frames, both battery envelopes, saved native geometry, PCB placement, actual KiCad STEP registration, matching viewer meshes and aligned multicolor print exports. A separate readback compares all 2,242 exporter pair selections against analytic bounds for this saved geometry. [Historical digital checks](../validation/revI-slim-flush.json).

It does **not** prove the absolute minimum physical height. Lead diameter and terminal exits remain nominal, the 105 mm routes are modeled assumptions, and actual contact engagement has not been measured. Printed fits, magnetic retention, cell tolerances, flexing during service, RF, charging and electrical operation still need hardware testing. Both PCB studies remain unrouted with 104 unconnected items per half.

The earlier [height and mounting study](slim-mount-study.md) is retained as historical evidence. Its tall generic connector and floating cable paths do not establish a lower limit for this revised arrangement.

## Reproduce

The editable file is [`Flan36.FCStd`](../mechanical/revI/Flan36.FCStd). Opening it needs no custom Python proxy. Modify its parameters and native features, then export with the current scripts in the [CAD guide](cad.md).

To reproduce the migration, extract the pre-update native file from commit `a4add9f817357bbc01d6296a21c4767d417461de` into an ignored staging folder and run:

```sh
mkdir -p build/slim-flush/source
git show a4add9f817357bbc01d6296a21c4767d417461de:mechanical/revI/Flan36.FCStd > build/slim-flush/source/Flan36.FCStd
python3 tools/freecad/run_macos.py tools/freecad/install_slim_flush.py \
  --source build/slim-flush/source/Flan36.FCStd \
  --output build/slim-flush/reproduced/Flan36.FCStd --export
```

Use a new output directory. The installer preserves the input, checks the allowed case change and key geometry, then saves and reopens the candidate. It does not replace the published reference automatically. The committed delivery receipt binds the adopted files. Temporary `build/slim-flush/` candidates are ignored. Reproduce the retained STEP calibration fixtures with `python3 tools/freecad/run_macos.py tools/freecad/check_pcb_step_registration.py --calibrate-only` and the socket fixture with the same command using `--j2-fixture`. Each command writes a checked receipt alongside its geometry.
