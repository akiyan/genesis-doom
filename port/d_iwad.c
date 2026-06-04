/* GENESIS DOOM - IWAD データ供給
 *
 * GbaWadUtil が doom1.wad(シェアウェア v1.9) を変換済みの C 配列
 * (third_party/GBADoom/source/iwad/doom1.c) を取り込み、doom_iwad[] と
 * doom_iwad_len を供給する。third_party は無改変のまま include で参照する。
 * (doom1.c のパスは Makefile の -I で解決)
 */
#include "doom_iwad.h"

#include "doom1.c"   /* const unsigned char doom_iwad[3842044] = {...}; */

const unsigned int doom_iwad_len = sizeof(doom_iwad);
