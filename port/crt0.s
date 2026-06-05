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

| CPU 例外: 68000 group0(bus=2/adr=3)は +2 アクセスアドレス(l)/+10 PC(l)、
|   group1/2(ill/div/他)は +2 PC(l)。例外時 SP は描画スタック深部を指すので、
|   PC/addr を退避後に SP を RAM 最上位へ付け替えてから GEN_fault(kind,addr,pc) を呼ぶ。
_exc_bus:                                   | バスエラー: kind=0
        move.l  2(%sp), %d0
        move.l  10(%sp), %d1
        movea.l #0x00FFFFF0, %sp
        move.l  %d1, -(%sp)
        move.l  %d0, -(%sp)
        clr.l   -(%sp)
        jsr     GEN_fault
9:      bra     9b
_exc_adr:                                   | アドレスエラー: kind=1
        move.l  2(%sp), %d0
        move.l  10(%sp), %d1
        movea.l #0x00FFFFF0, %sp
        move.l  %d1, -(%sp)
        move.l  %d0, -(%sp)
        move.l  #1, -(%sp)
        jsr     GEN_fault
8:      bra     8b
_exc_ill:                                   | 不正命令: kind=2, addr=例外直前SP, pc=PC@+2
        move.l  2(%sp), %d1
        lea     6(%sp), %a0
        move.l  %a0, %d0
        movea.l #0x00FFFFF0, %sp
        move.l  %d1, -(%sp)
        move.l  %d0, -(%sp)
        move.l  #2, -(%sp)
        jsr     GEN_fault
7:      bra     7b
_exc_div:                                   | ゼロ除算: kind=3, PC@+2
        move.l  2(%sp), %d1
        movea.l #0x00FFFFF0, %sp
        move.l  %d1, -(%sp)
        move.l  %d1, -(%sp)
        move.l  #3, -(%sp)
        jsr     GEN_fault
6:      bra     6b
_exc_err:                                   | その他: kind=4, PC@+2
        move.l  2(%sp), %d1
        movea.l #0x00FFFFF0, %sp
        move.l  %d1, -(%sp)
        move.l  %d1, -(%sp)
        move.l  #4, -(%sp)
        jsr     GEN_fault
5:      bra     5b

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
        | スタック高水位計測ペイント: 残スタック [0xFFFA00 .. 0xFFFFF0) を 0xA5 で塗る
        | (スタックスクラッチ。描画無害。例外時 GEN_stack_check で最深点を読む)
        movea.l #0x00FFFA00, %a1
        movea.l #0x00FFFFF0, %a2
        move.l  #0xA5A5A5A5, %d0
7:      move.l  %d0, (%a1)+
        cmpa.l  %a1, %a2
        bhi     7b

        | 割り込み許可 (IPL=0)。動作確認上これが無いと起動が進まないため維持。
        move.w  #0x2000, %sr

        | main(0, 0) を呼ぶ
        clr.l   -(%sp)                  | argv = NULL
        clr.l   -(%sp)                  | argc = 0
        jsr     main
        addq.l  #8, %sp

6:      bra     6b                      | 戻ってきたら停止
