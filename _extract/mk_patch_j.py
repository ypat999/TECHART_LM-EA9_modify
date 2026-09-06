# mk_patch_j.py - J generation: ride the I7 hit. b30 (low byte of u16 @norm05 body b30..31,
# orig 0x00A0=160) -> 0x80=128 gave "明显加快+更好" (first solid positive on pupil axis, §11.3ag).
# b2E axis was murky (I5 worse / I6 ~baseline); I8 combo lacked b30. => J = b30 peak-search + combo.
# Gradient: 0xA0(160 orig) | 0x90(144) | 0x80(128 = I7 HIT) | 0x70(112) | 0x60(96).
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
b2E, b30, b33, b34 = N05B+0x2E, N05B+0x30, N05B+0x33, N05B+0x34
assert d0[b2E] == 0x18 and d0[b30] == 0xA0 and d0[b33] == 0x20 and d0[b34] == 0x50

jobs = [
    ("J1", "22.1.0", 0x29, [(b30, 0x70)]),                        # deeper than hit (112)
    ("J2", "22.2.0", 0x2A, [(b30, 0x60)]),                        # deepest probe (96)
    ("J3", "22.3.0", 0x2B, [(b30, 0x90)]),                        # shallower control (144) - curve shape
    ("J4", "22.4.0", 0x2C, [(b30, 0x80), (b33, 0x18), (b34, 0x48)]),  # hit + neighbor gradient (I7+I8 rest)
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E

def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF

def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF; a[off+ln-2] = (c >> 8) & 0xFF

def name18(tag):
    raw = b"TECHART LM-EA9-" + tag.encode()
    return raw + bytes(18 - len(raw))

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, edits in jobs:
    a = bytearray(d0)
    for off, bv in edits:
        a[off] = bv
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 pupil b30 peak-search %s VER %s (base=V3, riding I7 hit)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%d ck_ok=%s  b2E..34=%s" % (tag, ver, diff, ok_ck, b[N05B+0x2E:N05B+0x35].hex(" ")))
