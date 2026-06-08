#!/usr/bin/env python3
"""GENESIS DOOM 検証用アセット生成。
doom1.wad から PLAYPAL と TITLEPIC を取り出し、
 - Genesis 16色 CRAM パレット(palette0)
 - PLAYPAL 256 -> 4bit(0..15) の最近傍 LUT
 - TITLEPIC を フルスクリーン(256x224) / ゲームビューポート(224x96) のインデックス画像へ
 - TITLEPIC専用の16色タイルデータ(最下行8pxのみ別16色パレット可)
を C 配列として出力する。色削減はオフライン(ここ)で完結し、on-target は LUT 引き+タイル化のみ。
"""
import struct, sys, os

WAD = sys.argv[1] if len(sys.argv) > 1 else "wad/doom1.wad"
OUT = sys.argv[2] if len(sys.argv) > 2 else "port/gen/assets_gen"

d = open(WAD, "rb").read()
_, num, off = struct.unpack("<4sii", d[:12])
dirs = {}
for i in range(num):
    e = d[off+i*16:off+i*16+16]
    fp, sz = struct.unpack("<ii", e[:8])
    nm = e[8:16].split(b'\0')[0].decode('latin1')
    dirs.setdefault(nm, (fp, sz))

# --- PLAYPAL[0] : 256 x RGB ---
pp, _ = dirs["PLAYPAL"]
playpal = [tuple(d[pp + i*3 + c] for c in range(3)) for i in range(256)]

# --- TITLEPIC patch -> 320x200 indexed ---
def decode_patch(pos):
    w, h, lo, to = struct.unpack("<HHhh", d[pos:pos+8])
    colofs = struct.unpack("<%dI" % w, d[pos+8:pos+8+4*w])
    img = bytearray([0]) * (w*h)
    for x in range(w):
        p = pos + colofs[x]
        while d[p] != 0xFF:
            top = d[p]; cnt = d[p+1]; p += 3  # skip unused byte
            for k in range(cnt):
                y = top + k
                if 0 <= y < h:
                    img[y*w + x] = d[p+k]
            p += cnt + 1  # trailing unused byte
        # column terminated
    return w, h, img

tw, th, timg = decode_patch(dirs["TITLEPIC"][0])
assert (tw, th) == (320, 200), (tw, th)

# --- パレット選択用の PLAYPAL インデックス頻度 ---
# 3Dゲーム画面を見やすくするため、ホストGENESIS経路のE1M1サンプルPPMがあれば
# TITLEPICではなくその色分布を使う。PPMはPLAYPAL RGBから出力されるのでRGBで逆引きできる。
def load_ppm_rgb(path):
    try:
        with open(path, "rb") as f:
            magic = f.readline().strip()
            if magic != b"P6":
                return None
            line = f.readline()
            while line.startswith(b"#"):
                line = f.readline()
            w, h = map(int, line.split())
            maxv = int(f.readline())
            if maxv != 255:
                return None
            pix = f.read(w*h*3)
            if len(pix) != w*h*3:
                return None
            return pix
    except OSError:
        return None

used = [0]*256
sample_rgb = load_ppm_rgb("host_e1m1_gen.ppm")
if sample_rgb:
    rgb_to_idx = {playpal[i]: i for i in range(256)}
    for i in range(0, len(sample_rgb), 3):
        c = (sample_rgb[i], sample_rgb[i+1], sample_rgb[i+2])
        if c in rgb_to_idx:
            used[rgb_to_idx[c]] += 1
    source_note = "host_e1m1_gen.ppm"
else:
    for v in timg:
        used[v] += 1
    source_note = "TITLEPIC"

# --- median-cut で 16 色を選ぶ (使用色を RGB 空間で再帰分割) ---
pts = [(playpal[i], used[i]) for i in range(256) if used[i] > 0]

def median_cut(points, depth):
    if depth == 0 or len(points) <= 1:
        tw_ = sum(w for _, w in points) or 1
        r = sum(c[0]*w for c, w in points)//tw_
        g = sum(c[1]*w for c, w in points)//tw_
        b = sum(c[2]*w for c, w in points)//tw_
        return [(r, g, b)]
    # 最も分散の大きいチャネルで分割
    ranges = []
    for ch in range(3):
        vals = [c[ch] for c, _ in points]
        ranges.append(max(vals) - min(vals))
    ch = ranges.index(max(ranges))
    points.sort(key=lambda cw: cw[0][ch])
    mid = len(points)//2
    return median_cut(points[:mid], depth-1) + median_cut(points[mid:], depth-1)

def median_cut_boxes(points, depth):
    if depth == 0 or len(points) <= 1:
        return [points]
    ranges = []
    for ch in range(3):
        vals = [c[ch] for c, _ in points]
        ranges.append(max(vals) - min(vals))
    ch = ranges.index(max(ranges))
    points = sorted(points, key=lambda cw: cw[0][ch])
    mid = len(points)//2
    return median_cut_boxes(points[:mid], depth-1) + median_cut_boxes(points[mid:], depth-1)

pal16 = median_cut(pts, 4)              # 2^4 = 16 色

# Genesis はRGB各3bitなので、RGB上の別色が同じCRAM語へ潰れることがある。
# 16枠を無駄にしないため、頻出する量子化済み色で重複枠を置き換える。
def qkey(c):
    return (c[0] >> 5, c[1] >> 5, c[2] >> 5)
def qrgb(k):
    return (k[0] << 5, k[1] << 5, k[2] << 5)

qcount = {}
for i, n in enumerate(used):
    if n:
        k = qkey(playpal[i])
        qcount[k] = qcount.get(k, 0) + n
top_qkeys = [k for k, _ in sorted(qcount.items(), key=lambda kv: kv[1], reverse=True)]

fixed = []
seen = set()
for c in pal16:
    k = qkey(c)
    if k in seen:
        repl = next((tk for tk in top_qkeys if tk not in seen), k)
        fixed.append(qrgb(repl))
        seen.add(repl)
    else:
        fixed.append(c)
        seen.add(k)
while len(fixed) < 16:
    repl = next((tk for tk in top_qkeys if tk not in seen), (0, 0, 0))
    fixed.append(qrgb(repl))
    seen.add(repl)
pal16 = fixed[:16]

# --- 256 -> 0..15 最近傍 LUT (全 PLAYPAL を 16色へ写像) ---
def nearest(c):
    best, bi = 1 << 30, 0
    for i, p in enumerate(pal16):
        dd = (c[0]-p[0])**2 + (c[1]-p[1])**2 + (c[2]-p[2])**2
        if dd < best:
            best, bi = dd, i
    return bi
lut = [nearest(playpal[i]) for i in range(256)]

# --- Genesis CRAM 語 (0000 BBB0 GGG0 RRR0) ---
def cram(c):
    r, g, b = (c[0] >> 5), (c[1] >> 5), (c[2] >> 5)
    return (b << 9) | (g << 5) | (r << 1)
cram16 = [cram(c) for c in pal16]

# --- リサンプル (最近傍) して指定サイズのインデックス画像を作る ---
def resample(dst_w, dst_h):
    out = bytearray(dst_w*dst_h)
    for y in range(dst_h):
        sy = y * th // dst_h
        for x in range(dst_w):
            sx = x * tw // dst_w
            out[y*dst_w + x] = timg[sy*tw + sx]
    return out

FULL_W, FULL_H = 256, 224          # フルスクリーン(H32)
VIEW_W, VIEW_H = 224, 96           # ゲームビューポート(横長・縦半分)
ENG_W,  ENG_H  = 120, 160          # エンジン内部解像度(縦長)。表示時に横2倍で 240x160 に矯正
img_full = resample(FULL_W, FULL_H)
img_view = resample(VIEW_W, VIEW_H)
img_eng  = resample(ENG_W,  ENG_H)

# --- TITLEPIC 専用: palette0=上部216px, palette1=最下行8px ---
TITLE_TILES = (FULL_W // 8) * (FULL_H // 8)
title_used = [0] * 256
title_bottom_used = [0] * 256
for y in range(FULL_H):
    used_dst = title_bottom_used if y >= FULL_H - 8 else title_used
    row = img_full[y * FULL_W:(y + 1) * FULL_W]
    for v in row:
        used_dst[v] += 1

title_all_used = [a + b for a, b in zip(title_used, title_bottom_used)]
title_pts = [(playpal[i], title_used[i]) for i in range(256) if title_used[i] > 0]
title_bottom_pts = [(playpal[i], title_bottom_used[i]) for i in range(256) if title_bottom_used[i] > 0]
if not title_bottom_pts:
    title_bottom_pts = title_pts

title_qcount = {}
for i, n in enumerate(title_all_used):
    if n:
        k = qkey(playpal[i])
        title_qcount[k] = title_qcount.get(k, 0) + n
title_top_qkeys = [k for k, _ in sorted(title_qcount.items(), key=lambda kv: kv[1], reverse=True)]

def fix_palette_unique(cols, box_points):
    box_qcount = {}
    for c, n in box_points:
        k = qkey(c)
        box_qcount[k] = box_qcount.get(k, 0) + n
    box_top = [k for k, _ in sorted(box_qcount.items(), key=lambda kv: kv[1], reverse=True)]
    fixed, seen = [], set()
    for c in cols:
        k = qkey(c)
        if k in seen:
            repl = next((tk for tk in box_top + title_top_qkeys if tk not in seen), k)
            fixed.append(qrgb(repl))
            seen.add(repl)
        else:
            fixed.append(c)
            seen.add(k)
    while len(fixed) < 16:
        repl = next((tk for tk in box_top + title_top_qkeys if tk not in seen), (0, 0, 0))
        fixed.append(qrgb(repl))
        seen.add(repl)
    fixed[0] = (0, 0, 0)
    return fixed[:16]

title_palette = fix_palette_unique(median_cut(title_pts, 4), title_pts)
title_bottom_palette = fix_palette_unique(median_cut(title_bottom_pts, 4), title_bottom_pts)
title_cram32 = [cram(c) for c in title_palette + title_bottom_palette]

def nearest_in_palette(c, pal):
    best, bi = 1 << 30, 0
    for i, p in enumerate(pal):
        dd = (c[0]-p[0])**2 + (c[1]-p[1])**2 + (c[2]-p[2])**2
        if dd < best:
            best, bi = dd, i
    return bi, best

title_tiles_4bpp = bytearray()
title_names = []
for ty in range(FULL_H // 8):
    for tx in range(FULL_W // 8):
        pal = title_bottom_palette if ty == (FULL_H // 8) - 1 else title_palette
        for y in range(8):
            nibbles = []
            for x in range(8):
                idx = img_full[(ty * 8 + y) * FULL_W + tx * 8 + x]
                nibbles.append(nearest_in_palette(playpal[idx], pal)[0])
            for i in range(0, 8, 2):
                title_tiles_4bpp.append((nibbles[i] << 4) | nibbles[i + 1])
        name_palette = 1 if ty == (FULL_H // 8) - 1 else 0
        title_names.append((name_palette << 13) | (1 + ty * (FULL_W // 8) + tx))

# --- C 出力 ---
def carr(name, data, typ="unsigned char", perline=16):
    s = ["const %s %s[%d] = {" % (typ, name, len(data))]
    for i in range(0, len(data), perline):
        s.append("  " + ",".join(str(v) for v in data[i:i+perline]) + ",")
    s.append("};")
    return "\n".join(s)

def carr_u16(name, data, perline=8):
    s = ["const unsigned short %s[%d] = {" % (name, len(data))]
    for i in range(0, len(data), perline):
        s.append("  " + ",".join(str(v) for v in data[i:i+perline]) + ",")
    s.append("};")
    return "\n".join(s)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT + ".h", "w") as f:
    f.write("""/* 自動生成: tools/gen_assets.py。編集しないこと。 */
#ifndef ASSETS_GEN_H
#define ASSETS_GEN_H
#define ASSET_FULL_W %d
#define ASSET_FULL_H %d
#define ASSET_VIEW_W %d
#define ASSET_VIEW_H %d
extern const unsigned short asset_cram16[16];      /* Genesis CRAM palette0 */
extern const unsigned char  asset_pal_lut[256];    /* PLAYPAL idx -> 0..15 */
extern const unsigned char  asset_title_full[%d];  /* %dx%d indexed */
extern const unsigned char  asset_title_view[%d];  /* %dx%d indexed */
#define ASSET_ENG_W %d
#define ASSET_ENG_H %d
extern const unsigned char  asset_title_eng[%d];   /* %dx%d indexed (内部解像度) */
#define ASSET_TITLE_TILES %d
extern const unsigned short asset_title_cram32[32];       /* TITLEPIC palette0 + bottom-row palette1 */
extern const unsigned char  asset_title_tiles4[%d];       /* 32x28 4bpp tiles */
extern const unsigned short asset_title_names[%d];        /* Plane A names with palette bits */
#endif
""" % (FULL_W, FULL_H, VIEW_W, VIEW_H,
       FULL_W*FULL_H, FULL_W, FULL_H, VIEW_W*VIEW_H, VIEW_W, VIEW_H,
       ENG_W, ENG_H, ENG_W*ENG_H, ENG_W, ENG_H,
       TITLE_TILES, len(title_tiles_4bpp), len(title_names)))

with open(OUT + ".c", "w") as f:
    f.write('/* 自動生成: tools/gen_assets.py。編集しないこと。 */\n')
    f.write('#include "assets_gen.h"\n\n')
    f.write(carr("asset_cram16", cram16, "unsigned short", 8) + "\n\n")
    f.write(carr("asset_pal_lut", lut) + "\n\n")
    f.write(carr("asset_title_full", img_full) + "\n\n")
    f.write(carr("asset_title_view", img_view) + "\n\n")
    f.write(carr("asset_title_eng", img_eng) + "\n")
    f.write("\n\n" + carr_u16("asset_title_cram32", title_cram32) + "\n\n")
    f.write(carr("asset_title_tiles4", title_tiles_4bpp) + "\n\n")
    f.write(carr_u16("asset_title_names", title_names) + "\n")

print("palette source:", source_note)
print("pal16 (RGB):", pal16)
print("CRAM words :", [hex(x) for x in cram16])
print("title CRAM32:", [hex(x) for x in title_cram32])
print("wrote %s.{c,h}  full=%dx%d view=%dx%d" % (OUT, FULL_W, FULL_H, VIEW_W, VIEW_H))
