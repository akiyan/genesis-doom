# CLAUDE.md — Doom → Sega Genesis (Mega Drive) 移植プロジェクト

このファイルは Claude Code がこのプロジェクトで作業する際の前提・制約・確定事項をまとめたもの。
**作業前に必ず読むこと。** 設計判断はここに書かれた制約を上書きしない。

---

## プロジェクト概要

- **目的**: id Software の Doom を **ノーマル Sega Genesis 単体**（32X / SegaCD 等の拡張なし）に移植する。
- **方針**: 完全再現ではなく「単体 Genesis 上で Doom として成立する最小実装」を最優先する。
- **ソース基盤**: Doom のソースは公式に GPL 公開済み。ROM 逆アセンブルは一切しない。整数化・省メモリ化が進んだ既存 source port（GBA port 系 / PrBoom 軽量版系）を土台にする方針（最終確定は未）。

---

## ターゲットハード（ノーマル Genesis 単体・最高難度）

| 項目 | 仕様 |
|---|---|
| CPU | Motorola 68000 @ 約7.6MHz |
| サブCPU | Z80（サウンド用、本移植では補助） |
| メインRAM | 64KB |
| VRAM | 64KB |
| 映像 | VDP（タイル8x8 + スプライト方式、フレームバッファ非搭載） |
| 浮動小数点 | **なし**（全て固定小数点で実装する） |
| データ配置 | レベル/テクスチャ等は ROM 直読み前提、バンク切り替え（マッパー）必要 |

---

## ビルド / ツールチェーン

- **SGDK 固定**（Sega Genesis Development Kit、68000向け gcc + VDP/DMA ライブラリ）。
- 表示モードは **H32**（256x224）。SGDK 側の初期化を H32 に合わせる（`VDP_setScreenWidth256` 系）。
- ビルドのオーケストレーションを Node 側で回す場合、パッケージ管理は **pnpm を使う**（npm は使わない）。

---

## 画面 / 画設計（確定）

| 項目 | 値 |
|---|---|
| 表示モード | H32（256x224, 32x28タイル） |
| タイトルセーフ後の有効領域 | 224x192（28x24タイル） |
| 3Dビューポート | **224x96（28x12 = 336タイル）** ※横長・縦薄 |
| 画面下半分（縦96px相当） | HUD / 黒帯 |
| 描画方式 | 描画結果をタイルパターンに変換し VRAM へ DMA 転送 |

- 縦を半分に削るのは縦方向の描画負荷を確実に半減させるための割り切り。
- ダブルバッファ時のパターン消費は 672タイル ≒ 21KB で VRAM パターン領域に収まる。

---

## フレームレート / 転送設計（確定）

- **目標 15fps**（NTSC 60Hz に対し **4VBlankに1回更新**）。
- 転送量: 336タイル × 32バイト = **約10.75KB / 更新**。
- これを **4VBlankに分散** → 各VBlank **約2.7KB**。VBlank単発上限（~7.6KB目安）に対し大幅な余裕。
- **結論: DMA転送帯域はもうボトルネックではない。**

---

## 現在のボトルネック（主敵の交代）

| フェーズ | 主敵 | 状態 |
|---|---|---|
| H32確定まで | DMA転送帯域 | **解決済み**（4分割で各2.7KB） |
| 15fps確定後 | **68000のレンダリング演算時間** | これから取り組む |

- 1フレームのCPU時間バジェット: 約66ms（4/60秒）= 68000 @7.6MHz で **約50万サイクル**。
- Doom のカラム描画をこの中に収められるかが次の勝負どころ。

---

## レンダラ最適化の優先順位

1. **事前計算テーブルの徹底** — 三角関数 / 距離→高さスケール / テクスチャステップを ROM テーブル引きに置換。遅い68000除算をホットパスから消すのが最優先。
2. **固定小数点経路の純化** — PC版に残る浮動小数点を全て 16.16 固定小数点へ。素地はあるので対象は限定的。
3. **カラム描画の内製化** — SGDK汎用描画は使わず、ビューポート専用の書き込みループを68000向けに最適化（必要に応じ部分的にアセンブリ）。
4. **内部レンダー解像度のさらなる縮小** — 50万サイクルに収まらない場合のみ、224x96 より内部解像度を落としてカラム数を削る。**転送に余裕があるためCPU救済の最後のカードとして温存。**

---

## メモリ運用方針

- メインRAM 64KB は極めて逼迫。RAM には「今フレームで触る最小限」のみ。
- レベルジオメトリ / テクスチャは ROM 直読み前提。マップは1エリアごとに切る。
- ホットパスで触るものは RAM、滅多に触らないものは ROM、という仕分けを徹底。

---

## やらないこと / 禁止事項

- 市販ROMの逆アセンブル・抽出は行わない（公式GPLソースのみ使用）。
- 32X / SegaCD 等の拡張ハードに逃げない（ノーマル単体が要件）。
- 「動くように見えるが中身が別実装」の成果物を完了扱いにしない。各ステップは検証可能な単位で前進させる。
- npm は使わない（pnpm を使用）。

---

## ベース port（確定）

- **GBADoom（doomhack/GBADoom）に確定**。prBoom ベースを GBA（ARM7 / 256KB RAM / バンク切替ROM）向けに整数化・省メモリ化済み。固定小数点・ROM直読み・限界除去の巻き戻しなど Genesis の制約に最も近い。
- 取得先: `third_party/GBADoom/`（GPL、id原典互換のライセンスヘッダあり）。
- 構成: `source/` に約136ファイル（計21万行）。
  - **差し替えるプラットフォーム I/F 層**: `i_video.c`（VDP/フレーム転送へ）, `i_audio.c`（Z80/PSG/FMへ）, `i_system.c`, `i_main.c`。
  - **レンダラ中核（最重要ホットパス）**: `r_hotpath.iwram.c`（GBA の高速RAM=IWRAM に置いたカラム描画。68000向け最適化の主戦場）, `r_main.c`, `r_draw.c`, `r_things.c`, `r_plane.c`, `r_data.c`。
  - WAD は ROM 直リンク（`doom_iwad.c` / `GbaWadUtil`）。

## ビルド移植の到達点（GBA依存の隔離・完了）

- **エンジン C 核 59 ファイルが `-DGBA` 無しで 68000 向けに無改変コンパイル成功**。GBA ハード依存は全て `#ifdef GBA` ＋移植可能な C フォールバックで隔離済みだった。
- ビルド骨格は `port/`（`make objects` / `make unresolved`）。地雷マップ詳細は `port/PORTING.md`。
- 完全リンクに残る依存は 47 シンボルのみ:
  - **プラットフォーム層 8 関数**（`I_Error` / `I_GetBackBuffer` / `I_GetFrontBuffer` / `I_ProcessKeyEvents` / `I_*_e32` 4個）← 我々が Genesis 向けに実装。
  - **ゲームデータ** `doom_iwad` / `doom_iwad_len`（WAD→C 配列、`GbaWadUtil`）。
  - **標準ライブラリ**（libgcc/newlib 同梱で供給。`__divdi3` 等の 64bit 除算含む）。
- 残存浮動小数点は 3 ファイル（`f_finale` / `g_game` / `r_hotpath` の `I_GetTime` のみ）で全てコールドパス。**カラム描画内ループは既に整数・固定小数点化済み**。

## 初リンク（達成済み ✅）

- 全エンジン核 + シェアウェア WAD(`doom1.wad`, md5 f0cefca…) + 最小プラットフォーム層 8 関数が **68k-elf でリンク成功**。`port/build/genesis-doom-engine.{elf,bin}` 生成、リセットベクタ→`_start` 確認。
- 追加ファイル: `port/crt0.s`（ベクタ/ヘッダ/ランタイム起動）, `port/link.ld`, `port/plat_genesis.c`（8関数スタブ）, `port/d_iwad.c`（`iwad/doom1.c` を include）。`make rom` で再現。
- **計測した実機制約との乖離**:
  - ROM(コード+doom_iwad 3.84MB+libc) = **4.27MB** > 4MB フラット → **マッパー必須**。
  - 静的 RAM(.data+.bss) = **約63KB**（64KB をほぼ占有）＋ ゾーンヒープ **256KB**(malloc) → 合計 RAM 要求 **≈320KB 対 64KB（約5倍）**。
- 結論: ビルド経路は端から端まで通った。**次フェーズはメモリ収容**（ROM バンク切替・ゾーン削減・RAM 常駐最小化）とプラットフォーム層の実装化。詳細 `port/PORTING.md`。

## メモリ収容分析（完了・定量化済み）

詳細 `port/MEMORY_PLAN.md`。要点:
- **lump は ROM 直読み・RAM コスト 0**（`W_CacheLumpNum`→`&doom_iwad[]`）。`PU_CACHE` 不使用。不変ジオメトリ(vertexes/segs/nodes/lines/blockmap/reject)も ROM 直。可変状態(sectors/sides/subsectors/linedata/thingPool/blocklinks)のみ RAM。
- 実測: `globals_t`(`_g`)=**21.4KB**(うち約16KBは描画スクラッチ drawsegs8.4K/vissprites4.6K/openings3.8K…削減可)。E1M1 の PU_LEVEL=**38KB**(thingPool 17KB が最大)。
- **Genesis の最大武器: ソフトフレームバッファ廃止(−38KB)**。VDP タイル直描画で全フレームを RAM 常駐させない。
- 収容試算: E1M1 級なら ≈58KB で **収容圏内**。大マップは「1エリアごと分割」前提。不可分下限 ≈39KB(可変geometry+thingPool)。

## 映像出力層（実装・実機検証済み ✅）

詳細 `port/VIDEO.md`。
- エンジンの画素は **8bit PLAYPAL インデックス**（`lighttable_t=byte`, `colormap[idx]`）。非GBA framebuffer は short 配列だが値は 8bit インデックス。
- `port/plat_video.c`: VDP H32 初期化 / CRAM アップロード / `GEN_BlitIndexed`(8bit→4bpp タイル→VRAM+ネームテーブル, stride で engine(2)/test(1) 両対応)。
- 色削減はオフライン `tools/gen_assets.py`（PLAYPAL256 を median-cut で 16色化、256→4bit LUT と CRAM 生成）。on-target は LUT 引き+タイル化のみ。
- **検証**: 本物の Doom TITLEPIC を出力層へ流し、blastem 実機で**タイトル全画面(256x224)**と**ゲームビューポート(224x96 横長・縦半分・中央)**の両レイアウトを確認。`make harness` で再現（RAM 64KB に収まることも確認）。
- 割り切り: いまは 16色固定。Genesis は 64色(4パレット)同時可なので per-tile パレット割当で画質改善が次の候補。

## 次の一手（未確定・要指示）

- 映像の改善(16→64色 per-tile)か、メモリ収容本体(ゾーン256KB削減・上限定数Genesis化・link.ldを実機64KBへ)に進んでエンジンを実際に走らせる方向か。
