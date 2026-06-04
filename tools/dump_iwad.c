/* doom1.c の doom_iwad[] を実バイナリ WAD として書き出す(ホスト用)。
 * strip_wad.py の入力を生成するため。 */
#include <stdio.h>
extern const unsigned char doom_iwad[];
extern const unsigned int  doom_iwad_len;
int main(int argc, char** argv)
{
    const char* out = argc > 1 ? argv[1] : "doom1_proc.wad";
    FILE* f = fopen(out, "wb");
    if (!f) return 1;
    fwrite(doom_iwad, 1, doom_iwad_len, f);
    fclose(f);
    printf("wrote %s (%u bytes)\n", out, doom_iwad_len);
    return 0;
}
