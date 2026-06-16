#!/bin/bash
# GenesisDoom ROM を mednafen で起動し、エミュレート音声を WAV に録音して
# 「音楽(音)が鳴っているか」を判定するためのヘルパー。
# 使い方: emu_audio.sh <rom.bin> [out.wav] [wait_seconds]（省略時 12 秒）
# 録音後は必ず mednafen を終了させる(SIGTERMで正常終了させ WAV を確定)。
ROM="$(realpath "$1")"; OUT="${2:-/tmp/gdoom_audio.wav}"; WAIT="${3:-12}"
# デスクトップ(VNC/XFCE)は DISPLAY=:1。auth は ~/.Xauthority。
export XDG_RUNTIME_DIR=/run/user/1000 DISPLAY=:1
export XAUTHORITY=/home/ubuntu/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

hardkill() {
  systemctl --user stop gdoom-emu.service 2>/dev/null
  pkill -9 -f mednafen 2>/dev/null
}
trap hardkill EXIT

systemctl --user reset-failed gdoom-emu.service 2>/dev/null
systemctl --user stop gdoom-emu.service 2>/dev/null
pkill -9 -f mednafen 2>/dev/null
sleep 1
rm -f "$OUT" 2>/dev/null

# 実 ALSA カードが無い環境のため、SDL 音声ドライバ経由で pipewire-pulse に流す。
systemd-run --user --unit=gdoom-emu \
  --setenv=DISPLAY=:1 --setenv=XAUTHORITY=/home/ubuntu/.Xauthority \
  --setenv=XDG_RUNTIME_DIR=/run/user/1000 \
  --setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  --setenv=SDL_AUDIODRIVER=pulse \
  --setenv=PULSE_SERVER=unix:/run/user/1000/pulse/native \
  mednafen -video.driver softfb -sound 1 -sound.driver sdl \
  -soundrecord "$OUT" "$ROM" >/dev/null 2>&1

WIN=""
for i in $(seq 1 20); do
  sleep 0.5
  WIN=$(xwininfo -root -tree 2>/dev/null | grep -i mednafen | grep -oE '0x[0-9a-f]+' | head -1)
  [ -n "$WIN" ] && break
done
echo "win=$WIN active=$(systemctl --user is-active gdoom-emu.service 2>/dev/null)"

sleep "$WAIT"   # 音楽の進行を待ちながら録音

# 画面状態確認用に F9 スクショ → /tmp/gd_state.png
if [ -n "$WIN" ]; then
  rm -f ~/.mednafen/snaps/*.png 2>/dev/null
  xdotool windowactivate --sync "$WIN" 2>/dev/null
  sleep 0.4
  xdotool key --window "$WIN" F9 2>/dev/null
  sleep 1.2
  SNAP=$(ls -t ~/.mednafen/snaps/*.png 2>/dev/null | head -1)
  [ -n "$SNAP" ] && cp "$SNAP" /tmp/gd_state.png && echo "shot=/tmp/gd_state.png"
fi

# 正常終了させて soundrecord WAV を確定させる(SIGTERM)。
WPID=$(pgrep -f mednafen | head -1)
if [ -n "$WPID" ]; then
  kill -TERM "$WPID" 2>/dev/null
  for i in $(seq 1 20); do
    sleep 0.25
    kill -0 "$WPID" 2>/dev/null || break
  done
fi
hardkill
trap - EXIT
sleep 0.5

echo "=== mednafen journal (tail) ==="
journalctl --user -u gdoom-emu --no-pager 2>/dev/null | tail -15

if [ ! -f "$OUT" ]; then
  echo "NO WAV"; exit 0
fi
echo "=== wav ==="; ls -la "$OUT"
ffmpeg -hide_banner -nostats -i "$OUT" -af volumedetect -f null /dev/null 2>&1 \
  | grep -iE "Duration|mean_volume|max_volume|n_samples"
