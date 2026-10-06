#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a Canva-importable HTML deck from the manuscript and real WAD data.

Generated maps visualize source geometry. Emulator captures remain separately
identified from conceptual diagrams. No game assets are fetched externally.
"""
from pathlib import Path
import base64
import html
import json
import math
import re
import struct
import zipfile
from PIL import Image, ImageDraw
import os
from local_env import load_env
load_env()

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'presentation'
ASSETS = OUT / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
BG = '#101316'
FG = '#f2eee4'
MUTED = '#aeb7b7'
ORANGE = '#ff7848'
TEAL = '#62d8c2'
BLUE = '#80aaf9'

wad = Path(os.environ.get('DOOM1_WAD', ROOT / 'wad/doom1.wad')).read_bytes()
_, count, directory = struct.unpack_from('<4sII', wad)
entries = []
for i in range(count):
    p, size, name = struct.unpack_from('<II8s', wad, directory + 16*i)
    entries.append((name.rstrip(b'\0').decode('ascii'), p, size))
lumps = {n: wad[p:p+s] for n,p,s in entries}
mi = next(i for i,e in enumerate(entries) if e[0] == 'E1M1')
level = {n: wad[p:p+s] for n,p,s in entries[mi+1:mi+11]}
vertices = list(struct.iter_unpack('<hh', level['VERTEXES']))
linedefs = list(struct.iter_unpack('<7H', level['LINEDEFS']))
segs = list(struct.iter_unpack('<6H', level['SEGS']))
subsectors = list(struct.iter_unpack('<2H', level['SSECTORS']))
nodes = list(struct.iter_unpack('<12h2H', level['NODES']))
things = list(struct.iter_unpack('<5h', level['THINGS']))
spawn = next(t for t in things if t[3] == 1)
pal = [tuple(lumps['PLAYPAL'][i:i+3]) for i in range(0,768,3)]

def patch_image(data):
    w,h,_,_ = struct.unpack_from('<HHhh', data)
    image = Image.new('RGB', (w,h))
    px = image.load()
    for x in range(w):
        offset = struct.unpack_from('<I', data, 8+4*x)[0]
        while data[offset] != 255:
            top,n = data[offset:offset+2]
            for y in range(n):
                if top+y < h: px[x,top+y] = pal[data[offset+3+y]]
            offset += n+4
    return image

patch_image(lumps['TITLEPIC']).save(ASSETS/'wad-title.png')
for name in ['FLOOR0_1','FLOOR4_8','NUKAGE1','CEIL3_5']:
    if name in lumps and len(lumps[name]) == 4096:
        tex = Image.new('RGB',(64,64))
        tex.putdata([pal[v] for v in lumps[name]])
        tex.resize((256,256),Image.Resampling.NEAREST).save(ASSETS/f'{name}.png')

def hull(points):
    p = sorted(set(points))
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for q in p:
        while len(lower)>1 and cross(lower[-2],lower[-1],q)<=0: lower.pop()
        lower.append(q)
    upper=[]
    for q in reversed(p):
        while len(upper)>1 and cross(upper[-2],upper[-1],q)<=0: upper.pop()
        upper.append(q)
    return lower[:-1]+upper[:-1]

xmin,xmax = min(x for x,y in vertices),max(x for x,y in vertices)
ymin,ymax = min(y for x,y in vertices),max(y for x,y in vertices)
W,H=1800,1120
scale=min((W-100)/(xmax-xmin),(H-100)/(ymax-ymin))
def xy(p):
    return ((p[0]-(xmin+xmax)/2)*scale+W/2, H/2-(p[1]-(ymin+ymax)/2)*scale)

def clip(poly,x,y,dx,dy,side):
    def dist(p): return (dx*(p[1]-y)-dy*(p[0]-x))*(1 if side==0 else -1)
    result=[]
    if not poly: return result
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=dist(a),dist(b)
        if da<=0: result.append(a)
        if (da<0 and db>0) or (da>0 and db<0):
            t=da/(da-db)
            result.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return result

leaf_polys={}
def partition(index,poly):
    if index&0x8000:
        ssidx=index&0x7fff
        n,start=subsectors[ssidx]
        for s in segs[start:start+n]:
            a,b=vertices[s[0]],vertices[s[1]]
            poly=clip(poly,a[0],a[1],b[0]-a[0],b[1]-a[1],0)
        leaf_polys[ssidx]=poly
        return
    nd=nodes[index]
    for side in [0,1]: partition(nd[12+side],clip(poly,*nd[:4],side))
partition(len(nodes)-1,[(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)])

def make_map(mode):
    im=Image.new('RGB',(W,H),BG)
    dr=ImageDraw.Draw(im)
    colors=['#354957','#345f62','#63584b','#455c47','#674d52','#424365']
    for idx,(n,start) in enumerate(subsectors):
        ss=segs[start:start+n]
        poly=leaf_polys[idx]
        if len(poly)<3: continue
        color='#1e2b2f' if mode=='map' else colors[idx%len(colors)]
        dr.polygon([xy(v) for v in poly],fill=color)
    for a,b,flags,special,tag,right,left in linedefs:
        dr.line([xy(vertices[a]),xy(vertices[b])], fill=FG if left==65535 else '#527370',width=4 if left==65535 else 2)
    if mode=='bsp':
        # The root's partition is a real E1M1 NODES entry, not a ray cast.
        nd=nodes[-1]
        x,y,dx,dy=nd[:4]
        limits=[]
        if dx:
            for xx in (xmin,xmax):
                t=(xx-x)/dx; yy=y+t*dy
                if ymin<=yy<=ymax: limits.append((xx,yy))
        if dy:
            for yy in (ymin,ymax):
                t=(yy-y)/dy; xx=x+t*dx
                if xmin<=xx<=xmax: limits.append((xx,yy))
        if len(limits)>=2:
            dr.line([xy(limits[0]),xy(limits[1])],fill=ORANGE,width=8)
    sx,sy=xy(spawn[:2]); theta=math.radians(spawn[2])
    tip=(sx+33*math.cos(theta),sy-33*math.sin(theta))
    dr.ellipse((sx-13,sy-13,sx+13,sy+13),fill=ORANGE)
    dr.line([(sx,sy),tip],fill=ORANGE,width=9)
    im.save(ASSETS/f'e1m1-{mode}.png')
make_map('map')
make_map('bsp')

manifest={'wad':'wad/doom1.wad','level':'E1M1','vertices':len(vertices),'linedefs':len(linedefs),'nodes':len(nodes),'subsectors':len(subsectors),'bsp_bytes':sum(len(level[k]) for k in ['NODES','SEGS','SSECTORS']),'spawn':spawn,'captures':'Mednafen capture of port/build/engine/doom.bin; not a physical-console capture','map_images':'Actual WAD vertices/linedefs; subsectors clipped through the BSP tree and their seg half-planes; orange partition is the root NODES entry.'}

def uri(name):
    path=ASSETS/name
    mime='image/png'
    return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()

def text(s,x,y,w,size=34,color=FG,weight=400,lh=1.4,extra=''):
    return f'<div class="txt" style="left:{x}px;top:{y}px;width:{w}px;font-size:{size}px;color:{color};font-weight:{weight};line-height:{lh};{extra}">{s}</div>'

def rect(x,y,w,h,fill,stroke=None):
    return f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{fill};'+(f'border:2px solid {stroke};' if stroke else '')+'"></div>'

def line(x,y,w,color=MUTED,h=2): return rect(x,y,w,h,color)

def image(name,x,y,w,h,fit='contain',opacity=1):
    return f'<img src="{uri(name)}" alt="{html.escape(name)}" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;object-fit:{fit};image-rendering:pixelated;opacity:{opacity};"/>'

def arrow(x,y,w=85,color=ORANGE):
    return rect(x,y+12,w-14,4,color)+f'<div style="position:absolute;left:{x+w-17}px;top:{y+3}px;width:0;height:0;border-top:11px solid transparent;border-bottom:11px solid transparent;border-left:17px solid {color};"></div>'

def labelbox(s,x,y,w,h=100,color=TEAL):
    return rect(x,y,w,h,'#1c2529',color)+text(s,x+20,y+25,w-40,30,FG,500)

parts=(ROOT/'Presentation.md').read_text().strip().split('\n\n')
def notes(*indices,extra=''):
    return '\n\n'.join(parts[i] for i in indices)+(('\n\n'+extra) if extra else '')

slides=[]
def add(title,body,note,caption=''):
    i=len(slides)+1
    head=text(title,80,62,1440,58,FG,700,1.2) if title else ''
    foot=text(caption,80,838,1380,19,MUTED) if caption else ''
    foot+=text(f'{i:02}',1475,835,50,22,MUTED,500,extra='text-align:right')
    slides.append(f'<section class="slide" data-document-role="page" data-label="{html.escape(title or "メガドライブに Doom を移植してみた",quote=True)}" data-speaker-notes="{html.escape(note,quote=True)}">{head}{body}{foot}</section>')

# 01 — large pixels, minimal cover.
add('',image('spawn.png',715,115,820,655)+text('メガドライブに',80,168,650,64,FG,700)+text('Doom を',80,265,660,112,ORANGE,800)+text('移植してみた',80,420,650,72,FG,700)+text('AI と、64 KB の RAM。',85,600,650,35,MUTED),notes(1), 'GBADoom ベース / メガドライブ単体を対象 / Mednafen 実行画面')

# 02 — comparison values are EWRAM vs main RAM, not a total-RAM assertion.
b=text('GBA',85,205,380,38,TEAL,600)+text('256 KB',80,255,650,106,TEAL,700)+rect(85,405,1120,64,TEAL)
b+=text('メガドライブ',85,510,550,38,ORANGE,600)+text('64 KB',80,558,600,106,ORANGE,700)+rect(85,710,280,64,ORANGE)
b+=text('ARM 用の GBADoom を\n68000 用 GCC で移植',965,545,560,36,FG,500)
add('移植元は GBADoom',b,notes(2),'比較：GBA の外部 RAM 256 KB ／ メガドライブのメイン RAM 64 KB')

# 03 — source assets, not generated decoration.
b=text('WAD',80,186,350,95,ORANGE,700)+text("Where’s All the Data?",85,310,650,30,MUTED)+image('wad-title.png',80,400,430,270)
b+=image('e1m1-map.png',610,205,850,495)
for j,name in enumerate(['FLOOR0_1','FLOOR4_8','NUKAGE1','CEIL3_5']): b+=image(f'{name}.png',650+j*190,673,132,132)
b+=text('起動画面',80,704,400,30)+text('マップ',645,160,500,30)+text('テクスチャ',80,765,430,30,MUTED)
add('ゲームデータは WAD にまとまっている',b,notes(3),'画像は手元の Doom shareware WAD から抽出・可視化。実行エンジンは別。')

# 04 — full authentic title capture.
add('まず、起動画面が出た',image('title.png',620,185,900,590)+text('最初の手応えは\nエミュレータの画面。',80,285,560,48,FG,500)+text('起動コード\nVDP 初期化\n画像データの転送',85,495,470,31,MUTED),notes(4),'Mednafen 実行画面 / 現在の ROM で再撮影')

# 05 — intentional simple conceptual pixels.
b=text('内部',85,192,450,30,MUTED)+text('120 × 128',80,230,650,72,FG,700)+text('表示',920,192,450,30,MUTED)+text('240 × 128',915,230,650,72,FG,700)
for yy in range(5):
    for xx in range(5):
        c=[TEAL,'#355753',ORANGE,'#24413d'][(xx+yy*3)%4]
        b+=rect(115+xx*54,380+yy*54,51,51,c)+rect(885+xx*108,380+yy*54,105,51,c)
b+=arrow(545,505,210)+text('横に 2 倍',545,562,250,32,ORANGE,600)
add('横長ドットで描く',b,notes(4),'画素の拡大方法を示す模式図。内部解像度の初期構成。')

# 06 — real palette LUT.
asset_text=(ROOT/'port/gen/assets_gen.c').read_text()
match=re.search(r'asset_cram16\[16\]\s*=\s*\{([^}]+)',asset_text)
cram=[int(v.strip(),0) for v in match.group(1).split(',') if v.strip()]
b=text('256 色',80,188,550,80,FG,700)+text('16 色',1025,188,500,80,ORANGE,700)
for i,c in enumerate(pal): b+=rect(85+(i%16)*32,335+(i//16)*23,30,21,'#%02x%02x%02x'%c)
for i,v in enumerate(cram):
    c=tuple(((v>>shift)&7)*255//7 for shift in [1,5,9])
    b+=rect(1015+(i%4)*112,345+(i//4)*90,108,86,'#%02x%02x%02x'%c)
b+=arrow(665,490,210)+text('変換表',677,415,250,34,TEAL,600)+text('実行時は表を引くだけ',85,750,1300,40,FG,500)
add('色の変換は、事前にテーブル化',b,notes(4),'左：WAD の PLAYPAL ／ 右：現在のゲーム用 CRAM パレット。移植初期からの設計。')

# 07 — RAM budget reductions, no invented proportional total layout.
b=text('64 KB に収める',85,193,1350,92,ORANGE,700)
b+=text('テクスチャのキャッシュ',85,353,700,36)+text('16 KB',85,420,400,74,FG,700)+arrow(405,449,150)+text('128 B',605,420,500,74,TEAL,700)
b+=line(85,552,1420,'#3a4447')+text('計算用の領域を縮小',85,595,710,36)+text('ステータス表示を省略',850,595,650,36)+text('敵・アイテムは出現させない',85,687,1300,44,TEAL,600)
add('最初のゴールは「描画して歩く」',b,notes(5),'容量は columnCache の変更記録。プレイヤーの内部状態を全削除したわけではない。')

# 08 — stack concept explicitly not linker map.
b=rect(85,238,790,180,'#294c48')+text('ヒープなどの作業領域',120,296,700,38)+rect(85,422,790,105,'#20272b')+text('余裕を持たせたつもりの空き',120,449,710,31,MUTED)+rect(85,531,790,196,'#5b332d')+text('スタック',120,588,690,43,ORANGE,700)
b+=text('関数を呼ぶほど\n使用量が増える',1030,260,470,44)+text('余裕が足りないと\n別の領域を壊す',1030,507,490,44,ORANGE,600)
b+=rect(902,338,7,281,ORANGE)+text('↑',884,278,85,65,ORANGE,700)
add('収まっても、スタックで止まる',b,notes(5),'メモリ領域の関係を示す模式図。実際の配置・容量比ではありません。')

# 09 — byte order.
b=text('0x12345678',85,188,1380,70,TEAL,600)
b+=text('GBA / リトルエンディアン',85,340,1380,35)+text('68000 / ビッグエンディアン',85,574,1380,35)
for j,v in enumerate(['78','56','34','12']): b+=labelbox(v,85+j*215,409,175,108,TEAL)
for j,v in enumerate(['12','34','56','78']): b+=labelbox(v,85+j*215,644,175,108,ORANGE)
b+=text('並び順が逆。\n入れ替え漏れで\nハングアップ。',1030,418,490,46,ORANGE,600)
add('同じ数値でも、バイトの順が逆',b,notes(6),'左から低位アドレス順に並べた 32 bit 数値の例')

# 10 — actual screenshot, status detail is cropped from it.
b=image('turn.png',730,205,810,567)+text('普通のログがない。\nステップ実行も使わない。',85,215,625,43,FG,500)+text('画面の色とラベルで\n「どこまで進んだか」を見る',85,440,635,40,TEAL,600)+text('AI を止めて、\nデバッグ情報を増やす',85,650,630,40,ORANGE,600)
add('見えるデバッグ情報を増やす',b,notes(7,8),'Mednafen 実行画面。下部に描画段階の診断表示。')

# 11 — dramatic performance value with actual screenshot.
b=text('0.5',70,238,700,220,ORANGE,800,1.0)+text('fps',535,390,230,74,ORANGE,600)+text('ようやく初期位置が安定。',85,585,650,40)+image('spawn.png',770,217,760,565)
add('動いた。でも、遅い',b,notes(9),'0.5 fps は開発初期の計測値。右の画像は現在の ROM の再撮影。')

# 12 — native editable flow blocks.
b=labelbox('3 ボタンパッド',85,345,380,120,ORANGE)+arrow(493,390,100)+labelbox('Doom の入力イベント',620,345,450,120,TEAL)+arrow(1100,390,100)+labelbox('移動処理',1230,345,280,120,TEAL)
b+=text('ハードから読み取る部分をつなぐ',85,574,1400,56,FG,600)+text('既存のゲーム処理をそのまま使える',85,674,1400,36,MUTED)
add('入力をつなぐと、歩けた',b,notes(9),'Genesis のパッド入力を既存の Doom イベント経路に接続')

# 13 — DMA diagram without implying parallel DMA speed guarantee.
b=text('CPU の逐次書き込み',85,195,1360,35,MUTED)+labelbox('RAM',85,265,260,100,MUTED)
for j in range(7): b+=arrow(388+j*108,299,72,MUTED)
b+=labelbox('VRAM',1230,265,280,100,MUTED)
b+=text('行ごとにまとめて DMA 転送',85,470,1400,43,TEAL,600)+labelbox('行バッファ A',85,575,380,110,TEAL)+labelbox('行バッファ B',85,700,380,90,TEAL)+arrow(530,621,570,TEAL)+labelbox('VRAM',1230,575,280,110,TEAL)
b+=text('近似除算も試したが、表示が崩れて不採用',85,392,1420,30,ORANGE)
add('計算と転送を軽くする',b,notes(10),'採用：行単位 DMA ／ 不採用：精度を落とす近似除算')

# 14 — current viewport from capture, resolution relationship.
b=text('120 × 128',85,225,680,78,FG,700)+text('120 × 64',85,450,680,78,TEAL,700)+text('描画する画素数を半分に',85,604,670,38,TEAL,600)+image('moved.png',810,210,710,548)+text('表示時に縦横 2 倍',870,755,650,32,MUTED)
b+=text('↓',300,335,120,80,ORANGE,600)
add('縦も半分。遠景も簡略化',b,notes(11),'内部解像度を 120×64 に削減。遠距離描画の上限とテクスチャの間引きを導入。')

# 15 — map and simple height diagram.
b=image('e1m1-map.png',50,190,960,585)+text('平面の間取り',85,766,850,34,TEAL,600)
for j,h in enumerate([55,95,140,185]):
    b+=rect(1050+j*110,665-h,106,h,'#355753')+line(1050+j*110,665-h,106,TEAL,4)
b+=line(1050,390,440,FG,5)+text('天井の高さ',1080,330,420,31)+text('床の高さ',1080,710,420,31)+text('高さの違いで\n段差や階段に',1050,190,465,39,ORANGE,600)
add('Doom の空間は「2.5D」',b,notes(12),'左：WAD から描いた E1M1 ／ 右：床・天井の高さを示す模式図')

# 16 — actual subsector geometry, conceptual tree separately labelled.
b=image('e1m1-bsp.png',45,190,1010,625)+text('BSP',1110,205,450,77,ORANGE,700)+text('空間を二分する\n木構造',1110,315,450,38)
b+=labelbox('空間',1170,465,210,85,ORANGE)+line(1120,583,320,MUTED,3)+rect(1274,550,3,34,MUTED)+rect(1120,583,3,40,MUTED)+rect(1437,583,3,40,MUTED)+labelbox('手前',1060,624,190,85,TEAL)+labelbox('奥',1340,624,190,85,TEAL)
add('BSP で、見えない部分の処理を省く',b,notes(13,extra='地図は実際の NODES / SEGS / SSECTORS から可視化。橙線は根ノードの分割線。右の木は概念図で、実際の可視判定結果を示すものではない。'),'E1M1：色分けはサブセクタ、橙線は BSP の根の分割線。右の木は模式図。')

# 17 — ROM addressing not RAM.
b=text('WAD 約 2.6 MB',85,200,1400,85,TEAL,700)+rect(85,382,1430,150,'#252d32')+rect(85,382,930,150,'#355753')+text('マップ・テクスチャなど',120,426,890,36)+text('コードなど',1080,426,380,36,MUTED)
b+=text('ROM 4 MB に収まる',85,593,1430,63,ORANGE,700)+text('メガドライブは、その ROM を CPU から直接読める',85,717,1430,34)
add('大きなデータを、そのまま読める',b,notes(14),'WAD は削減後の記録値。帯は概念図で、コード領域の実測内訳ではありません。')

# 18 — user-described MSX architecture, not presented as the universal layout.
b=text('一度に見えるのは 64 KB',85,185,1400,61,ORANGE,700)
for j,(p,label,c) in enumerate([('PAGE 0','エンジン・RAM',TEAL),('PAGE 1','エンジン・RAM',TEAL),('PAGE 2','マップ・テクスチャ',ORANGE),('PAGE 3','BSP',ORANGE)]):
    x=85+j*360
    b+=rect(x,340,335,210,'#1c2529',c)+text(p,x+22,363,300,26,c,600)+text(label,x+22,425,300,27,FG,500)+text('16 KB',x+22,492,300,25,MUTED)
b+=text('同じ窓に、別のバンクを入れ替える',85,650,1430,45)+text('大きな ROM',85,747,350,30,TEAL)+arrow(465,751,440,TEAL)+text('必要な 16 KB を選ぶ',950,742,560,32,TEAL)
add('MSX では、バンク切り替え',b,notes(15,16),'発表原稿にある今回の試作構成。MSX 全般の固定メモリ配置を示すものではありません。')

# 19 — honest failure + no fictional screenshot.
b=text('データを読むたびに\nバンクをやりくり',85,210,1050,68,FG,600)+text('表示の崩れ',85,466,690,49,ORANGE,600)+text('処理の遅さ・ハングアップ',85,554,1390,49,ORANGE,600)+text('MSX 版は、まだ安定動作に至らず',85,725,1430,43,MUTED)
add('MSX 版は、まだ苦戦中',b,notes(17),'MSX 側は発表者の試作報告に基づく。実行画面の素材は未収録。')

# 20 — reported performance, distinguish different viewpoints.
b=text('0.5',70,215,440,155,MUTED,700)+text('0.8',575,215,440,155,TEAL,700)+text('2 弱',1125,215,440,135,ORANGE,700)
b+=text('fps / 初期の開始地点',85,408,440,29,MUTED)+text('fps / 調整後の開始地点',595,408,490,29,TEAL)+text('fps / 壁に近づくと',1135,408,420,29,ORANGE)
b+=image('final.png',675,491,810,310)+text('おっそいけど、\n歩き回れる。',85,553,660,67,FG,700)
add('Doom の雰囲気を感じられるところまで',b,notes(18),'fps は原稿の報告値。壁際は開始地点と異なる視点での値。画像は現在の ROM の再撮影。')

# 21 — clean close.
b=image('moved.png',730,180,810,605)+text('音楽をつけて、',85,263,690,64,TEAL,600)+text('一旦の区切り。',85,366,690,70,FG,700)+text('AI でレトロハード開発',85,630,690,35,MUTED)
add('メガドライブで Doom が動いた',b,notes(18,extra='E1M1 の BGM は XGM ドライバで再生。画像はメガドライブのエミュレータ実行画面。'),'GBADoom ベース / E1M1 / メガドライブ単体を対象')

css='''*{box-sizing:border-box}html,body{margin:0;padding:0;background:#272c30}body{font-family:"Noto Sans CJK JP","Noto Sans JP",sans-serif}.slide{position:relative;width:1600px;height:900px;background:#101316;overflow:hidden;margin:0 auto 32px;page-break-after:always}.txt{position:absolute;white-space:pre-line;overflow-wrap:normal;word-break:normal}img{display:block}@media print{body{background:#101316}.slide{margin:0;page-break-after:always}@page{size:1600px 900px;margin:0}}'''
document='<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><title>メガドライブに Doom を移植してみた</title><style>'+css+'</style></head><body>'+''.join(slides)+'</body></html>'
(OUT/'Presentation.html').write_text(document)
manifest['slides']=len(slides)
manifest['manuscript']='Presentation.md'
(OUT/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(OUT/'Presentation-canva.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT/'Presentation.html','index.html')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
print('Created',OUT/'Presentation.html')
