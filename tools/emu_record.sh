#!/bin/bash
# SPDX-License-Identifier: MIT
# GenesisDoom ROM を RetroArch + Genesis Plus GX で決定的に録画し、ffmpeg で
# 「完成フレーム探し用コンタクトシート」と「最終フレーム」を書き出す。
# genesis-novel/scripts/demo_build_record.sh の RetroArch 経路を踏襲(音声は省略)。
#
# なぜ RetroArch + GPGX + --max-frames か:
#   Doom の 3D 描画は約0.85fps(1フレーム約1.2秒)で、60Hz 表示の大半は「描画途中の
#   フレームバッファ」を映す。F9 一発スナップはほぼ確実に描画途中(段 STP/CLP 等)を
#   撮ってしまう。--max-frames N で「ちょうど N エミュフレーム」走らせて全フレームを
#   録画し、後から描画が完成したフレームを選ぶ。これで実時間待ちのブレを排除する。
#
# 前提: ROM は -DGEN_AUTOSTART でビルドし、タイトルのボタン待ちを飛ばすこと
#       (無入力で E1M1 へ直行 → 完全に決定的)。
#
# 使い方: emu_record.sh <rom> <out_dir> [max_frames=900]
#   max_frames : 走らせるエミュフレーム数(60=1秒相当)。既定900=15秒相当。
#                0.85fps なら ~12 回の完成描画を含む。
#
# 出力(out_dir 内):
#   sheet.png … 末尾付近を等間隔サンプルした 4x3 タイル(完成フレームを目視選択)
#   last.png  … 最終フレーム
#   rec.mkv   … 生録画(ffv1 lossless)。個別抽出に使う
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/load_env.sh"
ROM="$(realpath "$1")"; OUTDIR="${2:-/tmp/emu_rec}"; MAXF="${3:-900}"

: "${GPGX_CORE:?Set GPGX_CORE to the installed Genesis Plus GX library in .env}"

if [ ! -f "$ROM" ]; then echo "NO ROM: $ROM"; exit 1; fi
command -v retroarch >/dev/null 2>&1 || { echo "NO RETROARCH"; exit 1; }
command -v ffmpeg     >/dev/null 2>&1 || { echo "NO FFMPEG"; exit 1; }
[ -f "$GPGX_CORE" ] || { echo "NO GPGX CORE: $GPGX_CORE"; exit 1; }
mkdir -p "$OUTDIR"

# 空き X ディスプレイ番号を探して自前 Xvfb を起動(genesis-novel と同方式)。
DISP=""; OWN_XVFB=0
unset XAUTHORITY
for n in 99 121 122 123 124 125 126 127; do
  [ -e "/tmp/.X${n}-lock" ] && continue
  [ -S "/tmp/.X11-unix/X${n}" ] && continue
  Xvfb ":${n}" -screen 0 800x600x24 -nolisten tcp >"/tmp/doom_xvfb_${n}.log" 2>&1 &
  OWN_XVFB=$!
  for _ in $(seq 1 30); do
    DISPLAY=":${n}" xdotool getdisplaygeometry >/dev/null 2>&1 && { DISP=":${n}"; break; }
    sleep 0.2
  done
  [ -n "$DISP" ] && break
  kill "$OWN_XVFB" 2>/dev/null || true; OWN_XVFB=0
done
[ -n "$DISP" ] || { echo "error: 空き X ディスプレイを確保できない" >&2; exit 1; }
export DISPLAY="$DISP" SDL_VIDEODRIVER=x11 SDL_VIDEO_X11_XINPUT2=0
echo "==> Xvfb display ${DISP}"

cleanup() {
  [ "$OWN_XVFB" != 0 ] && kill "$OWN_XVFB" 2>/dev/null || true
}
trap cleanup EXIT

# 録画コーデック = ffv1 lossless(既定プリセットは低ビットレートで潰れる)。
REC_CFG="$OUTDIR/retroarch_record.cfg"
cat > "$REC_CFG" <<'EOF'
vcodec = ffv1
acodec = flac
pix_fmt = yuv444p
EOF

# 音声は使わないので null。menu 無効・非スレッド・録画品質0(=設定ファイル準拠)。
CFG="$OUTDIR/retroarch_demo.cfg"
cat > "$CFG" <<EOF
video_driver = "gl"
audio_driver = "null"
audio_enable = "false"
menu_driver = "null"
video_fullscreen = "false"
video_threaded = "false"
video_record_quality = "0"
video_record_config = "$REC_CFG"
EOF

RAW="$OUTDIR/rec.mkv"; rm -f "$RAW"
echo "==> RetroArch+GPGX 録画 (max-frames=${MAXF}, size=256x224) -> $RAW"
timeout $(( MAXF / 60 + 120 )) retroarch -L "$GPGX_CORE" "$ROM" --config "$CFG" \
  --record "$RAW" --size 256x224 --max-frames "$MAXF" -v >"$OUTDIR/retroarch.log" 2>&1 || true
[ -s "$RAW" ] || { echo "録画失敗"; tail -20 "$OUTDIR/retroarch.log"; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW" 2>/dev/null)
NF=$(ffprobe -v error -count_frames -select_streams v:0 \
     -show_entries stream=nb_read_frames -of csv=p=0 "$RAW" 2>/dev/null)
echo "==> recorded dur=${DUR}s frames=${NF}"

# 完成フレーム探し: 末尾付近を等間隔サンプルし 4x3 タイルへ(256x224 等倍)。
ffmpeg -y -v error -i "$RAW" -vf "fps=1,scale=256:224:flags=neighbor,tile=4x3" \
  -frames:v 1 "$OUTDIR/sheet.png" 2>/dev/null
# 最終フレーム単体(等倍)。
ffmpeg -y -v error -sseof -1 -i "$RAW" -vframes 1 \
  -vf "scale=256:224:flags=neighbor" "$OUTDIR/last.png" 2>/dev/null
echo "sheet=$OUTDIR/sheet.png last=$OUTDIR/last.png"
