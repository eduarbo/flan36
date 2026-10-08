#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${FLAN36_ZMK_WORKSPACE:?Set to a west workspace containing the pinned ZMK and Zephyr sources}"
: "${CROSS_COMPILE:?Set to the verified arm-none-eabi- toolchain prefix}"
WEST=${FLAN36_WEST:-west}
command -v ninja >/dev/null || { echo 'Ninja must be on PATH (activate the build environment).' >&2; exit 1; }
APP="$FLAN36_ZMK_WORKSPACE/app"
test "$(git -C "$APP" rev-parse HEAD)" = edf5c0814fd3ea202e43aad2d68fd32e882a518c
test "$(git -C "$FLAN36_ZMK_WORKSPACE/zephyr" rev-parse HEAD)" = dacab4875df72109b96cc8977547a0dc04875bcd
test -z "$(git -C "$APP" status --porcelain)"
test -z "$(git -C "$FLAN36_ZMK_WORKSPACE/zephyr" status --porcelain)"
export ZEPHYR_TOOLCHAIN_VARIANT=cross-compile
export ZEPHYR_BASE="$FLAN36_ZMK_WORKSPACE/zephyr"
cd "$FLAN36_ZMK_WORKSPACE"
if [ "$#" -eq 0 ]; then set -- left right right-no-display; fi
for variant in "$@"; do
  python3 "$ROOT/tools/firmware_inputs.py" start "$variant"
  case "$variant" in
    left|right)
      "$WEST" build -p always -s "$APP" -d "$ROOT/build/firmware-$variant" -b nice_nano_v2 -- \
        "-DSHIELD=flan36_$variant nice_view" "-DZMK_CONFIG=$ROOT/firmware/config" ;;
    right-no-display)
      "$WEST" build -p always -s "$APP" -d "$ROOT/build/firmware-right-no-display" -b nice_nano_v2 -- \
        -DSHIELD=flan36_right "-DZMK_CONFIG=$ROOT/firmware/config" \
        "-DEXTRA_CONF_FILE=$ROOT/firmware/config/no-display.conf" ;;
    *) echo "Unknown firmware variant: $variant" >&2; exit 1 ;;
  esac
  python3 "$ROOT/tools/firmware_inputs.py" finish "$variant"
done
