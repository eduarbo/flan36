# Historical slim support study

This records the **previous 16.6 mm stack and raised decorations**. Its generic
JST reserve and floating lead paths exposed the problems addressed by the
[slim, flush redesign](slim-flush.md). The study ZIP and measurements below retain
their original geometry and findings; they are not the current print kit.

The completed study covers both halves, all **10 frames** and both battery
profiles: **Adafruit 1570** and **301230**. It also evaluates support consolidation
for Solid, Color rim and Terrace.

[Download the STEP/STL study pack](../mechanical/studies/slim-mounts.zip) ·
[Measured results](../validation/revI-slim-mounts.json)

## Height comparison

Dimensions start at the case bottom and exclude feet.

| Recipe | Display bottom | Plain roof | Decorated top | Static result |
| --- | ---: | ---: | ---: | --- |
| Reference | 14.2 mm | 16.6 mm | 17.2 mm | Clear in the modeled checks; retained |
| Lower candidate | 12.4 mm | 15.6 mm | 16.2 mm | Clear in the modeled checks; experimental |
| Rejected limit | 12.4 mm | 14.8 mm | 15.4 mm | Roof intersects the JST connector |

The selected KLP Lamé keycaps keep the complete assembly at **17.87 mm**
in every recipe. Lowering the electronics cover therefore changes
its profile without reducing this configuration's maximum height.

At 15.6 mm, the modeled JST-to-roof clearance is **0.5 mm**, and the shortest
MCU-to-display distance is **0.82 mm**. These are mechanical distances, not proof
of pin engagement or electrical continuity. At 14.8 mm, JST roof clearance becomes
**−0.3 mm** in every frame; the same obstruction also affects the first frame-lift
samples. The ZIP includes this rejected recipe for comparison, not as a print
recommendation.

## Fewer loose supports

| Study option | Result across both halves | Loose parts removed | Height change |
| --- | --- | ---: | ---: |
| Plate with its three washers fused in | All six case/half variants form one connected solid and preserve the combined envelope and PCB seats | 6 | 0 mm |
| Base with its battery saddle fused in | All six variants form one connected solid and preserve the combined envelope and datums | 2 more | 0 mm |

These parts are exported separately under `support-consolidation/` in the ZIP.
The fused saddle is optional because it loses independent replacement. Print
orientation, insulation, strength and retention still need physical tests.
The battery cage, MCU riser, display sled, magnets and independent fasteners remain;
this study does not qualify removing their support or retention functions.

## Service conflict to resolve

Lifting the display and sled together crosses modeled `battery-lead-0` and
`battery-lead-1` at **0.5–2 mm** of travel. Each recipe records **28 collision
samples** across both halves and batteries. This also affects the reference stack,
so the overall service checks **do not pass**.

The other recorded USB, driver, PCB-lift, cell-motion and insert/cage-capture checks
show no failures. Reference and 15.6 mm frame-lift samples are clear; the 14.8 mm
recipe additionally hits the JST connector. These are sampled checks, not proof
of a continuous extraction path or real connector disengagement.

The next mechanical change is to reroute or release the battery leads before
lifting the display, then recheck the complete extraction sequence and real lead
ends. The lower display also needs measured mating datums and pin engagement.
Physical fit, tolerances, wire forces, magnetic hold and print durability remain
unqualified.

## Reproduce

From the repository root with the documented FreeCAD macOS runtime:

```sh
FLAN36_STUDY_SOURCE="$PWD/mechanical/revI/Flan36.FCStd" \
FLAN36_STUDY_OUT="$PWD/build/slim-mount-recheck" \
python3 tools/freecad/run_macos.py tools/freecad/study_slim_mounts.py
```

Choose a new or empty output directory. The headless study leaves the native file
untouched and writes STEP/STL parts, `README.md`, measurements and hashes to the
ignored `build/` directory. The [checker](../tools/freecad/study_slim_mounts.py)
reports rejected geometry as findings; finishing a run does not mean its recipes
passed. To run a single recipe with the same checks, set `FLAN36_STUDY_RECIPE` to
`reference-16p6`, `nominal-15p6` or `limit-14p8` and use
[`study_slim_candidate.py`](../tools/freecad/study_slim_candidate.py) as the target.
