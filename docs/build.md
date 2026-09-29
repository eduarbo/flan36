# Build status

The current design is an inspectable digital prototype. Final Gerbers, a closed BOM and tested UF2 firmware are not available yet. Do not order the unrouted PCB studies as finished boards.

The intended sequence is:

1. Close the BOM and measure the actual components.
2. Print a Choc fit coupon and three KLP Lamé samples. Check stem fit, return and comfort before printing the full set.
3. After electrical layout passes review and DRC, assemble the PCBs and check continuity and polarity.
4. Flash each half and test all 36 keys.
5. Install the supported battery, controller, display and frames without loading the pouch or glass.
6. Verify BLE, charging, sleep/wake and measured power use.

PLA Basic and PETG HF are available for prototype trials; ABS is another case material. No filament/profile is qualified for the final parts yet. Print orientation and stem tolerances need physical tests. [Parts and alternatives](parts.md).

## Inspect the layout now

`design/layout.json` contains each half’s 18 key centers and angles in millimeters. The original Piantor boards and provenance are under `sources/` and [ATTRIBUTION.md](../ATTRIBUTION.md).

```sh
python3 tools/check_layout.py
python3 tools/render_layout.py
```

The checker compares all 36 positions/rotations with the original boards. The renderer regenerates the layout diagram. `sources/piantor/` contains the original **wired** reference boards, not Flan36’s wireless PCB designs.

## Magnetic frame and service

The frame is cosmetic and removable. The five internal structural screws per half keep the PCB and battery cage secured when the frame is lifted. Its three small locator lips resist sliding; magnets provide attraction. Do not use the frame as a carrying handle before retention is measured.

1. **Print the coupons first:** [magnet base](../mechanical/revI/coupon-magnet-base.stl), [frame target](../mechanical/revI/coupon-magnet-frame.stl), and [M2 thread](../mechanical/revI/coupon-m2-thread.stl). These are cropped production interfaces, at assembly coordinates. Orient the broad face on the bed and inspect every layer in the slicer.
2. **Pause and insert:** the base pocket is Ø2.3 × 3.2 mm for the Ø2 × 3 mm magnet; the frame pocket is Ø2.2 × 4.2 mm for the steel pin. Insert before the pocket closes and confirm the insert sits below the next nozzle path. The top coupon can print with its broad top face on the bed. Choose pauses from the actual sliced layer, not an assumed layer number.
3. **Qualify capture and heat:** enclosed inserts must stay captive after flexing and repeated removal. The reference magnet is rated to 80°C; verify its actual thermal exposure during printing. A low bed setting alone does not establish that. PLA Basic is the first coupon material to investigate; PETG HF and ABS remain alternatives to qualify.
4. **Check attraction and sliding:** reproduce the nominal 0.9 mm magnetic gap (pocket float allows roughly 0.7–1.1 mm before print tolerances). Check north-edge peel on a complete frame; a single-station coupon cannot establish whole-frame retention.
5. **Tap and test the M2 pilot:** use an M2 tap in the Ø1.7 mm printed hole, then test the specified screw without bottoming or stripping. Do not assume the screws are self-tapping.

For the nominal assembly, seat the open-bottom locator, cell directly on the **1.4 mm case floor**, and cage before lowering the PCB over the cell. The cage’s wider feet remain below the board. Install the three plate spacers and structural screws, then the removable modules and frame. Do not compress the pouch. Actual lead exit and strain relief remain to be qualified.

For service, power off and disconnect USB first. Lift the magnetic frame and use the [inherited nominal removal sequence](slim-flush.md) to expose and unplug the battery connector. Remove the caps, then the three plate screws and plate/Level upper shell, then the two short PCB screws and PCB before withdrawing the captured cage. The magnetic cover alone does not release the battery. Cable flex, connector grip and actual removal still need a physical trial. Reset is operated from the underside with a small tool through the recessed access hole.

The [historical support study](slim-mount-study.md) records why the earlier closed cable tunnels prevented display/sled removal. The [current Level stack](level-stack.md) retains the open-bottom support relief and lowers both battery-specific cable routes with the cell. Its glass remains at 13.39 mm beneath the 13.59 mm frame/shell plane and relies on an unqualified Samtec connector substitution; the stock display connector belongs to the previous taller stack. Digital checks do not qualify bending forces or real terminal tolerances.
