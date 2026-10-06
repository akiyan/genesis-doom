#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROM を指定サイズへパディングし、Mega Drive ヘッダのチェックサムをパッチする。
チェックサム = 0x200 以降の全 16bit ビッグエンディアン語の総和 (mod 0x10000)。"""
import sys

path, size = sys.argv[1], int(sys.argv[2])
data = bytearray(open(path, "rb").read())

if len(data) > size:
    sys.exit(f"ROM ({len(data)}B) が指定サイズ {size}B を超えています")
data += bytes(size - len(data))  # 0 パディング

checksum = 0
for i in range(0x200, len(data), 2):
    checksum = (checksum + (data[i] << 8) + data[i + 1]) & 0xFFFF
data[0x18E] = (checksum >> 8) & 0xFF
data[0x18F] = checksum & 0xFF

open(path, "wb").write(data)
print(f"OK: {path} {len(data)} bytes, checksum=0x{checksum:04X}")
