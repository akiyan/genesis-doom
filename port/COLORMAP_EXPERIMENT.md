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
