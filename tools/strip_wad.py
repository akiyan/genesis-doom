#!/usr/bin/env python3
"""処理済み WAD (doom1.c 由来) から不要マップを除去して ROM を 4MB 未満に収める。
GFX(テクスチャ/スプライト/フラット/UI) と E1M1 は保持、E1M2..E1M9 のマップを除去。
出力は doom_iwad[] と doom_iwad_len を定義する C ファイル。
使い方: strip_wad.py in.wad out.c [keepmaps=E1M1]
"""
import struct, sys, re

inp = sys.argv[1]
outc = sys.argv[2]
keep = set((sys.argv[3] if len(sys.argv) > 3 else "E1M1").split(","))

d = open(inp, "rb").read()
magic, num, off = struct.unpack("<4sii", d[:12])
assert magic == b"IWAD", magic

dirs = []
for i in range(num):
    e = d[off + i*16: off + i*16 + 16]
    fp, sz = struct.unpack("<ii", e[:8])
    nm = e[8:16].split(b'\0')[0].decode('latin1')
    dirs.append([nm, fp, sz])

MAPSUB = {"THINGS","LINEDEFS","SIDEDEFS","VERTEXES","SEGS","SSECTORS",
          "NODES","SECTORS","REJECT","BLOCKMAP"}
ismap = lambda n: re.match(r"E\dM\d$", n) is not None

# 除去対象: 不要マップの「サブlump データ」のみ。
# マーカー(E1Mx, 0バイト)は gamemode 検出(マーカー数を数える)のため全保持する。
drop = [False]*num
i = 0
while i < num:
    nm = dirs[i][0]
    if ismap(nm) and nm not in keep:
        # marker は残し、後続 sublump だけ落とす
        j = i+1
        while j < num and dirs[j][0] in MAPSUB:
            drop[j] = True; j += 1
        i = j
    else:
        i += 1

kept = [dirs[i] for i in range(num) if not drop[i]]

# 新 WAD を再構築: header + lump data(連結) + directory
HDR = 12
newdir_ofs_placeholder = 0
data = bytearray()
newdirs = []
data_base = HDR  # lump data はヘッダ直後から
for nm, fp, sz in kept:
    raw = d[fp:fp+sz] if sz > 0 else b""
    # 4 バイト境界に整列(68000 のワード/ロングアクセス安全側)
    while len(data) % 4 != 0:
        data.append(0)
    pos = data_base + len(data)
    data += raw
    newdirs.append((nm, pos if sz > 0 else 0, sz))

dir_ofs = data_base + len(data)
out = bytearray()
out += struct.pack("<4sii", b"IWAD", len(kept), dir_ofs)
out += data
for nm, pos, sz in newdirs:
    nb = nm.encode('latin1')[:8]; nb += b"\0"*(8-len(nb))
    out += struct.pack("<ii", pos, sz) + nb

# C 配列出力
with open(outc, "w") as f:
    f.write("/* 自動生成: tools/strip_wad.py。マップは %s のみ保持。編集禁止。 */\n" % ",".join(sorted(keep)))
    f.write('#include "doom_iwad.h"\n')
    f.write("const unsigned char doom_iwad[%d] = {\n" % len(out))
    for i in range(0, len(out), 20):
        f.write(",".join(str(b) for b in out[i:i+20]) + ",\n")
    f.write("};\n")
    f.write("const unsigned int doom_iwad_len = %d;\n" % len(out))

print("in =%d B (%.0f KB)  num=%d" % (len(d), len(d)/1024, num))
print("out=%d B (%.0f KB)  num=%d  removed %d lumps" % (len(out), len(out)/1024, len(kept), num-len(kept)))
print("kept maps:", sorted(keep))
