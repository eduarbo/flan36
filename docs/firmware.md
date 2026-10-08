# Firmware

Flan36 uses **ZMK v0.3.0**, pinned to `edf5c0814fd3ea202e43aad2d68fd32e882a518c`, on genuine **nice!nano v2** controllers with the standard UF2 bootloader. These files have been compiled and checked against the electrical matrix; flashing, radio operation and power use still need hardware tests.

| Download | Role | Display |
|---|---|---|
| [Left UF2](../firmware/uf2/flan36-left.uf2) | Central: connects to the computer | nice!view |
| [Right UF2](../firmware/uf2/flan36-right.uf2) | Peripheral: connects to the left half | nice!view |
| [Right UF2 without display](../firmware/uf2/flan36-right-no-display.uf2) | Peripheral, optional single-screen build | None |

Use one right-hand file. Both right variants use the same PCB pinout. USB on the right supports charging and bootloader access; the left half provides the keyboard's USB connection to the computer.

## Keymap

The [editable keymap](../firmware/config/flan36.keymap) has four layers. The physical order is left-to-right across the complete keyboard, including the six thumb keys. F and J correspond to the homing caps in the CAD.

- **Base:** QWERTY; left thumbs Ctrl/Esc, Numbers, Shift/Space; right thumbs Shift/Enter, Symbols, GUI/Backspace. Slash-separated keys tap the second function and hold the first.
- **Numbers:** digits, navigation, F1–F10.
- **Symbols:** punctuation, Alt/Delete, F11/F12 and volume.
- **Settings:** hold Symbols, then the Numbers thumb. Top row selects Bluetooth profiles 1–5, clears the active profile, selects BLE or USB, enters bootloader, or resets.

Sleep starts after 15 minutes; idle begins after 30 seconds. The scan matrix uses interrupts and supports waking by keypress. RGB, backlight and USB logging are disabled. Each display uses ZMK's official nice!view driver and status widget. The right display reports its local peripheral status; the left is not configured to proxy the right battery level.

## Wiring contract

| Function | Pro Micro labels | nRF52840 pins |
|---|---|---|
| Left rows 0–3 | D2, D3, D4, D5 | P0.17, P0.20, P0.22, P0.24 |
| Right rows 0–3 | D21, D20, D19, D18 | P0.31, P0.29, P0.02, P1.15 |
| Left column 0 / right column 0 | D6 / D15 | P1.00 / P1.13 |
| Both columns 1–5 | D7, D8, D9, D10, D16 | P0.11, P1.04, P1.06, P0.09, P0.10 |
| Display MOSI / SCK / CS | D1 / D0 / D14 | P0.06 / P0.08 / P1.11 |

The matrix has 18 populated positions per half. Electrical column 0 holds one thumb; it is not a sixth physical finger column. Diode cathodes connect to rows (`col2row`). The halves use different MCU pins to route around the battery opening without changing the case. The right transform reverses the visual key order. The [per-half pin map](../design/pinmap.json) is checked against both compiled firmware and PCB pads.

Flan36 defines its own `nice_view_spi`; **do not add `nice_view_adapter`**, whose default pins conflict with this matrix. Display CS is active high. UART and competing I²C/SPI controllers are disabled. The standard nice!nano bootloader configures the two NFC-capable pins used by columns 4/5 as GPIO; a clone or different bootloader must establish that independently.

## Build locally

The verified environment uses west 1.5, CMake, Ninja, Python build dependencies and the existing macOS GCC ARM 15.2.0 toolchain. The builder requires the compiler SHA-256 `7528680ad6078c1d2dd67a414fca656e5d78e56e7bc31f422a849bb15a7db04a`; another platform/compiler needs separate qualification. [west-frozen.yml](../firmware/west-frozen.yml) fixes all dependency revisions. Binary identity across different paths or machines is not promised.

The build expects the ZMK checkout **at the workspace root**, with its `app/` and the dependency `zephyr/` beside it. For a new, empty workspace, use this layout:

```sh
export FLAN36_REPO=/absolute/path/to/flan36
export FLAN36_ZMK_WORKSPACE=/absolute/path/to/new-zmk-workspace
git clone --no-checkout https://github.com/zmkfirmware/zmk.git "$FLAN36_ZMK_WORKSPACE"
git -C "$FLAN36_ZMK_WORKSPACE" checkout --detach edf5c0814fd3ea202e43aad2d68fd32e882a518c
west init -l "$FLAN36_ZMK_WORKSPACE/app"
cd "$FLAN36_ZMK_WORKSPACE"
west config manifest.file "$FLAN36_REPO/firmware/west-frozen.yml"
west manifest --validate
west update
west zephyr-export
cd "$FLAN36_REPO"
```

The external frozen-manifest selection and resolved paths were checked with west 1.5; builds reused an existing clean pinned workspace. The three binaries were rebuilt there with all 39 active dependency repositories checked. The conventional config-repository manifest in `firmware/config/west.yml` uses a different directory layout; it is not the initialization recipe for this builder.

```sh
export FLAN36_ZMK_WORKSPACE=/absolute/path/to/west-workspace
export CROSS_COMPILE=/absolute/path/to/arm-none-eabi-
# Activate the Python environment with west and Ninja on PATH.
# Optional: FLAN36_WEST=/absolute/path/to/venv/bin/west
sh tools/build_firmware.sh
python3 tools/check_firmware.py --zephyr "$FLAN36_ZMK_WORKSPACE/zephyr" --publish
```

The script expects the pinned ZMK checkout at `app/` and Zephyr at `zephyr/`, both clean. All active dependencies must match the pinned list and be clean. This version uses target `nice_nano_v2`; newer ZMK targets differ. The checker reads the actual compiled devicetrees, all 36 mappings, GPIO assignments, roles, sleep settings and every UF2 block. Before and after each build, the script records and compares sources, dependencies and compiler inputs. The checker requires that build-time attestation and verifies every output hash before copying any file. It records [source and binary hashes](../validation/revI-firmware.json).

`python3 tools/test_firmware_binding.py --zephyr "$FLAN36_ZMK_WORKSPACE/zephyr"` checks, in an isolated copy, that a changed key binding or altered binary is rejected without changing published files. Build products in `build/firmware-*` regenerate with these commands. [Dependency notices](../firmware/NOTICE.md).

## First hardware test

1. Verify battery connector polarity and inspect the assembled PCB for shorts before applying power. Keep the nice!nano **BOOST jumper open**: the selected small cells must not use its 500 mA charge mode.
2. Connect a USB data cable, double-tap reset and copy the matching UF2 to the bootloader drive. Do each half separately.
3. Power both halves, select profile 1 and pair **Flan36** with the computer. Verify all 36 keys and layer/thumb functions, including simultaneous presses and releases.
4. Check both displays, reset recovery, BLE reconnection, sleep/wake and measured current with the final assembled case. Repeat wake testing with both displays installed.
5. For charging, SW1 must connect the cell. With USB attached, opening SW1 disconnects the cell from charging but does not necessarily turn off the controller. Confirm the actual pack's permitted charge current before connecting it.

No real device has been flashed or electrically qualified by these build checks.

Sources: [nice!nano installation](https://nicekeyboards.com/docs/nice-nano/getting-started/), [nice!view pinout](https://nicekeyboards.com/docs/nice-view/pinout-schematic/), [ZMK v0.3.0](https://github.com/zmkfirmware/zmk/releases/tag/v0.3.0), [matrix configuration](https://zmk.dev/docs/config/kscan).
