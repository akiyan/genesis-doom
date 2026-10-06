<a id="en"></a>

EN / [JP](#jp)

# GENESIS DOOM memory plan: zone and RAM analysis for 64 KB

Historical analysis of GBADoom's zone heap and RAM use, including measurements from 2026-06-04.
The full-framebuffer removal proposal and “not implemented” entries describe the early design, not the current engine.
The current port retains a 120x64 byte framebuffer and boots E1M1 in emulation; see [AGENTS.md](../AGENTS.md).
BlastEm references below describe emulator validation rather than physical-console tests.

## Structural facts about GBADoom

1. Lumps are read directly from ROM and require no RAM cache. `W_CacheLumpNum()` returns `&doom_iwad[filepos]` (`w_wad.c`). Textures, sprites, flats, palettes, and colormaps refer directly to ROM-backed `doom_iwad[]`. There are no `PU_CACHE` users, so vanilla Doom's LRU cache eviction is unnecessary.
2. Immutable geometry is also ROM-backed (`p_setup.c`). ROM data includes `vertexes`, `segs`, `nodes`, `lines` (immutable linedefs), `blockmap`, and `reject`. Mutable RAM data includes `sectors`, `sides`, `subsectors`, `linedata` (mutable line state), `thingPool` (mobj), and `blocklinks`. The split between `lines` and `linedata` already separates immutable and mutable data.
3. The zone stores runtime mutable state only, tagged PU_STATIC / PU_LEVEL / PU_LEVSPEC.

## Measured RAM breakdown

### globals_t (`_g`, resident PU_STATIC): 21,954 B (21.4 KB)

About 16.3 KB consists of renderer working arrays sized for the GBA's 120x160 resolution and scene limits; these can be reduced.

| Member | Size | Limit | Notes |
|---|---|---|---|
| `drawsegs` | 8,448 | `MAXDRAWSEGS=192` | drawseg_t × 192; rendered segments |
| `vissprites` | 4,608 | `MAXVISSPRITES=96` | Visible sprites |
| `openings` | 3,840 | `MAXOPENINGS=SCREENWIDTH*16` | Column clipping |
| `intercepts` | 768 | `MAXINTERCEPTS=64` | Ray intersections |
| `sprtemp` | 638 | | Temporary sprite construction |
| `player` / `anims` / `hu_font` / weapon / HUD and others | Remaining ~5 KB | | Mostly necessary small allocations |

### E1M1 (first shareware map), PU_LEVEL: approximately 38.1 KB

| Array | Count × m68k sizeof | Total |
|---|---|---|
| `thingPool` (mobj_t) | 138 × 124 | 17,112 |
| `sides` (side_t) | 648 × 12 | 7,776 |
| `sectors` (sector_t) | 85 × 60 | 5,100 |
| `linedata` (linedata_t) | 475 × 8 | 3,800 |
| `blocklinks` | 828 × 4 | 3,312 |
| `subsectors` (subsector_t) | 237 × 8 | 1,896 |
| Additional dynamic mobj / visplane (266 B) / PU_LEVSPEC thinkers / zone headers | — | Additional |

`globals_t` plus the E1M1 level is approximately 59.5 KB, before dynamic allocations and rendering `.bss`.

### Rendering statics in .bss (r_hotpath and GBA VRAM staging)

`columnCache` 16 KB, `vram1,2,3_spare` about 6 KB, `current_colormap` 256 B, and related data total approximately 22 KB.
These belong to the GBA rendering pipeline and were candidates for shrinking or replacing in the Genesis tile path.

## Proposed Genesis advantage

The early proposal removed the large software framebuffer, saving about 38 KB.
GBA uses a 120x160x2-byte RAM backbuffer (the temporary `g_framebuffer` was also 38 KB).
The proposed Genesis path converted columns directly to VDP tile patterns for DMA without retaining a full-frame buffer in RAM.
This was the largest projected saving; the current implementation instead keeps a smaller 120x64 byte buffer.

## Proposed E1M1-sized allocation within 64 KB

| Item | Initial size | Proposed change | Target |
|---|---|---|---|
| Software framebuffer | 38 KB | Direct VDP tile drawing; remove framebuffer | 0 |
| globals_t rendering scratch | 16.3 KB | `MAXDRAWSEGS 192→96`, `MAXVISSPRITES 96→48`, viewport-width openings and smaller limits | ~7 KB |
| Other globals_t data | ~5.6 KB | Mostly unchanged | ~5.6 KB |
| Mutable level geometry | 21.9 KB | Slim side_t / sector_t and examine further ROM placement | ~18 KB |
| thingPool (mobj) | 17.1 KB | Slim mobj_t, delayed spawn, or count limits | ~12 KB |
| Rendering .bss (columnCache and others) | 22 KB | Redesign for Genesis tiles | ~8 KB |
| Dynamic mobj / visplane / thinkers / zone | Additional | Limits and pools | ~6 KB |
| Stack | — | | ~2 KB |

The rough target was `0 + 12.6 + 18 + 12 + 8 + 6 + 2 ≈ 58.6 KB`, within reach for an E1M1-sized scene.
Larger maps such as E1M7 would exceed it, motivating the earlier CLAUDE.md proposal to split maps into areas.

## Mutable-state baseline

E1M1's mutable geometry (about 22 KB) plus thingPool (17 KB) requires approximately 39 KB in this representation.
Reducing it requires auditing members of mobj_t (124 B), sector_t (60 B), and side_t (12 B), or limiting object counts and simultaneous visibility.
The latter changes the supported game content.

## Native host measurements, 2026-06-04

The engine under `port/host/` loaded and rendered E1M1 on a PC.
Actual zone use within `maxHeapSize=256 KB` was:

| Phase | Zone used | Breakdown |
|---|---|---|
| After InitGlobals | 22.0 KB | `globals_t` (`_g`) alone |
| Title, no level | 31.8 KB (67 blocks) | `_g`, R_Init texture / sprite management tables, HU / ST |
| E1M1 gameplay | 82.5 KB (140 blocks) | Level data (including 17 KB thingPool), dynamic mobj, many 284 B visplanes, block headers |

The title's zone used 31.8 KB.
A byte framebuffer (19 KB) and reduced columnCache could make a 64 KB title-only engine milestone possible.
E1M1's 82.5 KB zone alone exceeded all RAM; adding the 38 KB framebuffer and 22 KB rendering `.bss` brought the total to approximately 140 KB, about 2.2 times capacity.
It required smaller structures, object limits, shared rendering buffers, and possibly map splitting.
The earlier 38 KB level estimate omitted block headers and dynamic allocations; use measurements as the baseline.

## Early barriers to 68k startup

These were the barriers to running the engine in BlastEm, which accurately mirrors the 64 KB RAM address space.

| # | Barrier | Status at that stage | Approach |
|---|---|---|---|
| 1 | ROM exceeded 4 MB: WAD 3.84 MB + code 0.62 MB = 4.46 MB | Resolved | Reduce processed WAD to E1M1 data, about 2629 KB; remove 1200 KB of E1M2–E1M9 data. The historical build retained all map markers for gamemode detection. Total ROM about 3.2 MB, verified on the host with `make wad-min`. GBADoom had already removed sound / music data. |
| 2 | Zone did not fit in 64 KB | Design understood | `Z_Init` adapts to the largest allocatable heap in 4-byte steps. Limit `_sbrk`'s heap allowance to shrink the zone. A ~34 KB heap accommodates the 31.8 KB title zone, but not E1M1's 82.5 KB. |
| 3 | 38 KB short framebuffer filled .bss | Verified for title path | Use `GENESIS` for 120-wide, one-byte pixels. `V_DrawPatch` in `v_video.c` was converted and verified on the host with a 19 KB title buffer. `R_DrawColumn` and other 3D paths still needed byte conversion for E1M1. |
| 4 | 16 KB columnCache and 6 KB vram_spare for GBA VRAM staging | Pending | Shrink or remove on Genesis. |
| 5 | Platform integration | Pending | Wire I_FinishUpdate_e32 to GEN_BlitIndexed, use frame counting for I_GetTime, provide _sbrk, and trace I_Error using backdrop colors. |
| 6 | 68000 address errors from odd-address word access | Prevented | strip_wad aligns lumps to 4-byte boundaries. |

The title-startup estimate was a 19 KB byte framebuffer + ~1 KB columnCache + 6 KB vram_spare + 34 KB heap + 2 KB stack ≈ 62 KB.
It was expected to fit 64 KB; E1M1 still needed structure reduction and related work.

Implementation notes at that stage: `V_DrawPatch` in `v_video.c` had a `#ifdef GENESIS` path for 120-wide single-byte writes with `byte_pitch=SCREENPITCH`.
The `pixel` typedef (`r_hotpath:287`), `byte_topleft` (`r_draw.h`), and R_DrawColumn / Span / Fuzz / Sprite still needed byte conversion for E1M1.
`columnCache[128*128]` (16 KB) and vram_spare (6 KB) lived in r_hotpath's `.bss`.
The title did not use columnCache, so it could be reduced for title tests; 3D needed it.
Host validation used `-DGENESIS` and produced `host_title_gen.ppm`.

## Proposed next implementation steps

1. Settle the large-framebuffer replacement path, connecting `I_FinishUpdate_e32` to VDP tile transfers for the largest RAM saving.
2. Set Genesis renderer limits for `MAXDRAWSEGS`, `MAXVISSPRITES`, and openings, then measure the smaller globals_t.
3. Restore `link.ld` RAM to the physical 64 KB limit and instrument zone usage (`Z_Init` logging) while loading E1M1.
4. Fit remaining allocations by slimming structures or splitting maps.

---

<a id="jp"></a>

[EN](#en) / JP

# GENESIS DOOM メモリ収容設計 — ゾーン/RAM 分析（64KB に収める）

2026-06-04 の測定を含む、初期のメモリ分析の記録です。
フレームバッファ廃止案と未実装項目は当時の設計であり、現在のエンジンの状態ではありません。
現在は 120x64 バイトのフレームバッファを保持し、エミュレータで E1M1 が起動します。[AGENTS.md](../AGENTS.md) を参照してください。
以下の BlastEm による検証は、実機ではなくエミュレータ上の実行です。

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

## 当時の Genesis 向け削減案

- **ソフトウェアフレームバッファ不要（−38KB 相当）。** GBA は 120×160×2B のバックバッファを RAM に持つ（今のスタブ `g_framebuffer` 38KB）。当時の Genesis 案ではカラム描画結果を直接 VDP タイルパターン化して DMA 転送し、フルフレームバッファを RAM に常駐させない計画でした。
  最大の削減見込みでしたが、現在の実装は小さい 120x64 バイトのバッファを保持しています。

## 当時の 64 KB 収容案（E1M1 級を想定）

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

## 実測値（ホスト native ビルドで計測, 2026-06-04）

`port/host/` でエンジンを PC 上で実行し E1M1 をロード・描画して正しく動くことを確認。
ゾーン実使用量（`maxHeapSize`=256KB の中で）:

| フェーズ | ゾーン used | 内訳 |
|---|---|---|
| InitGlobals 後 | **22.0 KB** | `globals_t`(`_g`) 単独 |
| **タイトル(レベル無)** | **31.8 KB** (67 blk) | `_g` + R_Init テクスチャ/スプライト管理テーブル + HU/ST |
| **E1M1 ゲーム中** | **82.5 KB** (140 blk) | + level(thingPool 17KB ほか) + 動的mobj + visplane(284B×多数) + ブロックヘッダ |

→ **タイトルは 31.8KB**。framebuffer をバイト化(19KB)し columnCache を縮めれば **64KB 収容可能** = 先に到達できる「実機でエンジンが動く」マイルストーン。
→ **E1M1 は 82.5KB**。これ単独で 64KB 超。framebuffer(38KB)+描画.bss(22KB) を足すと総計 ≈140KB で実機の約2.2倍。構造体スリム化＋オブジェクト数制限＋描画バッファ共有＋(必要なら)マップ分割が要る本丸。
※ 推定(旧)では level 38KB と見たが、実測はブロックヘッダ・動的分込みでより大きい。実測を基準にする。

## 初期の 68k 起動での障害

エンジンを blastem(64KB RAM を正確にミラー再現)で動かすための障害:

| # | 関門 | 状態 | 対策 |
|---|---|---|---|
| 1 | **ROM > 4MB**（WAD3.84MB+code0.62MB=4.46MB、68k フラット空間4MB超） | **✅ 解決** | 処理済WAD を E1M1 のみ保持に削減=2629KB(マップマーカー全保持で gamemode 検出維持、E1M2-9 データ1200KB除去)。総ROM≈3.2MB。ホストで無傷確認。`make wad-min`。音/音楽は GBADoom が既に全削除済。 |
| 2 | **ゾーンが 64KB に収まらない** | 設計判明 | `Z_Init` は 4バイト刻みで「確保可能な最大ヒープ」に自動適応。_sbrk で渡すヒープ量を絞ればゾーンが縮む。タイトル31.8KB→~34KBヒープで可。E1M1(82.5KB)は不可(別途)。 |
| 3 | **framebuffer 38KB(short)** が .bss を圧迫 | **✅ 検証(タイトル経路)** | `GENESIS` マクロで 120幅・1バイト/画素に。`v_video.c` の `V_DrawPatch` を byte 化済→ホストでタイトルを 19KB バッファに正しく描画確認。3D 描画関数(r_hotpath の R_DrawColumn 等)の byte 化は E1M1 で必要(後段)。 |
| 4 | columnCache 16KB / vram_spare 6KB(GBA VRAM ステージング) | 未 | Genesis では縮小/廃止。 |
| 5 | プラットフォーム配線 | 未 | I_FinishUpdate_e32→GEN_BlitIndexed、I_GetTime(フレーム計数)、_sbrk、I_Error=背景色トレース。 |
| 6 | 68000 アドレスエラー(奇数アドレスのワードアクセス) | 予防済 | strip_wad は lump を 4バイト境界整列。 |

**タイトル起動(31.8KB)の RAM 試算**: byte fb 19KB + columnCache縮小 ~1KB + vram_spare 6KB + ヒープ34KB + stack 2KB ≈ 62KB → 64KB 収容可能の見込み。E1M1 ゲームは構造体スリム化等の本丸(後段)。

**GENESIS バイト経路の実装メモ**: `v_video.c` の `V_DrawPatch` に `#ifdef GENESIS`(120幅, byte_pitch=SCREENPITCH, 単バイト書込)を追加済。`pixel` typedef(r_hotpath:287)/`byte_topleft`(r_draw.h)/3D描画関数(R_DrawColumn/Span/Fuzz/Sprite)の byte 化は E1M1 描画時に必要。columnCache[128*128]=16KB と vram_spare 6KB は r_hotpath の .bss。columnCache はタイトルでは未使用なので縮小可(3D では要)。host 検証は `-DGENESIS` でビルド→`host_title_gen.ppm`。

## 当時の実装予定

1. **ソフトフレームバッファ廃止**の経路確定（`I_FinishUpdate_e32` を VDP タイル転送に。最大の RAM 回収）。
2. レンダラ上限定数を Genesis 値へ（`MAXDRAWSEGS/MAXVISSPRITES/openings` 縮小）→ globals_t 圧縮を実測。
3. `link.ld` の RAM を実機 64KB に戻し、E1M1 を load した時の zone 実使用を計測する計装（`Z_Init` ログ）。
4. 収まらない分を構造体スリム化 / マップ分割で詰める。
