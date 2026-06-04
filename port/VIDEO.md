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
  - `GEN_BlitIndexed(idx, stride, w, h, col, row, lut, tilebase)` — 各 8x8 を 4bpp タイル化して
    VRAM へ直書き＋ネームテーブル配置。`stride` でエンジン(short=2)/テスト画像(byte=1)両対応。
- 色削減はオフライン(`tools/gen_assets.py`)で完結：PLAYPAL256 を median-cut で 16色化し、
  `256→0..15` 最近傍 LUT と Genesis CRAM 語を生成。on-target は LUT 引きとタイル化のみ。

## レイアウト（確定）

| モード | 内部 | 配置 |
|---|---|---|
| タイトル | 256x224 = 32x28 タイル | 全画面 |
| ゲームビューポート | 224x96 = 28x12 タイル | 中央(col=2,row=8、残り黒) ※CLAUDE.md の 3Dビューポート |

## 検証（blastem 実機）

`tools/gen_assets.py` で TITLEPIC を 256x224 / 224x96 に展開 → ハーネス `harness_video.c` が
本番出力層に流す。`build/harness/{title,view}.bin` を blastem で表示し、Doom タイトルが
両レイアウトで正しく出ることを確認（スクリーンショット取得済み）。RAM 64KB に収まることも確認
（画像は ROM 常駐、出力層は数十バイトの一時バッファのみ）。

### ビルド/実行
```sh
python3 tools/gen_assets.py wad/doom1.wad port/gen/assets_gen
# port/ で:
bash -c 'TC=$HOME/toolchains/mars/m68k-elf/bin; ...'   # 下記 make harness 参照
blastem build/harness/title.bin   # 全画面
blastem build/harness/view.bin    # ビューポート
```

## 既知の割り切りと次の改善

- **16色固定（1 CRAM パレット）**。Genesis は 4パレット×16=64色同時可（タイル毎にパレット選択）。
  静的画像なら per-tile パレット割当で 64色化して画質を上げられる（次の改善候補）。
- 現状はオフライン固定パレット。`I_SetPallete_e32` は本来 Doom の動的パレット（被弾赤/アイテム黄の
  フラッシュ等）を受ける。64色化と合わせ on-target 量子化 or 事前計算テーブルで対応予定。
- 本番結線: エンジンが RAM に収まって走るようになったら、`I_FinishUpdate_e32(src,pal,w,h)` を
  `GEN_BlitIndexed(src, 2, w, h, <中央>, lut, base)` に繋ぐ（stride=2）。
- 内部レンダー解像度の landscape 化（224x96 を直接描く）は別ステップ（エンジン稼働後）。
