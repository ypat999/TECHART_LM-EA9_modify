# mk_patch_i2r.py - I-gen round 2: SINGLE-BYTE pupil-candidate steps inside the PROVEN-SAFE W2 region
# (b2E..b33 of norm05 body). Round-1 lesson: W1(b38..43) bricked bodies (b3B=01 is a protocol flag,
# our patches zeroed it) => DO NOT touch W1 again. I2 was safe but near no-op (EA9 vs Viltrox bytes
# nearly identical there). Region truth: b2E=0x18(24 => /16=1.5  xhs author's "EA9 writes 1.5"),
# b30=0xA0(160 => /128=1.25 or /64=2.5), b33=0x20(32), b34=0x50(80 => /64=1.25).
# Round 2 = meaningful-magnitude single steps:
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
b2E, b30, b33, b34 = N05B+0x2E, N05B+0x30, N05B+0x33, N05B+0x34
assert d0[b2E] == 0x18 and d0[b30] == 0xA0 and d0[b33] == 0x20 and d0[b34] == 0x50

jobs = [
    ("I5", "21.5.0", 0x25, [(b2E, 0x14)]),                 # 1.5 -> 1.25 (/16)
    ("I6", "21.6.0", 0x26, [(b2E, 0x12)]),                 # 1.5 -> 1.125 (/16)
    ("I7", "21.7.0", 0x27, [(b30, 0x80)]),                 # 1.25 -> 1.0 (/128) at b30
    ("I8", "21.8.0", 0x28, [(b2E, 0x14), (b33, 0x18), (b34, 0x48)]),  # gradient-ish triple step
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
        "LM-EA9 pupil step2 %s VER %s (safe W2 region single bytes)" % (tag, ver))
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
