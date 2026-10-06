/* SPDX-License-Identifier: MIT */
#include "xgm_player.h"
#include "xgm_driver_gen.h"
#include "xgm_music_gen.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define Z80_RAM        ((volatile u8*)0x00A00000)
#define Z80_BUS        (*(volatile u16*)0x00A11100)
#define Z80_RESET      (*(volatile u16*)0x00A11200)
#define Z80_BANK       ((volatile u8*)0x00A06000)
#define Z80_COMMAND    (*(volatile u8*)0x00A00100)
#define Z80_STATUS     (*(volatile u8*)0x00A00102)   /* bit7=READY (Z80_DRV_STAT_READY) */
#define Z80_PARAMS     ((volatile u8*)0x00A00104)
#define Z80_MODIFYING  (*(volatile u8*)0x00A00112)
#define Z80_PENDING    (*(volatile u8*)0x00A00113)

static int g_xgm_started;

static void z80_request(void)
{
    Z80_BUS = 0x0100;
    Z80_RESET = 0x0100;
    while (Z80_BUS & 0x0100) { }
}

static void z80_release(void)
{
    Z80_BUS = 0x0000;
}

static void z80_reset_assert(void)
{
    Z80_RESET = 0x0000;
}

static void z80_reset_release(void)
{
    Z80_RESET = 0x0100;
}

static void z80_set_bank0(void)
{
    for (int i = 0; i < 9; i++)
        *Z80_BANK = 0;
}

static void z80_upload(unsigned addr, const u8 *src, unsigned len)
{
    volatile u8 *dst = Z80_RAM + addr;
    while (len--)
        *dst++ = *src++;
}

static void set_next_frame(unsigned count, int replace)
{
    z80_request();
    while (Z80_MODIFYING) {
        z80_release();
        for (volatile int i = 0; i < 16; i++) { }
        z80_request();
    }
    if (replace)
        Z80_PENDING = (u8)count;
    else
        Z80_PENDING = (u8)(Z80_PENDING + count);
    z80_release();
}

static void xgm_load_driver(void)
{
    /* SGDK Z80_loadDriverInternal と同じ順序で Z80 を起動する。
     * 旧実装は bus 解放前に reset を解除しており、mednafen 等で Z80 が
     * 起動せず READY も立たない(=完全無音)原因になっていた。
     * 正しくは upload 後に startReset → releaseBus → wait → endReset。 */
    z80_request();
    z80_set_bank0();
    for (unsigned i = 0; i < 0x2000; i++)
        Z80_RAM[i] = 0;
    z80_upload(0, xgm_driver, xgm_driver_len);
    z80_reset_assert();                          /* startReset */
    z80_release();                               /* releaseBus(reset 保持のまま) */
    for (volatile long i = 0; i < 4000; i++) { } /* waitSubTick 相当 */
    z80_reset_release();                         /* endReset → Z80 実行開始 */
}

static void xgm_start_song(const u8 *song)
{
    u8 ids[0x100 - 4];
    for (unsigned i = 0; i < 0x3F; i++) {
        u32 addr = ((u32)song[i * 4 + 0] << 8) | ((u32)song[i * 4 + 1] << 16);
        if (addr == 0x00FFFF00u)
            addr = 0;
        else
            addr += (u32)song + 0x100u;
        ids[i * 4 + 0] = (u8)(addr >> 8);
        ids[i * 4 + 1] = (u8)(addr >> 16);
        ids[i * 4 + 2] = song[i * 4 + 2];
        ids[i * 4 + 3] = song[i * 4 + 3];
    }

    z80_request();
    z80_upload(0x1C00 + 4, ids, sizeof(ids));

    u32 addr = (u32)song + 0x100u;
    addr += ((u32)song[0xFC] << 8) | ((u32)song[0xFD] << 16);
    addr += 4u;

    Z80_PARAMS[0] = (u8)(addr >> 0);
    Z80_PARAMS[1] = (u8)(addr >> 8);
    Z80_PARAMS[2] = (u8)(addr >> 16);
    Z80_PARAMS[3] = (u8)(addr >> 24);
    Z80_COMMAND = (u8)((Z80_COMMAND & 0x0F) | (1 << 6));
    z80_release();

    set_next_frame(0, 1);
}

/* ドライバ起動完了(Z80_DRV_STATUS bit7=READY)を確認する。
 * SGDK XGM_loadDriver はここを待ってから play コマンドを送る。これを省くと
 * ドライバ初期化中にコマンド/パラメータが無効化され、再生されない。 */
static int xgm_driver_ready(void)
{
    int r;
    z80_request();
    r = (Z80_STATUS & 0x80) ? 1 : 0;
    z80_release();
    return r;
}

static void xgm_wait_ready(void)
{
    /* READY を待つ。ハング防止に上限を設ける(visual degradation > 停止)。 */
    for (long guard = 0; guard < 200000; guard++) {
        if (xgm_driver_ready())
            return;
        for (volatile int i = 0; i < 64; i++) { }   /* ~waitMs 相当の小休止 */
    }
}

void GEN_XgmStart(void)
{
    if (g_xgm_started)
        return;
    xgm_load_driver();
    xgm_wait_ready();               /* ドライバ起動完了まで待ってから再生開始 */
    xgm_start_song(xgm_music);
    g_xgm_started = 1;
}

void GEN_XgmVBlank(void)
{
    if (g_xgm_started)
        set_next_frame(1, 0);
}
