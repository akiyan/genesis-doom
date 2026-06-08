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

移植元は Game Boy Advance 版 Doom 移植の GBADoom です。
現在は必要なエンジン部分を `port/engine/` に移し、この Mega Drive 移植のソースとして管理しています。
GBA 専用の表示や音声処理は使わず、Mega Drive 用の処理を新しく用意しています。

GBADoom を選んだ理由は、元の PC 版 Doom よりも組み込み機向けに寄せやすく、整数演算中心で扱いやすいからです。

## ビルド方法

最初にローカル toolchain を作ります。
既定ではリポジトリ内の `.toolchain/marsdev/mars` を使うため、`~/toolchains` には依存しません。

```sh
tools/setup_marsdev_toolchain.sh --jobs 8
```

ROM をビルドします。

```sh
cd port
make engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

生成物は `port/build/engine/doom.bin` です。
Mednafen などの Mega Drive / Genesis エミュレータで起動できます。

```sh
mednafen build/engine/doom.bin
```

別の Marsdev を使いたい場合は `MARS_ROOT` を指定できます。

```sh
make engine-rom MARS_ROOT=/path/to/mars EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE"
```

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
