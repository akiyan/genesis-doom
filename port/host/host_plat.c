/* GENESIS DOOM - ホスト(native 32bit)計測ビルド
 *
 * 目的: 同じ GBADoom エンジンを PC 上で走らせ
 *   (a) 起動〜レベルロード〜描画が論理的に通ることを確認
 *   (b) E1M1 ロード時のゾーン実使用量(ピーク近似)を実測
 *   (c) 描画結果を PPM 出力して目視検証
 * これにより 68k 収容の「目標 RAM 量」を確定する。
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>

#include "doomdef.h"
#include "d_main.h"
#include "g_game.h"
#include "z_zone.h"

typedef unsigned char  u8;
typedef unsigned short u16;

/* ---- バックバッファ ----
 * GENESIS: 120x160 の 1バイト/画素 (19KB)。非GENESIS: 240x160 相当の short バッファ。 */
#ifdef GENESIS
#define GEN_FB_H (SCREENHEIGHT - 32)         /* viewheight=128: ステータスバー描画しない */
static u8  backbuf[SCREENWIDTH * GEN_FB_H];
#else
static u16 backbuf[SCREENWIDTH * SCREENHEIGHT];
#endif
static u8  cur_pal[256 * 3];

unsigned int g_recomposites = 0;   /* columnCache 再合成カウンタ(CPU影響計測) */

unsigned short* I_GetBackBuffer(void)  { return (unsigned short*)backbuf; }
unsigned short* I_GetFrontBuffer(void) { return (unsigned short*)backbuf; }

void I_InitScreen_e32(void)       {}
void I_CreateBackBuffer_e32(void) {}
int  I_GetVideoWidth_e32(void)    { return SCREENWIDTH; }
int  I_GetVideoHeight_e32(void)   { return SCREENHEIGHT; }
void I_ProcessKeyEvents(void)     {}
int  I_GetTime_e32(void)          { return 0; }
void I_Quit_e32(void)             { exit(0); }

void I_SetPallete_e32(const byte* pal) { if (pal) memcpy(cur_pal, pal, 256*3); }

void I_Error(const char* error, ...)
{
    va_list ap; va_start(ap, error);
    fprintf(stderr, "\nI_Error: "); vfprintf(stderr, error, ap); fprintf(stderr, "\n");
    va_end(ap);
    exit(1);
}

/* ---- ゾーン使用量の計測 (z_zone.c の構造を複製して走査) ---- */
typedef struct memblock_s {
    unsigned int size:24;
    unsigned int tag:4;
    void** user;
    struct memblock_s* next;
    struct memblock_s* prev;
} memblock_t;
typedef struct { memblock_t blocklist; memblock_t* rover; } memzone_t;
extern memzone_t* mainzone;
extern const unsigned int maxHeapSize;

static void zone_report(const char* when)
{
    if (!mainzone) { printf("[zone] %s: mainzone=NULL\n", when); return; }
    unsigned used = 0, freeb = 0, nused = 0, nfree = 0, biggestfree = 0;
    for (memblock_t* b = mainzone->blocklist.next; b != &mainzone->blocklist; b = b->next) {
        if (b->user) { used += b->size; nused++; }
        else { freeb += b->size; nfree++; if (b->size > biggestfree) biggestfree = b->size; }
    }
    printf("[zone] %-18s heap=%uKB  used=%uB(%uKB,%u blk)  free=%uB(%uKB,%u blk) maxfree=%uKB\n",
           when, maxHeapSize/1024, used, used/1024, nused, freeb, freeb/1024, nfree, biggestfree/1024);
}

/* ---- 描画結果 → PPM ---- */
static void dump_ppm(const char* path)
{
    FILE* f = fopen(path, "wb");
    if (!f) return;
#ifdef GENESIS
    const int H = GEN_FB_H;       /* 128: ステータスバー無し */
#else
    const int H = SCREENHEIGHT;
#endif
    fprintf(f, "P6\n%d %d\n255\n", SCREENWIDTH, H);
    for (int i = 0; i < SCREENWIDTH*H; i++) {
        u8 idx = backbuf[i] & 0xFF;   /* GENESIS=byte配列, 非GENESIS=short低バイト */
        fputc(cur_pal[idx*3+0], f); fputc(cur_pal[idx*3+1], f); fputc(cur_pal[idx*3+2], f);
    }
    fclose(f);
    printf("[ppm] wrote %s (%dx%d)\n", path, SCREENWIDTH, SCREENHEIGHT);
}

/* ---- フレーム駆動 + 計測トリガ ---- */
static int frames = 0;
static int level_loaded = 0;

void I_FinishUpdate_e32(const byte* src, const byte* pal, unsigned int w, unsigned int h)
{
    (void)src; (void)pal; (void)w; (void)h;
    frames++;

#ifdef GENESIS
    /* GENESIS byte 経路の検証: E1M1 を 3D 描画して 120x160 byte で出力 */
#ifdef GEN_CACHE_STATS
    extern unsigned int g_recomposites;
    static unsigned int last_rc = 0;
    if (frames > 5 && frames <= 40)
        printf("[colcache] frame %d: 再合成 %u 回/フレーム\n", frames, g_recomposites - last_rc);
    last_rc = g_recomposites;
#endif
    if (frames == 3) {
        zone_report("title(GENESIS byte fb)");
        printf("[host] loading E1M1 (GENESIS byte path)...\n");
        G_DeferedInitNew(sk_medium, 1, 1);
    }
    if (frames == 40) {
        zone_report("E1M1(GENESIS byte fb)");
        dump_ppm("host_e1m1_gen.ppm");
        printf("[host] GENESIS E1M1 dumped. frames=%d\n", frames);
        exit(0);
    }
#else
    if (frames == 3) {
        zone_report("title(pre-level)");
        printf("[host] loading E1M1...\n");
        G_DeferedInitNew(sk_medium, 1, 1);
    }
    if (frames >= 4 && !level_loaded) {
        level_loaded = 1;
    }
    if (frames == 40) {
        zone_report("E1M1(in-game)");
        dump_ppm("host_e1m1.ppm");
        printf("[host] done. frames=%d\n", frames);
        exit(0);
    }
#endif
}

/* ---- 非標準 libc 補完 ---- */
char* strupr(char* s) { for (char* p = s; *p; p++) if (*p >= 'a' && *p <= 'z') *p -= 32; return s; }
char* itoa(int v, char* buf, int base) {
    char tmp[34]; int i = 0, neg = (v < 0 && base == 10);
    unsigned int u = neg ? -v : v;
    if (!u) tmp[i++] = '0';
    while (u) { int d = u % base; tmp[i++] = d < 10 ? '0'+d : 'a'+d-10; u /= base; }
    int j = 0; if (neg) buf[j++] = '-';
    while (i) buf[j++] = tmp[--i];
    buf[j] = 0; return buf;
}

/* ---- main: i_main.c を踏襲 (sound はスタブ) ---- */
void I_Init(void);
int main(int argc, const char* const* argv)
{
    (void)argc; (void)argv;
    printf("[host] GENESIS DOOM host measurement build\n");
    I_PreInitGraphics();
    Z_Init();
    zone_report("after Z_Init");
    InitGlobals();
    zone_report("after InitGlobals");
    D_DoomMain();    /* ループ。I_FinishUpdate_e32 内で計測して exit する */
    return 0;
}
