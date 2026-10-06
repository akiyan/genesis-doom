<a id="en"></a>

EN / [JP](#jp)

# Build-time colormap composition experiment

Status: experimental, not ready to enable by default. The instrumented
comparison completes, but the normal precomposed build faulted at startup
while the saved unmodified normal build rendered E1M1 with the same launch
procedure. There is no measured fps gain to justify adopting this change.

`GEN_PRECOMPOSE_COLORMAP` is opt-in. It keeps the original texture indices in
ROM and replaces the lighting tables with
`asset_pal_lut[COLORMAP[level][original_index]]`. The framebuffer remains
120x64 bytes, containing Genesis color indices 0..15. Normal DMA row packing
no longer looks up a palette LUT. Initial name-table upload accepts a null LUT
for this representation. The title's separate asset path is unaffected.

`tools/gen_colormap16.py` reads the locally generated reduced engine WAD C
array and generated gameplay LUT, preserving all 34 colormaps. Make regenerates
the header if either input changes; it does not rewrite the WAD. Generated
tables are const and aligned to four bytes for the existing bulk-copy path.

Patch drawing, background fill, rectangles and automap pixels convert their
raw source colors when writing. Genesis byte pitches are used in the newly
gated fill/pixel paths. Fuzz rendering samples already reduced framebuffer
colors, so its 16-entry table is an approximation (the modal original result
within each palette bin). It cannot preserve all original fuzz results.
The existing psprite issue remains; use `GEN_SKIP_PSPRITE`.

## Measurement, 2026-09-14

Mednafen 1.29.0, NTSC, default `-O2`, E1M1 spawn, no input, with
`GEN_BOOT_E1M1`, `GEN_DBGSTAGE`, `GEN_SKIP_PSPRITE`, and
`GEN_BENCH_FRAMES=32` in both variants. Only the after variant adds
`GEN_PRECOMPOSE_COLORMAP`. The benchmark bypasses the title button wait,
discards three complete updates, and measures the next 32 update intervals
using the ROM's VBlank counter. This includes game processing, rendering,
and upload; it is not a texture-only microbenchmark. Emulation wall-clock
speed (`-nothrottle`) is not used in the calculation.

| Variant | Elapsed VBlanks | Frames | Average fps (60 Hz convention) |
| --- | ---: | ---: | ---: |
| Original palette path | 2336 | 32 | 0.821918 |
| Precomposed palette path | 2336 | 32 | 0.821918 |

Two independent cold starts per variant produced the same 2,336 ticks and
pixel-identical screenshots. No overall fps improvement was measured in this scene. The counter has
one-VBlank resolution; these numbers do not prove zero CPU-cycle savings.
Do not generalize this one spawn view to other positions or effects.

The normal baseline has 15,356 bytes of `.bss`; the normal experimental
build also has 15,356. The benchmark ROM text grows by 8,648 bytes. Benchmark counters add eight bytes equally to both
variants. Intermediate experimental ROM layouts faulted before completing
the benchmark. Aligning the new tables alone did not eliminate that behavior;
the root cause is not established. Keep this experiment gated rather than
treating the existing placement-dependent stability problem as fixed.
The normal-build comparison screenshots are `build/colormap-bench/normal-before.png`
and `build/colormap-bench/normal.png`. The latter shows the fault indication;
it is not a successful gameplay screenshot.

## Reproduction

Run from the repository root. Preserve each ROM before the next clean build:

```sh
mkdir -p port/build/colormap-bench
make -C port engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE -DGEN_BENCH_FRAMES=32"
cp port/build/engine/doom.bin port/build/colormap-bench/before.bin
make -C port engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE -DGEN_BENCH_FRAMES=32 -DGEN_PRECOMPOSE_COLORMAP"
cp port/build/engine/doom.bin port/build/colormap-bench/after.bin
bash tools/emu_bench_shot.sh port/build/colormap-bench/before.bin port/build/colormap-bench/before.png
bash tools/emu_bench_shot.sh port/build/colormap-bench/after.bin port/build/colormap-bench/after.png
python3 tools/check_colormap16.py
```

Successful benchmark completion freezes with a green backdrop. The eight
digits below the viewport are elapsed VBlanks; the lower-right sprite shows
rounded average fps. Compute `60 * 32 / ticks` for more precision. A fault in
a benchmark build instead freezes red with the decimal fault PC and exception
kind in the same fields; never interpret that as a performance result.

The capture helper uses an isolated Mednafen directory and X display. Its
wait duration only determines when to capture the already-frozen result.
Verify the completion indicator, and increase the wait on a slower host.

`tools/check_colormap16.py` checks all 8,704 combined entries and compiles the
actual before/after C tile-row builders on the host, comparing all 15,360
output bytes for a deterministic 120x64 input. It does not exercise the 68000,
VDP DMA, fuzz approximation, or every UI/gameplay path.

For normal play, omit `GEN_BENCH_FRAMES=32`; omit
`GEN_PRECOMPOSE_COLORMAP` as well to restore the original palette path.

Final default build (experiment and benchmark disabled) was byte-identical
to the saved pre-change ROM, SHA-256:
`0015f70a70461aed523623691e527dc8a03355c62490577d0a2ecf49c9ca6802`.

---

<a id="jp"></a>

[EN](#en) / JP

# ビルド時のカラーマップ合成実験

この実験は既定で有効にできる状態にはありません。
計測用ビルドの比較は完了しましたが、通常の事前合成ビルドは起動時に例外を起こしました。
保存した変更前の通常ビルドは、同じ起動手順で E1M1 を描画しました。
採用を裏づける FPS 向上は測定できていません。

`GEN_PRECOMPOSE_COLORMAP` は明示指定で有効になります。
ROM 内の元のテクスチャインデックスを保持し、照明テーブルを `asset_pal_lut[COLORMAP[level][original_index]]` に置き換えます。
フレームバッファは 120x64 バイトのままで、Genesis の色番号 0..15 を格納します。
通常の DMA 行生成ではパレット LUT を参照しなくなります。
初回のネームテーブル転送は、この形式では null LUT を受け付けます。
タイトル画面の別アセット経路には影響しません。

`tools/gen_colormap16.py` は、ローカルで生成した縮小 WAD の C 配列とゲーム用 LUT を読み、34 個すべてのカラーマップを保持します。
Make はいずれかの入力が変わるとヘッダを再生成しますが、WAD は書き換えません。
生成テーブルは const で、既存の一括コピー経路に合わせて 4 バイト境界に配置します。

パッチ描画、背景塗り、矩形、オートマップの画素は、書き込み時に元の色を変換します。
新たに条件付きで追加した塗り・画素経路は、Genesis のバイト単位の行幅を使います。
fuzz 描画は既に減色した画面の色を参照するため、16 要素のテーブルは近似です。
各パレット区分で元の結果の最頻値を選びますが、元の fuzz 結果をすべて保持することはできません。
既存の武器スプライトの問題は残るため、`GEN_SKIP_PSPRITE` を使ってください。

## 測定：2026-09-14

Mednafen 1.29.0、NTSC、既定の `-O2`、E1M1 の開始地点、入力なしで比較しました。
両案に `GEN_BOOT_E1M1`、`GEN_DBGSTAGE`、`GEN_SKIP_PSPRITE`、`GEN_BENCH_FRAMES=32` を指定し、変更後だけに `GEN_PRECOMPOSE_COLORMAP` を加えました。
ベンチマークはタイトルのボタン待ちを飛ばし、完了した更新 3 回を捨てた後、次の 32 更新間隔を ROM の VBlank カウンタで測ります。
ゲーム処理、描画、転送を含む測定であり、テクスチャ処理だけの測定ではありません。
エミュレーションの実時間速度（`-nothrottle`）は計算に使いません。

| 案 | 経過 VBlank | フレーム数 | 平均 FPS（60 Hz 換算） |
|---|---:|---:|---:|
| 元のパレット経路 | 2336 | 32 | 0.821918 |
| 事前合成パレット経路 | 2336 | 32 | 0.821918 |

各案を独立に 2 回コールドスタートし、いずれも 2336 tick と画素が完全一致する画像を得ました。
この場面で全体の FPS 向上は測定できませんでした。
カウンタの分解能は 1 VBlank なので、CPU サイクルの節約がゼロだと証明する数値ではありません。
この開始地点だけの結果を、別の位置や効果へ一般化しないでください。

通常の基準ビルドと通常の実験ビルドの `.bss` は、ともに 15,356 バイトです。
ベンチマーク ROM の text は 8648 バイト増えます。
計測カウンタは両案に同じ 8 バイトを加えます。
途中の実験 ROM の配置では、計測完了前に例外が起きました。
新テーブルのアラインメントだけでは解消せず、原因は確定していません。
配置に依存する既存の安定性問題が直ったとは扱わず、実験は条件付きのままにします。
通常ビルドの比較画像は `build/colormap-bench/normal-before.png` と `build/colormap-bench/normal.png` です。
後者は例外表示であり、正常なゲーム画面ではありません。

## 再現手順

リポジトリのルートから実行します。
次のクリーンビルドの前に、各 ROM を保存してください。

```sh
mkdir -p port/build/colormap-bench
make -C port engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE -DGEN_BENCH_FRAMES=32"
cp port/build/engine/doom.bin port/build/colormap-bench/before.bin
make -C port engine-rom EXTRA="-DGEN_BOOT_E1M1 -DGEN_DBGSTAGE -DGEN_SKIP_PSPRITE -DGEN_BENCH_FRAMES=32 -DGEN_PRECOMPOSE_COLORMAP"
cp port/build/engine/doom.bin port/build/colormap-bench/after.bin
bash tools/emu_bench_shot.sh port/build/colormap-bench/before.bin port/build/colormap-bench/before.png
bash tools/emu_bench_shot.sh port/build/colormap-bench/after.bin port/build/colormap-bench/after.png
python3 tools/check_colormap16.py
```

計測が正常に完了すると緑の背景で停止します。
ビューポート下の 8 桁は経過 VBlank、右下のスプライトは丸めた平均 FPS です。
より正確な値は `60 * 32 / ticks` で求めます。
計測ビルドで例外が起きると赤の背景で停止し、同じ欄に 10 進の例外 PC と例外種別を表示します。
これを性能結果として読まないでください。

撮影ヘルパーは専用の Mednafen ディレクトリと X ディスプレイを使います。
待ち時間は、既に停止した結果をいつ撮影するかだけを決めます。
完了表示を確認し、遅いホストでは待ち時間を延ばしてください。

`tools/check_colormap16.py` は合成した 8704 要素すべてを検査します。
実際の変更前・変更後の C タイル行生成関数をホストでコンパイルし、再現可能な 120x64 入力について出力 15,360 バイトを比較します。
68000、VDP DMA、fuzz の近似、すべての UI・ゲーム経路は検証しません。

通常プレイでは `GEN_BENCH_FRAMES=32` を外します。
元のパレット経路へ戻す場合は `GEN_PRECOMPOSE_COLORMAP` も外してください。

実験と計測を無効にした最終の既定ビルドは、保存した変更前 ROM とバイト単位で一致しました。
SHA-256 は `0015f70a70461aed523623691e527dc8a03355c62490577d0a2ecf49c9ca6802` です。
