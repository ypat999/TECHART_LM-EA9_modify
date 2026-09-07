# mk_patch_m.py - M generation: AUTHOR-CONFIRMED encoding of 05 body[38..43] (xhs comment thread):
#   TWO data groups rotate in these 6 bytes, selected by MSB (bit7) of FIRST byte: 1=vignetting(shading),
#   0=pupil-magnification. b3B holds "ED" data per insider 深圳牛马科技; our I1 bricked it by zeroing
#   b3B(01) AND writing 0xA0 to b3A (MSB=1 = flipped the selector!). Full-frame needs 9 bytes, APS-C 6!
# Hypothesis: 5 pupil values live at b38,b39,b3A,b3C,b3D with b3B=01 & b3E=01 as group IDs (untouchable),
#   /64 fixed point (author's 1.24..1.16 = 79,78,77,76,74 ALL <0x80 => MSB=0 => pupil group - self-consistent).
# K4(136) = confirmed b30 peak (L verdict). M3/M4 = K4 + this region (max plausibility stack).
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
b30  = N05B + 0x30
P38, P39, P3A, P3B, P3C, P3D, P3E = [N05B + k for k in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E)]
assert d0[P3B] == 0x01 and d0[P3E] == 0x01 and d0[b30] == 0xA0   # IDs intact, peak byte original

FWD = [0x4F, 0x4E, 0x4D, 0x4C, 0x4A]           # 1.24,1.22,1.20,1.18,1.16 @/64 center->edge
REV = FWD[::-1]                                 # reversed order probe

def slots(vals):
    return [(P38, vals[0]), (P39, vals[1]), (P3A, vals[2]), (P3C, vals[3]), (P3D, vals[4])]

jobs = [
    ("M1", "25.1.0", 0x34, slots(FWD)),                          # pure author-fill (b30 stays 160)
    ("M2", "25.2.0", 0x35, slots(REV)),                          # reversed order
    ("M3", "25.3.0", 0x36, slots(FWD) + [(b30, 0x88)]),          # author-fill + K4 peak = max bet
    ("M4", "25.4.0", 0x37, slots(REV) + [(b30, 0x88)]),          # reversed + K4 peak
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
    assert a[P3B] == 0x01 and a[P3E] == 0x01                     # IDs MUST survive
    assert all(a[p] < 0x80 for p in (P38, P39, P3A, P3C, P3D))   # MSB=0 everywhere = pupil group
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 author-encoding pupil fill %s VER %s" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%d ck_ok=%s  b38..3F=%s b30=%02X" % (tag, ver, diff, ok_ck,
          b[N05B+0x38:N05B+0x40].hex(" "), b[b30]))
