/* GENESIS DOOM - エンジン ROM 用リンカスクリプト (実機相当)
 * ROM 4MB (縮小WADで総ROM≈3.2MB), RAM 64KB。
 * _end の先(.bss直後)が malloc/_sbrk のヒープ開始。 */
OUTPUT_ARCH(m68k)
ENTRY(_start)

MEMORY
{
    rom (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00400000  /* 4MB フラット */
    ram (rwx) : ORIGIN = 0x00FF0000, LENGTH = 0x00010000  /* 64KB 実機 */
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
        . = ALIGN(4);
        __bss_end = .;
    } > ram

    _end = .; end = .;          /* malloc/_sbrk ヒープ開始 */

    /DISCARD/ : { *(.comment) *(.note.*) *(.eh_frame*) }
}
