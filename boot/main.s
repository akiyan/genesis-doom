| ============================================================================
| GENESIS DOOM - minimal boot ROM
| 画面に "GENESIS DOOM" を表示するだけの自己完結ベアメタル ROM
|   - SGDK 非依存 (VDP を直接叩く)
|   - 表示モード H32 (256x224)
|   - 8x8 内蔵フォント (必要な 8 文字のみ) を 4bpp タイルへ展開
| ============================================================================

        .equ    VDP_DATA, 0x00C00000        | VDP データポート
        .equ    VDP_CTRL, 0x00C00004        | VDP コントロールポート

| ----------------------------------------------------------------------------
| 68000 例外ベクタテーブル (256 byte = 64 longs)
| ----------------------------------------------------------------------------
        .section .vectors, "ax"
        .long   0x00FFFE00                  | 0: 初期スタックポインタ
        .long   _start                      | 1: 初期 PC (リセット)
        .rept   62                          | 2..63: 残り全例外は rte で無視
        .long   _int
        .endr

| ----------------------------------------------------------------------------
| ROM ヘッダ (0x100 から 256 byte)
| ----------------------------------------------------------------------------
        .section .header, "ax"
        .ascii  "SEGA MEGA DRIVE "          | 0x100 コンソール名
        .ascii  "(C)TAPFUN 2026  "          | 0x110 著作権
        .ascii  "GENESIS DOOM                                    " | 0x120 国内名(48)
        .ascii  "GENESIS DOOM                                    " | 0x150 海外名(48)
        .ascii  "GM 00000000-00"            | 0x180 シリアル(14)
        .word   0x0000                      | 0x18E チェックサム(後でパッチ)
        .ascii  "J               "          | 0x190 I/O サポート(16)
        .long   0x00000000                  | 0x1A0 ROM 開始
        .long   0x0003FFFF                  | 0x1A4 ROM 終了 (256KB)
        .long   0x00FF0000                  | 0x1A8 RAM 開始
        .long   0x00FFFFFF                  | 0x1AC RAM 終了
        .ascii  "            "              | 0x1B0 SRAM 情報(12)
        .ascii  "            "              | 0x1BC モデム情報(12)
        .ascii  "                                        " | 0x1C8 ノート(40)
        .ascii  "JUE             "          | 0x1F0 リージョン(16)

| ----------------------------------------------------------------------------
| コード
| ----------------------------------------------------------------------------
        .section .text, "ax"
        .global _start

_int:   rte                                 | 例外/割り込み共通: 何もしない

_start:
        move.w  #0x2700, %sr                | 全割り込み禁止

| --- TMSS 解除 (MD1 VA6 以降で必要) ---
        movea.l #0x00A10001, %a3
        move.b  (%a3), %d0                  | ハードウェアバージョン
        andi.b  #0x0F, %d0
        beq     1f                          | 旧 MD1 (TMSS なし) ならスキップ
        movea.l #0x00A14000, %a3
        move.l  #0x53454741, (%a3)          | 'SEGA' を書いて VDP ロック解除
1:

| --- ポインタ準備 ---
        movea.l #VDP_CTRL, %a1
        movea.l #VDP_DATA, %a0

| --- VDP レジスタ初期化 (reg 0..18) ---
        movea.l #reglist, %a2
        moveq   #18, %d0                    | 19 本 (dbf は count+1 回)
        move.w  #0x8000, %d1                | 0x80 | (reg<<8) | value
regloop:
        move.b  (%a2)+, %d1                 | 下位 8bit = レジスタ値
        move.w  %d1, (%a1)
        add.w   #0x0100, %d1                | 次のレジスタ番号へ
        dbf     %d0, regloop

| --- パレット (CRAM addr 0) ---
        move.l  #0xC0000000, (%a1)
        move.w  #0x0000, (%a0)              | 色0 = 黒 (背景)
        move.w  #0x0EEE, (%a0)              | 色1 = 白 (文字)

| --- VRAM 全クリア (64KB) ---
        move.l  #0x40000000, (%a1)          | VRAM addr 0 write
        move.w  #0x3FFF, %d0                | 16384 longs = 65536 byte
        moveq   #0, %d2
clrloop:
        move.l  %d2, (%a0)
        dbf     %d0, clrloop

| --- フォント展開: 1bpp 8x8 -> 4bpp タイル (tile1..tile8) ---
        move.l  #0x40200000, (%a1)          | VRAM addr 0x20 (tile #1)
        movea.l #font, %a2
        moveq   #7, %d5                     | 8 タイル
tileloop:
        moveq   #7, %d6                     | 8 行
rowloop:
        move.b  (%a2)+, %d1                 | 1 行分のビット (bit7=左端)
        moveq   #0, %d2                     | 展開先 (8 ニブル = 4 byte)
        moveq   #7, %d3                     | 8 ピクセル
        moveq   #7, %d4                     | ビット番号 7..0
pxloop:
        lsl.l   #4, %d2
        btst    %d4, %d1
        beq     pxzero
        addq.l  #1, %d2                     | 前景ピクセル = パレット色1
pxzero:
        subq.w  #1, %d4
        dbf     %d3, pxloop
        move.l  %d2, (%a0)                  | 1 行 (8px) を VRAM へ
        dbf     %d6, rowloop
        dbf     %d5, tileloop

| --- ネームテーブルへ "GENESIS DOOM" を配置 (Plane A, row14 col10) ---
        move.l  #0x47140003, (%a1)          | VRAM 0xC714 (0xC000 + (14*64+10)*2)
        movea.l #name, %a2
        moveq   #11, %d0                    | 12 文字
nameloop:
        move.w  (%a2)+, (%a0)
        dbf     %d0, nameloop

| --- 完了: 無限ループ ---
forever:
        bra     forever

| ----------------------------------------------------------------------------
| データ
| ----------------------------------------------------------------------------
        .section .rodata, "a"

| VDP レジスタ 0..18 (H32 / 256x224)
reglist:
        .byte   0x04        | reg00: H-int off, MD mode
        .byte   0x54        | reg01: 表示ON, DMA許可, MD(M5)
        .byte   0x30        | reg02: Plane A = 0xC000
        .byte   0x00        | reg03: Window  = 0x0000
        .byte   0x07        | reg04: Plane B = 0xE000
        .byte   0x6C        | reg05: Sprite  = 0xD800
        .byte   0x00        | reg06
        .byte   0x00        | reg07: 背景色 = パレット0 色0
        .byte   0x00        | reg08
        .byte   0x00        | reg09
        .byte   0x00        | reg0A: H-int カウンタ
        .byte   0x00        | reg0B
        .byte   0x00        | reg0C: H32 (RS0=RS1=0), 非インタレース
        .byte   0x3F        | reg0D: HScroll = 0xFC00
        .byte   0x00        | reg0E
        .byte   0x02        | reg0F: オートインクリメント 2
        .byte   0x01        | reg10: スクロールサイズ 64x32
        .byte   0x00        | reg11: Window H
        .byte   0x00        | reg12: Window V
        .align  2

| 8x8 1bpp フォント (bit7=左端)。順に G E N S I D O M = tile 1..8
font:
        .byte 0x7E,0xC3,0xC0,0xCF,0xC3,0xC3,0x7E,0x00   | G (tile1)
        .byte 0xFE,0xC0,0xC0,0xFC,0xC0,0xC0,0xFE,0x00   | E (tile2)
        .byte 0xC3,0xE3,0xF3,0xDB,0xCF,0xC7,0xC3,0x00   | N (tile3)
        .byte 0x7E,0xC0,0xC0,0x7C,0x03,0x03,0xFC,0x00   | S (tile4)
        .byte 0x3C,0x18,0x18,0x18,0x18,0x18,0x3C,0x00   | I (tile5)
        .byte 0xFC,0xC6,0xC3,0xC3,0xC3,0xC6,0xFC,0x00   | D (tile6)
        .byte 0x7E,0xC3,0xC3,0xC3,0xC3,0xC3,0x7E,0x00   | O (tile7)
        .byte 0xC3,0xE7,0xFF,0xDB,0xC3,0xC3,0xC3,0x00   | M (tile8)

| "GENESIS DOOM" をタイル番号で (space=0/空白タイル)
name:
        .word 1,2,3,2,4,5,4,0,6,7,7,8
