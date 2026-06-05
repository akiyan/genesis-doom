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

## エンジン動作実証 & ゾーン実測（完了 ✅）

- **GBADoom エンジンはホスト(native 32bit)ビルドで完全動作**。E1M1 をロードして正しく描画（`make host`→`build/host/doom_host`→`host_e1m1.ppm`）。移植先と同じコードが WAD/BSP/スプライト/武器/HUD まで動く＝68k 移植は「メモリ収容＋配線」の問題に確定。
- **ゾーン実測**: InitGlobals=22KB / **タイトル(レベル無)=31.8KB** / **E1M1=82.5KB**。
- 収容方針: タイトル(31.8KB)は framebuffer バイト化＋columnCache 縮小で **64KB 収容可能**＝先に到達する「実機でエンジン起動」マイルストーン。E1M1(82.5KB)は描画.bss/framebuffer 込み総計≈140KB で実機の約2.2倍、構造体スリム化等の本丸。詳細 `port/MEMORY_PLAN.md`。

## 68k 起動への前進（ROM 関門クリア ✅）

- **第1関門「ROM>4MB」を解決**: 処理済WAD を E1M1 のみ保持に削減(2629KB、`make wad-min`→`gen/doom_iwad_min.c`)。総ROM≈3.2MB<4MB。マップマーカーは全保持で gamemode 検出維持。ホストで title/E1M1 無傷確認。
- 残る関門は `port/MEMORY_PLAN.md`「68k 起動の関門スタック」に整理: ②ゾーン(Z_Init は確保可能最大に自動適応、_sbrk で制御) ③framebuffer byte化(38→19KB) ④columnCache/vram_spare縮小 ⑤プラットフォーム配線 ⑥アドレス整列(済)。

## byte framebuffer 検証済（関門③、タイトル経路）✅

- `GENESIS` マクロで framebuffer を **120幅・1バイト/画素(19KB)** に。`v_video.c` `V_DrawPatch` を byte 化 → ホスト(`-DGENESIS`)でタイトルを 19KB バッファに正しく描画確認(`host_title_gen.ppm`)。zone も 31.8KB のまま正常。
- 残: 3D 描画関数(r_hotpath の R_DrawColumn/Span/Fuzz/Sprite + pixel typedef + byte_topleft)の byte 化(E1M1 描画で必要)、columnCache 縮小、プラットフォーム配線、68k リンク。

## エンジン実機起動 達成 ✅✅（2026-06-04）

**GBADoom エンジン本体が emulated Genesis(mednafen, 68000)で起動し、タイトル画面を実機描画**（`make engine-rom`→`port/build/engine/doom.bin`、`tools/run_emu.sh ROM 名` で起動/F9スクショ）。実際の起動経路(main→Z_Init→InitGlobals→D_DoomMain→W_Init→R_Init→…→D_StartTitle→D_DoomLoop→D_PageDrawer→V_DrawPatch→I_FinishUpdate→GEN_BlitIndexed→VDP)を通る。64KB RAM・<4MB ROM 収容、横2倍で 240x160 表示。

到達までに解決した要点:
- **エンディアン(最大の壁)**: WAD はLE, 68000 はBE。`m_swap.h` を BE でスワップに修正＋ w_wad/d_main/v_video/r_data の WAD 整数読みに `LONG()/SHORT()` 付与（GBADoom が GBA=LE 前提で外していた）。未対応だと numlumps 等が巨大値→ループでハング。
- **ヒープ枯渇**: `Z_Init` がヒープ全消費後に `lprintf`→printf の内部 malloc 失敗 → GENESIS で lprintf を no-op 化。
- **時間源**: VBlank 割り込みは不調 → VDP ステータスの VBlank ビット(0x08)をポーリングして I_GetTime を進める(plat_genesis の clock())。
- **背景透明**: パレット index0 は Genesis で透明 → backdrop 黒。
- **起動デバッグ**: backdrop 色を段階で変える GEN_trace でハング箇所を二分探索(#ifdef GENESIS で残置、要整理)。
- エミュは mednafen `-video.driver softfb`＋`systemd-run --user`（[[emulator-launch]] 参照）。

## E1M1 3D 描画: 主因バグ発見・修正（壁テクスチャのエンディアン）✅

**根本原因を特定し修正**: `patch_t` の `columnofs[]`(LONG)と `width`/`topoffset`/`leftoffset`(SHORT)を
描画ホットパス(`r_hotpath.iwram.c` の `R_GetColumn`/`R_ComposeColumn`/`R_DrawVisSprite`/`R_DrawPSprite`/
`R_ProjectSprite`)が**生読みしていた**。パッチは WAD で LE、68000 は BE なので生読みは値が壊れる
(`V_DrawPatch` は LONG/SHORT 済だったが 3D 経路は未対応)。壊れた `columnofs` で
`R_DrawColumnInCache` の `while(patch->topdelta!=0xff)` が**無限ループ**(最初の合成テクスチャ壁=
E1M1 の subsector#9/seg#3 で発生)。これが BSP 走査が止まる主因だった。**17箇所に LONG/SHORT を付与して解決**
(LE host では恒等なので host 描画は無変化)。

到達手段: 二分探索(subsector#9→seg#3→R_RenderSegLoop→R_DrawColumnInCache)。
途中、color 復号の自作ツールに ImageMagick ヘッダ行を拾うバグがあり結果を誤読していた(修正済)。

**修正後の状態**: **BSP 走査＋壁テクスチャ＋床/天井(R_DrawPlanes)まで g_fb に描けるようになった**
(旧 trace12=BSP ハングを突破し、R_DrawMasked 手前=RDBG10 まで到達)。ただし**二次ブロッカー**残存。

**二次ブロッカー = 配置依存のメモリ破壊(wild jump, PC=0)**:
- crt0 例外を GEN_fault 化し PC をニブル単色(GEN_PC_NIBBLE)で読むと **PC=0x000000**(NULL/ゼロ化された戻りアドレス
  or 関数ポインタ)。GEN_ILL_PHASE(例外時 backdrop 不変)で直前 RDBG を読むと発生フェーズは **暗紫=BSP 中**。
- **配置依存が極端**: フラグ/定数/静的化を1つ変えるだけで症状が飛ぶ(早期 black ↔ BSP の不正命令 ↔ DrawMasked)。
  これは「固定サイズの境界外書き込み(or スタック溢れ)が、配置次第で戻りアドレスに当たったり当たらなかったり」する徴候。
- **試して効かなかった(=単純なスタックオーバーフローではない)**:
  ・`stack[128]`/`tmpCache[128]` 静的化(描画は非再帰)→ 症状が移動するだけ・.bss 増で逆効果 → **revert 済**。
  ・`_sbrk` limit を下げ stack +640B → 効果なし(単純な深さ不足ではない)。
  ・静的 visplane プール/pre-alloc → 配置ずらしの偶然で前進するだけ・title の .bss を壊す → **不採用**。
  ・GEN_DETECT_RENDER_MALLOC で「描画中の Z_Malloc 無し」を確認(Z_Malloc 説は否定)。
  ・cacheheight>128(tmpCache 溢れ)→ 起きていない。visplane top/bottom は byte[SCREENWIDTH] で範囲内。
- RAM 内訳: static ~20.3KB(うち g_fb 15KB) + zone(spawn 視点)~39.8KB + stack ~1.5KB ≈ 64KB をギリギリ超過。
  scratch 実測ピーク(host RSCRATCH_PEAK 全域): drawsegs 77/96, openings 1072/1200, vissprites 0/8, visplane 需要72/プール24。
- patch BE 修正後、geometry/patch のエンディアンは全て整合確認済。**残破壊源は未特定**(固定サイズ OOB の発生箇所)。

**現状の採用分**: columnofs/寸法エンディアン修正のみ(=確実に正しい根因修正)。静的化/sbrk 等の実験は全て revert。
title 描画は維持。E1M1 は壁テクスチャ無限ループ(旧)は突破し BSP まで進むが上記 wild jump で停止。

**注意(emulator)**: `pkill -f mednafen` はコマンド文字列に "mednafen" を含むと自分自身を kill する。
起動は別スクリプト(/tmp/run_direct.sh / burst_direct.sh)を "mednafen" 抜きのコマンドで叩く。

debug 足場(全て GEN_* でゲート、通常ビルド無影響): RDBG/GEN_PROBE9/GEN_PS3/GEN_HALT_*/GEN_LOOPGUARD/
GEN_BLIT_PLANES/GEN_ILL_PHASE/GEN_DETECT_RENDER_MALLOC/GEN_PC_NIBBLE、plat_genesis の GEN_fault(例外PC点滅
＋レンジ/SP 判定)/GEN_stack_check、crt0 のスタックペイント＋例外 GEN_fault 化(title 無害確認済)。

## 次の一手（未確定・要指示）

- ①**残破壊源(固定サイズ OOB)の特定**: PC=0=ゼロ書き込みが戻りアドレスに当たる箇所を、描画各段に
  canary/境界チェックを入れて追う(配置依存なので「どの書き込みが固定で OOB か」を直接検出するのが筋)。
- ②並行で**E1M1 RAM を削る本丸**(scratch/ゾーン構造体)→ 配置に余裕を作れば症状が消える可能性。
- ③デバッグ足場の除去・整理 ④R_DrawMasked(武器スプライト)経路 ⑤パッド入力。
