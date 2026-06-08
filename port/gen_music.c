#include "gen_music.h"
#include "music_gen.h"
#include "z80_music_gen.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define Z80_RAM    ((volatile u8*)0xA00000)
#define Z80_BUSREQ (*(volatile u16*)0xA11100)
#define Z80_RESET  (*(volatile u16*)0xA11200)

#define Z80_CMD       0x1f00
#define Z80_BANK_LO   0x1f01
#define Z80_BANK_HI   0x1f02
#define Z80_OFF_LO    0x1f03
#define Z80_OFF_HI    0x1f04
#define Z80_LOOPING   0x1f05
#define Z80_VOLUME    0x1f06

static u8 g_loaded;
static u8 g_volume = 15;

static void z80_request_bus(void)
{
    Z80_BUSREQ = 0x0100;
    Z80_RESET = 0x0100;
    for (unsigned timeout = 0; timeout < 65535; timeout++)
        if (!(Z80_BUSREQ & 0x0100))
            break;
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

static void z80_write(u16 addr, u8 value)
{
    Z80_RAM[addr] = value;
}

static void z80_reset_delay(void)
{
    for (volatile unsigned i = 0; i < 4096; i++) { }
}

static void z80_load_driver(void)
{
    z80_request_bus();

    for (u16 i = 0; i < z80_music_driver_len; i++)
        Z80_RAM[i] = z80_music_driver[i];
    for (u16 i = z80_music_driver_len; i < 0x1f10; i++)
        Z80_RAM[i] = 0;

    z80_write(Z80_VOLUME, g_volume);
    z80_reset_assert();
    z80_release_bus();
    z80_reset_delay();
    z80_reset_release();
    g_loaded = 1;
}

void GEN_MusicInit(void)
{
    z80_load_driver();
}

void GEN_MusicPlayE1M1(int looping)
{
    u32 addr;
    u16 bank;
    u16 off;

    if (!g_loaded)
        z80_load_driver();

    addr = (u32)music_e1m1_stream;
    bank = (u16)(addr >> 15);
    off = (u16)(0x8000u | (addr & 0x7fffu));

    z80_request_bus();
    z80_write(Z80_CMD, 2);
    z80_write(Z80_BANK_LO, (u8)bank);
    z80_write(Z80_BANK_HI, (u8)(bank >> 8));
    z80_write(Z80_OFF_LO, (u8)off);
    z80_write(Z80_OFF_HI, (u8)(off >> 8));
    z80_write(Z80_LOOPING, looping ? 1 : 0);
    z80_write(Z80_VOLUME, g_volume);
    z80_write(Z80_CMD, 1);
    z80_release_bus();
}

void GEN_MusicStop(void)
{
    if (!g_loaded)
        return;
    z80_request_bus();
    z80_write(Z80_CMD, 2);
    z80_release_bus();
}

void GEN_MusicSetVolume(int volume)
{
    if (volume < 0) volume = 0;
    if (volume > 15) volume = 15;
    g_volume = (u8)volume;
    if (g_loaded) {
        z80_request_bus();
        z80_write(Z80_VOLUME, g_volume);
        z80_release_bus();
    }
}

