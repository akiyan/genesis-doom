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
