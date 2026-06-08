#!/bin/bash
# GenesisDoom ROM を desktop session の mednafen(softfb) で起動し F9 スクショ。
# 使い方: emu_shot.sh <rom.bin> <out.png> [wait_seconds]（省略時8秒）
# run_emu.sh の堅牢版(set -e なし・ウィンドウ待ち・F9 リトライ)。
ROM="$(realpath "$1")"; OUT="${2:-/tmp/emu_shot.png}"; WAIT="${3:-8}"
export XDG_RUNTIME_DIR=/run/user/1000
if [ -z "$DISPLAY" ]; then
  for d in 1 2 3 0; do
    if DISPLAY=:$d XAUTHORITY="$HOME/.Xauthority" xwininfo -root >/dev/null 2>&1; then
      DISPLAY=:$d
      XAUTHORITY="$HOME/.Xauthority"
      break
    fi
  done
fi
export DISPLAY
export XAUTHORITY="${XAUTHORITY:-$(pgrep -a Xwayland | grep -oE '/run/user/1000/[^ ]*auth[^ ]*' | head -1)}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

MD_INPUT_ARGS=(
  -md.input.port1 gamepad
  -md.input.port1.gamepad.a "keyboard 0x0 13"
  -md.input.port1.gamepad.b "keyboard 0x0 14"
  -md.input.port1.gamepad.c "keyboard 0x0 15"
)

systemctl --user reset-failed gdoom-emu.service 2>/dev/null
systemctl --user stop gdoom-emu.service 2>/dev/null
pkill -9 -f mednafen 2>/dev/null
sleep 1
rm -f ~/.mednafen/snaps/*.png 2>/dev/null

systemd-run --user --unit=gdoom-emu \
  --setenv=DISPLAY="$DISPLAY" --setenv=XAUTHORITY="$XAUTHORITY" \
  --setenv=XDG_RUNTIME_DIR=/run/user/1000 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  mednafen -video.driver softfb -sound 0 "${MD_INPUT_ARGS[@]}" "$ROM" >/dev/null 2>&1

# ウィンドウ出現を待つ(最大10s)
WIN=""
for i in $(seq 1 20); do
  sleep 0.5
  WIN=$(xwininfo -root -tree 2>/dev/null | grep -i mednafen | grep -oE '0x[0-9a-f]+' | head -1)
  [ -n "$WIN" ] && break
done
echo "win=$WIN active=$(systemctl --user is-active gdoom-emu.service 2>/dev/null)"
[ -z "$WIN" ] && { echo "NO WINDOW"; exit 0; }

sleep "$WAIT"                 # ロード/描画の進行を待つ
xdotool windowactivate --sync "$WIN" 2>/dev/null
sleep 0.5
xdotool key --window "$WIN" F9 2>/dev/null
sleep 1.5
SNAP=$(ls -t ~/.mednafen/snaps/*.png 2>/dev/null | head -1)
if [ -n "$SNAP" ]; then
  cp "$SNAP" "$OUT"
  echo "shot=$OUT"
else
  echo "NO SNAP"
fi
