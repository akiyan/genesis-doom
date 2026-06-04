# ============================================================================
# GENESIS DOOM - GBADoom エンジン核を 68k-elf 向けにコンパイルするビルド骨格
#
#   方針: -DGBA を「定義しない」ことで GBADoom 内の #ifdef GBA 経路を回避し、
#         移植可能な C 経路（FixedDiv→C 64bit除算, memcpy/memset 等）に落とす。
#
#   現状の到達点:
#     - エンジン核 59 個の .c が 68000 向けに無改変でコンパイル成功（make objects）。
#     - 完全リンク(ROM 生成)には、別途以下が必要:
#         1) プラットフォーム層 8 関数 (I_Error / I_GetBackBuffer / I_GetFrontBuffer
#            / I_ProcessKeyEvents / I_*_e32 4個) を Genesis 向けに実装
#         2) ゲームデータ doom_iwad / doom_iwad_len (WAD→C 配列, GbaWadUtil)
#         3) crt0 + リンカスクリプト + libgcc/newlib リンク
#   詳細は PORTING.md を参照。
# ============================================================================

TC      := $(HOME)/toolchains/mars/m68k-elf/bin
CC      := $(TC)/m68k-elf-gcc
AS      := $(TC)/m68k-elf-as
NM      := $(TC)/m68k-elf-nm
OBJCOPY := $(TC)/m68k-elf-objcopy
SIZE    := $(TC)/m68k-elf-size

GBADOOM := ../third_party/GBADoom
SRCDIR  := $(GBADOOM)/source
INCDIR  := $(GBADOOM)/include
IWADDIR := $(GBADOOM)/source/iwad
BUILD   := build

# GBA を定義しない。68000 / freestanding / 標準 C ライブラリは後段でリンク。
CFLAGS  := -m68000 -I$(INCDIR) -I$(IWADDIR) -std=gnu11 -O2 -ffreestanding -fno-builtin -Wno-attributes

# doom_iwad.c は WAD データ(iwad/*.c)生成が前提なので核ビルドからは除外。
# プラットフォーム別 .cpp (i_system_gba/_e32) も除外（独自 Genesis 層で置換）。
CSRC    := $(filter-out $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c))
OBJ     := $(patsubst $(SRCDIR)/%.c, $(BUILD)/%.o, $(CSRC))

# port 側オブジェクト: crt0 + プラットフォーム層 + IWAD データ
PORTOBJ := $(BUILD)/crt0.o $(BUILD)/plat_genesis.o $(BUILD)/d_iwad.o

TARGET  := genesis-doom-engine
LDFLAGS := -m68000 -T link.ld -nostartfiles -Wl,--gc-sections --specs=nosys.specs

.PHONY: all objects unresolved rom harness host clean
all: objects

# --- 68k エンジン ROM (タイトル起動): GENESIS+GEN_TITLE_ONLY, 縮小WAD, 実機64KB ---
# -MMD -MP: ヘッダ依存(.d)を生成。末尾で -include して header 変更時に確実にリビルドする。
ECF := -m68000 -DGENESIS -DGEN_TITLE_ONLY -I$(INCDIR) -I$(IWADDIR) -Igen -std=gnu11 -O2 -ffreestanding -fno-builtin -Wno-attributes -MMD -MP
EB  := $(BUILD)/engine
ECSRC := $(filter-out $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c))
EOBJ  := $(patsubst $(SRCDIR)/%.c, $(EB)/%.o, $(ECSRC))
engine-rom: gen/doom_iwad_min.c gen/assets_gen.c $(EOBJ) $(EB)/iwad.o $(EB)/plat_video.o $(EB)/plat_genesis.o $(EB)/assets_gen.o $(EB)/crt0.o engine.ld
	$(CC) -m68000 -T engine.ld -nostartfiles -Wl,--gc-sections --specs=nosys.specs -o $(EB)/doom.elf \
	  $(EB)/crt0.o $(EOBJ) $(EB)/iwad.o $(EB)/plat_video.o $(EB)/plat_genesis.o $(EB)/assets_gen.o -lc -lgcc 2>/dev/null
	$(OBJCOPY) -O binary $(EB)/doom.elf $(EB)/doom.bin
	python3 ../boot/fixrom.py $(EB)/doom.bin 4194304
	$(SIZE) $(EB)/doom.elf
$(EB)/%.o: $(SRCDIR)/%.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/iwad.o: gen/doom_iwad_min.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/assets_gen.o: gen/assets_gen.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/plat_video.o: plat_video.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/plat_genesis.o: plat_genesis.c | $(EB)
	$(CC) $(ECF) -c $< -o $@
$(EB)/crt0.o: crt0.s | $(EB)
	$(AS) -m68000 --register-prefix-optional -o $@ $<
$(EB):
	@mkdir -p $(EB)

# ヘッダ依存(.d)を取り込む(header 変更で確実にリビルド。今回の stale ビルド問題対策)
-include $(EOBJ:.o=.d)
-include $(EB)/plat_genesis.d $(EB)/plat_video.d $(EB)/assets_gen.d $(EB)/iwad.d

# --- WAD 削減: doom1.c(処理済) → E1M1 のみ保持の縮小 WAD (ROM<4MB 化) ---
gen/doom_iwad_min.c:
	gcc -m32 -O1 -I$(INCDIR) -I$(IWADDIR) ../tools/dump_iwad.c d_iwad.c -o $(BUILD)/dump_iwad
	$(BUILD)/dump_iwad /tmp/doom1_proc.wad
	python3 ../tools/strip_wad.py /tmp/doom1_proc.wad gen/doom_iwad_min.c E1M1
wad-min: gen/doom_iwad_min.c

# --- ホスト(native 32bit)計測ビルド: エンジンを PC で実行しゾーン量計測+描画PPM ---
HOSTCF := -m32 -include host/host_prelude.h -I$(INCDIR) -I$(IWADDIR) -std=gnu11 -O2 -w -fno-strict-aliasing
HOSTC  := $(filter-out $(SRCDIR)/i_main.c $(SRCDIR)/doom_iwad.c, $(wildcard $(SRCDIR)/*.c)) d_iwad.c host/host_plat.c
host:
	@mkdir -p $(BUILD)/host
	gcc $(HOSTCF) $(HOSTC) -o $(BUILD)/host/doom_host -lm
	@echo "run: $(BUILD)/host/doom_host  (E1M1 をロードして host_e1m1.ppm 出力)"

# --- 映像出力層 検証ハーネス (エンジン非依存) ---
HCF := -m68000 -Igen -std=gnu11 -O2 -ffreestanding -fno-builtin -Wall
HB  := $(BUILD)/harness
assets: gen/assets_gen.c
gen/assets_gen.c:
	python3 ../tools/gen_assets.py ../wad/doom1.wad gen/assets_gen

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
