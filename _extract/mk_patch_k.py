# mk_patch_k.py - K generation: attribute J4's possible edge (b33 vs b34 decomposition) + refine peak.
# Curve so far (b30): 160=base | 144(J3)~96(J2) | 128(I7)=PEAK* | 112(J1) unstable; J4(128+b33:18+b34:48) >= I7 maybe.
# NOTE J2(96)>J1(112) non-monotonic => either shoulder readings are noise-limited; hence also second-sample
# the shoulders 120/136 to firm the peak. All edits inside PROVEN-SAFE W2 island.
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
b30, b33, b34 = N05B+0x30, N05B+0x33, N05B+0x34
assert d0[b30] == 0xA0 and d0[b33] == 0x20 and d0[b34] == 0x50

jobs = [
    ("K1", "23.1.0", 0x2D, [(b30, 0x80), (b33, 0x18)]),           # J4 minus b34
    ("K2", "23.2.0", 0x2E, [(b30, 0x80), (b34, 0x48)]),           # J4 minus b33
    ("K3", "23.3.0", 0x2F, [(b30, 0x78)]),                        # 120 - left shoulder refine
    ("K4", "23.4.0", 0x30, [(b30, 0x88)]),                        # 136 - right shoulder refine
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
        "LM-EA9 pupil K %s VER %s (J4 attribution + peak refine, base=V3)" % (tag, ver))
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
