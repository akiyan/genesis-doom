/* GENESIS DOOM - 映像ハーネス用リンカスクリプト
 * 実機相当: ROM 4MB / RAM 64KB。ハーネスは RAM をほぼ使わない(画像は ROM 常駐)ので
 * 64KB に収まることも同時に示す。 */
OUTPUT_ARCH(m68k)
ENTRY(_start)

MEMORY
{
    rom (rx)  : ORIGIN = 0x00000000, LENGTH = 0x00400000  /* 4MB */
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
        *(.bss) *(.bss.*) *(COMMON)
        . = ALIGN(2);
        __bss_end = .;
    } > ram

    . = ALIGN(4); _end = .; end = .;
    /DISCARD/ : { *(.comment) *(.note.*) *(.eh_frame*) }
}
