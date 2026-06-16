#!/bin/bash
# GenesisDoom ROM を仮想 X ディスプレイ(Xvfb)上の mednafen(softfb)で起動し F9 スクショ。
# 物理コンソール側に GUI/ディスプレイマネージャは不要(実機ログインは CLI のままでよい)。
#
# 使い方: emu_shot.sh <rom.bin> <out.png> [wait_seconds] [press_keys] [load_seconds]
#   wait_seconds : ウィンドウ出現後、最初のキー送出までの待ち(省略時8秒)
#   press_keys   : F9 直前に順送するキー列(xdotool keysym、空白区切)。省略時 "Return"。
#                  例: "Return"            タイトル→ゲーム遷移のみ
#                      "Return Up Up Right" 遷移後に前進2+右回頭
#                      ""                   何も押さない(タイトルのまま撮る)
#   load_seconds : press_keys 送出後、F9 までのロード/描画待ち(省略時6秒)。
#                  低速デバッグビルドで初フレームに時間がかかる場合に延ばす。
#
# パッド対応(mednafen gamepad ← キーボード scancode):
#   Start=Return  Up/Down/Left/Right=矢印  A=j(use) B=k(fire) C=l(strafe)
ROM="$(realpath "$1")"; OUT="${2:-/tmp/emu_shot.png}"; WAIT="${3:-8}"
PRESS="${4-Return}"   # 未指定なら Return。明示的に "" を渡せば無送出。
LOADWAIT="${5:-6}"    # press 後 F9 までのロード待ち。

if [ ! -f "$ROM" ]; then echo "NO ROM: $ROM"; exit 1; fi
if ! command -v xvfb-run >/dev/null 2>&1; then echo "NO XVFB (apt install xvfb)"; exit 1; fi

EMU_UID="$(id -u)"
export XDG_RUNTIME_DIR="/run/user/$EMU_UID"
[ -d "$XDG_RUNTIME_DIR" ] || export XDG_RUNTIME_DIR="/tmp/xdg-$EMU_UID"
mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null

# 同一 base-dir の多重起動ロックを回避(直前インスタンスは下で必ず落とす)。
export MEDNAFEN_ALLOWMULTI=1
pkill -9 -f mednafen 2>/dev/null
sleep 1
rm -f ~/.mednafen/snaps/*.png 2>/dev/null

# xvfb-run が DISPLAY を自動割当(-a)。以降の本体は仮想 X 上で完結させる。
# 内部 bash には ROM/OUT/WAIT/PRESS を位置引数で渡す。
exec xvfb-run -a -s "-screen 0 800x600x24" bash -c '
  ROM="$0"; OUT="$1"; WAIT="$2"; PRESS="$3"; LOADWAIT="$4"

  # Genesis 3ボタンパッド + 上下左右 + Start を keyboard scancode(SDL)へ割当。
  MD_INPUT_ARGS=(
    -md.input.port1 gamepad
    -md.input.port1.gamepad.up    "keyboard 0x0 82"
    -md.input.port1.gamepad.down  "keyboard 0x0 81"
    -md.input.port1.gamepad.left  "keyboard 0x0 80"
    -md.input.port1.gamepad.right "keyboard 0x0 79"
    -md.input.port1.gamepad.a     "keyboard 0x0 13"
    -md.input.port1.gamepad.b     "keyboard 0x0 14"
    -md.input.port1.gamepad.c     "keyboard 0x0 15"
    -md.input.port1.gamepad.start "keyboard 0x0 40"
  )

  # -nothrottle 1: 速度スロットルを外しホスト CPU 最速で 68000 を回す。
  # 低速デバッグビルドでも実時間の待機を大幅短縮できる(エミュは実機より高速)。
  mednafen -nothrottle 1 -video.driver softfb -sound 0 "${MD_INPUT_ARGS[@]}" "$ROM" >/dev/null 2>&1 &
  MED_PID=$!
  trap "kill -9 $MED_PID 2>/dev/null" EXIT

  # ウィンドウ出現を待つ(最大10s)
  WIN=""
  for i in $(seq 1 20); do
    sleep 0.5
    kill -0 "$MED_PID" 2>/dev/null || { echo "MEDNAFEN EXITED"; exit 1; }
    WIN=$(xwininfo -root -tree 2>/dev/null | grep -i mednafen | grep -oE "0x[0-9a-f]+" | head -1)
    [ -n "$WIN" ] && break
  done
  echo "disp=$DISPLAY win=$WIN"
  [ -z "$WIN" ] && { echo "NO WINDOW"; exit 1; }

  xdotool windowactivate --sync "$WIN" 2>/dev/null
  sleep "$WAIT"                 # タイトル/ロードの進行を待つ

  # PRESS のキーを順送(タイトル→ゲーム遷移や移動)。各キー後に小待ち。
  if [ -n "$PRESS" ]; then
    for k in $PRESS; do
      xdotool key --window "$WIN" --clearmodifiers "$k" 2>/dev/null
      sleep 0.6
    done
    sleep "$LOADWAIT"           # レベルロード/描画の進行を待つ
  fi

  xdotool key --window "$WIN" F9 2>/dev/null
  sleep 1.5
  SNAP=$(ls -t ~/.mednafen/snaps/*.png 2>/dev/null | head -1)
  if [ -n "$SNAP" ]; then
    cp "$SNAP" "$OUT"
    echo "shot=$OUT"
  else
    echo "NO SNAP"; exit 1
  fi
' "$ROM" "$OUT" "$WAIT" "$PRESS" "$LOADWAIT"
