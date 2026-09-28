# Design with free tools

**KiCad for the circuit. FreeCAD for the case. StepUp to bring them together.**

## Start here

1. Download the [complete repository ZIP](https://github.com/eduarbo/flan36/archive/refs/heads/main.zip) and unzip it.
2. Install [FreeCAD](https://www.freecad.org/downloads.php) and [KiCad](https://www.kicad.org/download/).
3. In FreeCAD’s Addon Manager, install [KiCad StepUp](https://github.com/easyw/kicadStepUpMod).
4. Open [`mechanical/revI/Flan36.FCStd`](../mechanical/revI/Flan36.FCStd). Importing STEP instead loses the editable history.

The source opens and recomputes without StepUp, CadQuery or custom Python proxies. StepUp is only needed for exchange with KiCad. KLP keycaps and the 36 linked Choc v1 instances are meshes. The nano, display and standard switches have separate nominal visual parts; some connectors remain dimensional reserves. [Component sources and limits](../components/README.md).

## Navigate the assembly

The tree contains **Parameters**, **Left** and **Right**. Select a part and press **Space** to hide or show it. Expand **Construction** for sketches and operations. Each half has an **ActiveFrame** link to one of ten cover bodies; an **ActiveBattery** link selects Adafruit 1570 or 301230. Hidden alternatives do not represent extra installed parts.

For keycaps, frame styles and colors, use the [configurator and companion macro](customize.md#save-a-configuration-for-freecad). Keep a personal copy with **File → Save As** before editing dimensions.

## Three editing examples

### 1. Change the cover

In **Parameters**, increase `FrameTop` by **0.4 mm** and recompute. The cover and its co-printed color volumes follow the new roof together; no decoration rises above it. Save, close and reopen to confirm the change, then restore the original value.

`FrameRoof` controls roof thickness and `WindowMargin` the clearance around the glass. Start from 1.2 and 0.4 mm respectively. The supplied dimensions were checked as a nominal assembly; arbitrary edits are not automatically cleared for fit or printing. For new frame shapes, edit the outline sketch (or loft sections for Beveled/Faceted) while preserving the shared cavity and mounts.

### 2. Move the display

Hide the active frame and keycaps. Change `DisplayShiftY` from **2.4 to 3.4 mm**. The complete display, sled and window move together; do not drag the glass alone. Restore 2.4 mm before comparison with the published PCB.

`MCUShiftY`, `MCUBottom`, `BatteryShiftY`, `BatteryBottom` and plate dimensions provide other study controls. **Moving a part in FreeCAD does not update KiCad footprints or traces.**

### 3. Inspect the PCB with StepUp

Open `hardware/revI/flan36-left.kicad_pro` in KiCad. RevI matches the chosen contour and adds battery/magnet clearances. The current slim interfaces use a 2 mm JST PH footprint at J1, a bottom-mounted reset at SW2, and the revised battery opening. All key transforms and nets are preserved. Switches are locked to preserve the layout; both boards remain unrouted.

The project-relative STEP files show the current nominal component models in KiCad's 3D Viewer. Their source, colors and placement are checked without changing footprints. The side-entry battery connector is a nominal reconstruction; measured fit limits remain identified in the [component guide](../components/README.md).

In StepUp, enable **Virtual models**, keep **Grid Origin**, include holes from **0 mm**, and apply no outline tolerance. The boards’ grid origin is explicitly **(10, 10) mm**. In a new FreeCAD document, use **Load KiCad PCB**.

Work on a copy for **Pull Sketch from PCB** / **Push Sketch to PCB**. The historical revF exchange example moves only the battery opening’s rear edge from KiCad **Y 46.95 to 47.45 mm**, along with its two connecting segments. Reopen the copy in KiCad and verify that switch centers, angles, pads, connectivity and the outer contour are unchanged. This demonstrates exchange, not an approved battery-opening improvement.

The native assembly uses **X = KiCad X, Y = −KiCad Y**, with PCB top at **Z 5.4 mm**. To overlay a StepUp import for inspection, move its complete group by **X +10, Y −10, Z +5.4 mm**. Preserve the original import for pushing back. The right half’s **161 mm X separation** in the assembly is visual only and must never be written to its PCB.

## Export the right file

| Format | Use |
|---|---|
| FCStd | Editable mechanical source and assembly history |
| KiCad project / schematic / PCB | Editable circuit, layout and routing |
| STEP | Solid geometry for other CAD tools; no full feature history or KLP meshes |
| STL | Individual part for slicing; check orientation and fit first |
| GLB from the viewer | Visual assembly with selected keycaps and frames, in meters |
| Configuration JSON | Keycap variants, rotations and individual colors; case/frame colors and battery profile; not manual shape edits |

Select a part and use **File → Export**. Store exports outside the reference folders and keep the edited FCStd. The generation scripts rebuild the reference from scratch and overwrite its files; do not run them over manual work.

The project remains a digital prototype. Both boards have **zero geometric DRC violations and 104 unconnected items each**; measured minimum pad-to-outline clearance is about **0.524 mm**. Final cable/connector geometry, printed fit and retention, RF and power measurements remain open. [CAD reproduction and validation](cad.md).

## Interchangeable cases

[Solid, Color rim and Terrace](cases.md) are native source bodies. The configuration macro changes `ActiveTray` and `ActivePlate` per half. `DisplayCoverInstalled` records whether to include the printed frame and its steel targets; JSON import applies the corresponding visibility, and export honors this property. Save a custom FCStd copy to retain your choices. The property represents installation, independently from temporary eye visibility.
