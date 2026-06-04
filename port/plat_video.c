/* GENESIS DOOM - VDP 映像出力層 (本番用)
 *
 * 8bit インデックス画像 → 256→4bit LUT → 4bpp タイル → VDP VRAM + ネームテーブル。
 * GBADoom の I_FinishUpdate_e32 が要求する「描いた結果を画面へ出す」処理の Genesis 実装。
 * 表示モード H32(256x224)。レイアウト:
 *   - フルスクリーン(タイトル): 32x28 タイル全面
 *   - ゲームビューポート: 224x96(28x12) を中央配置(残りは黒)
 */
typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

/* --- VDP ポート --- */
#define VDP_DATA_L  (*(volatile u32*)0xC00000)
#define VDP_DATA_W  (*(volatile u16*)0xC00000)
#define VDP_CTRL_L  (*(volatile u32*)0xC00004)
#define VDP_CTRL_W  (*(volatile u16*)0xC00004)

#define PLANE_A     0xC000u           /* ネームテーブル A */
#define PLANE_W     64                /* スクロールプレーン横セル数(reg10=0x01) */

static inline void vdp_reg(u8 r, u8 v)      { VDP_CTRL_W = 0x8000 | (r << 8) | v; }
static inline void vdp_vram_addr(u32 a)     { VDP_CTRL_L = 0x40000000u | ((a & 0x3FFF) << 16) | ((a >> 14) & 3); }
static inline void vdp_cram_addr(u32 a)     { VDP_CTRL_L = 0xC0000000u | ((a & 0x3FFF) << 16) | ((a >> 14) & 3); }

/* H32(256x224) 初期化レジスタ 0..18 (boot/ で実機検証済みの値) */
static const u8 vdp_regs[19] = {
    0x04, 0x74, 0x30, 0x00, 0x07, 0x6C, 0x00, 0x00,   /* reg1=0x74: 表示ON+DMA+VInt有効(時刻源) */
    0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0x00, 0x02,
    0x01, 0x00, 0x00
};

void GEN_VideoInit(void)
{
    for (int i = 0; i < 19; i++)
        vdp_reg(i, vdp_regs[i]);

    /* VRAM 全クリア */
    vdp_vram_addr(0);
    for (int i = 0; i < 0x4000; i++)
        VDP_DATA_L = 0;
}

/* 16色を CRAM palette0 へ */
void GEN_SetPalette16(const u16* cram16)
{
    vdp_cram_addr(0);
    for (int i = 0; i < 16; i++)
        VDP_DATA_W = cram16[i];
}

/* プレーン A を tile0(空白) で埋める */
void GEN_ClearPlaneA(void)
{
    vdp_vram_addr(PLANE_A);
    for (int i = 0; i < PLANE_W * 32; i++)   /* 64x32 セル */
        VDP_DATA_W = 0;
}

/*
 * インデックス画像を 8x8 タイルへ変換して配置する。
 *   idx     : 画素データ先頭 (各画素 8bit パレットインデックス)
 *   stride  : 1画素あたりのバイト数 (エンジンの byte buffer=1, short=2)
 *   w,h     : ソース画像サイズ(h は8の倍数前提)
 *   col,row : 配置先のタイル座標(プレーン A セル)
 *   lut     : PLAYPAL(256) -> 0..15 写像
 *   tilebase: パターン VRAM 先頭タイル番号
 *   hscale  : 水平拡大率(1 or 2)。2 なら各ソース画素を横2回展開し、
 *             120幅の縦長 framebuffer を 240幅(正しい横長)で表示する。
 *             表示幅 = w*hscale, 表示タイル列数 = (w*hscale)/8。
 */
void GEN_BlitIndexed(const u8* idx, int stride, int w, int h,
                     int col, int row, const u8* lut, int tilebase, int hscale)
{
    const int cols = (w * hscale) >> 3;     /* 表示幅 / 8 */
    const int rows = h >> 3;
    const int hshift = hscale - 1;          /* hscale 1->>>0, 2->>>1 (68000の遅い除算回避) */
    int tilenum = 0;

    for (int cy = 0; cy < rows; cy++)
    {
        for (int cx = 0; cx < cols; cx++)
        {
            const int tile = tilebase + tilenum++;

            /* パターンを VRAM へ直書き (1タイル=8行x4バイト) */
            vdp_vram_addr((u32)tile * 32);
            for (int y = 0; y < 8; y++)
            {
                const u8* srow = idx + ((cy * 8 + y) * w) * stride;
                u32 rowbits = 0;
                for (int j = 0; j < 8; j++)
                {
                    const int sx = (cx * 8 + j) >> hshift;  /* 横拡大: ソース画素を共有 */
                    rowbits = (rowbits << 4) | (lut[srow[sx * stride]] & 0x0F);
                }
                VDP_DATA_L = rowbits;        /* 8画素=4バイト */
            }

            /* ネームテーブル: パレット0, 反転なし → 値=タイル番号 */
            const u32 cell_addr = PLANE_A + (((row + cy) * PLANE_W) + (col + cx)) * 2;
            vdp_vram_addr(cell_addr);
            VDP_DATA_W = (u16)tile;
        }
    }
}
