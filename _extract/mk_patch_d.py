# mk_patch_d.py - D generation: gradient refinement around the x10 position-scale (fn@0x6D2C, insns @0x6D42..0x6D47)
# C-gen verdict (M40): C0(x10-equiv)==V3 OK, C1(x8) weaker, C2(x12) edge slightly better, C3(x13) no diff.
# D-gen probes whether the x12 blip is a real peak or noise: D1 x11, D2 x14, D3 x16, D4 x20.
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
A42, A44, A46, A48 = 0x6D42, 0x6D44, 0x6D46, 0x6D48

d0 = open(BIN, "rb").read()
assert len(d0) == 20172
orig = d0[A42-BASE:A48-BASE+2]
assert orig == bytes.fromhex("9300 d218 5300 1bb2".replace(" ", "")), orig.hex()

def h(v): return struct.pack("<H", v)
MOVS = lambda n: h(0x2300 | n)          # movs r3,#n  (n<256)
MULS_r3_r2 = h(0x4353)                  # mul r3,r2   -> result in r3 (matches original tail)
NOPs = h(0x0000)                        # movs r0,r0 : value-preserving 2-byte filler
LSL_r3_r2 = lambda s: h((s << 6) | (2 << 3) | 3)   # lsls r3,r2,#s

jobs = [
    ("D1", "16.1.0", 0xF1, MOVS(11) + MULS_r3_r2 + NOPs),        # x11
    ("D2", "16.2.0", 0xF2, MOVS(14) + MULS_r3_r2 + NOPs),        # x14
    ("D3", "16.3.0", 0xF3, LSL_r3_r2(4) + NOPs + NOPs),          # x16
    ("D4", "16.4.0", 0xF4, MOVS(20) + MULS_r3_r2 + NOPs),        # x20
]

# frame helpers (offsets from cksum_scan/frame map, all asserted)
I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E

def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF

def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF; a[off+ln-2] = (c >> 8) & 0xFF
    return c

def name18(tag):
    raw = b"TECHART LM-EA9-" + tag.encode()
    assert len(raw) <= 18
    return raw + bytes(18 - len(raw))

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, repl in jobs:
    a = bytearray(d0)
    a[A42-BASE:A42-BASE+6] = repl
    a[I07B+6] = nib                                   # version probe in init07@6
    a[I3FB+1:I3FB+19] = name18(tag)                   # probe lens name
    c1 = write_ck(a, I07, I07L); c2 = write_ck(a, I3F, I3FL)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 code-patch %s VER %s (position scale, base=V3)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    # verify
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = (sum_ck(b, I07, I07L) == struct.unpack_from("<H", b, I07+I07L-3)[0]) and \
            (sum_ck(b, I3F, I3FL) == struct.unpack_from("<H", b, I3F+I3FL-3)[0])
    assert b[I3FB+1:I3FB+19] == name18(tag)
    print("%s ver=%s codebytes=%s diff=%d ck_ok=%s" % (tag, ver, b[A42-BASE:A48-BASE].hex(" "), diff, ok_ck))

# disasm check with capstone
from capstone import *
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
for tag, ver, nib, repl in jobs:
    b = open(r"d:\work\techart\patches" + "\\EA9-%s.bin" % tag, "rb").read()
    print("\n%s disasm:" % tag)
    for ins in md.disasm(b[A42-BASE:A48-BASE+2], A42):
        print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
