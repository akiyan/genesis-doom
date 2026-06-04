/* GENESIS DOOM - port リンカスクリプト
 * ROM: コード + .rodata(doom_iwad 内包) を 0x000000 から配置
 * RAM: .data(ROM からコピー) + .bss を 0xFF0000 から配置
 *
 * 注: ram LENGTH は実機 Genesis の 64KB。.bss がこれを超えるとリンクエラーになり、
 *     それ自体が「64KB に収まらない量」を定量化する。初リンク確認時は必要に応じ
 *     LENGTH を一時的に拡張して .bin を生成し、実サイズを別途計測・報告する。
 */
OUTPUT_ARCH(m68k)
ENTRY(_start)

/* 注: 以下は「初リンク検証用」に拡張した値。
 *   実機は rom=4MB フラット(マッパーで拡張), ram=64KB。
 *   doom_iwad(3.84MB)+エンジンは 4MB に収まらず、RAM 作業域も 64KB を超える。
 *   この乖離の定量化が目的であり、real 値での収容はメモリ最適化フェーズで対応する。 */
MEMORY
{
    rom (rx)  : ORIGIN = 0x00000000, LENGTH = 0x01000000  /* 16MB (検証用に拡張) */
    ram (rwx) : ORIGIN = 0x00E00000, LENGTH = 0x00200000  /* 2MB  (検証用に拡張) */
}

SECTIONS
{
    .text 0x00000000 :
    {
        KEEP(*(.vectors))
        . = 0x100;
        KEEP(*(.header))
        . = 0x200;
        *(.text) *(.text.*)
        *(.rodata) *(.rodata.*)
        *(.gcc_except_table*)
        . = ALIGN(4);
    } > rom

    __data_load = LOADADDR(.data);
    .data 0x00FF0000 : AT(ADDR(.text) + SIZEOF(.text))
    {
        __data_start = .;
        *(.data) *(.data.*)
        . = ALIGN(2);
        __data_end = .;
    } > ram

    .bss (NOLOAD) :
    {
        __bss_start = .;
        *(.bss) *(.bss.*)
        *(COMMON)
        . = ALIGN(2);
        __bss_end = .;
    } > ram

    /* newlib _sbrk 用ヒープ開始シンボル */
    . = ALIGN(4);
    _end = .;
    end = .;
    __end__ = .;

    /DISCARD/ : { *(.comment) *(.note.*) *(.eh_frame*) }
}
