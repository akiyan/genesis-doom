#!/bin/bash
# GenesisDoom ROM を デスクトップセッションの mednafen(softfb) で起動し F9 スクショを撮る。
# 使い方: run_emu.sh <rom.bin> [outname]
# 詳細はメモリ emulator-launch 参照。
set -e
ROM="$(realpath "$1")"; OUT="${2:-shot}"   # systemd サービスは cwd が違うので絶対パス必須
AUTH=$(pgrep -a Xwayland | grep -oE '/run/user/1000/[^ ]*auth[^ ]*' | head -1)
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
export DISPLAY=:0 XAUTHORITY="$AUTH"

systemctl --user reset-failed gdoom-emu.service 2>/dev/null || true
systemctl --user stop gdoom-emu.service 2>/dev/null || true
pkill -9 -f mednafen 2>/dev/null || true
sleep 1
rm -f ~/.mednafen/snaps/*.png 2>/dev/null || true

systemd-run --user --unit=gdoom-emu \
  --setenv=DISPLAY=:0 --setenv=XAUTHORITY="$AUTH" \
  --setenv=XDG_RUNTIME_DIR=/run/user/1000 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  mednafen -video.driver softfb -sound 0 "$ROM" >/dev/null 2>&1
sleep 7

WIN=$(xwininfo -root -tree 2>/dev/null | grep -iE '"[^"]*": \("mednafen"' | grep -oE '0x[0-9a-f]+' | head -1)
echo "win=$WIN active=$(systemctl --user is-active gdoom-emu.service)"
xdotool windowactivate --sync "$WIN" 2>/dev/null || true
sleep 0.5
xdotool key --window "$WIN" F9 2>/dev/null || true
sleep 1.5
SNAP=$(ls -t ~/.mednafen/snaps/*.png 2>/dev/null | head -1)
cp "$SNAP" "/tmp/$OUT.png"
echo "snap=/tmp/$OUT.png ($(identify -format '%wx%h colors=%k' "/tmp/$OUT.png"))"
