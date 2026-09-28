# Creative frames

Choose a thumbnail in the [viewer](https://eduarbo.github.io/flan36/), adjust its HEX colors and export the print kit. All seven decorative frames use **flush inlays**; Smooth, Beveled and Faceted remain plain options.

| Frame | Motif | Default palette |
| --- | --- | --- |
| Handheld | D-pad, buttons and speaker | Cream, charcoal, berry, gray |
| Retro TV | CRT surround, tuning dial and grille | Walnut, ivory, brass, charcoal |
| Cyberpunk | Vents, traces and status panel | Graphite, steel, cyan, magenta |
| Cartridge | Grip ribs, label and contact fingers | Saffron, violet, pale gold, coral |
| Arcade | Marquee, joystick and buttons | Midnight, violet, pink, yellow |
| Mecha | Armor, hazard bars and reactor | Ivory, slate, orange, cyan |
| Kintsugi | Porcelain islands and repair lines | Blue, porcelain, gold, celadon |

Controls are decorative. The **0.4 mm** color volumes replace material in the roof and finish at its top surface. The checked backing is at least **0.8 mm**. Each design inherits the Smooth frame's screen window, service openings and magnetic interfaces.

**Download print kit** includes the recessed shell and aligned inlay volumes as a multipart 3MF and individual STLs. Co-print them as one assembly. The fused single-color STL has the complete plain envelope; it cannot carry the inlay pattern by itself. Some details are only **0.45 mm** wide, so inspect the sliced paths. [Printing and filament assignment](themes-printing.md).

## Edit in FreeCAD

Open [Flan36.FCStd](../mechanical/revI/Flan36.FCStd) and expand **Construction → Flush frame materials**. Boxes, cylinders, sketches and Boolean operations remain native editable features. `MaterialParts` identifies the body and three inlay colors; `InlayDepth` follows the top surface through expressions. No custom Python proxy is required.

Save a personal copy before editing. Keep the inlays within the roof, preserve backing and rerun the [slim/flush checks](slim-flush.md). The shared recipes are in [frame-finishes.json](../design/frame-finishes.json) and [frame-extensions.json](../design/frame-extensions.json).

Printed fit, multicolor bonding and magnetic retention still need a physical trial.
