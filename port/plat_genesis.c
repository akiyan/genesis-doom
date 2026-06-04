/* GENESIS DOOM - プラットフォーム層 最小スタブ
 *
 * GBADoom のエンジンが要求する i_system_e32.* の表面を Genesis 向けに埋める。
 * 現段階は「初リンクを通す」ことが目的の最小実装（黒画面・無入力）。
 * 後段で VDP タイル変換転送・パッド入力・VBlank タイマへ肉付けする。
 */
#include "doomdef.h"
#include "doomtype.h"
#include "i_system_e32.h"

/* 内部解像度 120x160 のバックバッファ（暫定。実機 RAM には収まらない量で、
 * メモリ最適化フェーズで VDP 経由の縮小描画へ置換する想定）。 */
static unsigned short g_framebuffer[SCREENWIDTH * SCREENHEIGHT];

void I_InitScreen_e32(void)        { /* TODO: VDP H32 初期化 */ }
void I_CreateBackBuffer_e32(void)  { /* TODO */ }

int  I_GetVideoWidth_e32(void)     { return SCREENWIDTH; }
int  I_GetVideoHeight_e32(void)    { return SCREENHEIGHT; }

void I_FinishUpdate_e32(const byte* srcBuffer, const byte* pallete,
                        const unsigned int width, const unsigned int height)
{
    (void)srcBuffer; (void)pallete; (void)width; (void)height;
    /* TODO: 120x160 → タイルパターン化して VDP へ DMA 転送 */
}

void I_SetPallete_e32(const byte* pallete) { (void)pallete; /* TODO: CRAM 更新 */ }

void I_ProcessKeyEvents(void)      { /* TODO: パッド読み取り→イベント */ }

int  I_GetTime_e32(void)           { return 0; /* TODO: VBlank カウンタ */ }
void I_Quit_e32(void)              { for(;;) {} }

unsigned short* I_GetBackBuffer(void)  { return g_framebuffer; }
unsigned short* I_GetFrontBuffer(void) { return g_framebuffer; }

void I_Error(const char* error, ...)
{
    (void)error;
    /* TODO: メッセージ表示。今は停止のみ */
    for(;;) {}
}
