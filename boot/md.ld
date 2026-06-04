/* Sega Genesis / Mega Drive リンカスクリプト (ベアメタル) */
OUTPUT_ARCH(m68k)
ENTRY(_start)

MEMORY
{
    rom (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00400000  /* 4MB 上限 */
    ram (rwx) : ORIGIN = 0x00FF0000, LENGTH = 0x00010000  /* 64KB */
}

SECTIONS
{
    .text 0x00000000 :
    {
        KEEP(*(.vectors))       /* 0x000: ベクタテーブル (256B) */
        . = 0x100;
        KEEP(*(.header))        /* 0x100: ROM ヘッダ (256B)     */
        . = 0x200;
        *(.text)                /* 0x200: コード               */
        *(.text.*)
        *(.rodata)
        *(.rodata.*)
        . = ALIGN(2);
    } > rom

    .bss (NOLOAD) :
    {
        *(.bss)
        *(.bss.*)
        *(COMMON)
    } > ram

    /DISCARD/ : { *(.comment) *(.note.*) }
}
