# Credits and licenses

Flan36 and its CAD are an original design by Eduardo Ruiz. Piantor by beekeeb was an inspiration for the number of keys. Imported reference files and third-party component meshes are credited individually below; their provenance does not make the complete Flan36 CAD a derivative of Piantor. There is no implied affiliation or certification by beekeeb or component manufacturers.

| Material | Author / source | License and changes |
|---|---|---|
| `sources/piantor/*.kicad_pcb` | beekeeb / Leo, [Piantor](https://github.com/beekeeb/piantor), commit `cd847afb4f9a86e8c1c8e36f243140644013afb2` | GPL-3.0; unchanged original copies |
| Choc footprint `keyswitches:Kailh_socket_PG1350_optional` | daprice, [keyswitches.pretty](https://github.com/daprice/keyswitches.pretty) | CC-BY-SA-4.0; notice in [LICENSES/Keyswitches.md](LICENSES/Keyswitches.md) |
| `Keebio-Parts:TRRS-PJ-320A` footprint | [Keebio](https://github.com/keebio/Keebio-Parts.pretty), commit `063565dcba9a8ee807d49772de0ed75ecaedcc26` | MIT; copyright/permission in [LICENSES/Keebio-MIT.txt](LICENSES/Keebio-MIT.txt) |
| `RPi_Pico:RPi_Pico_SMD_TH` footprint | [TPCWare / Nicola Carandini](https://github.com/ncarandini/KiCad-RP-Pico), commit `dc6f9b9f213dc36eebce626aa9ee72a333fa0db3` | [TPCWare license](LICENSES/TPCWare-KiCad.txt): CC-BY-SA-4.0 with design exception |
| Standard KiCad footprints, including `Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | [KiCad libraries](https://www.kicad.org/libraries/license/) | [CC-BY-SA-4.0 with design exception](LICENSES/KiCad-Libraries.md) |
| `design/layout.json`, layout diagram | Archived coordinate-reference provenance: Piantor source commit and source-coordinate fields | GPL-3.0; existing reference metadata retained unchanged. This is file-level historical provenance, not attribution of the complete CAD |
| `keycaps/*.stl`, `keycaps/variants/*.stl`, KLP meshes in FCStd/viewer/GLB | [KLP Lamé by braindefender](https://github.com/braindefender/KLP-Lame-Keycaps), commit `4a67a824232d3054c61599ea047c56a340faaba2` | CC-BY-SA-4.0; unchanged meshes, placed and colored. RevG catalogs all 38 Choc-stem files, Choc/MX body sizes. [Original three sources](keycaps/sources.json), [complete pinned sources](keycaps/variants-source.json) |
| `docs/images/revE-*.png` through `revI-*.png`, including case screenshots | Original Flan36 CAD renders incorporating credited KLP Lamé meshes | CC-BY-SA-4.0; calculated from attributed meshes, no image retouching |
| Original CAD, project tools and original documentation | Eduardo Ruiz / Flan36 contributors | GPL-3.0-or-later, except identified materials above |
| Embedded 3D engine | [Three.js](https://github.com/mrdoob/three.js), 0.180.0 | MIT; full [notice](LICENSES/Three-MIT.txt) also embedded in offline HTML |
| External product photos in the parts guide | Typeractive, Adafruit and respective rights holders | Linked/embedded from supplier listings; not copied into the asset tree or relicensed under the repository license |

The viewer retains source notices; exported GLB includes attribution and source/license links. Viewer code is under GPL-3.0-or-later; esbuild is a pinned build dependency. Gzip packaging does not alter the underlying geometry.

The three `docs/images/branding/flan36-*-concept.png` boards were generated with OpenAI's built-in image generation tool for Eduardo's Flan36 identity exploration. They are concept art, not renders of the measured CAD. Four additional Caramel refinements (`flan36-caramel-soft.png`, `flan36-caramel-drop.png`, `flan36-caramel-bold.png`, `flan36-caramel-outline.png`) use the selected Caramel board as their reference. Prompts and provenance are retained in `design/branding-prompts.json`, `design/branding-caramel-prompts.json` and `design/branding.json`; their reuse follows the repository's GPL-3.0-or-later terms to the extent applicable.

Full texts: [GPL](LICENSE), [CC-BY-SA-4.0](LICENSES/CC-BY-SA-4.0.txt). Original upstream hashes: [sources/manifest.json](sources/manifest.json).

Libraries under `hardware/revF/libraries` contain KiCad sources with the design exception, daprice’s Choc footprint under CC-BY-SA-4.0, and Flan36 symbols/footprints. STEP files under `hardware/revF/models` are original nominal envelopes, not manufacturer-certified models.

FreeCAD, StepUp, ZMK, Zephyr, nice!nano and nice!view retain their own names/licenses. FreeCAD/StepUp are installed separately; firmware candidates are distributed with pinned sources and [dependency notices](firmware/NOTICE.md). Supplier links do not imply sponsorship.

## Commercial component representations

KiSwitch Choc v1 source CAD is used under its MIT option (copyright 2019–2022 keyswitch-kicad-library contributors). KiCad PCM12, TL3342 and SOD-123 assets use CC-BY-SA-4.0 with the KiCad library exception. See [per-file sources, transformations and limits](components/README.md) and [asset hashes](components/sources.json). nice!nano v2 is an original nominal reconstruction referenced to official photographs and the Woovie community drawing; no official photograph is embedded or relicensed.

The `docs/branding/outline/flan36-*.svg` artwork is a deterministic vector conversion of the selected Outline board’s monochrome reference. Letterforms are traced paths, not a bundled or substituted font. Source, reference hash and contour checks are recorded in `tools/build_outline_logo.py`, `validation/branding-outline-trace.json` and `design/branding-outline-vectors.json`. The preview and SVG kit follow GPL-3.0-or-later to the extent applicable.

## CAD authorship correction · 2026-10-09

Earlier viewer credits, GLB metadata and project descriptions incorrectly described the whole CAD as derived from Piantor. Eduardo Ruiz clarified that the CAD is his original design and Piantor inspired the key count. Current descriptions and exports reflect that correction. Historical coordinate-reference metadata, archived upstream copies and third-party license notices are preserved; no geometry or license terms changed.
