<a id="en"></a>

EN / [JP](#jp)

# Sources and third-party notices

## Engine

- [id Software DOOM](https://github.com/id-Software/DOOM): original Doom engine,
  copyright id Software / ZeniMax Media. The official repository grants GPL v2.
- [PrBoom](https://prboom.sourceforge.net/): Doom / Boom / LxDoom / SDL Doom
  lineage. Existing file headers retain their authors and GPL v2-or-later notices.
- [GBADoom](https://github.com/doomhack/GBADoom): ROM-backed data structures and
  GBA-oriented engine work. Original submodule revision:
  `89097b3ff31ac1e1b2cdce9854e49726cfa462bf`; vendored into `port/engine/` in
  this repository's commit `c983f6c`. See upstream for doomhack and other
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
Documentation screenshots in `docs/screenshots/` were captured in Mednafen
from a locally built ROM using Doom shareware data. The depicted Doom artwork
belongs to its original rights holders and is not covered by the project's MIT code license.

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

## Removed upstream assets

Earlier versions imported GBADoom sound effects, Bloodshedder (Bill Koch)'s
**Chiptune Doom** and **Chiptune Doom 2** tracker music, and a CodeProphet library.
References: [GBADoom upstream](https://github.com/doomhack/GBADoom) and
[Bloodshedder's Doomworld profile](https://www.doomworld.com/profile/13-bloodshedder/).
The upstream `chipdoom.txt` / `chipdm2.txt` files contain the author's
redistribution and reuse conditions. Those materials are not dependencies of
this port. Game assets, generated data, compiled binaries and the former
`gfx/stbar.h` image have been removed from every retained local branch and tag.
The original pre-cleanup history is backed up outside this repository.

Development commits are retained with rewritten IDs. Local WADs, music and
build outputs remain ignored inputs. Updating a remote repository requires
publishing the rewritten refs separately; remote copies are not altered by
this local cleanup.

---

<a id="jp"></a>

[EN](#en) / JP

# 出典と第三者の権利表記

## エンジン

- [id Software DOOM](https://github.com/id-Software/DOOM)：元の Doom エンジン。著作権者は id Software / ZeniMax Media。公式リポジトリで GPL v2 の許諾を提供しています。
- [PrBoom](https://prboom.sourceforge.net/)：Doom / Boom / LxDoom / SDL Doom から続く派生元。既存のファイルヘッダに著作者と GPL v2 以降の表記を保持しています。
- [GBADoom](https://github.com/doomhack/GBADoom)：ROM 参照型データ構造と GBA 向けエンジンの移植元。元のサブモジュールのリビジョンは `89097b3ff31ac1e1b2cdce9854e49726cfa462bf`。このリポジトリのコミット `c983f6c` で `port/engine/` に取り込みました。doomhack ほかの貢献者は上流を参照してください。Genesis 向けの変更はこのリポジトリで管理しています。

## ビルド環境とサウンドドライバ

- [Marsdev](https://github.com/andwn/marsdev)：外部のビルド環境。`toolchain/marsdev.lock` で版を固定し、このソースには同梱していません。
- [SGDK](https://github.com/Stephane-D/SGDK)：著作権 2025 Stephane Dallongeville。XGM ドライバと変換ツールは MIT。固定した Marsdev ビルドは SGDK の `cb114acadc454440fcddd616d9a7dd5a693b1b13` を使用します。ライセンスは `LICENSES/SGDK-MIT.txt`。
- [Newlib](https://sourceware.org/newlib/)：リンクする C ランタイム、版は 4.2.0。上流の権利表記を `LICENSES/Newlib.txt` に保持しています。
- [GCC runtime exception](https://www.gnu.org/licenses/gcc-exception-3.1.html)：libgcc のランタイム利用条件。`LICENSES/GCC-Runtime-Exception.txt` に保持しています。
- [GbaWadUtil](https://github.com/doomhack/GbaWadUtil)：元の IWAD の幾何データを GBADoom の ROM 参照形式へ変換する外部ツール。ソース、バイナリ、`gbadoom.wad` は同梱していません。付属ファイルや処理済みゲームデータをコピーする前に、上流の条件を個別に確認してください。

## 外部ゲームデータ

Doom shareware の `doom1.wad` は利用者がローカルに用意します。
出典は [id Software DOOM README](https://github.com/id-Software/DOOM/blob/master/README.TXT) を参照してください。
元の WAD、処理済み WAD、抽出画像、生成した C 配列は Git 管理外です。
エンジンの GPL 許諾は、ゲームデータの再配布権を与えるものではありません。
市販コンソール ROM は、この移植の入力に使っていません。
`docs/screenshots/` の文書用画像は、Doom shareware データでローカルビルドした ROM を Mednafen で撮影したものです。
画像内の Doom の素材は元の権利者に帰属し、このプロジェクトの MIT コードライセンスの対象ではありません。

## 外部音楽

以前の `music/e1m1_hangar.mid` は、FyreOnix がシーケンスした **At Doom's Gate** で、[VGMusic の配布ページ](https://www.vgmusic.com/file/f4135d253bec49497cb3323be35a0cce.html) に由来します。
MD5 は `f4135d253bec49497cb3323be35a0cce` で、以前このリポジトリで使用したファイルと一致します。
この出典表記は [Genesis64KBDoom](https://github.com/akiyan/genesis-DOOM64KB) の構成を参考にしています。
変換にはこのリポジトリ独自の `tools/midi_to_fm_vgm.py` を使います。
MIDI は `MUSIC_MIDI` でローカルから指定してください。
MIDI / VGM / XGM と生成した音楽配列は、現在のソースには同梱していません。
出典の明記だけでは、楽曲を含む録音や ROM の再配布許可にはなりません。

## 除去した上流素材

以前は GBADoom の効果音、Bloodshedder（Bill Koch）の **Chiptune Doom** と **Chiptune Doom 2** のトラッカー音楽、CodeProphet ライブラリを取り込んでいました。
参照元は [GBADoom 上流](https://github.com/doomhack/GBADoom) と [Bloodshedder の Doomworld プロフィール](https://www.doomworld.com/profile/13-bloodshedder/) です。
上流の `chipdoom.txt` / `chipdm2.txt` に作者の再配布・再利用条件があります。
これらの素材は、この移植の依存物ではありません。
ゲーム素材、生成データ、コンパイル済みバイナリ、以前の `gfx/stbar.h` 画像は、保持する全ローカルブランチとタグの履歴から除去しました。
整理前の履歴は、リポジトリ外にバックアップしています。

開発コミットは ID を書き換えて保持しています。
ローカルの WAD、音楽、ビルド生成物は引き続き Git 管理外です。
リモートへの反映には、書き換えた参照の push が必要です。
ローカルで履歴を整理するだけでは、リモートのコピーは変わりません。
