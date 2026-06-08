#!/bin/bash
# GenesisDoom ROM を desktop session の mednafen(softfb) で起動し F9 スクショ。
# 使い方: emu_shot.sh <rom.bin> <out.png> [wait_seconds]（省略時8秒）
# run_emu.sh の堅牢版(set -e なし・ウィンドウ待ち・F9 リトライ)。
ROM="$(realpath "$1")"; OUT="${2:-/tmp/emu_shot.png}"; WAIT="${3:-8}"
TELEGRAM_NOTICE_CHAT_ID="${TELEGRAM_NOTICE_CHAT_ID:-}"
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

systemd-run --user --unit=gdoom-emu \
  --setenv=DISPLAY=:0 --setenv=XAUTHORITY="$XAUTHORITY" \
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
  if [ -n "${TELEGRAM_NOTICE_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_NOTICE_CHAT_ID:-}" ] && command -v curl >/dev/null 2>&1; then
    CAPTION="$(basename "$ROM") $(date +%Y-%m-%dT%H:%M:%S%z)"
    if curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_NOTICE_BOT_TOKEN}/sendPhoto" \
      -F "chat_id=${TELEGRAM_NOTICE_CHAT_ID}" \
      -F "photo=@${OUT}" \
      -F "caption=${CAPTION}" >/dev/null; then
      echo "telegram=sent"
    else
      echo "telegram=failed"
    fi
  fi
else
  echo "NO SNAP"
fi
