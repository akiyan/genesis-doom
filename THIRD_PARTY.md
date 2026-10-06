# Sources and third-party notices

## Engine

- [id Software DOOM](https://github.com/id-Software/DOOM): original Doom engine,
  copyright id Software / ZeniMax Media. The official repository grants GPL v2.
- [PrBoom](https://prboom.sourceforge.net/): Doom / Boom / LxDoom / SDL Doom
  lineage. Existing file headers retain their authors and GPL v2-or-later notices.
- [GBADoom](https://github.com/doomhack/GBADoom): ROM-backed data structures and
  GBA-oriented engine work. Original submodule revision:
  `89097b3ff31ac1e1b2cdce9854e49726cfa462bf`; vendored into `port/engine/` in
  this repository's commit `d955edf`. See upstream for doomhack and other
  contributors. Local Genesis modifications remain in this repository.

## Build and sound driver

- [Marsdev](https://github.com/andwn/marsdev): external build environment, pinned
  in `toolchain/marsdev.lock`; not shipped with this source snapshot.
- [SGDK](https://github.com/Stephane-D/SGDK), copyright 2025 Stephane Dallongeville:
  XGM driver and tools, MIT. The pinned Marsdev build selects SGDK revision
  `cb114acadc454440fcddd616d9a7dd5a693b1b13`. License: `LICENSES/SGDK-MIT.txt`.
- [Newlib](https://sourceware.org/newlib/), version 4.2.0: linked C runtime;
  bundled upstream notices are retained in `LICENSES/Newlib.txt`.
- [GCC runtime exception](https://www.gnu.org/licenses/gcc-exception-3.1.html):
  libgcc runtime terms, retained in `LICENSES/GCC-Runtime-Exception.txt`.
- [GbaWadUtil](https://github.com/doomhack/GbaWadUtil): external utility for
  converting original IWAD geometry into GBADoom's ROM-ready structures.
  Its source/binaries and `gbadoom.wad` are not vendored here. Consult upstream
  terms separately before copying any of its files or processed game data.

## External game data

Doom shareware `doom1.wad` must be supplied locally. Source reference:
[id Software DOOM README](https://github.com/id-Software/DOOM/blob/master/README.TXT).
Original WAD, processed WAD, extracted images and generated C arrays are ignored.
The engine's GPL grant does not grant redistribution rights for game data.
No commercial console ROM is an input to this port.

## External music

The former `music/e1m1_hangar.mid` is **At Doom's Gate**, sequenced by **FyreOnix**,
from [VGMusic's source entry](https://www.vgmusic.com/file/f4135d253bec49497cb3323be35a0cce.html).
Its MD5 is `f4135d253bec49497cb3323be35a0cce`, matching the file previously
used here. This attribution follows the setup documented by
[Genesis64KBDoom](https://github.com/akiyan/genesis-DOOM64KB).
This repository uses its own `tools/midi_to_fm_vgm.py` for conversion.
Supply the MIDI locally through `MUSIC_MIDI`; MIDI/VGM/XGM and generated music
arrays are not distributed in the current snapshot. Attribution alone does
not establish permission to redistribute a recording or ROM containing it.

## Historical assets

Older commits contain GBADoom sound effects, Bloodshedder (Bill Koch)'s
**Chiptune Doom** and **Chiptune Doom 2** tracker music, and a CodeProphet library.
References: [GBADoom upstream](https://github.com/doomhack/GBADoom) and
[Bloodshedder's Doomworld profile](https://www.doomworld.com/profile/13-bloodshedder/).
The historical `chipdoom.txt` / `chipdm2.txt` files contain the author's
redistribution and reuse conditions. Those materials are not dependencies of
this port and are absent from the current snapshot. The former `gfx/stbar.h`
image, labeled as a GBA Doom II HUD upstream, has also been removed.

This cleanup removes assets only from the current snapshot. It does not rewrite
history: publishing this Git repository still exposes assets in old commits.
A source archive of the cleaned snapshot does not include that history.
