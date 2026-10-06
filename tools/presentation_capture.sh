#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Isolated Mednafen captures for the presentation; leaves other sessions alone.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/load_env.sh"
ROM=$(realpath "$1")
OUT=$(realpath -m "$2")
mkdir -p "$OUT"
RUN_DIR=$(mktemp -d /tmp/doom-presentation-XXXXXX)
xvfb-run -a -s '-screen 0 1024x768x24' bash -eu -c '
  export MEDNAFEN_HOME="$1"
  export SDL_VIDEODRIVER=x11
  mkdir -p "$1/snaps"
  mednafen -nothrottle 1 -video.driver softfb -sound 0 -md.xscale 1 -md.yscale 1 \
    -md.input.port1 gamepad \
    -md.input.port1.gamepad.up "keyboard 0x0 82" \
    -md.input.port1.gamepad.right "keyboard 0x0 79" \
    -md.input.port1.gamepad.start "keyboard 0x0 40" \
    "$2" >"$3/capture.log" 2>&1 &
  emu_pid=$!
  trap "kill $emu_pid 2>/dev/null || true; wait $emu_pid 2>/dev/null || true" EXIT
  win=$(timeout 15 xdotool search --sync --pid "$emu_pid" --onlyvisible | head -1)
  xdotool windowfocus --sync "$win"
  shot() {
    xdotool windowfocus --sync "$win"
    xdotool keydown F9
    sleep 0.2
    xdotool keyup F9
    sleep 1
    newest=$(find "$1/snaps" -name "*.png" -printf "%T@ %p\n" | sort -nr | head -1 | cut -d" " -f2-)
    if [ -n "$newest" ]; then
      cp "$newest" "$3/$4.png"
    else
      import -window "$win" "$3/$4.png"
    fi
    echo "Captured $4"
  }
  sleep 3
  shot "$1" "$2" "$3" title
  xdotool keydown Return
  sleep 0.3
  xdotool keyup Return
  sleep 8
  shot "$1" "$2" "$3" spawn
  xdotool keydown Up
  sleep 0.6
  xdotool keyup Up
  sleep 5
  shot "$1" "$2" "$3" moved
  xdotool keydown Right
  sleep 0.25
  xdotool keyup Right
  sleep 5
  shot "$1" "$2" "$3" turn
  xdotool keydown Up
  sleep 0.6
  xdotool keyup Up
  sleep 5
  shot "$1" "$2" "$3" final
' bash "$RUN_DIR" "$ROM" "$OUT"
echo "Isolated emulator state: $RUN_DIR"
