#!/usr/bin/env python3
import sys


def main():
    if len(sys.argv) != 5:
        print("usage: bin_to_c.py input.bin output_base symbol header_guard", file=sys.stderr)
        return 2
    data = open(sys.argv[1], "rb").read()
    base = sys.argv[2]
    symbol = sys.argv[3]
    guard = sys.argv[4]
    with open(base + ".h", "w") as f:
        f.write(f"#ifndef {guard}\n#define {guard}\n\n")
        f.write("typedef unsigned char u8;\ntypedef unsigned int u32;\n\n")
        f.write(f"extern const u8 {symbol}[];\n")
        f.write(f"extern const u32 {symbol}_len;\n\n")
        f.write(f"#endif /* {guard} */\n")
    with open(base + ".c", "w") as f:
        f.write(f"#include \"{base.split('/')[-1]}.h\"\n\n")
        f.write(f"const u8 {symbol}[] __attribute__((aligned(2))) = {{\n")
        for i in range(0, len(data), 12):
            chunk = ", ".join(f"0x{b:02x}" for b in data[i:i + 12])
            f.write(f"    {chunk},\n")
        f.write("};\n")
        f.write(f"const u32 {symbol}_len = {len(data)}u;\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
