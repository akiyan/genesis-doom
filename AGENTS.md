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
- Source base is GBADoom in `third_party/GBADoom/`, chosen because it is already
  integer-heavy and designed around ROM-backed data and tight memory.

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

- The implementation writes tile pattern data through the VDP data port from the
  68000. It is not currently using DMA for the game framebuffer upload.
- The game view is fixed 2x2: the 120x64 framebuffer is expanded to 240x128 by `GEN_BlitIndexed2x2(...)` without generic scale branches.
- Tile numbers/layout are stable for the game viewport. The name table is
  written only by `GEN_BlitIndexedWithNames(...)` on the first game blit after
  Plane A clear; subsequent frames call the pattern-only `GEN_BlitIndexed2x2(...)`.
- Offline asset conversion in `tools/gen_assets.py` reduces PLAYPAL to one
  16-color Genesis palette plus a 256-entry LUT. If `host_e1m1_gen.ppm` is
  present in the working directory, that game-view sample is used for palette
  selection instead of TITLEPIC. Per-tile palette selection is out of scope; keep a single fixed gameplay palette.

See `port/VIDEO.md` for the video layer details.

## Engine State

Current milestone:

- E1M1 boots on emulated Genesis and renders the 3D view.
- The view is slow: measured around 0.5 fps at E1M1 spawn in previous profiling.
- The dominant cost is wall rendering/column work on the 68000, not VDP transfer
  bandwidth.
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

- `third_party/GBADoom/` - upstream engine source base.
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
