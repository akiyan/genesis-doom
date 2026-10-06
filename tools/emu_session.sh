#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Shared isolated Mednafen session. mode: shot, burst, audio.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/load_env.sh"
MODE=$1
ROM=$(realpath "$2")
OUT=$(realpath -m "$3")
WAIT=${4:-8}
PRESS=${5-Return}
LOADWAIT=${6:-6}
COUNT=${7:-1}
INTERVAL=${8:-0.5}
RUN_DIR=$(mktemp -d)
trap 'rm -rf "$RUN_DIR"' EXIT
mkdir -p "$RUN_DIR/snaps"
if [ "$MODE" = burst ]; then mkdir -p "$OUT"; else mkdir -p "$(dirname "$OUT")"; fi
# Honor an existing X session; otherwise allocate a private virtual display.
LAUNCH=(bash)
if [ -z "${DISPLAY:-}" ]; then LAUNCH=(xvfb-run -a -s '-screen 0 800x600x24' bash); fi
"${LAUNCH[@]}" -eu -c '
    export MEDNAFEN_HOME="$1"
    export SDL_VIDEODRIVER=x11
    mode=$2; rom=$3; out=$4; wait_time=$5; press=$6; load_wait=$7; count=$8; interval=$9
    audio_args=(-sound 0 -nothrottle 1)
    if [ "$mode" = audio ]; then audio_args=(-sound 1 -sound.driver sdl -soundrecord "$out"); fi
    mednafen -video.driver softfb -md.xscale 1 -md.yscale 1 "${audio_args[@]}" \
        -md.input.port1 gamepad \
        -md.input.port1.gamepad.up "keyboard 0x0 82" \
        -md.input.port1.gamepad.down "keyboard 0x0 81" \
        -md.input.port1.gamepad.left "keyboard 0x0 80" \
        -md.input.port1.gamepad.right "keyboard 0x0 79" \
        -md.input.port1.gamepad.a "keyboard 0x0 13" \
        -md.input.port1.gamepad.b "keyboard 0x0 14" \
        -md.input.port1.gamepad.c "keyboard 0x0 15" \
        -md.input.port1.gamepad.start "keyboard 0x0 40" \
        "$rom" >"$1/emulator.log" 2>&1 &
    emu_pid=$!
    trap "kill $emu_pid 2>/dev/null || true; wait $emu_pid 2>/dev/null || true" EXIT
    win=$(timeout 15 xdotool search --sync --pid "$emu_pid" --onlyvisible | head -1)
    sleep "$wait_time"
    xdotool windowfocus --sync "$win"
    for key in $press; do
        xdotool keydown "$key"
        sleep 0.2
        xdotool keyup "$key"
        sleep 0.6
    done
    sleep "$load_wait"
    if [ "$mode" = audio ]; then
        kill -TERM "$emu_pid"
        wait "$emu_pid" || true
        exit 0
    fi
    for ((i=1; i<=count; i++)); do
        if [ "$mode" = burst ]; then
            kill -0 "$emu_pid"
            printf -v name "%03d.png" "$i"
            import -window "$win" "$out/$name"
            sleep "$interval"
            continue
        fi
        xdotool keydown F9
        sleep 0.2
        xdotool keyup F9
        sleep "$interval"
    done
    sleep 1
    if [ "$mode" != burst ]; then
        newest=$(find "$1/snaps" -name "*.png" -printf "%T@ %p\n" | sort -nr | head -1 | cut -d" " -f2-)
        kill -0 "$emu_pid"
        if [ -n "$newest" ]; then
            cp "$newest" "$out"
        else
            # Some SDL/X sessions do not deliver the snapshot hotkey.
            import -window "$win" "$out"
        fi
    fi
' bash "$RUN_DIR" "$MODE" "$ROM" "$OUT" "$WAIT" "$PRESS" "$LOADWAIT" "$COUNT" "$INTERVAL"
echo "Output: $OUT"
