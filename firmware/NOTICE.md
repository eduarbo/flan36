# Firmware sources and notices

Flan36's shield, keymap and build tools are project sources under GPL-3.0-or-later. They originate from Eduardo's earlier Piantor Slim configuration and have been renamed, mapped to the Flan36 geometry and given a separate right-half pin assignment. This configuration does not change the upstream license of ZMK or its libraries.

Distributed UF2 files contain these separately licensed components. The complete pinned dependency list is in [west-frozen.yml](west-frozen.yml) and [dependencies.json](dependencies.json); build receipts identify the actual clean revisions and compiler inputs. Upstream sources are available at the URLs in the frozen manifest.

| Source | Notice retained here |
|---|---|
| ZMK `edf5c0814fd3ea202e43aad2d68fd32e882a518c` | [MIT](licenses/ZMK-MIT.txt) |
| Zephyr `dacab4875df72109b96cc8977547a0dc04875bcd` | [Apache 2.0](licenses/Zephyr-Apache-2.0.txt) |
| ARM CMSIS | [Apache 2.0](licenses/CMSIS-Apache-2.0.txt) |
| Nordic nrfx | [Nordic notice](licenses/Nordic-nrfx.txt) |
| LVGL | [MIT](licenses/LVGL-MIT.txt) |
| TinyCrypt | [BSD notice](licenses/TinyCrypt-BSD.txt) |
| Nanopb, included in the pinned dependency workspace | [zlib](licenses/Nanopb-zlib.txt) |
| GCC runtime | [GPL 3.0](licenses/GCC-GPL-3.0.txt), [Runtime Library Exception](licenses/GCC-runtime-exception.txt) |
| Newlib toolchain libraries | [Notices](licenses/Newlib-notices.txt) |

The compiler itself is not bundled. Toolchain identity is recorded to reproduce the candidate, not to promise identical output across machines. Follow the [firmware build guide](../docs/firmware.md). The binaries are untested on physical hardware.
