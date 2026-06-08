#include "xgm_player.h"
#include "gen/xgm_driver_gen.h"
#include "gen/xgm_music_gen.h"

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

#define Z80_RAM8        ((volatile u8*)0x00A00000)
#define Z80_BUSREQ      (*(volatile u16*)0x00A11100)
#define Z80_RESET       (*(volatile u16*)0x00A11200)
#define Z80_BANK_REG    (*(volatile u8*)0x00A06000)
#define YM2612_PORT     ((volatile signed char*)0x00A04000)
#define PSG_PORT        (*(volatile u8*)0x00C00011)

#define XGM_CMD         0x0100
#define XGM_STATUS      0x0102
#define XGM_PARAMS      0x0104
#define XGM_SAMPLE_TBL  0x1C00
#define XGM_PCM_RATE    14000
#define XGM_VBL_HZ      60
#define XGM_LOOP_MARGIN 2

static volatile unsigned g_xgm_ready;
static unsigned g_xgm_loop_frames;
static unsigned g_xgm_frame;
static const u8 g_xgm_null_sample[256] __attribute__((aligned(256))) = { 0 };

static void z80_request_bus(void)
{
    Z80_BUSREQ = 0x0100;
    Z80_RESET = 0x0100;
    while (Z80_BUSREQ & 0x0100) { }
}

static void z80_release_bus(void)
{
    Z80_BUSREQ = 0x0000;
}

static void z80_reset_assert(void)
{
    Z80_RESET = 0x0000;
}

static void z80_reset_release(void)
{
    Z80_RESET = 0x0100;
}

static void short_delay(void)
{
    for (volatile unsigned i = 0; i < 8192; i++) { }
}

static void ym_write(unsigned port, u8 data)
{
    while (YM2612_PORT[0] < 0) { }
    YM2612_PORT[port & 3] = (signed char)data;
    __asm__ volatile ("nop\n\tnop\n\tnop\n\tnop\n\tnop" ::: "memory");
}

static void ym_write_reg(unsigned part, u8 reg, u8 data)
{
    const unsigned port = (part << 1) & 2;
    ym_write(port + 0, reg);
    ym_write(port + 1, data);
}

static void ym_write_slot(unsigned part, unsigned ch, unsigned sl, u8 reg, u8 value)
{
    ym_write_reg(part, reg | (sl * 4) | ch, value);
}

static void ym_reset(void)
{
    ym_write_reg(0, 0x22, 0x00);
    ym_write_reg(0, 0x27, 0x00);
    ym_write_reg(0, 0x2B, 0x00);

    for (unsigned part = 0; part < 2; part++) {
        for (unsigned ch = 0; ch < 3; ch++) {
            for (unsigned sl = 0; sl < 4; sl++) {
                ym_write_slot(part, ch, sl, 0x30, 0x00);
                ym_write_slot(part, ch, sl, 0x40, 0x7F);
                ym_write_slot(part, ch, sl, 0x50, 0x00);
                ym_write_slot(part, ch, sl, 0x60, 0x00);
                ym_write_slot(part, ch, sl, 0x70, 0x00);
                ym_write_slot(part, ch, sl, 0x80, 0xFF);
                ym_write_slot(part, ch, sl, 0x90, 0x00);
            }
        }
    }

    for (unsigned part = 0; part < 2; part++) {
        for (unsigned ch = 0; ch < 3; ch++) {
            ym_write_reg(part, 0xA0 | ch, 0x00);
            ym_write_reg(part, 0xA4 | ch, 0x00);
            ym_write_reg(part, 0xA8 | ch, 0x00);
            ym_write_reg(part, 0xAC | ch, 0x00);
            ym_write_reg(part, 0xB0 | ch, 0x00);
            ym_write_reg(part, 0xB4 | ch, 0xC0);
        }
    }

    ym_write(0, 0x28);
    for (unsigned ch = 0; ch < 3; ch++) {
        ym_write(1, 0x00 | ch);
        ym_write(1, 0x04 | ch);
    }
}

static void psg_reset(void)
{
    for (unsigned i = 0; i < 4; i++) {
        PSG_PORT = 0x80 | (i << 5) | 0x00;
        PSG_PORT = 0x00;
        PSG_PORT = 0x90 | (i << 5) | 0x0F;
    }
}

static void z80_set_bank(unsigned bank)
{
    for (unsigned i = 0; i < 9; i++) {
        Z80_BANK_REG = (u8)bank;
        bank >>= 1;
    }
}

static void write_sample_entry(unsigned dst, u32 addr, u8 len256, u8 flags)
{
    Z80_RAM8[dst + 0] = (u8)(addr >> 8);
    Z80_RAM8[dst + 1] = (u8)(addr >> 16);
    Z80_RAM8[dst + 2] = len256;
    Z80_RAM8[dst + 3] = flags;
}

static void xgm_play_e1m1_sample(void)
{
    Z80_RAM8[XGM_PARAMS + 0x04] = 0x0F;
    Z80_RAM8[XGM_PARAMS + 0x05] = 1;
    Z80_RAM8[XGM_CMD] = 0x01;
}

static void z80_wait_modifiable_bus_held(void)
{
    while (Z80_RAM8[XGM_PARAMS + 0x0E]) {
        z80_release_bus();
        __asm__ volatile ("movem.l %%d0-%%d3,-(%%sp)\n\tmovem.l (%%sp)+,%%d0-%%d3" ::: "memory");
        z80_request_bus();
    }
}

void GEN_XgmInit(void)
{
    z80_reset_assert();
    z80_request_bus();
    z80_set_bank(0);
    ym_reset();
    psg_reset();

    for (unsigned i = 0; i < 0x2000; i++) {
        Z80_RAM8[i] = 0;
    }
    for (unsigned i = 0; i < xgm_driver_len; i++) {
        Z80_RAM8[i] = xgm_driver[i];
    }

    write_sample_entry(XGM_SAMPLE_TBL, (u32)g_xgm_null_sample, 1, 0);

    z80_reset_assert();
    z80_release_bus();
    short_delay();
    z80_reset_release();
    short_delay();

    u8 ready = 0;
    for (unsigned tries = 0; tries < 65535; tries++) {
        z80_request_bus();
        const u8 status = Z80_RAM8[XGM_STATUS];
        z80_release_bus();
        if (status & 0x80) {
            ready = 1;
            break;
        }
    }
    if (!ready) {
        return;
    }

    z80_request_bus();

    /* Play the D_E1M1 render as one XGM PCM sample on channel 0. */
    const u32 pcm_addr = (u32)xgm_e1m1_50s + 0x100;
    write_sample_entry(XGM_SAMPLE_TBL + 4, pcm_addr, xgm_e1m1_50s[0x02], xgm_e1m1_50s[0x03]);
    const u32 pcm_len = ((u32)xgm_e1m1_50s[0x02] | ((u32)xgm_e1m1_50s[0x03] << 8)) << 8;
    g_xgm_loop_frames = (unsigned)((pcm_len * XGM_VBL_HZ) / XGM_PCM_RATE);
    if (g_xgm_loop_frames > XGM_LOOP_MARGIN) {
        g_xgm_loop_frames -= XGM_LOOP_MARGIN;
    }
    g_xgm_frame = 0;

    xgm_play_e1m1_sample();
    Z80_RAM8[XGM_PARAMS + 0x0F] = 1;
    g_xgm_ready = 1;
    z80_release_bus();
}

void GEN_XgmVBlank(void)
{
    if (!g_xgm_ready) {
        return;
    }

    z80_request_bus();
    Z80_RAM8[XGM_PARAMS + 0x0F]++;
    if (++g_xgm_frame >= g_xgm_loop_frames) {
        xgm_play_e1m1_sample();
        g_xgm_frame = 0;
    }
    z80_release_bus();
}
