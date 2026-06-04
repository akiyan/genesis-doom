/* GENESIS DOOM - プラットフォーム層 (68k 実機/blastem 向け本番配線)
 *
 * エンジンの I_*_e32 表面を Genesis VDP/RAM に接続する。
 *   - 映像: I_FinishUpdate_e32 → GEN_BlitIndexed(byte stride, hscale=2 で 120x160→240x160)
 *   - 起動トレース: 画面ボーダー色(backdrop) を段階で変える
 *       青 = グラフィック初期化到達 / 緑 = 描画ループ到達(起動成功) / 赤 = I_Error
 *   - ヒープ: _sbrk が _end〜RAM 上限から払い出し(Z_Init が収まる分だけ確保)
 *   - I_GetTime=0: タイトルに留まりデモ(E1M1=メモリ超過)へ進ませない
 */
#include "doomdef.h"
#include "doomtype.h"
#include "i_system_e32.h"
#include "assets_gen.h"
#include <time.h>

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

#define VDP_CTRL_L (*(volatile u32*)0xC00004)
#define VDP_CTRL_W (*(volatile u16*)0xC00004)
#define VDP_DATA_W (*(volatile u16*)0xC00000)

extern void GEN_VideoInit(void);
extern void GEN_SetPalette16(const u16*);
extern void GEN_ClearPlaneA(void);
extern void GEN_BlitIndexed(const u8*, int, int, int, int, int,
                            const u8*, int, int);

/* 3D ビューのみ描画(ステータスバー下32行は描かない)。framebuffer は
 * 120 x viewheight(=160-32=128) の 1バイト/画素 = 15KB。 */
#define GEN_FB_H  (SCREENHEIGHT - 32)        /* = viewheight = 128 */
static u8 g_fb[SCREENWIDTH * GEN_FB_H];

/* --- backdrop(画面ボーダー/透明色) を CRAM[63] 経由で設定。
 *     I_Error 表示と、起動デバッグ用 GEN_trace に使う。 --- */
#define TRACE_RED   0x000E
static void trace(u16 color)
{
    VDP_CTRL_L = 0xC07E0000;                 /* CRAM 書き込み addr=63(=0x7E) */
    VDP_DATA_W = color;
    VDP_CTRL_W = 0x8000 | (7 << 8) | 0x3F;   /* reg7 = palette3 色15 = CRAM63 */
}

/* エンジン起動の段階トレース(backdrop色)。ハング箇所の二分探索用に外部公開。
 * 使い方: エンジン内の任意点に `extern void GEN_trace(int); GEN_trace(N);` を挿し、
 * 停止時の画面ボーダー色で到達段階を判定する(E1M1 デバッグで再利用)。 */
void GEN_trace(int n)
{
    static const u16 pal[16] = {
        0x0E00, /*0 青*/ 0x00E0, /*1 緑*/ 0x000E, /*2 赤*/ 0x00EE, /*3 黄*/
        0x0E0E, /*4 マゼンタ*/ 0x0EE0, /*5 シアン*/ 0x0EEE, /*6 白*/ 0x0888, /*7 灰*/
        0x0006, /*8 暗赤*/ 0x0060, /*9 暗緑*/ 0x0600, /*10 暗青*/ 0x0066, /*11 暗黄*/
        0x0808, /*12 暗紫*/ 0x0680, /*13 橙*/ 0x0086, /*14 黄緑*/ 0x0408 /*15*/
    };
    trace(pal[n & 15]);
}

unsigned short* I_GetBackBuffer(void)  { return (unsigned short*)g_fb; }
unsigned short* I_GetFrontBuffer(void) { return (unsigned short*)g_fb; }

void I_InitScreen_e32(void)
{
    GEN_VideoInit();
    GEN_SetPalette16(asset_cram16);
    trace(0x0000);                           /* backdrop=黒: index0(透明)画素を黒に */
}

void I_CreateBackBuffer_e32(void) {}
int  I_GetVideoWidth_e32(void)    { return SCREENWIDTH; }
int  I_GetVideoHeight_e32(void)   { return SCREENHEIGHT; }
void I_SetPallete_e32(const byte* p) { (void)p; }   /* パレットは固定(asset_cram16) */
void I_ProcessKeyEvents(void)     {}
int  I_GetTime_e32(void)          { return 0; }
void I_Quit_e32(void)             { for(;;) {} }

static int g_cleared = 0;
void I_FinishUpdate_e32(const byte* src, const byte* pal,
                        unsigned int w, unsigned int h)
{
    (void)pal; (void)h;
#if defined(GEN_BOOT_E1M1) && defined(GEN_CHECK_FB)
    /* g_fb(=src)に可視画素(非ゼロ)があるか確認 → 空出力の切り分け。緑=内容あり/赤=全ゼロ。 */
    {
        unsigned nz = 0;
        for (unsigned i = 0; i < (unsigned)(SCREENWIDTH * GEN_FB_H); i++)
            if (((const u8*)src)[i]) { if (++nz > 64) break; }
        trace(nz > 64 ? 0x00E0 : 0x000E);
    }
#endif
    if (!g_cleared) { GEN_ClearPlaneA(); g_cleared = 1; }
    /* 120x128(3Dビュー)を横2倍=240x128 で中央(col=1,row=6)へ。下部はHUD/黒帯。 */
    GEN_BlitIndexed((const u8*)src, 1, (int)w, GEN_FB_H, 1, 6, asset_pal_lut, 1, 2);
}

void I_Error(const char* error, ...)
{
    (void)error;
#ifndef GEN_BOOT_E1M1
    trace(TRACE_RED);   /* 通常: I_Error=赤 */
#endif
    /* GEN_BOOT_E1M1 デバッグ時は背景を変えず停止 → 直前の GEN_trace 色が残り
     * P_SetupLevel のどこで I_Error に到達したかを画面色で判定できる。 */
    for(;;) {}
}

/* --- 時間源: VBlank 割り込み(crt0 _vblank)が 60Hz で加算する g_vblank。
 *     I_GetTime(非GBA) が使う clock() がこれを返す。ポーリングより堅牢で VDP 状態に非干渉。 --- */
volatile int g_vblank = 0;
clock_t clock(void) { return (clock_t)g_vblank * (CLOCKS_PER_SEC / 35); }

/* --- newlib malloc 用ヒープ: _end 〜 RAM 上限手前 から払い出し --- */
extern char _end;
static char* g_hp = 0;
void* _sbrk(int incr)
{
    char* const limit = (char*)0x00FFFA00;   /* 元に戻す(ゾーン41KB維持) */
    char* p;
    if (!g_hp) g_hp = &_end;
    if (g_hp + incr > limit) return (void*)-1;
    p = g_hp;
    g_hp += incr;
#if defined(GEN_BOOT_E1M1) && defined(GEN_ZERO_HEAP)
    /* テスト: 払い出すヒープをゼロ化(host のクリーン環境を模倣)。これで描画が
     * 安定すれば未初期化メモリ(Z_Malloc 非Calloc 等)が破損の原因と確定。 */
    { char* q = p; int n = incr; while (n-- > 0) *q++ = 0; }
#endif
    return p;
}
