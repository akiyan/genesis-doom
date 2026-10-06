#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check table equivalence and real C tile packing; run from repository root."""
import sys
sys.dont_write_bytecode = True
import ctypes as C
import importlib.util
from pathlib import Path
import random
import subprocess
import tempfile
spec=importlib.util.spec_from_file_location('g','tools/gen_colormap16.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
lut=g.c_array('port/gen/assets_gen.c','asset_pal_lut')
wad=g.c_array('port/gen/doom_iwad_min.c','doom_iwad')
combined, fuzz=g.compose(wad,lut)
import struct
count, directory=struct.unpack_from('<II',wad,4)
for i in range(count):
    offset,size,name=struct.unpack_from('<II8s',wad,directory+16*i)
    if name.rstrip(b'\0')==b'COLORMAP':
        assert combined==bytes(lut[c] for c in wad[offset:offset+size])
        assert len(fuzz)==16 and max(fuzz)<16
        print(f'All {size} light-map entries preserve the original final color.')
        break
else:
    raise AssertionError('missing COLORMAP')
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'check.c'
    source.write_text('#include "'+str(Path('port/plat_video.c').resolve())+'"\nvoid check(const u8* p, int row, const u8* lut, u16* out) {build_indexed_row_2x2(p,120,row,lut,30,out);}\n')
    libs=[]
    for variant in ('before','after'):
        so=Path(tmp)/(variant+'.so')
        subprocess.run(['gcc','-shared','-fPIC','-O2','-DGENESIS']+(['-DGEN_PRECOMPOSE_COLORMAP'] if variant=='after' else [])+[str(source),'-o',str(so)],check=True)
        libs.append(C.CDLL(str(so)))
    rng=random.Random(68)
    original=bytes(rng.randrange(256) for _ in range(120*64))
    reduced=bytes(lut[p] for p in original)
    table=(C.c_ubyte*256).from_buffer_copy(lut)
    for row in range(16):
        outputs=[]
        for lib,data in zip(libs,(original,reduced)):
            out=(C.c_uint16*480)()
            lib.check((C.c_ubyte*len(data)).from_buffer_copy(data),row,table,out)
            outputs.append(bytes(out))
        assert outputs[0]==outputs[1],row
    print('All 16 DMA rows (15,360 bytes) match exactly after prequantization.')
