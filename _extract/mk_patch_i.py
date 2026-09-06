# mk_patch_i.py - I generation: PUPIL MAGNIFICATION fill (xhs post #4/#5 breakthrough).
# Author (who has a decoded real lens firmware, unlike us): 0x05 msg bytes 38..43 = 6B,
#   u16 init + 4 x 1-byte increments = pupil magnification at center +4 more sample points
#   center->edge; range 0..2; decreases toward edge AND with distance near->far.
#   EA9 hardcodes 1.5,0,0,0,0 (his claim); he wrote 1.24,1.22,1.20,1.18,1.16 -> focus area 30%->66%.
# OUR REAL DATA (sig_pupil.py over our 5 captures): Viltrox 05 region b2E..b33 = 18 00 a0 00 00 16(EF50)/21(EFS24) 50
#   -> b2E..2F=0x0018 (24/16=1.5), b30..31=0x00A0 (160/128=1.25), b32..33 = 00 16/21 + 50 (author's "39/42th byte"!)
#   selp1650: same region all 00. => two encoding interpretations exist; offset ambiguity (whole-frame vs body-based)
#   => patch BOTH windows (W1=body[0x38..0x3D], W2=body[0x2E..0x33]) with BOTH real-data variants.
# Values:
#  P_VX (copy Viltrox EFS24 bytes):        18 00 A0 00 21 50
#  P_AU (author gradient @1/64: 1.24..1.16): F0 EC E4 DC D4 C8   (u16 240 + bytes 236,228,212,200)
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
N05, N05L, N05B = 0x4B7C, 105, 0x4B82
d0 = open(BIN, "rb").read()
assert len(d0) == 20172

# NOTE: frame tables live at FILE offsets (< BASE=0x6000); do NOT subtract BASE for them!
W1 = N05B + 0x38   # author's "38th..43rd byte" if 0-based body
W2 = N05B + 0x2E   # region located by our real-capture comparison
print("W1 orig:", d0[W1:W1+6].hex(" "))
print("W2 orig:", d0[W2:W2+6].hex(" "))

P_VX = bytes.fromhex("1800A0002150")
P_AU = bytes.fromhex("F0ECE4DCD4C8")

jobs = [
    ("I1", "21.1.0", 0x21, [(W1, P_VX)]),            # W1 + Viltrox copy (main)
    ("I2", "21.2.0", 0x22, [(W2, P_VX)]),            # W2 + Viltrox copy
    ("I3", "21.3.0", 0x23, [(W1, P_AU)]),             # W1 + author gradient
    ("I4", "21.4.0", 0x24, [(W1, P_VX), (W2, P_VX)]), # both windows VX
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
    for off, by in edits:
        a[off:off+len(by)] = by          # off is a FILE offset (frame tables)
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05, N05L)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 pupil-mag fill %s VER %s (05 b38/b2e windows, base=V3)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05, N05L)))
    print("%s ver=%s diff=%d ck_ok=%s  W1=%s W2=%s" % (tag, ver, diff, ok_ck,
          b[W1:W1+6].hex(" "), b[W2:W2+6].hex(" ")))
