# GENESIS DOOM - minimal boot ROM ビルド
MARS_ROOT ?= $(abspath ../.toolchain/marsdev/mars)
TC      := $(MARS_ROOT)/m68k-elf/bin
CC      := $(TC)/m68k-elf-gcc
AS      := $(TC)/m68k-elf-as
LD      := $(TC)/m68k-elf-ld
OBJCOPY := $(TC)/m68k-elf-objcopy

CPU     := -m68000
ASFLAGS := $(CPU) --register-prefix-optional
LDFLAGS := -T md.ld -nostdlib

TARGET  := genesis-doom
ROMSIZE := 262144           # 256KB

all: $(TARGET).bin

$(TARGET).o: main.s
	$(AS) $(ASFLAGS) -o $@ $<

$(TARGET).elf: $(TARGET).o md.ld
	$(LD) $(LDFLAGS) -o $@ $(TARGET).o

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@
	# 256KB へパディングし、ヘッダのチェックサムをパッチ
	python3 fixrom.py $@ $(ROMSIZE)

clean:
	rm -f $(TARGET).o $(TARGET).elf $(TARGET).bin

.PHONY: all clean
