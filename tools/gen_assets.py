#!/usr/bin/env python3
"""GENESIS DOOM 検証用アセット生成。
doom1.wad から PLAYPAL と TITLEPIC を取り出し、
 - Genesis 16色 CRAM パレット(palette0)
 - PLAYPAL 256 -> 4bit(0..15) の最近傍 LUT
 - TITLEPIC を フルスクリーン(256x224) / ゲームビューポート(224x96) のインデックス画像へ
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

# E1M1 start-area pools read too dark with the automatically selected dark blue.
# Keep a single gameplay palette, but reserve that blue slot for a clearer water
# color so PLAYPAL blues quantize to something recognizable on Genesis CRAM.
GEN_POOL_BLUE_RGB = (32, 96, 224)
gen_pool_blue_index = None
for i, c in enumerate(pal16):
    if qkey(c) == (0, 0, 1):
        pal16[i] = GEN_POOL_BLUE_RGB
        gen_pool_blue_index = i
        break

# --- 256 -> 0..15 最近傍 LUT (全 PLAYPAL を 16色へ写像) ---
def nearest(c):
    best, bi = 1 << 30, 0
    for i, p in enumerate(pal16):
        dd = (c[0]-p[0])**2 + (c[1]-p[1])**2 + (c[2]-p[2])**2
        if dd < best:
            best, bi = dd, i
    return bi
lut = [nearest(playpal[i]) for i in range(256)]
if gen_pool_blue_index is not None:
    for i in range(118, 128):
        lut[i] = gen_pool_blue_index

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

# --- C 出力 ---
def carr(name, data, typ="unsigned char", perline=16):
    s = ["const %s %s[%d] = {" % (typ, name, len(data))]
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
#endif
""" % (FULL_W, FULL_H, VIEW_W, VIEW_H,
       FULL_W*FULL_H, FULL_W, FULL_H, VIEW_W*VIEW_H, VIEW_W, VIEW_H,
       ENG_W, ENG_H, ENG_W*ENG_H, ENG_W, ENG_H))

with open(OUT + ".c", "w") as f:
    f.write('/* 自動生成: tools/gen_assets.py。編集しないこと。 */\n')
    f.write('#include "assets_gen.h"\n\n')
    f.write(carr("asset_cram16", cram16, "unsigned short", 8) + "\n\n")
    f.write(carr("asset_pal_lut", lut) + "\n\n")
    f.write(carr("asset_title_full", img_full) + "\n\n")
    f.write(carr("asset_title_view", img_view) + "\n\n")
    f.write(carr("asset_title_eng", img_eng) + "\n")

print("palette source:", source_note)
print("pal16 (RGB):", pal16)
print("CRAM words :", [hex(x) for x in cram16])
print("wrote %s.{c,h}  full=%dx%d view=%dx%d" % (OUT, FULL_W, FULL_H, VIEW_W, VIEW_H))
