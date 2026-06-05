/* GENESIS DOOM - プラットフォーム層 (68k 実機/blastem 向け本番配線)
 *
 * エンジンの I_*_e32 表面を Genesis VDP/RAM に接続する。
 *   - 映像: I_FinishUpdate_e32 → GEN_BlitIndexed(byte stride, hscale=2 で 120x64→240x128)
 *   - 起動トレース: 画面ボーダー色(backdrop) を段階で変える
 *       青 = グラフィック初期化到達 / 緑 = 描画ループ到達(起動成功) / 赤 = I_Error
 *   - ヒープ: _sbrk が _end〜RAM 上限から払い出し(Z_Init が収まる分だけ確保)
 *   - I_GetTime=0: タイトルに留まりデモ(E1M1=メモリ超過)へ進ませない
 */
#include "doomdef.h"
#include "doomtype.h"
#include "d_event.h"
#include "i_system_e32.h"
#include "assets_gen.h"
#include <time.h>

typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned int   u32;

#define VDP_CTRL_L (*(volatile u32*)0xC00004)
#define VDP_CTRL_W (*(volatile u16*)0xC00004)
#define VDP_DATA_W (*(volatile u16*)0xC00000)

extern void GEN_VideoInit(void);
extern void GEN_SetPalette16(const u16*);
extern void GEN_ClearPlaneA(void);
extern void GEN_BlitIndexed(const u8*, int, int, int, int, int,
                            const u8*, int, int, int);

/* 3D ビューのみ描画(ステータスバー下32行は描かない)。framebuffer は
 * 120 x viewheight(=96-32=64) の 1バイト/画素 = 7.5KB。 */
#define GEN_FB_H  (SCREENHEIGHT - 32)        /* = viewheight = 64 */
static u8 g_fb[SCREENWIDTH * GEN_FB_H];

/* --- backdrop(画面ボーダー/透明色) を CRAM[63] 経由で設定。
 *     I_Error 表示と、起動デバッグ用 GEN_trace に使う。 --- */
#define TRACE_RED   0x000E
static void trace(u16 color)
{
    VDP_CTRL_L = 0xC07E0000;                 /* CRAM 書き込み addr=63(=0x7E) */
    VDP_DATA_W = color;
    VDP_CTRL_W = 0x8000 | (7 << 8) | 0x3F;   /* reg7 = palette3 色15 = CRAM63 */
}

/* エンジン起動の段階トレース(backdrop色)。ハング箇所の二分探索用に外部公開。
 * 使い方: エンジン内の任意点に `extern void GEN_trace(int); GEN_trace(N);` を挿し、
 * 停止時の画面ボーダー色で到達段階を判定する(E1M1 デバッグで再利用)。 */
static const u16 g_tracepal[16] = {
    0x0E00, /*0 青*/ 0x00E0, /*1 緑*/ 0x000E, /*2 赤*/ 0x00EE, /*3 黄*/
    0x0E0E, /*4 マゼンタ*/ 0x0EE0, /*5 シアン*/ 0x0EEE, /*6 白*/ 0x0888, /*7 灰*/
    0x0006, /*8 暗赤*/ 0x0060, /*9 暗緑*/ 0x0600, /*10 暗青*/ 0x0066, /*11 暗黄*/
    0x0808, /*12 暗紫*/ 0x0680, /*13 橙*/ 0x0086, /*14 黄緑*/ 0x0408 /*15*/
};
void GEN_trace(int n) {
#if defined(GEN_BOOT_E1M1) && defined(GEN_DBGSTAGE)
    /* 段表示は左下スプライト(色付き■＋ラベル)のみ。backdrop は黒固定にして段色■を視認可能に。 */
    { extern void GEN_DbgStage(int); GEN_DbgStage(n); }
#else
    trace(g_tracepal[n & 15]);
#endif
}

/* 例外時にフォルト PC / アクセスアドレスをニブル色で点滅表示する。
 *   プロトコル(ループ): 白(同期,長) → kind を1色 → 黒(区切) →
 *     PC 8ニブル(MSB先) → 黒(区切) → addr 8ニブル → (繰り返し)
 *   各ニブルは g_tracepal[nibble] 色を約1秒。0.5秒間隔のバースト撮影で復号する。 */
static void fdelay(unsigned units)            /* おおよそ units×0.15秒 のビジー待ち */
{
    for (unsigned u = 0; u < units; u++)
        for (volatile unsigned i = 0; i < 16000u; i++) { }
}
void GEN_fault(int kind, unsigned addr, unsigned pc)
{
    __asm__ volatile ("move.w #0x2700,%sr");  /* 割り込み禁止: VBlank 再入で点滅が止まるのを防ぐ */
#if defined(GEN_BOOT_E1M1) && defined(GEN_PC_NIBBLE)
    /* 不正命令(kind=2)の PC の第 GEN_PC_NIBBLE ニブルを単色固定表示(MSB=7..LSB=0)。 */
    if (kind == 2) { trace(g_tracepal[(pc >> (GEN_PC_NIBBLE * 4)) & 15]); for(;;){} }
#endif
#if defined(GEN_BOOT_E1M1) && defined(GEN_ILL_PHASE)
    /* 不正命令(kind=2)で backdrop を変えずに停止 → 直前の RDBG 色が残り、
     * どの描画フェーズ(BSP/DrawPlanes/DrawMasked)で wild jump したか判別。 */
    if (kind == 2) { for(;;){} }
#endif
#if defined(GEN_BOOT_E1M1) && defined(GEN_ILL_STACKWM)
    /* 不正命令(kind=2)時にスタック高水位を判定。例外時 SP は巻き戻り済だが、
     * crt0 のペイント残りから描画中の最深点を読む。赤=底到達(オーバーフロー)/黄/緑。 */
    if (kind == 2) { extern void GEN_stack_check(void); GEN_stack_check(); for(;;){} }
#endif
    /* まず例外種別を「単色固定」で表示(点滅前)。例外が起きたか/種別を一発判別:
     * bus=シアン / addr=白 / ill=灰 / div=橙 / other=色15。これらは GEN_trace 通常色と
     * 衝突しない(青0/暗紫12 と区別可)。確認後にニブル点滅へ。 */
    /* GEN_trace パレット(0,6,8,E のみ)と衝突しない奇数ニブル色で例外種別を表示:
     * bus=0x0C0C紫 / addr=0x0CC0シアン緑 / ill=0x000C赤 / div=0x0CC0... → 一意化 */
    static const u16 kc[5] = { 0x0C0C, 0x0CC0, 0x000C, 0x0AA0, 0x00CA };
    trace(kc[(unsigned)kind % 5]); fdelay(4);
    for (;;) {
        trace(0x0EEE); fdelay(8);             /* 白: 同期(長, サイクル先頭マーカー) */
        for (int s = 28; s >= 0; s -= 4) { trace(g_tracepal[(pc >> s) & 15]); fdelay(3); }  /* PC 8ニブル MSB先 */
        trace(0x0000); fdelay(4);             /* 黒: 末尾区切 */
    }
}

/* --- スタック高水位チェック: crt0 が [0xFFFA00..0xFFFFF0) を 0xA5 で塗った。
 *     スタックは 0xFFFFFE から下へ伸びるので、下から上へ走査して最初に
 *     0xA5 でないバイト = 最深到達点(high-water)。peak = 0xFFFFFE - hw。
 *     緑=安全(<1KB) / 黄=逼迫(1KB〜) / 赤=底到達(ゾーンヒープ侵食の危険)。 --- */
void GEN_stack_check(void)
{
    const unsigned long base = 0x00FFFA00, top = 0x00FFFFFE;
    unsigned long hw = base;
    for (unsigned long a = base; a < 0x00FFFFF0; a++) {
        if (*(volatile unsigned char*)a != 0xA5) { hw = a; break; }
    }
    if (hw == base) trace(0x000E);              /* 赤: 底=ヒープ侵食の危険 */
    else if ((top - hw) >= 1024) trace(0x00EE); /* 黄: 1KB超 */
    else trace(0x00E0);                          /* 緑: 安全 */
}

/* VBlank フック(crt0 _vblank から毎フレーム呼ばれる)。非計測ビルドでは実質空。
 * 計測ビルドではハング中でも(VBlank は割り込みで生きる)一定時間後に高水位を読む。 */
void GEN_vblank_tick(void)
{
#if defined(GEN_BOOT_E1M1) && defined(GEN_STACKWM)
    extern volatile int g_vblank;
    extern void GEN_stack_check(void);
    if (g_vblank == 180) { GEN_stack_check(); for(;;){} }   /* 約3秒後に読む */
#endif
}

/* 計測用: 8bit 値を「白(同期)→上位ニブル→下位ニブル→黒」でループ表示。
 * burst で2ニブルを復号して読む(GEN_fault と同じ要領)。 */
void GEN_show_u8(unsigned v)
{
    __asm__ volatile ("move.w #0x2700,%sr");   /* 割り込み禁止(点滅安定) */
    for (;;) {
        trace(0x0EEE); fdelay(6);                          /* 白: 同期(長) */
        trace(g_tracepal[(v >> 4) & 15]); fdelay(4);       /* 上位ニブル */
        trace(g_tracepal[v & 15]);        fdelay(4);       /* 下位ニブル */
        trace(0x0000); fdelay(4);                          /* 黒: 区切 */
    }
}

unsigned short* I_GetBackBuffer(void)  { return (unsigned short*)g_fb; }
unsigned short* I_GetFrontBuffer(void) { return (unsigned short*)g_fb; }

void I_InitScreen_e32(void)
{
    GEN_VideoInit();
    GEN_SetPalette16(asset_cram16);
    trace(0x0000);                           /* backdrop=黒: index0(透明)画素を黒に */
#if defined(GEN_BOOT_E1M1) && defined(GEN_DBGSTAGE)
    { extern void GEN_DbgInit(const u16*); GEN_DbgInit(g_tracepal); }   /* 左下に段表示スプライト */
#endif
}

void I_CreateBackBuffer_e32(void) {}
int  I_GetVideoWidth_e32(void)    { return SCREENWIDTH; }
int  I_GetVideoHeight_e32(void)   { return SCREENHEIGHT; }
void I_SetPallete_e32(const byte* p) { (void)p; }   /* パレットは固定(asset_cram16) */
/* --- Genesis 3ボタンパッド(ポート1) → Doom 入力 ---
 * D-pad=移動/旋回, A=use(+run), B=fire, C=ストレイフ右, Start=menu。
 * I_StartTic(毎tic)から呼ばれ、前回状態とのエッジで ev_keydown/keyup を D_PostEvent。
 * ボタンは active-low(0=押下)。TH(bit6)をトグルして上段(U D L R B C)/下段(A Start)を読む。 */
#define PAD1_DATA (*(volatile u8*)0xA10003)
#define PAD1_CTRL (*(volatile u8*)0xA10009)
static unsigned GEN_ReadPad1(void)
{
    PAD1_CTRL = 0x40;                       /* TH を出力に */
    PAD1_DATA = 0x40; __asm__ volatile("nop\n\tnop\n\tnop\n\tnop");
    u8 hi = PAD1_DATA;                       /* TH=1: b0=U b1=D b2=L b3=R b4=B b5=C */
    PAD1_DATA = 0x00; __asm__ volatile("nop\n\tnop\n\tnop\n\tnop");
    u8 lo = PAD1_DATA;                       /* TH=0: b4=A b5=Start */
    PAD1_DATA = 0x40;
    unsigned b = 0;
    if (!(hi & 0x01)) b |= 1u<<0;   /* Up    */
    if (!(hi & 0x02)) b |= 1u<<1;   /* Down  */
    if (!(hi & 0x04)) b |= 1u<<2;   /* Left  */
    if (!(hi & 0x08)) b |= 1u<<3;   /* Right */
    if (!(hi & 0x10)) b |= 1u<<4;   /* B     */
    if (!(hi & 0x20)) b |= 1u<<5;   /* C     */
    if (!(lo & 0x10)) b |= 1u<<6;   /* A     */
    if (!(lo & 0x20)) b |= 1u<<7;   /* Start */
    return b;
}
void I_ProcessKeyEvents(void)
{
    static const int keymap[8] = {
        KEYD_UP, KEYD_DOWN, KEYD_LEFT, KEYD_RIGHT,
        KEYD_B,  KEYD_R,    KEYD_A,    KEYD_START
    };
    static unsigned prev = 0;
    unsigned cur = GEN_ReadPad1();
    unsigned changed = cur ^ prev;
    if (changed) {
        extern void D_PostEvent(event_t*);
        for (int i = 0; i < 8; i++)
            if (changed & (1u<<i)) {
                event_t ev;
                ev.type  = (cur & (1u<<i)) ? ev_keydown : ev_keyup;
                ev.data1 = keymap[i];
                ev.data2 = ev.data3 = 0;
                D_PostEvent(&ev);
            }
    }
    prev = cur;
}
int  I_GetTime_e32(void)          { return 0; }
void I_Quit_e32(void)             { for(;;) {} }

static int g_cleared = 0;
void I_FinishUpdate_e32(const byte* src, const byte* pal,
                        unsigned int w, unsigned int h)
{
    (void)pal; (void)h;
#if defined(GEN_BOOT_E1M1) && defined(GEN_CHECK_FB)
    /* g_fb(=src)に可視画素(非ゼロ)があるか確認 → 空出力の切り分け。緑=内容あり/赤=全ゼロ。
     * 最初の~20フレーム(タイトル前/ロード)は飛ばし、E1M1 描画フレームのみ判定。 */
    {
        static int fbframe = 0;
        if (++fbframe > 20) {
            unsigned nz = 0;
            for (unsigned i = 0; i < (unsigned)(SCREENWIDTH * GEN_FB_H); i++)
                if (((const u8*)src)[i]) { if (++nz > 64) break; }
            trace(nz > 64 ? 0x00E0 : 0x000E);
        }
    }
#endif
    if (!g_cleared) { GEN_ClearPlaneA(); g_cleared = 1; }
    /* 120x64(3Dビュー)を横2倍・縦2倍=240x128 で中央(col=1,row=6)へ。下部はHUD/黒帯。 */
    GEN_BlitIndexed((const u8*)src, 1, (int)w, GEN_FB_H, 1, 6, asset_pal_lut, 1, 2, 2);
#if defined(GEN_BOOT_E1M1) && defined(GEN_FPSMEAS)
    /* 10秒(600 VBlank)窓のフレーム数を数えて表示。fps = 値/10。最初の1秒(ロード)は除外。 */
    {
        extern volatile int g_vblank; extern void GEN_show_u8(unsigned);
        static unsigned f = 0, t0 = 0;
        if (g_vblank > 60) {
            if (!t0) t0 = (unsigned)g_vblank;
            f++;
            if ((unsigned)g_vblank - t0 >= 600) GEN_show_u8(f);
        }
    }
#endif
#if defined(GEN_BOOT_E1M1) && defined(GEN_HEARTBEAT)
    /* フレーム完走の心拍: ブリット後に backdrop を 1 フレームごと巡回させる。
     * burst で色が変われば「描画ループは回っている(=blue はハングでなく表示残留)」、
     * 固定色なら本当に描画内でハング、と切り分ける。 */
    { static int hb = 0; GEN_trace(hb++ & 15); }
#endif
}

void I_Error(const char* error, ...)
{
    (void)error;
#ifndef GEN_BOOT_E1M1
    trace(TRACE_RED);   /* 通常: I_Error=赤 */
#endif
    /* GEN_BOOT_E1M1 デバッグ時は背景を変えず停止 → 直前の GEN_trace 色が残り
     * P_SetupLevel のどこで I_Error に到達したかを画面色で判定できる。 */
    for(;;) {}
}

/* --- 時間源: VBlank 割り込み(crt0 _vblank)が 60Hz で加算する g_vblank。
 *     I_GetTime(非GBA) が使う clock() がこれを返す。ポーリングより堅牢で VDP 状態に非干渉。 --- */
volatile int g_vblank = 0;
clock_t clock(void) { return (clock_t)g_vblank * (CLOCKS_PER_SEC / 35); }

/* --- newlib malloc 用ヒープ: _end 〜 RAM 上限手前 から払い出し --- */
extern char _end;
static char* g_hp = 0;
void* _sbrk(int incr)
{
#ifdef GEN_SBRK_LIMIT
    char* const limit = (char*)GEN_SBRK_LIMIT; /* テスト: スタック余地を増やす(ヒープ縮小) */
#else
    char* const limit = (char*)0x00FFFA00;   /* 元に戻す(ゾーン41KB維持) */
#endif
    char* p;
    if (!g_hp) g_hp = &_end;
    if (g_hp + incr > limit) return (void*)-1;
    p = g_hp;
    g_hp += incr;
#if defined(GEN_BOOT_E1M1) && defined(GEN_ZERO_HEAP)
    /* テスト: 払い出すヒープをゼロ化(host のクリーン環境を模倣)。これで描画が
     * 安定すれば未初期化メモリ(Z_Malloc 非Calloc 等)が破損の原因と確定。 */
    { char* q = p; int n = incr; while (n-- > 0) *q++ = 0; }
#endif
    return p;
}
