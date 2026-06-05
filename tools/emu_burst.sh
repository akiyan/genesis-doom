#!/bin/bash
# ROM を起動し、F9 を一定間隔で連射してスナップを連続取得する(例外ニブル点滅の復号用)。
# 使い方: emu_burst.sh <rom.bin> <outdir> [count] [interval]
ROM="$(realpath "$1")"; OUT="${2:-/tmp/burst}"; N="${3:-44}"; IV="${4:-0.5}"
export XDG_RUNTIME_DIR=/run/user/1000 DISPLAY=:0
export XAUTHORITY=$(pgrep -a Xwayland | grep -oE '/run/user/1000/[^ ]*auth[^ ]*' | head -1)
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
rm -rf "$OUT"; mkdir -p "$OUT"

systemd-run --user --unit=gdoom-emu \
  --setenv=DISPLAY=:0 --setenv=XAUTHORITY="$XAUTHORITY" \
  --setenv=XDG_RUNTIME_DIR=/run/user/1000 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  mednafen -video.driver softfb -sound 0 "${MD_INPUT_ARGS[@]}" "$ROM" >/dev/null 2>&1

WIN=""
for i in $(seq 1 20); do
  sleep 0.5
  WIN=$(xwininfo -root -tree 2>/dev/null | grep -i mednafen | grep -oE '0x[0-9a-f]+' | head -1)
  [ -n "$WIN" ] && break
done
echo "win=$WIN active=$(systemctl --user is-active gdoom-emu.service 2>/dev/null)"
[ -z "$WIN" ] && { echo "NO WINDOW"; exit 0; }
xdotool windowactivate --sync "$WIN" 2>/dev/null
sleep 0.1

for k in $(seq 1 "$N"); do
  xdotool key --window "$WIN" F9 2>/dev/null
  sleep "$IV"
done
sleep 1
# 収集(撮影順 = 時系列)
j=0
for f in $(ls -tr ~/.mednafen/snaps/*.png 2>/dev/null); do
  printf -v nm "%03d" "$j"
  cp "$f" "$OUT/$nm.png"; j=$((j+1))
done
echo "captured $j frames -> $OUT"
systemctl --user stop gdoom-emu.service 2>/dev/null
