# mk_patch_f.py - F generation: INDEPENDENT focal-declaration offsets (user: "focal dev too large affects focus-in").
# Target: norm05 body+0x18/+0x1A LE16 double-copy = 400 (40.0mm, rides the xN chain: 400*N/100 mm display).
# F1: 400->280 (declare 28mm, judgment-window-loosening hypothesis)   F2: 400->700 (opposite direction control)
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
N05, N05L, N05B = 0x4B7C, 105, 0x4B82
SLOT1, SLOT2 = N05B + 0x18, N05B + 0x1A

d0 = open(BIN, "rb").read()
assert len(d0) == 20172
assert struct.unpack_from("<H", d0, SLOT1)[0] == 400
assert struct.unpack_from("<H", d0, SLOT2)[0] == 400

jobs = [
    ("F1", "18.1.0", 0x63, 280),
    ("F2", "18.2.0", 0x64, 700),
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
    assert len(raw) <= 18
    return raw + bytes(18 - len(raw))

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, foc in jobs:
    a = bytearray(d0)
    struct.pack_into("<H", a, SLOT1, foc)
    struct.pack_into("<H", a, SLOT2, foc)          # keep double-copy aligned (T1 lesson)
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05, N05L)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 focal-decl patch %s VER %s (norm05 40mm->%d.%dmm, base=V3)" % (tag, ver, foc//10, foc%10))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05, N05L)))
    got1, got2 = struct.unpack_from("<H", b, SLOT1)[0], struct.unpack_from("<H", b, SLOT2)[0]
    print("%s ver=%s foc=%d/%d diff=%d ck_ok=%s" % (tag, ver, got1, got2, diff, ok_ck))
