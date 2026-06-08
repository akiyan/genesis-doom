# GENESIS DOOM 移植 — GBA依存 地雷マップ / ビルド状況

GBADoom を 68k-elf 単体でビルド可能にするための依存調査結果（option 1 の成果）。

## 結論（朗報）

**GBADoom のエンジン C 核は、`-DGBA` を定義しなければ 68000 向けに無改変でコンパイルできる。**
GBA ハード依存はすべて `#ifdef GBA` で囲まれ、移植可能な C フォールバックが既に存在する。

- `source/*.c` のうち **59 ファイルが m68k-elf でコンパイル成功**（`make objects`）。
- 唯一落ちる `doom_iwad.c` は GBA 依存ではなく、ゲームデータ `iwad/doomu.c`（WAD を C 配列化したもの）が未生成なだけ。

## GBA 依存の所在（隔離対象）

| 種別 | 実体 | 扱い |
|---|---|---|
| 中央シム | `include/gba_functions.h` | `#ifdef GBA`。非GBA側は memcpy/memset/`a/b`。**そのまま使える** |
| 固定小数点除算 | `m_fixed.h` `FixedDiv` | 非GBA側は純C 64bit除算。ARM版 `source/fixeddiv.s`(udiv64_arm) は **GBA時のみ・ビルドから除外** |
| プラットフォーム層(GBA) | `source/i_system_gba.cpp` (gba.h/maxmod/timers/input) | **不使用**。独自 Genesis 層で置換 |
| プラットフォーム層(汎用) | `source/i_system_e32.cpp` (`#ifndef GBA`, Symbian C++) | 参照実装。Genesis 層を C で書き起こす |
| オーディオ | `source/i_audio.c` の gba.h/maxmod ブロック | `#ifdef GBA` でガード済 |
| セーブ | `g_game.c` の SRAM 0xE000000 直書き | Genesis SRAM/マッパーへ要置換 |
| IWRAM配置 | `*.iwram.c`（例 `r_hotpath.iwram.c`） | ファイル名規約のみ。C コードは可搬。68k では通常ファイル扱い |

## リンクに必要な残り（真の未解決シンボル: 47 個）

`make unresolved` で再生成可能。3 分類：

### (A) プラットフォーム層 — 我々が Genesis 向けに実装（8 関数のみ）
```
I_Error  I_GetBackBuffer  I_GetFrontBuffer  I_ProcessKeyEvents
I_CreateBackBuffer_e32  I_FinishUpdate_e32  I_InitScreen_e32  I_SetPallete_e32
```
（`i_system_e32.cpp` が定義していたもの。Genesis の VDP/タイル変換・パッド入力に接続）

### (B) ゲームデータ — WAD を C 配列化（GbaWadUtil）
```
doom_iwad  doom_iwad_len
```

### (C) 標準ライブラリ — ツールチェーン同梱で供給（実装不要）
`memcpy/memset/strcpy/sprintf/qsort/malloc/calloc/printf/...` と libgcc ソフト演算
`__divdi3 __udivdi3`(FixedDivの64bit除算) `__mulsi3 __divsi3 __modsi3` 等。
`libgcc.a` / newlib `libc.a` / `libnosys.a` はマルチリブに存在 → リンク可能。

## 残存浮動小数点（CLAUDE.md 優先度#2）

softfloat を引くのは **3 ファイルのみ**、いずれもコールドパス：
- `f_finale.c` — エンディング演出
- `g_game.c` — FPS/デモ計時
- `r_hotpath.iwram.c` — **`I_GetTime()` の `clock()`/double 計算のみ**。カラム描画内ループは純整数。
  → Genesis では I_GetTime を VBlank カウンタ（整数）に置換するため自然消滅。

**カラム描画ホットパスは既に整数・固定小数点化済み。** CLAUDE.md の「素地はあるので対象は限定的」を裏付け。

## 初リンク — 達成済み ✅

全エンジン核 + シェアウェア WAD + 最小プラットフォーム層が **68k-elf でリンク成功**し、
`build/genesis-doom-engine.{elf,bin}` を生成。リセットベクタ 0x04 → `_start`(0x25802) 確認。

構成:
- `crt0.s` — Genesis ベクタ/ヘッダ + C ランタイム起動(.data コピー/.bss クリア → `main`)
- `link.ld` — ROM(コード+rodata) / RAM(.data/.bss) 配置。newlib 用 `end` シンボル供給
- `plat_genesis.c` — プラットフォーム層 8 関数の最小スタブ（黒画面・無入力・無音）
- `d_iwad.c` — `gen/doom_iwad_min.c`(縮小済みシェアウェア IWAD) を include し `doom_iwad[]`/`len` 供給
- リンク: `-lc -lgcc --specs=nosys.specs`（newlib syscall は未実装スタブ＝警告のみ）

### セクションサイズ（= 実機制約との乖離の定量化）

| 領域 | サイズ | 実機(ノーマル Genesis) | 判定 |
|---|---|---|---|
| text(コード+`doom_iwad` 3.84MB+libc) | **4.27 MB** | ROM 4MB フラット | **超過 → マッパー必須**（CLAUDE.md 既知）|
| 静的 RAM (.data+.bss) | **約 63 KB** | RAM 64KB | ほぼ満杯（ゾーンヒープ前で） |
| ゾーンヒープ (`maxHeapSize`, malloc) | **256 KB** | — | 別途 64KB に対し 4倍 |

→ **合計 RAM 要求 ≈ 320KB 対 64KB（約 5倍）。** これがプロジェクト中核の課題（CLAUDE.md メモリ運用方針）。
bss 大口は暫定スタブ `g_framebuffer`(38KB)・`columnCache`(16KB) 等。

注: `link.ld` の MEMORY は初リンク検証用に rom=16MB/ram=2MB へ一時拡張してある（実機値はコメント参照）。

## ビルド方法

```sh
cd port
make objects      # エンジン核 59 個を build/ にコンパイル
make rom          # 初リンク: ELF+BIN 生成、セクションサイズ表示
make unresolved   # 真の外部依存を列挙
```

## 次の一手（メモリ最適化フェーズ）

リンクは通ったが**実機 RAM/ROM には収まらない**。ここからが本丸:
1. ROM バンク切替（マッパー）で 4MB 超の `doom_iwad` を ROM 直読み
2. ゾーンヒープ 256KB → 数十KB へ削減（または ROM 直読み比率を上げて RAM 常駐を最小化）
3. プラットフォーム層の実装化（VDP H32 タイル転送 / パッド入力 / VBlank タイマ / PSG・FM 音）
4. `r_hotpath` の 68000 向けカラム描画最適化（CLAUDE.md レンダラ最適化の優先順位）
