# GENESIS DOOM メモリ収容設計 — ゾーン/RAM 分析（64KB に収める）

GBADoom のゾーンヒープ・RAM 使用を実測し、ノーマル Genesis 64KB RAM への収容戦略を定量化したもの。

## 前提となる構造的事実（GBADoom の設計）

1. **lump は ROM 直読み・RAM コスト 0。**
   `W_CacheLumpNum()` は `&doom_iwad[filepos]` を返すだけ（`w_wad.c`）。
   テクスチャ/スプライト/フラット/パレット/colormap は全て ROM 上の `doom_iwad[]` を直接参照。
   → **`PU_CACHE` は1つも使われていない**（vanilla の LRU キャッシュ退避は不要）。

2. **不変ジオメトリも ROM 直読み。** `p_setup.c`:
   - ROM直: `vertexes` / `segs` / `nodes` / `lines`(不変linedef) / `blockmap` / `reject`
   - RAM(可変): `sectors` / `sides` / `subsectors` / `linedata`(可変line状態) / `thingPool`(mobj) / `blocklinks`
   → **可変状態だけ RAM** という分離が既に実装済み（`lines` と `linedata` の分割が好例）。

3. ゾーンが保持するのは **実行時の可変状態のみ**。タグは PU_STATIC / PU_LEVEL / PU_LEVSPEC。

## 実測した RAM 内訳

### globals_t (`_g`, PU_STATIC 常駐) = 21,954 B（21.4 KB）
うち **約 16.3 KB が「レンダラ作業配列」**（GBA 解像度 120×160 とシーン上限で決め打ち、削減可能）:

| メンバ | サイズ | 上限定数 | 備考 |
|---|---|---|---|
| `drawsegs` | 8,448 | `MAXDRAWSEGS=192` | drawseg_t×192。描画セグメント |
| `vissprites` | 4,608 | `MAXVISSPRITES=96` | 可視スプライト |
| `openings` | 3,840 | `MAXOPENINGS=SCREENWIDTH*16` | カラムクリップ |
| `intercepts` | 768 | `MAXINTERCEPTS=64` | 射線交差 |
| `sprtemp` | 638 | | スプライト構築一時 |
| `player`/`anims`/`hu_font`/武器・HUD 等 | 残り ~5KB | | 概ね必要・小物 |

### E1M1（シェアウェア最初の面）PU_LEVEL = 約 38.1 KB

| 配列 | 数 × m68k sizeof | 計 |
|---|---|---|
| `thingPool` (mobj_t) | 138 × 124 | **17,112** |
| `sides` (side_t) | 648 × 12 | 7,776 |
| `sectors` (sector_t) | 85 × 60 | 5,100 |
| `linedata` (linedata_t) | 475 × 8 | 3,800 |
| `blocklinks` | 828 × 4 | 3,312 |
| `subsectors` (subsector_t) | 237 × 8 | 1,896 |
| 別途: 動的 mobj / visplane(266B) / PU_LEVSPEC thinker / zone ヘッダ | — | +α |

**globals_t + E1M1 level ≈ 59.5 KB**（+ 動的分・描画 .bss）。

### 現状の .bss 描画スタティック（r_hotpath, GBA VRAM ステージング）
`columnCache` 16KB / `vram1,2,3_spare` 約6KB / `current_colormap` 256B 等 ≈ 22KB。
※ これは GBA の描画パイプライン専用。Genesis ではタイル変換経路へ再設計し縮小対象。

## Genesis の構造的アドバンテージ

- **ソフトウェアフレームバッファ不要（−38KB 相当）。** GBA は 120×160×2B のバックバッファを RAM に持つ（今のスタブ `g_framebuffer` 38KB）。Genesis はカラム描画結果を**直接 VDP タイルパターン化して DMA**するので、フルフレームバッファを RAM に常駐させない。これが最大の削減源。

## 64KB 収容の攻め筋（E1M1 級を想定）

| 項目 | 現状 | 施策 | 目標 |
|---|---|---|---|
| ソフトフレームバッファ | 38 KB | VDP タイル直描画へ（フレームバッファ廃止） | **0** |
| globals_t 描画スクラッチ | 16.3 KB | `MAXDRAWSEGS 192→96`, `MAXVISSPRITES 96→48`, openings をビューポート幅基準に, 上限縮小 | ~7 KB |
| globals_t その他 | ~5.6 KB | ほぼ据置 | ~5.6 KB |
| level 可変(geometry) | 21.9 KB | 構造体スリム化（side_t/sector_t のメンバ削り）/ ROM 移譲余地精査 | ~18 KB |
| thingPool (mobj) | 17.1 KB | mobj_t スリム化 or 遅延 spawn / 上限 | ~12 KB |
| 描画 .bss(columnCache 等) | 22 KB | Genesis タイル経路へ再設計 | ~8 KB |
| 動的 mobj/visplane/thinker/zone | +α | 上限・プール化 | ~6 KB |
| スタック | — | | ~2 KB |

→ ざっくり **0 + 12.6 + 18 + 12 + 8 + 6 + 2 ≈ 58.6 KB**。E1M1 級なら**収容圏内**。
　大きい面（E1M7 等）は超過 → CLAUDE.md「マップは1エリアごとに切る」で分割が必要。

## 不可分の下限（動かしにくいコスト）

E1M1 の純粋な可変状態 = level geometry(可変) 約22KB + thingPool 17KB ≈ **39KB** は本質的に必要。
ここを削るには構造体スリム化（mobj_t 124B / sector_t 60B / side_t 12B の各メンバ精査）か、
オブジェクト数・同時可視数の制限という「ゲーム内容の割り切り」が要る。

## 次の実装ステップ（提案順）

1. **ソフトフレームバッファ廃止**の経路確定（`I_FinishUpdate_e32` を VDP タイル転送に。最大の RAM 回収）。
2. レンダラ上限定数を Genesis 値へ（`MAXDRAWSEGS/MAXVISSPRITES/openings` 縮小）→ globals_t 圧縮を実測。
3. `link.ld` の RAM を実機 64KB に戻し、E1M1 を load した時の zone 実使用を計測する計装（`Z_Init` ログ）。
4. 収まらない分を構造体スリム化 / マップ分割で詰める。
