#!/bin/bash
# SPDX-License-Identifier: MIT
# Capture a GEN_BENCH_FRAMES ROM after it freezes with a green border.
# Usage: bash tools/emu_bench_shot.sh rom.bin output.png [wait_seconds=45] [keys_before_wait]
# Each run has its own emulator state and X display; no existing process is killed.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/load_env.sh"
ROM=$(realpath "$1")
OUT=$(realpath -m "$2")
WAIT=${3:-45}
PRESS=${4:-}
RUN_DIR=$(mktemp -d /tmp/doom-bench-XXXXXX)
trap 'rm -rf "$RUN_DIR"' EXIT
mkdir -p "$RUN_DIR/snaps"
xvfb-run -a -s '-screen 0 800x600x24' bash -eu -c '
    export MEDNAFEN_HOME="$1"
    export SDL_VIDEODRIVER=x11
    mednafen -nothrottle 1 -video.driver softfb -sound 0 \
        -md.xscale 1 -md.yscale 1 "$2" >"$3.log" 2>&1 &
    emu_pid=$!
    trap "kill $emu_pid 2>/dev/null || true; wait $emu_pid 2>/dev/null || true" EXIT
    if [ -n "$5" ]; then
        win=$(timeout 10 xdotool search --sync --pid "$emu_pid" --onlyvisible | head -1)
        xdotool windowfocus --sync "$win"
        sleep 1
        xdotool key --delay 200 $5
    fi
    sleep "$4"
    kill -0 "$emu_pid"
    win=$(xdotool search --pid "$emu_pid" --onlyvisible | head -1)
    xdotool windowfocus --sync "$win"
    xdotool key F9
    sleep 2
    snap=$(find "$1/snaps" -name "*.png" -print -quit)
    if [ -n "$snap" ]; then
        cp "$snap" "$3"
    else
        import -window "$win" "$3"
    fi
' bash "$RUN_DIR" "$ROM" "$OUT" "$WAIT" "$PRESS"
echo "Screenshot: $OUT (confirm green border and completed tick count)"
