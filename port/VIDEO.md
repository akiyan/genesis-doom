# GENESIS DOOM 映像出力層（I_FinishUpdate 経路）

ソフトフレームバッファを廃し、**8bit インデックス画像 → VDP タイル → DMA → ネームテーブル**で
画面へ出す Genesis 実装。本物の Doom TITLEPIC を流して blastem 実機で検証済み。

## エンジン側の画素形式（確定事項）

- `lighttable_t = byte`、`colormap[idx]` は **8bit PLAYPAL インデックス**（ライティング適用済み）を返す。
- 非GBA ビルドの framebuffer は `unsigned short[SCREENWIDTH*SCREENHEIGHT]`、各 short = `(idx<<8)|idx`
  （低/高バイトとも同じ 8bit インデックス。m68k big-endian でもどちらのバイトでも値は同じ）。
- つまり描画結果は **8bit パレットインデックス**で、Genesis のパレット方式と素直に対応する。

## 実装

- `plat_video.c`:
  - `GEN_VideoInit()` — VDP H32(256x224) 初期化（`boot/` で実機検証済みのレジスタ値）。
  - `GEN_SetPalette16(cram16)` — 16色を CRAM palette0 へ。
  - `GEN_BlitIndexed2x2(idx, w, h, lut, tilebase)` — 各 8x8 を 4bpp タイル化して
    VRAM へ直書き。`GEN_BlitIndexedWithNames(...)` は初期配置/ハーネス用に、汎用 `stride,hscale,vscale` 付きでネームテーブルも書く。
- 色削減はオフライン(`tools/gen_assets.py`)で完結：明示した `PALETTE_SAMPLE` の P6 PPM があればその画面の色分布を使い、未指定なら TITLEPIC 基準でPLAYPAL256を median-cut で16色化する。
  `256→0..15` 最近傍 LUT とGenesis CRAM語を生成し、CRAM丸め後の重複枠は頻出色で補う。on-target は LUT 引きとタイル化のみ。

## アスペクト矯正：framebuffer 120幅のまま VDP 転送で横2倍（確定・実機確認済）

Genesis のゲーム内部解像度は 120×64。framebuffer は 7.5KB のバイトバッファで持ち、
**`GEN_BlitIndexed2x2` で各ソース画素/行を横2回・縦2回展開して 240×128で表示**する。
- framebuffer は 120×64 のまま。表示時に横2倍・縦2倍へ展開する。
- 横2倍・縦2倍は「どうせ毎フレーム行うタイル変換」の中で行うのでレンダラ CPU は増えない。
- ゲーム本体の通常フレームは固定2x2専用化し、汎用 `hscale/vscale` 分岐や `stride` 計算を通らない。
- これは GBA が「120 描画 → 240 表示」しているのと同じ手法。blastem 実機でタイトルを 240×160 で正しく表示確認。

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

## 検証（blastem 実機）

`tools/gen_assets.py` でE1M1向け固定16色パレットと、TITLEPICを 256x224 / 224x96(旧ビューポートハーネス) に展開 → ハーネス `harness_video.c` が
本番出力層に流す。`build/harness/{title,view}.bin` を blastem で表示し、Doom タイトルが
両レイアウトで正しく出ることを確認（スクリーンショット取得済み）。RAM 64KB に収まることも確認
（画像は ROM 常駐、出力層は数十バイトの一時バッファのみ）。

### ビルド/実行
```sh
python3 tools/gen_assets.py wad/doom1.wad port/gen/assets_gen
# port/ で:
make harness
blastem build/harness/title.bin   # 全画面
blastem build/harness/view.bin    # ビューポート
```

## 既知の割り切りと次の改善

- **16色固定（1 CRAM パレット）**。複数パレット/per-tile パレット割当は採用しない。
- 現状はオフライン固定パレット。`I_SetPallete_e32` は本来 Doom の動的パレット（被弾赤/アイテム黄の
  フラッシュ等）を受けるが、当面はゲーム画面向け固定16色を優先する。
- 本番結線: エンジンが RAM に収まって走るようになったら、`I_FinishUpdate_e32(src,pal,w,h)` を
  `GEN_BlitIndexed2x2(src, w, h, lut, base)` に繋ぐ（stride=2）。
- Genesis ゲーム描画は 120x64 を横2倍・縦2倍で 240x128 表示する。
