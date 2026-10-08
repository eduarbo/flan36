# Revision I review

**Chosen Contour outline, magnetic frames and two battery profiles. Digital prototype only.**

The source reference requested a stepped finger outline, rectangular pinky foot, shallow recess and continuous thumb fan. The actual CAD and PCB now use that contour while preserving all 36 Piantor key transforms. Internal fasteners and magnetic stations add no perimeter lobes.

Two independent read-only reviews covered geometry/serviceability and failure modes before the magnetic design was adopted. The recorded source snapshots stayed unchanged during their review. [Decision record](../validation/revI-design-review.json).

## Key-aligned local curves and case variants

The latest contour replaces the spanning thumb spline with three key-parallel straight faces and local tangent rounds. Finger corners use R2.4 where space permits, smaller radii at short steps, and wider blends at the thumb joins/recess. The pinky backbone stays 90°. The LCD flank remains at left X=135 / right X=25. Both halves derive from one reflected contour.

Solid, Color rim and Terrace share that perimeter. The Color rim has a raised border 0.9 mm wide and inset plate; Terrace cuts two shallow exterior bands. See [case designs](cases.md). No key, mount, magnet or battery position changes. The straight-face allowance stays 4.75 mm: a 4 mm study failed against right-hand pads and was rejected before native generation. Actual copper clearance remains at least 0.5 mm.

The former broad-cubic revision remains in Git and in `revI-local-curves-baseline.json`. New acceptance checks target local native arcs, key-aligned faces, both actual PCB pad sets, all case/frame combinations and selected-mesh JSON/GLB/FreeCAD correspondence. Earlier review receipts below describe their dated snapshots, not the current corner geometry.

## Uniform rim correction — prior revision

The earlier contour was mirrored, but its exposed margins varied from **2.53 to 5.42 mm**. Hand-entered vertices and a containment-only test allowed that discrepancy. That revision derived its faces from the switch openings at **4.75 mm**, with offset thumb edges and H1 relocated to **(38.7, 37.5)** inside the first two columns. Its post is R2.1; the M2 screw is unchanged.

Why 4.75? The outer thumb hot-swap pad reaches 9.575 mm from its center. Preserving the 1.65 mm case-to-PCB offset and 0.5 mm copper rule requires at least **4.725 mm** of visible rim. A 4 mm draft cut that pad. Its envelope was 119.30 × 95.10 mm; its area differs by only 0.0072% from the previous contour. The electronics bay stays 24 mm.

The left contour alone generates both halves. Measured straight faces, local tangent blends, internal bridges and the bay joint have separate definitions. The test rejects the old outline and reads the actual native plate solids; it does not treat every interior key as peripheral. [Rim measurements](../validation/revI-rim-solids.json) · [Fastener/keycap travel](../validation/revI-fasteners.json) · [Decision and correction record](../validation/revI-rim-review.json).

The current diagram above supersedes that geometry; the previous receipt and regression fixture preserve its measurements.

## Earlier corrections during verification

- H3 was outside the new recess: it moved into existing material. H4/H5 moved below the electronics, with short screws and underside head reliefs.
- The earlier wide battery opening violated the copper-edge rule: the saddle now stays below the board, with only the cell/cage crossing a 12.5 mm opening.
- An initial magnet position cut a K25 pad: actual pad polygons exposed the conflict. Stations moved south; J1 and SW1 moved to preserve clearance. The power switch also moved inward. No key moved.
- The battery cage touched the controller support: the rear support bridge moved clear of the cage.

At this mechanical-review snapshot, both KiCad studies had **0 geometric violations and 104 unconnected items per half**. [Current routed-board evidence](electronics.md) supersedes that electrical status; physical qualification remains pending. The original 0.5 mm copper-edge rule remains in force; measured minimum pad clearance is approximately 0.524 mm.

- A frame could fit at rest yet catch the MCU while lifting. Its internal relief now opens to the lower rim; sampled extraction checks cover all six styles.
- A FreeCAD link dropped a battery box's placement. Each battery variant now has a native compound wrapper, and independent bounds checks verify the active link, exported mesh and configuration swap.

## Physical work still open

Magnetic holding force, north-edge peel, closed-pocket print capture, actual magnet temperature, printed M2 threads and cycling need coupons. Both battery fits use supplier nominal dimensions; wrapping, insulation, protection electronics, cable terminals and connector polarity must be checked on delivered parts. Socket heights, hot-swap assembly, firmware, charging, BLE and consumption remain unverified.

The wire study reserves two 105 mm paths with 1.5 mm bends and 0.6 mm insulation diameter. It is not a terminal-complete harness. Sampled frame lifts are nominal collision checks, not a continuous tolerance analysis or a physical extraction test.

[Mechanical](../validation/revI-mechanical.json) · [Outline and clearances](../validation/revI-outline.json) · [Electrical](../validation/revI-electrical.json) · [Service and coupons](../validation/revI-service.json) · [Build sequence](build.md).
