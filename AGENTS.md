<a id="en"></a>

EN / [JP](#jp)

# AGENTS.md - Doom -> Sega Genesis (Mega Drive) port

This file is the working guide for Codex and other coding agents in this
repository. Read it before changing code. Keep decisions here aligned with the
actual source tree and update it when major assumptions change.

## Project Goal

- Port id Software's GPL Doom source lineage to a stock Sega Genesis / Mega
  Drive.
- Target is the base console only: no 32X, no Sega CD, no commercial ROM
  reverse engineering.
- The goal is not perfect Doom. The goal is a minimal version that genuinely
  runs as Doom on stock Genesis hardware.
- Source base is GBADoom-derived engine code now vendored under `port/engine/`,
  chosen because it is already integer-heavy and designed around ROM-backed data
  and tight memory.

## Hardware Constraints

| Item | Constraint |
|---|---|
| CPU | Motorola 68000 at about 7.6 MHz |
| Sound CPU | Z80, reserved for sound work |
| Main RAM | 64 KB |
| VRAM | 64 KB |
| Video | VDP tile/sprite hardware, no linear framebuffer |
| Floating point | Not available; use fixed point/integer paths |
| ROM | Current E1M1-only ROM fits below 4 MB; full game needs banking/mapper work |

RAM is the hard limit. Keep hot mutable data in RAM, keep level data and assets
ROM-backed whenever possible, and avoid growing `.bss` casually. Small `.bss`
layout changes have previously exposed placement-dependent crashes.

## Build And Run

Work from `port/` for engine builds.

```sh
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

## Reproducing The Current Build Environment

The current known-good local environment is Ubuntu 24.04.2 LTS x86_64 with GNU
Make 4.3, host GCC 13.3.0, Python 3.12.3, and Mednafen 1.29.0. The Genesis
cross toolchain is Marsdev. The Makefiles default to the repo-local toolchain
root, and can be overridden with `MARS_ROOT=/path/to/mars`:

```sh
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc
```

Do not assume an arbitrary distro `m68k-elf-gcc` is equivalent. The current
compiler was configured as a bare-metal `m68k-elf` GCC with `--with-cpu=m68000`,
Newlib, `nosys.specs`, and libgcc available. `mars.sh` is not used by the
project Makefiles; the important part is that the binaries exist under
`$(MARS_ROOT)/m68k-elf/bin`.

The toolchain currently in use reports/fingerprints as:

```sh
m68k-elf-gcc (GCC) 13.1.0
GNU assembler (GNU Binutils) 2.40
Target: m68k-elf
Configured with: ../configure --target=m68k-elf --with-cpu=m68000 ... --with-newlib ...
```

The toolchain source pin is managed in `toolchain/marsdev.lock`, and the
bootstrap script is `tools/setup_marsdev_toolchain.sh`. Use this repo-managed
route instead of manually cloning Marsdev:

```sh
sudo apt install git build-essential texinfo wget default-jre-headless
tools/setup_marsdev_toolchain.sh --jobs 8
```

`default-jre-headless` (any `java` runtime) is mandatory: the script's SGDK
stage builds `xgmtool`/`libmd.a` and calls `need_cmd java` before it. Without
it the m68k-elf compiler installs fine but the run aborts late with
`error: missing required command: java`, leaving the toolchain incomplete (no
`xgmtool`/`libmd.a`). Re-running after installing Java resumes cleanly.

The script checks out the pinned Marsdev commit under `.toolchain/marsdev`,
initializes the pinned `m68k-gcc-toolchain` submodule, verifies its hash, builds
with `GCC_VER=13.1.0`, `BINUTILS_VER=2.40`, `NEWLIB_VER=4.2.0`, builds the SGDK
pieces needed for `libmd.a`/`xgmtool`, and installs to `.toolchain/marsdev/mars`
by default. Use a bounded job value such as `--jobs 8`; Marsdev upstream
documents that plain `-j` has caused unexplained build problems. If the Marsdev
default compiler changes, do not rely on it; update `toolchain/marsdev.lock`
only after validating the port.

Minimum host packages/tools needed by the checked-in Makefiles and helper
scripts:

- `git`, `make`, `gcc`, `g++`, `python3`, `wget`, `makeinfo` from `texinfo`
- A `java` runtime (`default-jre-headless`), required by the SGDK build stage of
  `tools/setup_marsdev_toolchain.sh` for `xgmtool`/`libmd.a`. Toolchain setup
  fails without it.
- 32-bit host C support for `gcc -m32` (`gcc-multilib` / `libc6-dev-i386` on
  Ubuntu), required by the native host harness. WAD stripping uses Python.
- `m68k-elf-gcc`, `m68k-elf-as`, `m68k-elf-objcopy`, `m68k-elf-size`, and
  `m68k-elf-nm` under `.toolchain/marsdev/mars/m68k-elf/bin` unless
  `MARS_ROOT` is overridden.
- `xvfb`, `xauth`, `mednafen`, `xdotool`, `xwininfo` from `x11-utils`, and ImageMagick tools
  such as `identify` for screenshot helpers.

Data/input assumptions:

- Original Doom shareware WAD, processed IWAD, music and all `port/gen/`
  outputs are local/ignored inputs or generated outputs; do not commit them.
- `port/d_iwad.c` supplies the native host's generated little-endian array via
  `gen/doom_iwad_host.c`. Genesis links `gen/doom_iwad_min.c` directly.
- Use external GbaWadUtil to create the little-endian ROM-ready IWAD first;
  `tools/strip_wad.py` does not accept the original DOS WAD geometry.
- Both arrays contain only E1M1; other map markers are removed too.
  CheckIWAD2 recognizes the single-map build under GENESIS / GEN_E1M1_ONLY.
- Configure DOOM1_WAD, PROCESSED_WAD, GBAWADUTIL, MUSIC_MIDI and optional
  PALETTE_SAMPLE in the ignored root `.env`; see `.env.example` and README.md.
- Assets always use TITLEPIC for palette selection unless PALETTE_SAMPLE is
  explicitly set. No implicit working-directory PPM input is allowed.
- `engine-rom` preserves generated outputs between builds. Delete `port/gen/`
  to rebuild all assets after changing input paths; do not restore them to Git.
- GPL v2 text is in LICENSE; individual upstream v2-or-later grants remain.
  Independent local tools/platform code is MIT; license scope and attribution
  are in LICENSES/README.md and THIRD_PARTY.md.
- Asset and generated-output paths have been removed from all retained local
  branch/tag histories. The pre-cleanup Git metadata backup lives outside the
  repository. Never fetch/merge the old remote history back into this checkout;
  publish rewritten refs separately. Presentation files stay local.

Quick environment sanity checks:

```sh
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc --version
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -v
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -print-file-name=nosys.specs
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -print-file-name=libc.a
printf 'int main(void){return 0;}\n' | gcc -m32 -x c - -o /tmp/m32_test
python3 --version
mednafen -version
```

Important build facts:

- `engine-rom` intentionally deletes `port/build/engine` and performs a clean
  engine rebuild every time. This avoids stale builds when `EXTRA` defines
  change.
- Generated WAD/assets under `port/gen/` are preserved because they are costly
  and not define-dependent.
- Use `pnpm` instead of `npm` if a Node-based workflow is introduced.
- `make harness` builds the video output harness ROMs.
- `make host` builds the native 32-bit host harness for engine/rendering checks.

Useful emulator helper:

```sh
bash ../tools/emu_shot.sh build/engine/doom.bin /tmp/shot.png
```

`tools/emu_shot.sh` is normally invoked through `bash`, not as an executable.

## Current Video Design

The current Genesis game view is:

| Item | Value |
|---|---|
| VDP mode | H32, 256x224, 32x28 tiles |
| Internal framebuffer | 120x64, 8-bit PLAYPAL indices |
| Displayed 3D viewport | 240x128, 30x16 tiles |
| View placement | Plane A at `col=1,row=6` |
| Bottom area | HUD / black band work area |

`port/plat_video.c` owns the Genesis VDP path:

- `GEN_VideoInit()` initializes H32 VDP state.
- `GEN_SetPalette16()` uploads the current 16-color palette to CRAM palette 0.
- `GEN_BlitIndexed2x2(idx, w, h, lut, tilebase)`
  converts 8-bit indices to 4bpp tile patterns and writes them to VRAM. `GEN_BlitIndexedWithNames(...)` is the one-shot variant that also initializes Plane A name table cells.

Current transfer behavior:

- The normal game-frame upload uses VDP DMA from two static 30-tile row buffers.
  Each row buffer is 960B; double buffering costs 1920B `.bss`. The first
  name-table setup blit still uses the generic direct-write path.
- The game view is fixed 2x2: the 120x64 framebuffer is expanded to 240x128 by `GEN_BlitIndexed2x2(...)` without generic scale branches.
- Tile numbers/layout are stable for the game viewport. The name table is
  written only by `GEN_BlitIndexedWithNames(...)` on the first game blit after
  Plane A clear; subsequent frames call the pattern-only `GEN_BlitIndexed2x2(...)`.
- Offline asset conversion in `tools/gen_assets.py` reduces PLAYPAL to one
  16-color Genesis palette plus a 256-entry LUT. If an explicit `PALETTE_SAMPLE` is
  configured, that game-view sample is used for palette selection instead of
  TITLEPIC. Unconfigured working-directory PPMs are ignored. Per-tile palette selection is out of scope; keep a single fixed gameplay palette.

See `port/VIDEO.md` for the video layer details.

An opt-in `GEN_PRECOMPOSE_COLORMAP` experiment generates ROM-backed
`LUT[COLORMAP[level][index]]` tables at build time. Its framebuffer still uses
one byte per pixel, but holds 0..15 rather than PLAYPAL indices. The default
path above is unchanged. See `port/COLORMAP_EXPERIMENT.md` for limitations,
the `GEN_BENCH_FRAMES` comparison procedure, and measured results.

## Engine State

Current milestone:

- E1M1 boots on emulated Genesis and renders the 3D view.
- The view is slow: measured around 0.5 fps at E1M1 spawn in previous profiling.
- The dominant cost is wall rendering/column work on the 68000, not VDP transfer
  bandwidth. GENESIS uses `GEN_RENDER_MAXDIST` (default 1024 map units) to
  skip far wall segments and sprites before expensive drawing work.
- Internal vertical resolution has already been reduced: Genesis uses
  `SCREENHEIGHT=96`, `viewheight=64`, framebuffer 120x64, displayed as 240x128.
- Pad input has been wired for Genesis 3-button pad movement/controls.

Current stable command for the E1M1 rendering loop is:

```sh
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

`GEN_SKIP_PSPRITE` is still important because the weapon psprite path has exposed
placement-dependent corruption. Do not treat psprite rendering as fixed unless
you have reproduced and verified it.

## Known Risks

- `.bss` layout is fragile. Adding globals, enlarging buffers, or moving static
  scratch can change crash behavior.
- Weapon psprite rendering previously caused delayed wild jumps / illegal
  instruction faults. Skipping psprites keeps the current E1M1 loop stable, but
  the root cause remains unresolved.
- Some cache/scratch buffers are tight. In particular, historical notes identify
  `columnCache[128]` / `tmpCache[128]` as risky for textures taller than 128 px.
- Debug gates such as `GEN_DBGSTAGE`, `GEN_FPSMEAS`, `GEN_SKIP_PSPRITE`,
  `GEN_SKIP_MASKEDSEG`, and other `GEN_*` probes may exist for diagnosis. Keep
  them gated and avoid affecting normal builds accidentally.
- Avoid `RANGECHECK` on Genesis unless intentionally debugging a halt. The
  preferred runtime failure mode is visual degradation over stopping the ROM.

## Optimization Guidance

Priorities:

1. Reduce rendered work before micro-optimizing individual instructions.
2. Keep RAM and `.bss` stable unless the change specifically addresses memory
   layout.
3. Profile before changing hot paths.
4. Prefer table lookups and simple fixed-point math, but do not assume all
   divisions are bottlenecks. Prior profiling showed wall-column work and
   multiplication-heavy paths dominating.
5. Be cautious with inline 68000 assembly. It can help, but host validation will
   not exercise it and previous C-level multiplication rewrites regressed speed.

Do not reintroduce a full software framebuffer beyond the current 120x64 byte
buffer. The VDP has no linear framebuffer, and the current path intentionally
converts directly to tiles.

## Repository Map

- `port/engine/` - GBADoom-derived engine source and headers used by this port.
- `port/` - Genesis port, linker scripts, platform layer, build system, host and
  video harnesses.
- `port/plat_genesis.c` - Genesis platform glue, game loop/update wiring,
  timing/input/debug integration.
- `port/plat_video.c` - VDP setup and indexed framebuffer-to-tile upload.
- `port/VIDEO.md` - detailed video-layer notes.
- `port/MEMORY_PLAN.md` - memory analysis and containment notes.
- `port/PORTING.md` - porting dependency map and build history.
- `tools/` - WAD stripping, asset generation, emulator helpers.
- `boot/` - ROM header/fixup helpers and low-level boot material.
- `wad/` - local WAD inputs.

## Development Rules

- Maintain prose documentation in English first and Japanese second, with
  `en` / `jp` anchors and language navigation. Keep commands, identifiers,
  measurements, and source links consistent between both versions.

- Do not reverse engineer or extract commercial ROM content.
- Do not switch target hardware to 32X/Sega CD.
- Do not call a visually similar standalone rewrite "done"; changes should move
  the actual GBADoom-based engine forward.
- Keep changes small and verifiable. Build and, when relevant, check a Mednafen
  screenshot/bounding box.
- Before committing, run at least:

```sh
git diff --check
git status --short
```

For display changes, build the ROM and verify the resulting image in Mednafen.

---

<a id="jp"></a>

[EN](#en) / JP

# AGENTS.md：Doom の Sega Genesis / Mega Drive 移植

このファイルは、このリポジトリで作業する Codex などのコーディングエージェント向けの手引きです。
コードを変更する前に読んでください。
記述を実際のソースと一致させ、主要な前提が変わったら更新してください。

## プロジェクトの目標

- id Software の GPL Doom ソースの系譜を、標準の Sega Genesis / Mega Drive へ移植する。
- 対象は本体のみ。32X、メガ CD、市販 ROM のリバースエンジニアリングは使わない。
- 完全な Doom の再現ではなく、標準本体で実際に Doom として動く最小構成を目指す。
- ソースの基盤は `port/engine/` に取り込んだ GBADoom 派生エンジン。整数演算中心で、ROM 参照型データと少ないメモリを前提としているため採用した。

## ハードウェア制約

| 項目 | 制約 |
|---|---|
| CPU | Motorola 68000、約 7.6 MHz |
| サウンド CPU | Z80。音声処理用に確保 |
| メイン RAM | 64 KB |
| VRAM | 64 KB |
| 映像 | VDP のタイル・スプライト方式。線形フレームバッファはない |
| 浮動小数点 | ハードウェア対応なし。固定小数点・整数の経路を使う |
| ROM | 現在の E1M1 限定 ROM は 4 MB 未満。フルゲームにはバンク切替・マッパー対応が必要 |

RAM が厳しい制約です。
頻繁に変更するデータは RAM に置き、レベルデータと素材は可能な限り ROM 参照にしてください。
`.bss` を安易に増やさないでください。
小さな `.bss` 配置変更で、配置依存のクラッシュが発生したことがあります。

## ビルドと実行

エンジンのビルドは `port/` で行います。

```sh
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

## 現在のビルド環境の再現

動作確認済みのローカル環境は Ubuntu 24.04.2 LTS x86_64、GNU Make 4.3、ホスト GCC 13.3.0、Python 3.12.3、Mednafen 1.29.0 です。
Genesis のクロスツールチェーンは Marsdev です。
Makefile の既定値はリポジトリ内のツールチェーンで、`MARS_ROOT=/path/to/mars` で変更できます。

```sh
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc
```

ディストリビューション付属の任意の `m68k-elf-gcc` が同等だとは扱わないでください。
現在のコンパイラは bare-metal の `m68k-elf` GCC で、`--with-cpu=m68000`、Newlib、`nosys.specs`、libgcc を利用できる構成です。
プロジェクトの Makefile は `mars.sh` を使いません。
バイナリが `$(MARS_ROOT)/m68k-elf/bin` にあることが必要です。

使用するツールチェーンの識別情報は次のとおりです。

```sh
m68k-elf-gcc (GCC) 13.1.0
GNU assembler (GNU Binutils) 2.40
Target: m68k-elf
Configured with: ../configure --target=m68k-elf --with-cpu=m68000 ... --with-newlib ...
```

ツールチェーンのソースの版は `toolchain/marsdev.lock` で固定しています。
導入スクリプトは `tools/setup_marsdev_toolchain.sh` です。
Marsdev を手動で clone せず、リポジトリ管理の手順を使ってください。

```sh
sudo apt install git build-essential texinfo wget default-jre-headless
tools/setup_marsdev_toolchain.sh --jobs 8
```

`default-jre-headless` などの `java` ランタイムは必須です。
スクリプトの SGDK 段階で `xgmtool` / `libmd.a` をビルドし、その前に `need_cmd java` を呼びます。
Java がないと m68k-elf コンパイラは導入できても、その後に `error: missing required command: java` で停止し、`xgmtool` / `libmd.a` のない不完全な状態になります。
Java を導入して再実行すると再開できます。

スクリプトは固定した Marsdev コミットを `.toolchain/marsdev` にチェックアウトし、固定した `m68k-gcc-toolchain` サブモジュールを初期化してハッシュを確認します。
`GCC_VER=13.1.0`、`BINUTILS_VER=2.40`、`NEWLIB_VER=4.2.0` でビルドし、`libmd.a` / `xgmtool` に必要な SGDK 部分も生成します。
既定の導入先は `.toolchain/marsdev/mars` です。
`--jobs 8` など、ジョブ数の上限を指定してください。
Marsdev 上流は、上限なしの `-j` で原因不明のビルド問題が起きたと記録しています。
Marsdev の既定コンパイラが変わっても、それに依存しないでください。
移植版を検証してから `toolchain/marsdev.lock` を更新します。

Makefile とヘルパースクリプトに必要な最小のホストパッケージ・ツールは次のとおりです。

- `git`、`make`、`gcc`、`g++`、`python3`、`wget`、`texinfo` の `makeinfo`。
- `java` ランタイム（`default-jre-headless`）。`tools/setup_marsdev_toolchain.sh` の SGDK 段階で `xgmtool` / `libmd.a` の生成に必要。ないとセットアップが失敗する。
- ネイティブのホスト検証プログラム用の `gcc -m32` 対応（Ubuntu では `gcc-multilib` / `libc6-dev-i386`）。WAD の縮小は Python で行う。
- `MARS_ROOT` を変更しない場合、`.toolchain/marsdev/mars/m68k-elf/bin` の `m68k-elf-gcc`、`m68k-elf-as`、`m68k-elf-objcopy`、`m68k-elf-size`、`m68k-elf-nm`。
- スクリーンショット用の `xvfb`、`xauth`、`mednafen`、`xdotool`、`x11-utils` の `xwininfo`、ImageMagick の `identify` など。

データと入力の前提は次のとおりです。

- Doom shareware の元 WAD、処理済み IWAD、音楽、`port/gen/` の全出力は、ローカル入力または生成物として Git 管理外にする。コミットしない。
- `port/d_iwad.c` は、ネイティブホスト用の生成済み little-endian 配列 `gen/doom_iwad_host.c` を取り込む。Genesis は `gen/doom_iwad_min.c` を直接リンクする。
- 外部の GbaWadUtil で、まず little-endian の ROM 参照用 IWAD を作る。`tools/strip_wad.py` は元の DOS WAD の幾何データを受け付けない。
- 両方の配列は E1M1 のみを含み、他のマップマーカーも除去する。CheckIWAD2 は GENESIS / GEN_E1M1_ONLY で単一マップのビルドを認識する。
- DOOM1_WAD、PROCESSED_WAD、GBAWADUTIL、MUSIC_MIDI、任意の PALETTE_SAMPLE は、ルートの Git 管理外 `.env` に設定する。`.env.example` と README.md を参照する。
- PALETTE_SAMPLE を明示しない場合、パレット選択は TITLEPIC を使う。作業ディレクトリの PPM を暗黙の入力にしない。
- `engine-rom` は生成物をビルド間で保持する。入力パスを変えて全素材を再生成する場合は `port/gen/` を削除する。Git へ戻さない。
- GPL v2 本文は LICENSE に置き、上流ファイルの v2 以降の許諾は保持する。独立した自作ツール・プラットフォームコードは MIT。適用範囲と出典は LICENSES/README.md と THIRD_PARTY.md に記録する。
- 素材・生成物のパスは、保持する全ローカルブランチ・タグの履歴から除去済み。整理前の Git メタデータのバックアップはリポジトリ外に置く。古いリモート履歴をこのチェックアウトへ fetch / merge しない。書き換えた参照を別途公開する。プレゼン資料はローカル専用。

環境の簡易確認は次のとおりです。

```sh
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc --version
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -v
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -print-file-name=nosys.specs
.toolchain/marsdev/mars/m68k-elf/bin/m68k-elf-gcc -print-file-name=libc.a
printf 'int main(void){return 0;}\n' | gcc -m32 -x c - -o /tmp/m32_test
python3 --version
mednafen -version
```

ビルド時の注意点は次のとおりです。

- `engine-rom` は毎回 `port/build/engine` を削除してエンジンをクリーンビルドする。`EXTRA` の定義変更による古いオブジェクトの混入を避けるため。
- `port/gen/` の WAD・素材は生成コストが高く、定義には依存しないため保持する。
- Node ベースの作業を導入する場合は `npm` ではなく `pnpm` を使う。
- `make harness` は映像出力のハーネス ROM を生成する。
- `make host` はエンジン・描画確認用のネイティブ 32-bit ホストプログラムを生成する。

エミュレータの撮影ヘルパーは次のとおりです。

```sh
bash ../tools/emu_shot.sh build/engine/doom.bin /tmp/shot.png
```

`tools/emu_shot.sh` は通常、実行ファイルとして直接呼ばず `bash` 経由で実行します。

## 現在の映像設計

現在の Genesis のゲーム画面は次の構成です。

| 項目 | 値 |
|---|---|
| VDP モード | H32、256x224、32x28 タイル |
| 内部フレームバッファ | 120x64、8-bit PLAYPAL インデックス |
| 表示する 3D ビューポート | 240x128、30x16 タイル |
| ビューの配置 | Plane A の `col=1,row=6` |
| 下部領域 | HUD / 黒帯用の作業領域 |

Genesis の VDP 経路は `port/plat_video.c` が担当します。

- `GEN_VideoInit()` は H32 の VDP 状態を初期化する。
- `GEN_SetPalette16()` は現在の 16 色を CRAM パレット 0 へ転送する。
- `GEN_BlitIndexed2x2(idx, w, h, lut, tilebase)` は 8-bit インデックスを 4bpp タイルパターンへ変換して VRAM に書く。`GEN_BlitIndexedWithNames(...)` は、Plane A のネームテーブルも初期化する一回限りの経路。

現在の転送方式は次のとおりです。

- 通常のゲームフレームは、静的な 30 タイルの行バッファ 2 個から VDP DMA で転送する。各バッファは 960 B、二重バッファで `.bss` を 1920 B 使う。初回のネームテーブル設定は汎用の直接書き込み経路を使う。
- ゲームビューの拡大は固定 2x2。`GEN_BlitIndexed2x2(...)` は汎用の拡大分岐を通らず、120x64 を 240x128 へ展開する。
- ビューポートのタイル番号と配置は固定。Plane A を消去した後、最初のゲーム転送でだけ `GEN_BlitIndexedWithNames(...)` がネームテーブルを書く。その後はパターンのみの `GEN_BlitIndexed2x2(...)` を使う。
- `tools/gen_assets.py` は PLAYPAL を単一の 16 色 Genesis パレットと 256 要素の LUT へオフライン変換する。PALETTE_SAMPLE を明示した場合は、TITLEPIC の代わりにそのゲーム画面を選色に使う。未指定の作業ディレクトリ内 PPM は無視する。タイルごとのパレット選択は対象外とし、ゲーム中は固定の単一パレットを維持する。

映像層の詳細は `port/VIDEO.md` を参照してください。

任意の `GEN_PRECOMPOSE_COLORMAP` 実験では、ROM 参照の `LUT[COLORMAP[level][index]]` をビルド時に生成します。
フレームバッファは 1 画素 1 バイトのままですが、PLAYPAL インデックスの代わりに 0..15 を保持します。
既定の経路は変わりません。
制限、`GEN_BENCH_FRAMES` による比較手順、実測結果は `port/COLORMAP_EXPERIMENT.md` にあります。

## エンジンの状態

現在の到達点は次のとおりです。

- エミュレータ上の Genesis で E1M1 が起動し、3D ビューを描画する。
- 描画は遅く、過去の計測では E1M1 開始地点で約 0.5 fps。
- 主な負荷は VDP 転送帯域ではなく、68000 の壁・カラム描画。GENESIS では `GEN_RENDER_MAXDIST`（既定 1024 マップ単位）で、重い描画前に遠い壁セグメントとスプライトを省く。
- 内部の縦解像度は既に削減済み。Genesis は `SCREENHEIGHT=96`、`viewheight=64`、120x64 のフレームバッファを使い、240x128 で表示する。
- Genesis の 3 ボタンパッドによる移動・操作を接続済み。

E1M1 の描画ループで現在安定しているコマンドは次のとおりです。

```sh
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

武器スプライト経路で配置依存の破損が起きたため、`GEN_SKIP_PSPRITE` は引き続き必要です。
再現と検証が済むまで、武器スプライトの描画が直ったとは扱わないでください。

## 既知の問題

- `.bss` 配置は不安定。グローバル追加、バッファ拡大、静的作業領域の移動でクラッシュの挙動が変わる場合がある。
- 武器スプライト描画で、遅れて不正ジャンプ・不正命令例外が起きた。スキップすれば現在の E1M1 ループは安定するが、原因は未解決。
- キャッシュ・作業バッファには余裕が少ない。過去の記録では、`columnCache[128]` / `tmpCache[128]` は高さ 128 px を超えるテクスチャに対して問題になり得る。
- `GEN_DBGSTAGE`、`GEN_FPSMEAS`、`GEN_SKIP_PSPRITE`、`GEN_SKIP_MASKEDSEG` などの `GEN_*` 診断定義がある。条件付きに保ち、通常ビルドへ意図せず影響させない。
- 停止を意図するデバッグ以外では Genesis の `RANGECHECK` を避ける。実行時の失敗では、ROM 停止より画面の劣化を許容する方針。

## 最適化の指針

優先順位は次のとおりです。

1. 命令単位の微調整より先に、描画する仕事量を減らす。
2. メモリ配置を目的とする変更以外では、RAM と `.bss` を安定させる。
3. 頻繁に使う経路を変える前に計測する。
4. テーブル参照と単純な固定小数点演算を優先する。ただし、除算を一律に主要な負荷だと仮定しない。過去の計測では壁カラム処理と乗算の多い経路が支配的だった。
5. 68000 のインラインアセンブリは慎重に使う。ホスト検証では通らず、C レベルの乗算書き換えで速度が落ちたこともある。

現在の 120x64 バイトのバッファを超える大きなソフトウェアフレームバッファを再導入しないでください。
VDP に線形フレームバッファはなく、現在の経路はタイルへ直接変換します。

## リポジトリの構成

- `port/engine/`：この移植で使う GBADoom 派生エンジンのソースとヘッダ。
- `port/`：Genesis 移植、リンカスクリプト、プラットフォーム層、ビルド、ホスト・映像ハーネス。
- `port/plat_genesis.c`：ゲームループ・更新、時刻、入力、デバッグを接続する Genesis 層。
- `port/plat_video.c`：VDP 設定とインデックス画像からタイルへの転送。
- `port/VIDEO.md`：映像層の詳細。
- `port/MEMORY_PLAN.md`：メモリ分析と収容計画。
- `port/PORTING.md`：移植依存関係とビルドの記録。
- `tools/`：WAD 縮小、素材生成、エミュレータ用ヘルパー。
- `boot/`：ROM ヘッダ・修正用ヘルパーと低レベルの起動処理。
- `wad/`：ローカルの WAD 入力。

## 開発ルール

- 説明文書は前半を英語、後半を日本語にし、`en` / `jp` アンカーと移動リンクを付ける。両言語でコマンド、識別子、測定値、出典リンクを一致させる。
- 市販 ROM のリバースエンジニアリングや素材抽出をしない。
- 対象を 32X / メガ CD へ変更しない。
- 見た目だけ似た独立実装を完成とは扱わない。実際の GBADoom 派生エンジンを前進させる。
- 変更は小さく、検証可能にする。ビルドし、必要に応じて Mednafen の画像や表示範囲を確認する。
- コミット前に最低限、次を実行する。

```sh
git diff --check
git status --short
```

表示を変更した場合は ROM をビルドし、Mednafen の出力画像を確認してください。
