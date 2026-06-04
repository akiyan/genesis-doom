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

# --- 68k(BE) 用ジオメトリのエンディアン変換 ---------------------------------
# vertexes/segs/nodes はエンジンが W_CacheLumpNum 直で SHORT/LONG 無しに raw 読み
# する(ホットパス)。WAD は LE なので 68000(BE) では byte-swap 化けし不正アドレス
# アクセス→例外になる。これらの lump だけビルド時に BE 化しておけば、ランタイムは
# raw 読みのまま正しく動く(CPU コスト 0)。他 lump(sectors/sides/things 等)は LE の
# まま SHORT() 読みされるので非対象。この出力は 68k 専用(host は doom1.c=LE を使用)。
# レコード layout はエンジンの構造体に厳密一致させること:
#   vertex_t = fixed_t x,y                                   → 4B×2
#   seg_t    = v1(4,4) v2(4,4) offset(4) angle(4)            → 4B×6
#              sidenum linenum frontsectornum backsectornum  → 2B×4   (計32B)
#   mapnode_t= x,y,dx,dy, bbox[2][4], children[2]            → 2B×14  (計28B)
def _rev(b, o, n):           # b[o:o+n] を反転(LE→BE)
    b[o:o+n] = b[o:o+n][::-1]
def be_vertexes(raw):        # 8B/レコード: 4B×2
    b = bytearray(raw)
    for o in range(0, len(b) - 7, 8):
        _rev(b, o, 4); _rev(b, o+4, 4)
    return bytes(b)
def be_nodes(raw):           # 28B/レコード: 2B×14
    b = bytearray(raw)
    for o in range(0, len(b) - 1, 2):
        _rev(b, o, 2)
    return bytes(b)
def be_segs(raw):            # 32B/レコード: 4B×6 ＋ 2B×4
    b = bytearray(raw)
    for o in range(0, len(b) - 31, 32):
        for k in range(0, 24, 4): _rev(b, o+k, 4)
        for k in range(24, 32, 2): _rev(b, o+k, 2)
    return bytes(b)
def be_lines(raw):           # 56B/レコード(line_t): v1,v2,lineno,dx,dy,bbox[4]=4B×11
    b = bytearray(raw)       #   sidenum[2],flags,const_special,tag,slopetype=2B×6
    for o in range(0, len(b) - 55, 56):
        for k in (0,4,8,12,16,20,24,32,36,40,44): _rev(b, o+k, 4)
        for k in (28,30,48,50,52,54):             _rev(b, o+k, 2)
    return bytes(b)
BE_SWAP = {"VERTEXES": be_vertexes, "NODES": be_nodes, "SEGS": be_segs,
           "LINEDEFS": be_lines}
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
    # 68k(BE) 用: vertexes/segs/nodes を構造別に BE 化(raw 読みのホットパス対策)
    if sz > 0 and nm in BE_SWAP:
        raw = BE_SWAP[nm](raw)
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
