<a id="en"></a>

EN / [JP](#jp)

# Genesis Performance Notes

This file records performance ideas and measured deltas for the Genesis port.
Keep FPS numbers tied to the exact visible test point when possible.

## Measurements

| Date | Change | Test Point | FPS Before | FPS After | Notes |
|---|---|---:|---:|---:|---|
| 2026-06-06 | Double-buffered row DMA for `GEN_BlitIndexed2x2` | E1M1 spawn/start view | 0.80 | 0.83 | User-measured. Uses two 30-tile row buffers, +1920B `.bss`. |
| 2026-06-06 | Floor/ceiling far span 2-pixel coarse sampling beyond 512 | E1M1 spawn/start view | 0.83 | 0.85 | Keeps wall/sprite distance at 1024. No `.bss` increase; 8s emulator screenshot normal. |
| 2026-06-06 | Far wall column 2-pixel vertical coarse sampling beyond 512 | E1M1 spawn/start view | 0.85 | 0.85 | Keeps wall/sprite distance at 1024. No `.bss` increase; 16s screenshot FPS read as 0.85. |
| 2026-06-06 | Tiny wall columns as single sampled solid color | E1M1 spawn/start view | 0.85 | 0.83 | Rejected. 1px-only and 1-3px versions both measured 0.83, likely branch/function overhead exceeded the saved texture sampling. |
| 2026-06-06 | Floor/ceiling span distance cutoff at 512 in `R_MapPlane` | E1M1 boot/spawn | - | failed | Drew only trace/debug colors; treated as a failed implementation and reverted. |
| 2026-06-06 | Floor/ceiling marking cutoff at 512 in `R_StoreWallRange` | E1M1 boot/spawn | - | failed | Safer retry also failed: boot/spawn did not progress to normal game view. Reverted. |
| 2026-06-06 | Far plane spans as solid color beyond 512 in `R_MapPlane` | E1M1 boot/spawn | - | failed | 20s screenshot was black/trace-only. Reverted. |
| 2026-06-06 | Existing global `GEN_RENDER_MAXDIST` lowered to 512 | E1M1 boot/spawn | TBD | rejected | 20s screenshot was nonblack, but this also lowered wall/sprite distance. Reverted because walls must remain 1024. |

## Optimization Ideas

1. Reduce floor/ceiling work in `R_DrawPlanes`.
   - Skip or simplify far plane spans.
   - Failed attempts are recorded above: returning from `R_MapPlane` and skipping far visplane marking at 512 both stopped boot/spawn progress.
2. Coarsen wall texture sampling without changing internal resolution.
   - Treat texture coordinates as lower resolution at draw time.
3. Use simplified far-wall rendering.
   - Beyond a distance threshold, draw representative colors or cheaper shading instead of full texture columns.
4. Split hot draw functions by mode instead of using per-call flags.
   - ROM size may grow, but branch work and RAM pressure can drop.
5. Reduce FPS sprite update frequency.
   - Update every few frames instead of every frame.
6. Add distance/size culling for sprites and things.
   - Skip very far or sub-pixel-small objects.

## Current Video Upload

The main game blit converts the 120x64 indexed framebuffer to 240x128 Genesis tiles and uploads pattern rows with VDP DMA. It uses two static row buffers:

- one row = 30 tiles * 32 bytes = 960B
- double buffer = 1920B `.bss`

The code starts DMA for row N, builds row N+1 into the other buffer, waits before starting the next DMA, and waits once at the end. Genesis VDP DMA may still stall the 68000 bus, so measured FPS is the source of truth.

---

<a id="jp"></a>

[EN](#en) / JP

# Genesis の性能メモ

この文書は Genesis 移植の最適化案と実測した変化を記録します。
FPS の数値には、可能な限り測定した画面位置を対応づけてください。

## 測定結果

| 日付 | 変更 | 測定位置 | 変更前 FPS | 変更後 FPS | 備考 |
|---|---|---|---:|---:|---|
| 2026-06-06 | `GEN_BlitIndexed2x2` の行 DMA を二重バッファ化 | E1M1 開始地点の視点 | 0.80 | 0.83 | 利用者による測定。30 タイルの行バッファを 2 個使用し、`.bss` が 1920 B 増加。 |
| 2026-06-06 | 距離 512 を超える床・天井 span を 2 ピクセル単位で粗くサンプリング | E1M1 開始地点の視点 | 0.83 | 0.85 | 壁・スプライトの距離は 1024 のまま。`.bss` 増加なし。エミュレータ起動 8 秒後の画像は正常。 |
| 2026-06-06 | 距離 512 を超える壁カラムを縦 2 ピクセル単位で粗くサンプリング | E1M1 開始地点の視点 | 0.85 | 0.85 | 壁・スプライトの距離は 1024 のまま。`.bss` 増加なし。16 秒後の画像で FPS は 0.85。 |
| 2026-06-06 | 小さい壁カラムを 1 回サンプリングした単色で描画 | E1M1 開始地点の視点 | 0.85 | 0.83 | 不採用。高さ 1 px のみ、1〜3 px の両案とも 0.83。分岐・関数の負荷がサンプリング削減を上回った可能性がある。 |
| 2026-06-06 | `R_MapPlane` で床・天井 span を距離 512 で打ち切る | E1M1 起動・開始地点 | - | 失敗 | トレース・デバッグ色しか描かれず、実装失敗として取り消し。 |
| 2026-06-06 | `R_StoreWallRange` で床・天井のマーキングを距離 512 で打ち切る | E1M1 起動・開始地点 | - | 失敗 | より慎重な再試行でも通常のゲーム画面へ進まず、取り消し。 |
| 2026-06-06 | `R_MapPlane` で距離 512 を超える平面 span を単色化 | E1M1 起動・開始地点 | - | 失敗 | 20 秒後の画像は黒画面かトレースのみ。取り消し。 |
| 2026-06-06 | 既存の全体設定 `GEN_RENDER_MAXDIST` を 512 へ下げる | E1M1 起動・開始地点 | 未測定 | 不採用 | 20 秒後の画像は黒画面ではなかったが、壁・スプライトの距離も縮む。1024 を維持するため取り消し。 |

## 最適化案

1. `R_DrawPlanes` の床・天井処理を減らす。遠方の span を省略・簡略化する。上表のとおり、`R_MapPlane` からの早期 return と距離 512 での visplane マーキング省略は、起動・開始地点の描画を止めた。
2. 内部解像度を変えず、描画時の壁テクスチャ座標のサンプリングを粗くする。
3. 距離のしきい値を超える壁は、完全なテクスチャカラムの代わりに代表色や安価な陰影で描く。
4. 呼び出しごとのフラグ判定を減らすため、頻繁に使う描画関数をモード別に分ける。ROM は増えても、分岐や RAM の負荷を減らせる可能性がある。
5. FPS スプライトの更新を毎フレームから数フレームごとへ減らす。
6. スプライトとオブジェクトに距離・サイズによる描画除外を加え、遠すぎるものや 1 ピクセル未満のものを省く。

## 現在の映像転送

ゲーム画面の転送では、120x64 のインデックス画像を 240x128 の Genesis タイルへ変換し、パターンを行単位で VDP DMA 転送します。
静的な行バッファを 2 個使います。

- 1 行は 30 タイル × 32 バイト = 960 B。
- 二重バッファは `.bss` を 1920 B 使用。

行 N の DMA を開始し、もう一方のバッファで行 N+1 を生成します。
次の DMA の前と、最後に完了を待ちます。
Genesis の VDP DMA は 68000 のバスを停止させる場合があるため、効果の判断には実測 FPS を使います。
