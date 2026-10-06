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
- The current cleanup leaves historical assets in Git; it does not certify
  that publishing the full history is cleared. Presentation files stay local.

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
