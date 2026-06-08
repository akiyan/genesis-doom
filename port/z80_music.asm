; Genesis Doom Z80 YM2612 music prototype.
; Command block is at Z80 RAM $1F00 and is written by 68k while Z80 is halted.
; YM2612 channel 5 is reserved for first-pass MUS channel 15 drums.

CMD: equ $1f00
BANK_LO: equ $1f01
BANK_HI: equ $1f02
OFF_LO: equ $1f03
OFF_HI: equ $1f04
LOOPING: equ $1f05
VOLUME: equ $1f06
TEMP_CH: equ $1f07
TEMP_HI: equ $1f08
TEMP_LO: equ $1f09
DRUM_TICKS: equ $1f0a

YM0_A: equ $4000
YM0_D: equ $4001
YM1_A: equ $4002
YM1_D: equ $4003
BANKREG: equ $6000

          org $0000
start:
          di
          ld sp,$1eff
wait_cmd:
          ld a,(CMD)
          cp 1
          jr z,play_start
          cp 2
          jr nz,wait_cmd
          xor a
          ld (CMD),a
          call all_off
          jr wait_cmd

play_start:
          xor a
          ld (CMD),a
          call ym_init
          ld a,(BANK_LO)
          ld l,a
          ld a,(BANK_HI)
          ld h,a
          call set_bank
          ld a,(OFF_LO)
          ld e,a
          ld a,(OFF_HI)
          ld d,a

next_event:
          call read_byte
          ld c,a
          call read_byte
          ld b,a
          call wait_bc
          call read_byte
          or a
          jr z,score_end
          cp 1
          jr z,ev_note
          cp 2
          jr z,ev_off
          cp 3
          jr z,ev_drum
          jr wait_cmd

ev_note:
          call read_byte
          ld c,a              ; channel
          call read_byte
          ld b,a              ; note
          call read_byte       ; volume ignored in first Z80 prototype
          ld a,c
          call key_off_a
          ld a,b
          call set_note_c_b
          ld a,(TEMP_CH)
          call key_on_a
          jr next_event

ev_off:
          call read_byte
          ld c,a
          call read_byte
          call read_byte
          ld a,c
          call key_off_a
          jr next_event

ev_drum:
          call read_byte       ; unused channel field
          call read_byte
          ld b,a              ; percussion note
          call read_byte       ; volume ignored, drum is deliberately loud
          call fm_drum_b
          jr next_event

score_end:
          ld a,(LOOPING)
          or a
          jp z,wait_cmd
          call all_off
          ld a,(BANK_LO)
          ld l,a
          ld a,(BANK_HI)
          ld h,a
          call set_bank
          ld a,(OFF_LO)
          ld e,a
          ld a,(OFF_HI)
          ld d,a
          jr next_event

read_byte:
          ld a,(de)
          ld (TEMP_LO),a
          inc de
          ld a,d
          or e
          jr nz,read_done
          ld de,$8000
          ld a,(BANK_LO)
          add a,1
          ld (BANK_LO),a
          ld l,a
          ld a,(BANK_HI)
          adc a,0
          ld (BANK_HI),a
          ld h,a
          call set_bank
read_done:
          ld a,(TEMP_LO)
          ret

set_bank:
          ld b,9
bank_loop:
          ld a,l
          and 1
          ld (BANKREG),a
          srl h
          rr l
          djnz bank_loop
          ret

wait_bc:
          ld a,b
          or c
          ret z
wait_tick_loop:
          push bc
          call wait_one_tick
          call fm_drum_tick
          pop bc
          dec bc
          ld a,b
          or c
          jr nz,wait_tick_loop
          ret

wait_one_tick:
          ld b,64
wt_outer:
          ld c,32
wt_inner:
          dec c
          jr nz,wt_inner
          djnz wt_outer
          ret

ym_ready:
          push bc
          ld b,0
yr_loop:
          ld a,(YM0_A)
          and $80
          jr z,yr_done
          djnz yr_loop
yr_done:
          pop bc
          ret

ym0:
          push af
          call ym_ready
          pop af
          ld (YM0_A),a
          call ym_ready
          ld a,c
          ld (YM0_D),a
          ret

ym1:
          push af
          call ym_ready
          pop af
          ld (YM1_A),a
          call ym_ready
          ld a,c
          ld (YM1_D),a
          ret

ym_ch_write:
          ; A=base register, B=channel 0..5, C=value
          ld e,a
          ld a,b
          cp 3
          jr c,ych_port0
          sub 3
          add a,e
          jp ym1
ych_port0:
          add a,e
          jp ym0

key_off_a:
          ; A=channel
          cp 3
          jr c,koff_code
          inc a
koff_code:
          ld c,0
          jp ym0_key

key_on_a:
          cp 3
          jr c,kon_code
          inc a
kon_code:
          or $f0
          ld c,a
          ld a,$28
          jp ym0

ym0_key:
          ld c,a
          ld a,$28
          jp ym0

set_note_c_b:
          ; C=channel, B=MIDI note. Uses a coarse 12-note FNUM table.
          ld a,c
          ld (TEMP_CH),a
          ld a,b
          cp 12
          jr nc,note_min_ok
          ld a,12
note_min_ok:
          cp 96
          jr c,note_max_ok
          ld a,95
note_max_ok:
          ld b,a
          ld c,0
oct_loop:
          ld a,b
          cp 12
          jr c,oct_done
          sub 12
          ld b,a
          inc c
          jr oct_loop
oct_done:
          ld a,c
          or a
          jr z,oct_zero
          dec a
oct_zero:
          sla a
          sla a
          sla a
          ld c,a               ; block bits
          ld a,b
          add a,a
          ld l,a
          ld h,0
          ld de,fnum_table
          add hl,de
          ld e,(hl)
          inc hl
          ld d,(hl)
          ld a,d
          and 7
          or c
          ld (TEMP_HI),a
          ld a,e
          ld (TEMP_LO),a
          ld a,(TEMP_CH)
          ld b,a
          ld a,(TEMP_HI)
          ld c,a
          ld a,$a4
          call ym_ch_write
          ld a,(TEMP_CH)
          ld b,a
          ld a,(TEMP_LO)
          ld c,a
          ld a,$a0
          call ym_ch_write
          ret


fm_drum_b:
          ld a,5
          call key_off_a
          ld a,b
          cp 38
          jr c,drum_kick
          cp 50
          jr c,drum_snare
drum_hat:
          call drum_patch_hat
          ld c,5
          ld b,72
          jr drum_go
drum_snare:
          call drum_patch_snare
          ld c,5
          ld b,48
          jr drum_go
drum_kick:
          call drum_patch_kick
          ld c,5
          ld b,32
drum_go:
          call set_note_c_b
          ld a,5
          call key_on_a
          ld a,4
          ld (DRUM_TICKS),a
          ret

fm_drum_tick:
          ld a,(DRUM_TICKS)
          or a
          ret z
          dec a
          ld (DRUM_TICKS),a
          ret nz
          ld a,5
          jp key_off_a

drum_patch_kick:
          ld b,5
          ld a,$40
          ld c,$00
          call ym_ch_write
          ld a,$44
          ld c,$18
          call ym_ch_write
          ld a,$48
          ld c,$1f
          call ym_ch_write
          ld a,$4c
          ld c,$04
          call ym_ch_write
          ld a,$50
          ld c,$1f
          call ym_ch_write
          ld a,$54
          ld c,$1f
          call ym_ch_write
          ld a,$58
          ld c,$1f
          call ym_ch_write
          ld a,$5c
          ld c,$1f
          call ym_ch_write
          ld a,$60
          ld c,$02
          call ym_ch_write
          ld a,$64
          ld c,$08
          call ym_ch_write
          ld a,$68
          ld c,$08
          call ym_ch_write
          ld a,$6c
          ld c,$02
          call ym_ch_write
          ld a,$80
          ld c,$0f
          call ym_ch_write
          ld a,$84
          ld c,$0f
          call ym_ch_write
          ld a,$88
          ld c,$0f
          call ym_ch_write
          ld a,$8c
          ld c,$0f
          call ym_ch_write
          ld a,$b0
          ld c,$07
          call ym_ch_write
          ret

drum_patch_snare:
          ld b,5
          ld a,$40
          ld c,$08
          call ym_ch_write
          ld a,$44
          ld c,$00
          call ym_ch_write
          ld a,$48
          ld c,$10
          call ym_ch_write
          ld a,$4c
          ld c,$00
          call ym_ch_write
          ld a,$50
          ld c,$1f
          call ym_ch_write
          ld a,$54
          ld c,$0f
          call ym_ch_write
          ld a,$58
          ld c,$1f
          call ym_ch_write
          ld a,$5c
          ld c,$0f
          call ym_ch_write
          ld a,$60
          ld c,$06
          call ym_ch_write
          ld a,$64
          ld c,$04
          call ym_ch_write
          ld a,$68
          ld c,$06
          call ym_ch_write
          ld a,$6c
          ld c,$04
          call ym_ch_write
          ld a,$80
          ld c,$0f
          call ym_ch_write
          ld a,$84
          ld c,$0f
          call ym_ch_write
          ld a,$88
          ld c,$0f
          call ym_ch_write
          ld a,$8c
          ld c,$0f
          call ym_ch_write
          ld a,$b0
          ld c,$07
          call ym_ch_write
          ret

drum_patch_hat:
          ld b,5
          ld a,$40
          ld c,$08
          call ym_ch_write
          ld a,$44
          ld c,$08
          call ym_ch_write
          ld a,$48
          ld c,$08
          call ym_ch_write
          ld a,$4c
          ld c,$00
          call ym_ch_write
          ld a,$50
          ld c,$1f
          call ym_ch_write
          ld a,$54
          ld c,$1f
          call ym_ch_write
          ld a,$58
          ld c,$1f
          call ym_ch_write
          ld a,$5c
          ld c,$0f
          call ym_ch_write
          ld a,$60
          ld c,$0a
          call ym_ch_write
          ld a,$64
          ld c,$0a
          call ym_ch_write
          ld a,$68
          ld c,$0a
          call ym_ch_write
          ld a,$6c
          ld c,$02
          call ym_ch_write
          ld a,$80
          ld c,$0f
          call ym_ch_write
          ld a,$84
          ld c,$0f
          call ym_ch_write
          ld a,$88
          ld c,$0f
          call ym_ch_write
          ld a,$8c
          ld c,$0f
          call ym_ch_write
          ld a,$b0
          ld c,$07
          call ym_ch_write
          ret

ym_init:
          xor a
          ld (DRUM_TICKS),a
          ld a,$22
          ld c,0
          call ym0
          ld a,$27
          ld c,0
          call ym0
          ld a,$2b
          ld c,0
          call ym0
          ld b,0
init_ch_loop:
          ld a,$30
          ld c,$01
          call ym_ch_write
          ld a,$34
          ld c,$01
          call ym_ch_write
          ld a,$38
          ld c,$01
          call ym_ch_write
          ld a,$3c
          ld c,$01
          call ym_ch_write
          ld a,$40
          ld c,$00
          call ym_ch_write
          ld a,$44
          ld c,$00
          call ym_ch_write
          ld a,$48
          ld c,$00
          call ym_ch_write
          ld a,$4c
          ld c,$00
          call ym_ch_write
          ld a,$50
          ld c,$1f
          call ym_ch_write
          ld a,$54
          ld c,$1f
          call ym_ch_write
          ld a,$58
          ld c,$1f
          call ym_ch_write
          ld a,$5c
          ld c,$1f
          call ym_ch_write
          ld a,$60
          ld c,$05
          call ym_ch_write
          ld a,$64
          ld c,$05
          call ym_ch_write
          ld a,$68
          ld c,$05
          call ym_ch_write
          ld a,$6c
          ld c,$05
          call ym_ch_write
          ld a,$80
          ld c,$0f
          call ym_ch_write
          ld a,$84
          ld c,$0f
          call ym_ch_write
          ld a,$88
          ld c,$0f
          call ym_ch_write
          ld a,$8c
          ld c,$0f
          call ym_ch_write
          ld a,$b0
          ld c,$07
          call ym_ch_write
          ld a,$b4
          ld c,$c0
          call ym_ch_write
          inc b
          ld a,b
          cp 6
          jp nz,init_ch_loop
          call all_off
          ret

all_off:
          xor a
          ld (DRUM_TICKS),a
          ld b,0
ao_loop:
          ld a,b
          call key_off_a
          inc b
          ld a,b
          cp 6
          jr nz,ao_loop
          ret

fnum_table:
          defw $0284,$02ab,$02d3,$02fe,$032d,$035c
          defw $038f,$03c5,$03ff,$043c,$047c,$04c0
