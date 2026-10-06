# ============================================================================
# GENESIS DOOM - GBADoom 由来エンジン核を 68k-elf 向けにコンパイルするビルド骨格
#
#   方針: -DGBA を「定義しない」ことで GBADoom 内の #ifdef GBA 経路を回避し、
#         移植可能な C 経路（FixedDiv→C 64bit除算, memcpy/memset 等）に落とす。
#
#   現状の到達点:
#     - エンジン核 59 個の .c が 68000 向けにコンパイル成功（make objects）。
#     - 完全リンク(ROM 生成)には、別途以下が必要:
#         1) プラットフォーム層 8 関数 (I_Error / I_GetBackBuffer / I_GetFrontBuffer
#            / I_ProcessKeyEvents / I_*_e32 4個) を Genesis 向けに実装
#         2) ゲームデータ doom_iwad / doom_iwad_len
#         3) crt0 + リンカスクリプト + libgcc/newlib リンク
#   詳細は PORTING.md を参照。
# ============================================================================

# .env uses unquoted KEY=value entries shared with the helper scripts.
-include ../.env
export
DOOM1_WAD ?= $(abspath ../wad/doom1.wad)
PROCESSED_WAD ?= $(abspath ../wad/doom1_processed.wad)
GBAWADUTIL ?= GbaWadUtil
MUSIC_MIDI ?= $(abspath ../music/e1m1_hangar.mid)
PALETTE_SAMPLE ?=
MARS_ROOT ?= $(abspath ../.toolchain/marsdev/mars)
TC      := $(MARS_ROOT)/m68k-elf/bin
CC      := $(TC)/m68k-elf-gcc
AS      := $(TC)/m68k-elf-as
AR      := $(TC)/m68k-elf-ar
NM      := $(TC)/m68k-elf-nm
OBJCOPY := $(TC)/m68k-elf-objcopy
SIZE    := $(TC)/m68k-elf-size
XGMTOOL := $(TC)/xgmtool
LIBMD   := $(MARS_ROOT)/m68k-elf/lib/libmd.a

SRCDIR  := engine/source
INCDIR  := engine/include
BUILD   := build

# GBA を定義しない。68000 / freestanding / 標準 C ライブラリは後段でリンク。
CFLAGS  := -m68000 -I$(INCDIR) -std=gnu11 -O2 -ffreestanding -fno-builtin -Wno-attributes

# doom_iwad.c は WAD データ(iwad/*.c)生成が前提なので核ビルドからは除外。
# プラットフォーム別 .cpp (i_system_gba/_e32) も除外（独自 Genesis 層で置換）。
CSRC    := $(filter-out $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c))
OBJ     := $(patsubst $(SRCDIR)/%.c, $(BUILD)/%.o, $(CSRC))

# port 側オブジェクト: crt0 + プラットフォーム層 + IWAD データ
PORTOBJ := $(BUILD)/crt0.o $(BUILD)/plat_genesis.o $(BUILD)/d_iwad.o

TARGET  := genesis-doom-engine
LDFLAGS := -m68000 -T link.ld -nostartfiles -Wl,--gc-sections --specs=nosys.specs

.PHONY: all objects unresolved rom harness host clean engine-rom engine-link assets wad-min regenerate-assets regenerate-wad
all: objects

# --- 68k エンジン ROM: GENESIS, 縮小WAD, 実機64KB ---
# -MMD -MP: ヘッダ依存(.d)を生成。末尾で -include して header 変更時に確実にリビルドする。
OPT ?= -O2
ECF := -m68000 -DGENESIS $(EXTRA) -I$(INCDIR) -Igen -std=gnu11 $(OPT) -ffreestanding -fno-builtin -Wno-attributes -MMD -MP
EB  := $(BUILD)/engine
ECSRC := $(filter-out $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c))
EOBJ  := $(patsubst $(SRCDIR)/%.c, $(EB)/%.o, $(ECSRC))
# engine-rom は「毎回クリーンビルド」。EXTRA(define)を変えても .c が変わらないと
# make が再ビルドしない stale ビルド地雷を根絶するため、build/engine を毎回消してから
# サブ make でオブジェクトを全てフレッシュにビルドする。
# (gen/ の WAD/アセット生成は高コストかつ define 非依存なので温存=prereq として先に作る)
engine-rom: gen/colormap16_gen.h gen/doom_iwad_min.c gen/assets_gen.c gen/xgm_driver_gen.c gen/xgm_music_gen.c
	@echo ">>> clean build: rm -rf $(EB)"
	rm -rf $(EB)
	+$(MAKE) engine-link EXTRA='$(EXTRA)' OPT='$(OPT)'

engine-link: gen/colormap16_gen.h gen/doom_iwad_min.c gen/assets_gen.c gen/xgm_driver_gen.c gen/xgm_music_gen.c $(EOBJ) $(EB)/iwad.o $(EB)/plat_video.o $(EB)/plat_genesis.o $(EB)/xgm_player.o $(EB)/assets_gen.o $(EB)/xgm_driver_gen.o $(EB)/xgm_music_gen.o $(EB)/crt0.o engine.ld
	$(CC) -m68000 -T engine.ld -nostartfiles -Wl,--gc-sections --specs=nosys.specs -o $(EB)/doom.elf \
	  $(EB)/crt0.o $(EOBJ) $(EB)/iwad.o $(EB)/plat_video.o $(EB)/plat_genesis.o $(EB)/xgm_player.o $(EB)/assets_gen.o $(EB)/xgm_driver_gen.o $(EB)/xgm_music_gen.o -lc -lgcc
	$(OBJCOPY) -O binary $(EB)/doom.elf $(EB)/doom.bin
	python3 ../boot/fixrom.py $(EB)/doom.bin 4194304
	$(SIZE) $(EB)/doom.elf
	@stamp=$$(date +%Y%m%d%H%M); cp $(EB)/doom.bin $(EB)/doom_$$stamp.md; \
	  echo ">>> ROM: $(EB)/doom_$$stamp.md"
$(EOBJ): gen/colormap16_gen.h

$(EB)/%.o: $(SRCDIR)/%.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/iwad.o: gen/doom_iwad_min.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/assets_gen.o: gen/assets_gen.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/xgm_driver_gen.o: gen/xgm_driver_gen.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/xgm_music_gen.o: gen/xgm_music_gen.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/plat_video.o: plat_video.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/plat_genesis.o: plat_genesis.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/xgm_player.o: xgm_player.c xgm_player.h gen/xgm_driver_gen.h gen/xgm_music_gen.h | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/crt0.o: crt0.s | $(EB)
	$(AS) -m68000 --register-prefix-optional -o $@ $<
$(EB):
	@mkdir -p $(EB)

# ヘッダ依存(.d)を取り込む(header 変更で確実にリビルド。今回の stale ビルド問題対策)
-include $(EOBJ:.o=.d)
-include $(EB)/plat_genesis.d $(EB)/plat_video.d $(EB)/xgm_player.d $(EB)/assets_gen.d $(EB)/xgm_driver_gen.d $(EB)/xgm_music_gen.d $(EB)/iwad.d

# --- Externally supplied WADs; all C arrays are generated and ignored. ---
$(PROCESSED_WAD):
	@test -f "$(DOOM1_WAD)" || { echo "Missing DOOM1_WAD; see README.md and .env.example"; exit 1; }
	@command -v "$(GBAWADUTIL)" >/dev/null || { echo "Provide PROCESSED_WAD or install GbaWadUtil; see README.md"; exit 1; }
	@mkdir -p "$(dir $(PROCESSED_WAD))"
	"$(GBAWADUTIL)" -in "$(DOOM1_WAD)" -out "$@"

gen/doom_iwad_min.c: $(PROCESSED_WAD) ../tools/strip_wad.py | gen
	python3 ../tools/strip_wad.py "$(PROCESSED_WAD)" $@ E1M1
gen/doom_iwad_host.c: $(PROCESSED_WAD) ../tools/strip_wad.py | gen
	python3 ../tools/strip_wad.py "$(PROCESSED_WAD)" $@ E1M1 --little-endian
wad-min: gen/doom_iwad_min.c
regenerate-assets:
	rm -f gen/assets_gen.c gen/assets_gen.h gen/colormap16_gen.h
	+$(MAKE) assets
regenerate-wad:
	rm -f gen/doom_iwad_min.c gen/doom_iwad_host.c
	+$(MAKE) wad-min gen/doom_iwad_host.c

gen:
	mkdir -p $@

# --- ホスト(native 32bit)計測ビルド: エンジンを PC で実行しゾーン量計測+描画PPM ---
HOSTCC ?= gcc
# GCC 14+ promotes inherited GBADoom pointer-type warnings to errors.
HOSTCF := -Wno-error=incompatible-pointer-types -DGEN_E1M1_ONLY -m32 -include host/host_prelude.h -I$(INCDIR) -std=gnu11 -O2 -w -fno-strict-aliasing
HOSTC  := $(filter-out $(SRCDIR)/i_main.c $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c)) d_iwad.c host/host_plat.c
host: gen/doom_iwad_host.c
	@mkdir -p $(BUILD)/host
	$(HOSTCC) $(HOSTCF) $(HOSTC) -o $(BUILD)/host/doom_host -lm
	@echo "run: $(BUILD)/host/doom_host  (E1M1 をロードして host_e1m1.ppm 出力)"

# --- 映像出力層 検証ハーネス (エンジン非依存) ---
HCF := -m68000 -Igen -std=gnu11 -O2 -ffreestanding -fno-builtin -Wall
HB  := $(BUILD)/harness
assets: gen/assets_gen.c
gen/assets_gen.c gen/assets_gen.h &: ../tools/gen_assets.py $(DOOM1_WAD) $(PALETTE_SAMPLE) ../.env.example $(wildcard ../.env) | gen
	python3 ../tools/gen_assets.py "$(DOOM1_WAD)" gen/assets_gen --sample "$(PALETTE_SAMPLE)"

gen/e1m1_hangar.vgm: $(MUSIC_MIDI) ../tools/midi_to_fm_vgm.py | gen
	python3 ../tools/midi_to_fm_vgm.py "$(MUSIC_MIDI)" $@
gen/e1m1_hangar.xgc: gen/e1m1_hangar.vgm
	$(XGMTOOL) $< $@ -s -n
gen/xgm_music_gen.c gen/xgm_music_gen.h &: gen/e1m1_hangar.xgc ../tools/bin_to_c.py
	python3 ../tools/bin_to_c.py gen/e1m1_hangar.xgc gen/xgm_music_gen xgm_music XGM_MUSIC_GEN_H

gen/xgm_driver.bin: $(LIBMD) | gen
	cd gen && rm -f z80_xgm.o drv_xgm.o && $(AR) x $(LIBMD) z80_xgm.o drv_xgm.o
	@if [ -f gen/z80_xgm.o ]; then \
	  $(OBJCOPY) -O binary -j .rodata gen/z80_xgm.o $@; \
	else \
	  $(OBJCOPY) -O binary -j .rodata gen/drv_xgm.o $@; \
	fi
gen/xgm_driver_gen.c gen/xgm_driver_gen.h &: gen/xgm_driver.bin ../tools/bin_to_c.py
	python3 ../tools/bin_to_c.py gen/xgm_driver.bin gen/xgm_driver_gen xgm_driver XGM_DRIVER_GEN_H

harness: gen/assets_gen.c | $(BUILD)
	@mkdir -p $(HB)
	$(AS) -m68000 --register-prefix-optional -o $(HB)/crt0.o crt0.s
	$(CC) $(HCF) -c plat_video.c     -o $(HB)/plat_video.o
	$(CC) $(HCF) -c gen/assets_gen.c -o $(HB)/assets_gen.o
	$(CC) $(HCF)            -c harness_video.c -o $(HB)/h_title.o
	$(CC) $(HCF) -DMODE_VIEW -c harness_video.c -o $(HB)/h_view.o
	$(CC) -m68000 -T harness.ld -nostartfiles -nostdlib -o $(HB)/title.elf $(HB)/crt0.o $(HB)/plat_video.o $(HB)/assets_gen.o $(HB)/h_title.o -lgcc
	$(CC) -m68000 -T harness.ld -nostartfiles -nostdlib -o $(HB)/view.elf  $(HB)/crt0.o $(HB)/plat_video.o $(HB)/assets_gen.o $(HB)/h_view.o  -lgcc
	$(OBJCOPY) -O binary $(HB)/title.elf $(HB)/title.bin && python3 ../boot/fixrom.py $(HB)/title.bin 524288
	$(OBJCOPY) -O binary $(HB)/view.elf  $(HB)/view.bin  && python3 ../boot/fixrom.py $(HB)/view.bin  524288
	@echo "harness ROMs: $(HB)/title.bin (全画面) / $(HB)/view.bin (ビューポート)"

objects: $(OBJ)
	@echo "compiled $(words $(OBJ)) engine objects -> $(BUILD)/"

$(BUILD)/%.o: $(SRCDIR)/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# port 側 C / asm
$(BUILD)/d_iwad.o: gen/doom_iwad_host.c
$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/crt0.o: crt0.s | $(BUILD)
	$(AS) -m68000 --register-prefix-optional -o $@ $<

# 初リンク: エンジン核 + port 層 + 標準ライブラリ
rom: $(OBJ) $(PORTOBJ) link.ld
	$(CC) $(LDFLAGS) -o $(BUILD)/$(TARGET).elf $(OBJ) $(PORTOBJ) -lc -lgcc
	$(OBJCOPY) -O binary $(BUILD)/$(TARGET).elf $(BUILD)/$(TARGET).bin
	@echo "=== セクションサイズ ==="; $(SIZE) $(BUILD)/$(TARGET).elf

$(BUILD):
	@mkdir -p $(BUILD)

# 全オブジェクト横断で「どこにも定義の無い」真の外部依存を列挙（地雷マップ再生成）
unresolved: objects
	@$(NM) $(BUILD)/*.o | awk 'NF==3 && $$2!="U"{print $$3} NF==2 && $$1!="U"{print $$2}' | sort -u > $(BUILD)/.defined
	@$(NM) $(BUILD)/*.o | awk 'NF==2 && $$1=="U"{print $$2}' | sort -u > $(BUILD)/.undef
	@comm -23 $(BUILD)/.undef $(BUILD)/.defined

clean:
	rm -rf $(BUILD)

# Compose from the actual engine WAD and selected gameplay palette.
gen/colormap16_gen.h: gen/doom_iwad_min.c gen/assets_gen.c ../tools/gen_colormap16.py
	python3 ../tools/gen_colormap16.py gen/doom_iwad_min.c gen/assets_gen.c $@
