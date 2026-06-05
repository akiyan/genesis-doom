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

static void vdp_dma_vram(u32 dst, const void* src, u16 words)
{
    u32 s = ((u32)src) >> 1;
    vdp_reg(19, words & 0xFF);
    vdp_reg(20, words >> 8);
    vdp_reg(21, s & 0xFF);
    vdp_reg(22, (s >> 8) & 0xFF);
    vdp_reg(23, (s >> 16) & 0x7F);
    VDP_CTRL_L = 0x40000080u | ((dst & 0x3FFF) << 16) | ((dst >> 14) & 3);
}

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
 *   hscale  : 水平拡大率(1 or 2)。2 なら各ソース画素を横2回展開する。
 *   vscale  : 垂直拡大率(1 or 2)。2 なら各ソース行を縦2回展開する。
 *             表示幅 = w*hscale, 表示高さ = h*vscale。
 */
static inline void blit_indexed_tile(const u8* idx, int stride, int w,
                                     int cx, int cy, const u8* lut,
                                     int hshift, int vscale, int tile)
{
    /* 汎用ハーネス用: hscale/vscale 1 or 2。ゲーム本体は下の2x2専用経路を使う。 */
    vdp_vram_addr((u32)tile * 32);
    if (vscale == 2)
    {
        for (int y = 0; y < 8; y += 2)
        {
            const int sy = (cy * 8 + y) >> 1;
            const u8* srow = idx + (sy * w) * stride;
            u32 rowbits = 0;
            for (int j = 0; j < 8; j++)
            {
                const int sx = (cx * 8 + j) >> hshift;
                rowbits = (rowbits << 4) | (lut[srow[sx * stride]] & 0x0F);
            }
            VDP_DATA_L = rowbits;
            VDP_DATA_L = rowbits;
        }
    }
    else
    {
        for (int y = 0; y < 8; y++)
        {
            const u8* srow = idx + ((cy * 8 + y) * w) * stride;
            u32 rowbits = 0;
            for (int j = 0; j < 8; j++)
            {
                const int sx = (cx * 8 + j) >> hshift;
                rowbits = (rowbits << 4) | (lut[srow[sx * stride]] & 0x0F);
            }
            VDP_DATA_L = rowbits;
        }
    }
}

#define GEN_DMA_ROW_TILES 30
static u16 gen_dma_row[2][GEN_DMA_ROW_TILES * 16];

static inline void vdp_dma_wait(void)
{
    while (VDP_CTRL_W & 0x0002) { }
}

static void build_indexed_row_2x2(const u8* idx, int w, int cy, const u8* lut, int cols, u16* dst)
{
    for (int cx = 0; cx < cols; cx++)
    {
        u16* tile = dst + cx * 16;
        for (int y = 0; y < 8; y += 2)
        {
            const u8* srow = idx + ((cy * 4) + (y >> 1)) * w;
            u32 rowbits = 0;
            for (int sx = 0; sx < 4; sx++)
            {
                const u32 px = lut[srow[cx * 4 + sx]] & 0x0F;
                rowbits = (rowbits << 8) | (px << 4) | px;
            }
            tile[y * 2 + 0] = (u16)(rowbits >> 16);
            tile[y * 2 + 1] = (u16)rowbits;
            tile[(y + 1) * 2 + 0] = (u16)(rowbits >> 16);
            tile[(y + 1) * 2 + 1] = (u16)rowbits;
        }
    }
}

static inline void start_indexed_row_dma(int tilebase, int cols, int cy, const u16* src)
{
    vdp_dma_vram((u32)(tilebase + cy * cols) * 32, src, (u16)(cols * 16));
}

void GEN_BlitIndexed2x2(const u8* idx, int w, int h, const u8* lut, int tilebase)
{
    const int cols = w >> 2;               /* 表示幅(w*2) / 8 */
    const int rows = h >> 2;               /* 表示高さ(h*2) / 8 */

    build_indexed_row_2x2(idx, w, 0, lut, cols, gen_dma_row[0]);
    start_indexed_row_dma(tilebase, cols, 0, gen_dma_row[0]);

    for (int cy = 1; cy < rows; cy++)
    {
        u16* buf = gen_dma_row[cy & 1];
        build_indexed_row_2x2(idx, w, cy, lut, cols, buf);
        vdp_dma_wait();
        start_indexed_row_dma(tilebase, cols, cy, buf);
    }
    vdp_dma_wait();
}

void GEN_BlitIndexedWithNames(const u8* idx, int stride, int w, int h,
                              int col, int row, const u8* lut, int tilebase, int hscale, int vscale)
{
    const int cols = (w * hscale) >> 3;     /* 表示幅 / 8 */
    const int rows = (h * vscale) >> 3;
    const int hshift = hscale - 1;          /* hscale 1->>>0, 2->>>1 (68000の遅い除算回避) */
    int tilenum = 0;

    for (int cy = 0; cy < rows; cy++)
    {
        for (int cx = 0; cx < cols; cx++)
        {
            const int tile = tilebase + tilenum++;
            blit_indexed_tile(idx, stride, w, cx, cy, lut, hshift, vscale, tile);

            /* ネームテーブル: パレット0, 反転なし -> 値=タイル番号 */
            const u32 cell_addr = PLANE_A + (((row + cy) * PLANE_W) + (col + cx)) * 2;
            vdp_vram_addr(cell_addr);
            VDP_DATA_W = (u16)tile;
        }
    }
}

/* ===== デバッグ: 描画段階を左下にスプライト(色付き■＋3字ラベル)で表示 =====
 * 3Dビューは tile 1..480 を使うので、デバッグ用パターンは tile 512+ の空きへ。
 * 各段=4タイル帯[■(段色) + 英3字]。段切替はスプライト pattern を1ワード書くだけ。 */
#define DBG_TILE   512u            /* デバッグ用パターン先頭タイル */
#define DBG_SAT    0xD800u         /* スプライト属性テーブル(reg5=0x6C) */
#define DBG_NSTAGE 12
#define FPS_TILE   (DBG_TILE + DBG_NSTAGE * 4u)

/* 5x7 フォント(MSB=左, bits7-3使用)。必要文字のみ。 */
static const char dbg_fchars[16] = {'B','C','D','E','F','I','K','L','M','N','P','S','T','V','2',' '};
static const u8 dbg_font[16][8] = {
    {0xE0,0x90,0x90,0xE0,0x90,0x90,0xE0,0}, /*B*/ {0x70,0x88,0x80,0x80,0x80,0x88,0x70,0}, /*C*/
    {0xE0,0x90,0x88,0x88,0x88,0x90,0xE0,0}, /*D*/ {0xF8,0x80,0x80,0xF0,0x80,0x80,0xF8,0}, /*E*/
    {0xF8,0x80,0x80,0xF0,0x80,0x80,0x80,0}, /*F*/ {0x70,0x20,0x20,0x20,0x20,0x20,0x70,0}, /*I*/
    {0x88,0x90,0xA0,0xC0,0xA0,0x90,0x88,0}, /*K*/ {0x80,0x80,0x80,0x80,0x80,0x80,0xF8,0}, /*L*/
    {0x88,0xD8,0xA8,0x88,0x88,0x88,0x88,0}, /*M*/ {0x88,0xC8,0xA8,0x98,0x88,0x88,0x88,0}, /*N*/
    {0xF0,0x88,0x88,0xF0,0x80,0x80,0x80,0}, /*P*/ {0x70,0x88,0x80,0x70,0x08,0x88,0x70,0}, /*S*/
    {0xF8,0x20,0x20,0x20,0x20,0x20,0x20,0}, /*T*/ {0x88,0x88,0x88,0x88,0x50,0x50,0x20,0}, /*V*/
    {0x70,0x88,0x08,0x30,0x40,0x80,0xF8,0}, /*2*/ {0,0,0,0,0,0,0,0},                       /*sp*/
};
/* 段の色(g_tracepal index)とラベル(R_RenderPlayerView の RDBG 順) */
static const u8 dbg_color[DBG_NSTAGE]      = {11,13,15,9,12,5,8,7,2,10,14,6};
static const char dbg_label[DBG_NSTAGE][4] = {"STP","CLP","CDS","CPL","BSP","BSE","PLN","PLE","VP2","MSK","MSE","FIN"};

static int dbg_glyph(char c){ for(int i=0;i<16;i++) if(dbg_fchars[i]==c) return i; return 15; }
static void dbg_char_tile(u32 tile, char c){
    const u8* g = dbg_font[dbg_glyph(c)];
    vdp_vram_addr(tile*32);
    for(int y=0;y<8;y++){ u32 row=0; u8 b=g[y];
        for(int x=0;x<8;x++) row=(row<<4)|((b&(0x80>>x))?0xF:0);
        VDP_DATA_L=row; }
}
/* ■: 段色(nib)ベタ塗り。 */
static void dbg_box_tile(u32 tile, unsigned nib){
    u32 row = nib*0x11111111u; vdp_vram_addr(tile*32);
    for(int y=0;y<8;y++) VDP_DATA_L = row;
}


static const u8 fps_font[11][8] = {
    {0x70,0x88,0x98,0xA8,0xC8,0x88,0x70,0}, /* 0 */
    {0x20,0x60,0x20,0x20,0x20,0x20,0x70,0}, /* 1 */
    {0x70,0x88,0x08,0x30,0x40,0x80,0xF8,0}, /* 2 */
    {0xF0,0x08,0x08,0x70,0x08,0x08,0xF0,0}, /* 3 */
    {0x10,0x30,0x50,0x90,0xF8,0x10,0x10,0}, /* 4 */
    {0xF8,0x80,0x80,0xF0,0x08,0x88,0x70,0}, /* 5 */
    {0x30,0x40,0x80,0xF0,0x88,0x88,0x70,0}, /* 6 */
    {0xF8,0x08,0x10,0x20,0x40,0x40,0x40,0}, /* 7 */
    {0x70,0x88,0x88,0x70,0x88,0x88,0x70,0}, /* 8 */
    {0x70,0x88,0x88,0x78,0x08,0x10,0x60,0}, /* 9 */
    {0x00,0x00,0x00,0x00,0x00,0x60,0x60,0}, /* . */
};

static void fps_write_tile(u32 tile, unsigned glyph)
{
    const u8* g = fps_font[glyph];
    vdp_vram_addr(tile * 32);
    for (int y = 0; y < 8; y++) {
        u32 row = 0;
        u8 b = g[y];
        for (int x = 0; x < 8; x++)
            row = (row << 4) | ((b & (0x80 >> x)) ? 0xF : 0);
        VDP_DATA_L = row;
    }
}

void GEN_DrawFps100(unsigned fps100);

void GEN_FpsInit(void)
{
    vdp_cram_addr(62);                      /* palette1 index15 = white */
    VDP_DATA_W = 0x0EEE;

    vdp_vram_addr(DBG_SAT+8);               /* sprite1: FPS, linked from debug sprite0 */
    VDP_DATA_W = 128+196;
    VDP_DATA_W = 0x0C00;
    VDP_DATA_W = 0xA000 | FPS_TILE;
    VDP_DATA_W = 128+216;

    GEN_DrawFps100(0);
}

void GEN_DrawFps100(unsigned fps100)
{
    if (fps100 > 999)
        fps100 = 999;
    fps_write_tile(FPS_TILE + 0, (fps100 / 100) % 10);
    fps_write_tile(FPS_TILE + 1, 10);
    fps_write_tile(FPS_TILE + 2, (fps100 / 10) % 10);
    fps_write_tile(FPS_TILE + 3, fps100 % 10);
}

/* init: パレット1 ＋ 段帯タイル生成 ＋ 左下スプライト設置。tracepal は段色源。 */
void GEN_DbgInit(const u16* tracepal){
    vdp_cram_addr(32);                      /* palette1(色16-31)=バイトaddr 32。0=透明,1..12=段色,15=白 */
    VDP_DATA_W = 0;
    for(int i=0;i<DBG_NSTAGE;i++) VDP_DATA_W = tracepal[dbg_color[i]];
    VDP_DATA_W=0; VDP_DATA_W=0;             /* 13,14 */
    VDP_DATA_W = 0x0EEE;                    /* 15 白 */
    for(int s=0;s<DBG_NSTAGE;s++){
        u32 base = DBG_TILE + s*4;
        dbg_box_tile(base, s+1);          /* ■ = palette1 index s+1 */
        for(int c=0;c<3;c++) dbg_char_tile(base+1+c, dbg_label[s][c]);
    }
    vdp_vram_addr(DBG_SAT);                 /* sprite0: 4x1, palette1, prio */
    VDP_DATA_W = 128+196;                   /* Y(画面下) */
    VDP_DATA_W = 0x0C01;                    /* size: 横4タイル/縦1, link1(FPS) */
    VDP_DATA_W = 0xA000 | DBG_TILE;         /* prio|pal1|pattern=帯0 */
    VDP_DATA_W = 128+8;                     /* X(画面左) */
}
/* 段切替: colorIdx(g_tracepal index)に対応する帯へスプライトを差し替え(1ワード)。 */
void GEN_DbgStage(int colorIdx){
    for(int s=0;s<DBG_NSTAGE;s++) if(dbg_color[s]==(u8)colorIdx){
        vdp_vram_addr(DBG_SAT+4);
        VDP_DATA_W = 0xA000 | (DBG_TILE + s*4);
        return;
    }
}
