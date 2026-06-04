/* GENESIS DOOM - 映像出力層 検証ハーネス
 *
 * エンジン本体はまだ RAM 制約で起動できないため、本番の VDP 出力層
 * (plat_video.c) に「実際の Doom 画像(TITLEPIC)」を流して blastem で目視検証する。
 *   MODE_VIEW 未定義: タイトル全画面 (256x224)
 *   MODE_VIEW 定義  : ゲームビューポート (224x96) を中央配置
 */
#include "assets_gen.h"

void GEN_VideoInit(void);
void GEN_SetPalette16(const unsigned short*);
void GEN_ClearPlaneA(void);
void GEN_BlitIndexed(const unsigned char*, int, int, int, int, int,
                     const unsigned char*, int);

int main(int argc, const char* const* argv)
{
    (void)argc; (void)argv;

    GEN_VideoInit();
    GEN_SetPalette16(asset_cram16);

#ifdef MODE_VIEW
    GEN_ClearPlaneA();
    /* 224x96=28x12 を中央へ: col=(32-28)/2=2, row=(28-12)/2=8 */
    GEN_BlitIndexed(asset_title_view, 1, ASSET_VIEW_W, ASSET_VIEW_H,
                    2, 8, asset_pal_lut, 1);
#else
    /* 256x224=32x28 全画面 */
    GEN_BlitIndexed(asset_title_full, 1, ASSET_FULL_W, ASSET_FULL_H,
                    0, 0, asset_pal_lut, 1);
#endif

    for (;;) { }
    return 0;
}
