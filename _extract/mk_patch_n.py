# mk_patch_n.py - N generation (LAST pupil probes):
# Layout reality (V3 template scan): 0x3B=01, 0x3E=01 are the ONLY two IDs in this zone (b41.. all 00)
#  => pool holds 4 data slots + 1 center value, i.e. APS-C 5-point form; FULL-FRAME 9B has NO extra slots
#  => 9-byte form needs a code-level new-frame patch (deferred). M verdict said: REV > FWD (real direction),
#  REV+peak ~ K4 (no stable additive). N = last sharpening of this axis:
#   N1: REV with b38=0x00 (MSB-selector experiment: keep ID-2 group's value, blank group-1 data,
#       MSB of FIRST byte=0 => maybe body only parses group starting after ID1?)
#   N2: K4 + MSB=1 vignetting-selector probe (answer "does selector semantics exist on EA9 at all")
import struct, shutil, os

d0 = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
P = {s: N05B + int(s, 16) for s in ("2E", "30", "31", "32", "33", "34", "35", "38", "39", "3A", "3B", "3C", "3D", "3E")}
assert d0[P["3B"]] == 0x01 and d0[P["3E"]] == 0x01 and d0[P["30"]] == 0xA0

REV = [0x4A, 0x4C, 0x4D, 0x4E, 0x4F]   # M2/M4 direction (b38,39,3A,3C,3D)

jobs = [
    ("N1", "26.1.0", 0x38, [(P["38"], 0x00), (P["39"], REV[1]), (P["3A"], REV[2]),
                             (P["3C"], REV[3]), (P["3D"], REV[4])]),          # blank first value, keep b30=160
    ("N2", "26.2.0", 0x39, [(P["30"], 0x88), (P["38"], 0xCF)]),               # K4 + MSB=1 selector probe
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E

def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF

def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF; a[off+ln-2] = (c >> 8) & 0xFF

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, edits in jobs:
    a = bytearray(d0)
    for off, bv in edits:
        a[off] = bv
    assert a[P["3B"]] == 0x01 and a[P["3E"]] == 0x01
    a[I07B+6] = nib
    raw = b"TECHART LM-EA9-" + tag.encode()
    a[I3FB+1:I3FB+19] = raw + bytes(18 - len(raw))
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 pupil last probes %s VER %s" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%d ck_ok=%s  b2E..34=%s b38..3F=%s" % (tag, ver, diff, ok_ck,
          b[N05B+0x2E:N05B+0x35].hex(" "), b[N05B+0x38:N05B+0x40].hex(" ")))
