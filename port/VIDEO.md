<a id="en"></a>

EN / [JP](#jp)

# GENESIS DOOM video output layer (I_FinishUpdate path)

Historical design and harness-validation notes.
For the current 120x64 byte framebuffer and double-buffered DMA path, see [AGENTS.md](../AGENTS.md) and [PERFORMANCE.md](PERFORMANCE.md).
References below to BlastEm validation describe emulator runs, not physical-console tests.

The Genesis output path converts an 8-bit indexed image into VDP tiles, transfers patterns, and sets the name table.
It avoids the original large software framebuffer.
The harness was checked with Doom's TITLEPIC in BlastEm.

## Engine pixel representation

- `lighttable_t = byte`; `colormap[idx]` returns an 8-bit PLAYPAL index with lighting applied.
- The inherited non-GBA framebuffer is `unsigned short[SCREENWIDTH*SCREENHEIGHT]`, with each short equal to `(idx<<8)|idx`. Both bytes contain the same index, so either byte has the same value on big-endian m68k.
- Rendering therefore produces 8-bit palette indices that can be mapped to the Genesis palette.

## Implementation

- `plat_video.c` supplies `GEN_VideoInit()` for VDP H32 (256x224) initialization using register settings validated with the `boot/` harness.
- `GEN_SetPalette16(cram16)` uploads 16 colors to CRAM palette 0.
- `GEN_BlitIndexed2x2(idx, w, h, lut, tilebase)` converts pixels into 4bpp 8x8 tiles and uploads them to VRAM. `GEN_BlitIndexedWithNames(...)` also writes the name table for initial placement and harness use, with generic `stride,hscale,vscale` parameters.
- Offline color reduction in `tools/gen_assets.py` uses the distribution of an explicitly configured P6 PPM `PALETTE_SAMPLE`, or TITLEPIC otherwise. Median-cut reduces PLAYPAL's 256 colors to 16, producing a nearest-color `256→0..15` LUT and Genesis CRAM words. Duplicate entries after CRAM rounding are filled with frequent colors. The target only performs LUT lookup and tile conversion.

## Aspect correction: retain a 120-wide framebuffer and scale during VDP upload

Gameplay renders at 120x64 into a 7.5 KB byte buffer.
`GEN_BlitIndexed2x2` repeats every source pixel and row twice to display 240x128.

- The framebuffer remains 120x64; display expansion is 2x horizontally and vertically.
- Expansion happens during the tile conversion already required each frame, adding no work to the engine renderer itself.
- The normal game path is specialized for fixed 2x2 expansion and avoids generic `hscale/vscale` branches and `stride` calculations.
- This follows GBA's “render 120, display 240” approach. A 240x160 title harness was displayed correctly in BlastEm.

## Layout

| Mode | Display | Placement |
|---|---|---|
| Title | 256x224 = 32x28 tiles | Full screen |
| Gameplay viewport | 240x128 = 30x16 tiles | Centered at col=1,row=6; remainder black |

## Recording and upload aspect ratio

Genesis Plus GX reports gameplay output as 256x224 with a display aspect ratio of approximately 1.306122 (64:49).
For square-pixel output corrected for H32's 8:7 pixel aspect ratio, use 2048x1568 (8x horizontally, 7x vertically).
Do not apply H40's 32:35 pixel aspect ratio for 320x224 to H32's 256x224 output.

```sh
ffmpeg -i video-lossless.mkv -i audio.wav \
  -vf "scale=2048:1568:flags=neighbor,setsar=1" \
  -c:v libx264 -crf 10 -preset fast -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart gameplay.mp4
```

If video and audio are captured separately, start both from the same emulation point.
The core's time base for this recording was approximately 59.922743 fps / 44100 Hz.
Retain that time base even when capture runs faster than real time; do not use the elapsed capture time as video duration.
Only the first seven startup frames were 256x192, so the native footage was padded at the bottom to 224 rows.

The former conversion from 256x224 to 1024x896 followed by padding to 1440x1080 added unnecessary borders and did not correct pixel aspect.
Do not use it.
Full-screen uploads should not add padding or force the picture to 4:3.

Black margins outside the 240x128 gameplay viewport are drawn by the ROM and remain in full-screen recordings.
The title uses the full 256x224 screen.
An enlarged gameplay-only version is a separate crop: `crop=240:128:8:48`, with a corrected display aspect ratio of 15:7.

## Historical harness validation (BlastEm)

`tools/gen_assets.py` generated a fixed 16-color palette for E1M1 and expanded TITLEPIC into 256x224 and 224x96 (the old viewport harness).
`harness_video.c` passed the data through the production video layer.
Both `build/harness/{title,view}.bin` layouts displayed the Doom title correctly in BlastEm, with screenshots captured.
The harness fit within 64 KB RAM: images remained in ROM and the output layer used only a few dozen bytes of temporary storage.
This describes the early harness, not the current DMA buffers.

### Build and run

```sh
python3 tools/gen_assets.py wad/doom1.wad port/gen/assets_gen
# From port/:
make harness
blastem build/harness/title.bin   # Full screen
blastem build/harness/view.bin    # Viewport
```

## Limits and historical next steps

- Use a fixed 16-color palette (one CRAM palette). Multiple palettes and per-tile palette assignment are out of scope.
- Palette selection is currently offline. `I_SetPallete_e32` originally receives Doom's dynamic palette effects, such as red damage and yellow item flashes; the fixed gameplay palette takes priority for now.
- The early integration plan was to connect `I_FinishUpdate_e32(src,pal,w,h)` to `GEN_BlitIndexed2x2(src, w, h, lut, base)` once the engine ran within RAM (`stride=2` in the inherited representation).
- Genesis gameplay uses 120x64 internally and displays it at 240x128 with 2x2 expansion.

---

<a id="jp"></a>

[EN](#en) / JP

# GENESIS DOOM 映像出力層（I_FinishUpdate 経路）

過去の映像設計とハーネス検証の記録です。
現在の 120x64 バイトのフレームバッファと二重バッファ DMA 経路は、[AGENTS.md](../AGENTS.md) と [PERFORMANCE.md](PERFORMANCE.md) を参照してください。
以下の BlastEm による検証はエミュレータ上の実行であり、実機での試験ではありません。

元の大きなソフトウェアフレームバッファを避け、8-bit インデックス画像を VDP タイルへ変換し、パターン転送とネームテーブル設定で表示します。
Doom の TITLEPIC を使い、BlastEm でハーネスを確認しました。

## エンジン側の画素形式（確定事項）

- `lighttable_t = byte`、`colormap[idx]` は **8bit PLAYPAL インデックス**（ライティング適用済み）を返す。
- 非GBA ビルドの framebuffer は `unsigned short[SCREENWIDTH*SCREENHEIGHT]`、各 short = `(idx<<8)|idx`
  （低/高バイトとも同じ 8bit インデックス。m68k big-endian でもどちらのバイトでも値は同じ）。
- つまり描画結果は **8bit パレットインデックス**で、Genesis のパレット方式と素直に対応する。

## 実装

- `plat_video.c`:
  - `GEN_VideoInit()` — VDP H32(256x224) 初期化（`boot/` でハーネス検証済みのレジスタ値）。
  - `GEN_SetPalette16(cram16)` — 16色を CRAM palette0 へ。
  - `GEN_BlitIndexed2x2(idx, w, h, lut, tilebase)` — 各 8x8 を 4bpp タイル化して
    VRAM へ直書き。`GEN_BlitIndexedWithNames(...)` は初期配置/ハーネス用に、汎用 `stride,hscale,vscale` 付きでネームテーブルも書く。
- 色削減はオフライン(`tools/gen_assets.py`)で完結：明示した `PALETTE_SAMPLE` の P6 PPM があればその画面の色分布を使い、未指定なら TITLEPIC 基準でPLAYPAL256を median-cut で16色化する。
  `256→0..15` 最近傍 LUT とGenesis CRAM語を生成し、CRAM丸め後の重複枠は頻出色で補う。on-target は LUT 引きとタイル化のみ。

## アスペクト矯正：framebuffer 120幅のまま VDP 転送で横2倍（確定・エミュレータ確認済）

Genesis のゲーム内部解像度は 120×64。framebuffer は 7.5KB のバイトバッファで持ち、
**`GEN_BlitIndexed2x2` で各ソース画素/行を横2回・縦2回展開して 240×128で表示**する。
- framebuffer は 120×64 のまま。表示時に横2倍・縦2倍へ展開する。
- 横2倍・縦2倍は「どうせ毎フレーム行うタイル変換」の中で行うのでレンダラ CPU は増えない。
- ゲーム本体の通常フレームは固定2x2専用化し、汎用 `hscale/vscale` 分岐や `stride` 計算を通らない。
- これは GBA が「120 描画 → 240 表示」しているのと同じ手法。BlastEmでタイトルを 240×160 で正しく表示確認。

## レイアウト（確定）

| モード | 内部 | 配置 |
|---|---|---|
| タイトル | 256x224 = 32x28 タイル | 全画面 |
| ゲームビューポート | 240x128 = 30x16 タイル | 中央(col=1,row=6、残り黒) |

## 録画とアップロード時の画面比率

Genesis Plus GXでこのROMを録画した場合、ゲーム開始後の出力は256×224、
報告される表示比率は約1.306122（64:49）。H32のピクセル比8:7を反映した
正方形ピクセルの出力として、2048×1568（横8倍、縦7倍）を使う。
H40の320×224用ピクセル比32:35を、H32の256×224へそのまま適用しない。

```sh
ffmpeg -i video-lossless.mkv -i audio.wav \
  -vf "scale=2048:1568:flags=neighbor,setsar=1" \
  -c:v libx264 -crf 10 -preset fast -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart gameplay.mp4
```

別々の素材を使う場合、映像と音声は同じエミュレーションの開始から取得する。
今回のコアの時間基準は約59.922743fps / 44100Hz。高速収録してもこの時間基準を
保持し、実時間の収録所要時間を動画の尺に使わない。起動直後の7フレームだけは
256×192だったため、ネイティブ素材では下端を224行まで補っている。

以前の「256×224を1024×896へ拡大して1440×1080へpadする」変換は、
上下左右へ余分な黒帯を追加し、ピクセル比も補正していなかった。使用しない。
全画面のアップロードにはpadや4:3への強制変形を加えない。

ゲーム中の240×128ビューポート以外の黒い余白はROMが描く領域。
全画面を保持する録画では残り、タイトル画面は256×224全域を使う。
ゲーム部分だけを拡大する場合は別のクロップ版として扱う（領域は
`crop=240:128:8:48`、ピクセル比補正後の表示比率は15:7）。

## 過去のハーネス検証（BlastEm）

`tools/gen_assets.py` でE1M1向け固定16色パレットと、TITLEPICを 256x224 / 224x96(旧ビューポートハーネス) に展開 → ハーネス `harness_video.c` が
本番出力層に流す。`build/harness/{title,view}.bin` を blastem で表示し、Doom タイトルが
両レイアウトで正しく出ることを確認（スクリーンショット取得済み）。RAM 64KB に収まることも確認
（画像は ROM 常駐、出力層は数十バイトの一時バッファのみ）。
これは初期ハーネスの記録であり、現在の DMA バッファの説明ではありません。

### ビルド/実行
```sh
python3 tools/gen_assets.py wad/doom1.wad port/gen/assets_gen
# port/ で:
make harness
blastem build/harness/title.bin   # 全画面
blastem build/harness/view.bin    # ビューポート
```

## 制限と当時の実装予定

- **16色固定（1 CRAM パレット）**。複数パレット/per-tile パレット割当は採用しない。
- 現状はオフライン固定パレット。`I_SetPallete_e32` は本来 Doom の動的パレット（被弾赤/アイテム黄の
  フラッシュ等）を受けるが、当面はゲーム画面向け固定16色を優先する。
- 当時の本番結線の計画: エンジンが RAM に収まって走るようになったら、`I_FinishUpdate_e32(src,pal,w,h)` を
  `GEN_BlitIndexed2x2(src, w, h, lut, base)` に繋ぐ（stride=2）。
- Genesis ゲーム描画は 120x64 を横2倍・縦2倍で 240x128 表示する。
