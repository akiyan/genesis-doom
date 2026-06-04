| ============================================================================
| GENESIS DOOM - port crt0
|   68000 ベクタ + ROM ヘッダ + C ランタイム起動 (.data コピー/.bss クリア → main)
|   boot/ のベアメタル資産を流用。VDP 初期化はプラットフォーム層(C)側で行う。
| ============================================================================

| --- 例外ベクタ (256B) ---
        .section .vectors, "ax"
        .long   0x00FFFFFE          | 0 初期 SP(RAM最上位=スタック最大化)
        .long   _start              | 1 リセット PC
        .long   _exc_bus            | 2 バスエラー       → 青
        .long   _exc_adr            | 3 アドレスエラー   → 赤(未整列アクセス)
        .long   _exc_ill            | 4 不正命令         → マゼンタ
        .long   _exc_div            | 5 ゼロ除算         → 緑
        .long   _exc_err            | 6 CHK              → 黄
        .long   _exc_err            | 7 TRAPV            → 黄
        .long   _exc_err            | 8 特権違反         → 黄
        .rept   21                  | 9..29: rte
        .long   _except
        .endr
        .long   _vblank             | 30 (L6 VBlank割り込み = 時刻源)
        .rept   33                  | 31..63: rte
        .long   _except
        .endr

| --- ROM ヘッダ (0x100, 256B) ---
        .section .header, "ax"
        .ascii  "SEGA MEGA DRIVE "
        .ascii  "(C)TAPFUN 2026  "
        .ascii  "GENESIS DOOM (GBADoom port)                     "
        .ascii  "GENESIS DOOM (GBADoom port)                     "
        .ascii  "GM 00000000-00"
        .word   0x0000
        .ascii  "JD              "
        .long   0x00000000
        .long   0x003FFFFF          | ROM 終了 (4MB-1; doom_iwad を内包)
        .long   0x00FF0000
        .long   0x00FFFFFF
        .ascii  "            "
        .ascii  "            "
        .ascii  "                                        "
        .ascii  "JUE             "

| --- 起動コード ---
        .section .text, "ax"
        .global _start

_except:
        rte

| VBlank 割り込み(L6): VDP status を読んで VInt を ack(これが無いと無限再入)、g_vblank 加算。
| tst.w はメモリ読みのみでレジスタを汚さない(CCR は rte が復元)。
_vblank:
        tst.w   0x00C00004          | VDP status 読み → VInt ack
        addq.l  #1, g_vblank
        rte

| CPU 例外: backdrop を例外種別ごとの原色にして停止 → どの例外かを一発判別。
| 全て CRAM63 backdrop(trace() と同じ) に書く。
_exc_bus:                                   | バスエラー = 青
        move.l  #0xC07E0000, 0x00C00004
        move.w  #0x0E00, 0x00C00000
        bra     _exc_set
_exc_adr:                                   | アドレスエラー(未整列) = 赤
        move.l  #0xC07E0000, 0x00C00004
        move.w  #0x000E, 0x00C00000
        bra     _exc_set
_exc_ill:                                   | 不正命令 = マゼンタ
        move.l  #0xC07E0000, 0x00C00004
        move.w  #0x0E0E, 0x00C00000
        bra     _exc_set
_exc_div:                                   | ゼロ除算 = 緑
        move.l  #0xC07E0000, 0x00C00004
        move.w  #0x00E0, 0x00C00000
        bra     _exc_set
_exc_err:                                   | その他(CHK/TRAPV/特権) = 黄
        move.l  #0xC07E0000, 0x00C00004
        move.w  #0x00EE, 0x00C00000
_exc_set:
        move.w  #0x873F, 0x00C00004        | reg7 = palette3 色15 = CRAM63
9:      bra     9b

_start:
        move.w  #0x2700, %sr            | 割り込み禁止
        movea.l #0x00FFFFFE, %sp

        | TMSS 解除
        movea.l #0x00A10001, %a0
        move.b  (%a0), %d0
        andi.b  #0x0F, %d0
        beq     1f
        move.l  #0x53454741, 0x00A14000
1:
        | .data を ROM(LMA) から RAM(VMA) へコピー
        movea.l #__data_load, %a0
        movea.l #__data_start, %a1
        movea.l #__data_end, %a2
2:      cmpa.l  %a1, %a2
        bls     3f
        move.b  (%a0)+, (%a1)+
        bra     2b
3:
        | .bss をゼロクリア
        movea.l #__bss_start, %a1
        movea.l #__bss_end, %a2
4:      cmpa.l  %a1, %a2
        bls     5f
        clr.b   (%a1)+
        bra     4b
5:
        | 割り込み許可 (IPL=0)。動作確認上これが無いと起動が進まないため維持。
        move.w  #0x2000, %sr

        | main(0, 0) を呼ぶ
        clr.l   -(%sp)                  | argv = NULL
        clr.l   -(%sp)                  | argc = 0
        jsr     main
        addq.l  #8, %sp

6:      bra     6b                      | 戻ってきたら停止
