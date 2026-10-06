# Genesis Doom

Mega Drive / Sega Genesis の実機相当の制約で Doom を動かすための移植実験です。
いまは製品版 Doom をそのまま遊べるものではなく、タイトル画面から E1M1 の 3D 画面を表示するところまでを動かしている段階です。

## いま動くもの

- Mega Drive / Genesis 向けの ROM をビルドできる。
- タイトル画面を表示し、ボタン入力後に一度黒画面へ切り替えてから E1M1 を起動する。
- E1M1 の 3D ビューを描画する。
- 右下に FPS 表示を出す。
- 3 ボタンパッド入力を Doom 側へ渡す。
- E1M1 の BGM を XGM 形式で再生する。

現在の安定確認では、武器の表示処理を外す `GEN_SKIP_PSPRITE` を付けてビルドしています。
武器表示まわりはまだメモリ破損や不正ジャンプの原因として切り分け中です。

## なぜ難しいか

Doom は PC 向けに書かれたゲームで、画面用メモリや作業用メモリをかなり使います。
一方、Mega Drive はおおまかに言うと次のような機械です。

- CPU は Motorola 68000、約 7.6MHz。
- メイン RAM は 64KB。
- 画面用の VRAM も 64KB。
- 画面は「好きな場所に直接ピクセルを書く」方式ではなく、8x8 ドットのタイルを並べる VDP で表示する。
- 色はパレット方式で、同時に使える色数にも強い制限がある。

そのため、この移植では Doom の描画結果をそのまま画面に出せません。
小さな 120x64 の Doom 用画面を作り、それを Mega Drive の 8x8 タイルへ変換して、240x128 に拡大して表示しています。

## ベースにしたもの

移植元は Game Boy Advance 版 Doom 移植の [GBADoom](https://github.com/doomhack/GBADoom) です。
現在は必要なエンジン部分を `port/engine/` に移し、この Mega Drive 移植のソースとして管理しています。
GBA 専用の表示や音声処理は使わず、Mega Drive 用の処理を新しく用意しています。

GBADoom を選んだ理由は、元の PC 版 Doom よりも組み込み機向けに寄せやすく、整数演算中心で扱いやすいからです。

## ライセンス

Doom 派生のエンジンと結合した ROM のコードは GPL v2 です。
元ファイルにある「v2 またはそれ以降」の許諾は保持しています。
独立した自作ツールと Genesis プラットフォーム層は MIT で公開します。
範囲は [LICENSES/README.md](LICENSES/README.md)、第三者の出典は [THIRD_PARTY.md](THIRD_PARTY.md) を参照してください。

現在のソースには WAD、楽曲、生成された画像や ROM を含めません。
利用者がゲームデータを用意し、ビルド時に変換します。
過去の Git 履歴には素材が残っています。

## ビルド環境

検証環境は Ubuntu 24.04 x86_64、GNU Make 4.3、Python 3.12、Marsdev の GCC 13.1.0 です。
Makefile は grouped targets を使うため GNU Make 4.3 以上が必要です。

```sh
sudo apt install git build-essential texinfo wget default-jre-headless gcc-multilib libc6-dev-i386 python3
bash tools/setup_marsdev_toolchain.sh --jobs 8
cp .env.example .env
mkdir -p wad music
```

`.env` は Git 管理外のローカル設定です。
GNU Make と Bash で共通に読むため、値は引用符を付けない `KEY=value` 形式で、空白を含まない絶対パスを使います。
既定のツールチェーンは `.toolchain/marsdev/mars` に入ります。
別の環境では `.env` または `make` の引数で `MARS_ROOT` を指定します。

## ゲームデータ

ローカルで Doom shareware の `doom1.wad` と、[GbaWadUtil](https://github.com/doomhack/GbaWadUtil) で処理した little-endian IWAD を用意します。
標準の DOS WAD を `strip_wad.py` に直接渡すことはできません。
GBADoom の頂点、壁、セグメント、テクスチャ番号は ROM 参照用の形式に変換する必要があります。

GbaWadUtil は外部ツールとして用意します。
Linux でソースから作る場合は Qt 5 の開発環境（`qtbase5-dev`、`qt5-qmake`）、`qmake`、`make` が必要です。
上流の実行ファイルは同じディレクトリの `gbadoom.wad` を読み込むため、外部ツールの付属ファイルとして配置します。
そのソース、バイナリ、付属 WAD の利用条件は上流で確認してください。
このリポジトリにはコピーしません。

```sh
GbaWadUtil -in /path/to/doom1.wad -out /path/to/doom1_processed.wad
```

`.env` に `DOOM1_WAD` と `PROCESSED_WAD` の絶対パスを記入します。
既定の置き場所は `wad/doom1.wad` と `wad/doom1_processed.wad` です。
`PROCESSED_WAD` が未生成の場合、Makefile は `GBAWADUTIL` で指定した実行ファイルを使って生成します。
元の WAD を変更した場合は処理済み WAD も作り直してください。

`strip_wad.py` は E1M1 のマーカーとマップデータだけを残し、Genesis 用には幾何データを big-endian に変換します。
E1M2〜E1M9 の空マーカーも取り除きます。
テクスチャ、スプライトなどの共通素材は E1M1 の描画に使用します。
ホスト検証用には little-endian の C 配列を別に生成します。

## 音楽

BGM の MIDI は [VGMusic の At Doom's Gate](https://www.vgmusic.com/file/f4135d253bec49497cb3323be35a0cce.html)（FyreOnix によるシーケンス）を参考にしています。
各自で用意した MIDI のパスを `.env` の `MUSIC_MIDI` に記入してください。
既定の置き場所は `music/e1m1_hangar.mid` です。
ビルド時に自作変換ツールで VGM、SGDK で XGM を生成します。
楽曲と生成データを Git に追加しないでください。

## ROM の生成

```sh
cd port
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

生成物は `port/build/engine/doom.bin` です。
`port/gen/` の C 配列、ヘッダ、音楽データもビルドで生成し、すべて Git 管理外に置きます。
`engine-rom` は毎回エンジンをクリーンビルドします。
生成した WAD やアセットは再利用します。
入力ファイルのパスを変えた場合は、次の方法で生成キャッシュを作り直してください。

```sh
# port/ で実行
rm -rf gen
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

パレットは既定で TITLEPIC を入力にするため、周囲に PPM があっても変わりません。
ゲーム画面から選色する場合は `.env` の `PALETTE_SAMPLE` で P6 PPM を明示し、`make regenerate-assets` を実行します。
`make regenerate-wad` は、現在の処理済み WAD から Genesis とホスト用の C 配列を作り直します。

## 動作確認

通常の起動とスクリーンショット取得には次を使います。

```sh
sudo apt install mednafen xvfb xauth xdotool x11-utils imagemagick
mednafen port/build/engine/doom.bin
bash tools/emu_shot.sh port/build/engine/doom.bin /tmp/doom.png
```

撮影ヘルパーは専用の Mednafen 保存先を使い、自分が起動したプロセスだけを停止します。
`DISPLAY` を指定しなければ Xvfb で仮想画面を起動します。
既存のデスクトップを使う場合は `.env` に `DISPLAY`、必要に応じて `XAUTHORITY` などを設定します。
音声録音は `bash tools/emu_audio.sh`、連続撮影は `bash tools/emu_burst.sh` で行えます。
録音では Mednafen の SDL 音声ドライバを使います。
音声の出力先が必要な環境では `.env` に `SDL_AUDIODRIVER`、`PULSE_SERVER` などを設定します。

`make -C port host` は 32bit のネイティブ検証プログラムを生成します。
`HOSTCC` でホスト用 C コンパイラを指定できます。
GCC 14 以降でエラーになる上流由来のポインタ型警告は、ホスト検証用ビルドでは警告として扱います。
`port/build/host/doom_host` は E1M1 を読み込み、カレントディレクトリに PPM を出力します。
Genesis の命令、VDP、割り込みを検証するには ROM をエミュレータで実行してください。
`tools/bstem_dbg.py` を使う場合は BlastEm を別途導入し、GUI の `DISPLAY` を環境変数または `.env` で指定します。

録画スクリプト `tools/emu_record.sh` は RetroArch、Genesis Plus GX、FFmpeg、Xvfb、xdotool を使います。
Genesis Plus GX の共有ライブラリは `.env` の `GPGX_CORE` で指定します。
プレゼン資料はローカル専用で、原稿と成果物を Git に含めません。
その生成スクリプトには Pillow（`python3-pil`）と Chromium が必要です。
描画スクリプトは `CHROMIUM`、PATH 上の Chromium、Playwright のローカルキャッシュの順にブラウザを探します。

## 画面まわり

Doom 側は 8-bit のパレット番号で 120x64 の小さな画面を描きます。
Mega Drive 側では、その内容を 4-bit のタイルデータへ変換して VDP に送ります。

通常フレームでは、最初だけ画面上のタイル配置を設定し、以後はタイルの中身だけを DMA 転送で更新します。
これにより、毎フレーム送るデータ量を少しでも減らしています。

タイトル画面は 16 色を基本にしています。
ただし最下行の 8 ドットだけは別パレットを使えるようにして、タイトル画像の見た目を少し保っています。
ボタンを押した後は、タイトル用の VRAM 書き換えが途中で画面に見えないように、まずパレットを黒にしてからゲーム画面へ切り替えます。

## メモリまわり

Mega Drive のメイン RAM は 64KB しかありません。
そのため、PC 版 Doom の感覚で大きな作業用配列を置くとすぐに破綻します。

この移植では次のような削減を入れています。

- ステータスバー描画を外して、画面バッファを小さくした。
- 描画中に使う一時バッファを Genesis 向けに縮めた。
- テクスチャ列キャッシュを最小限にした。
- ドア状態など、一部の動的確保を固定プールへ寄せた。
- IWAD データをできるだけ ROM 側に置く方針にした。

それでも `.bss` の配置が少し変わるだけで挙動が変わることがあります。
大きなグローバル変数を足す変更は特に注意が必要です。

## これまでに直した主な問題

- WAD 内の blockmap や壁テクスチャで、68k の endian 差による読み間違いを修正した。
- 3D 描画中のメモリ破損を、スタック、割り込み、未初期化メモリ、visplane 周辺へ順に切り分けた。
- `G_Ticker` の想定外 enum で止まらないようにした。
- タイトル画面からゲーム画面へ切り替える時、VRAM の途中状態が見えないようにした。
- FPS 表示のパターンがタイトル画面のタイルに上書きされないよう、FPS 初期化のタイミングをタイトル後へ移した。
- Marsdev / SGDK の版差で XGM driver の object 名が違う場合にも対応した。

## 音まわり

音楽は SGDK の XGM driver を使っています。
E1M1 の曲は MIDI から VGM / XGM へ変換し、ROM に組み込んで再生しています。

Mega Drive では Z80 側のサウンドドライバと 68000 側のゲーム処理が分かれているため、音を鳴らすだけでも PC 版 Doom とはかなり違う構成になります。

## 便利なデバッグ機能

移植中は、通常の printf が使いにくい場面が多いため、画面や色で状態を確認する仕組みを入れています。

- `GEN_DBGSTAGE`: 起動や描画の進行段階を画面に出す。
- `GEN_FPSMEAS`: FPS 計測を有効にする。
- `GEN_SKIP_PSPRITE`: 武器表示をスキップする。
- `GEN_SKIP_MASKEDSEG`: masked segment 描画を切り分ける。

例外発生時に backdrop color へ情報を出す経路や、スタック使用量を見るための経路もあります。

## まだ弱いところ

- 描画速度はまだ playable と言えるほど速くありません。
- 武器表示処理は未解決の不安定要因です。
- 64KB RAM にかなり詰め込んでいるため、少しの変更で壊れる可能性があります。
- フルゲーム化には ROM banking / mapper、WAD データ配置、音声まわりの整理がさらに必要です。
- テクスチャキャッシュはかなり小さくしているため、対応できるデータに制限があります。

## リポジトリ内の主な場所

- `port/`: Mega Drive 版のビルド、起動コード、VDP 表示、入力、音、移植 glue。
- `port/engine/`: GBADoom 由来の Doom エンジン本体。
- `tools/`: asset 生成や toolchain setup。
- `toolchain/`: pinned toolchain 設定。
- `.toolchain/`: setup script が作るローカル Marsdev toolchain。

## 現在の目標

まずは stock Mega Drive / Genesis の範囲で、E1M1 の表示と入力を安定させることを優先しています。
その次に、武器表示の復帰、描画速度の改善、より多くの WAD データを扱うための ROM 配置整理へ進む予定です。
