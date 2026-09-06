# mk_patch_h.py - H generation: make the 0x06 frame report ACTUAL travel instead of TARGET jump.
# Mechanism (re_af_engine.py 2026-09-05): main loop 0x6F92 calls AF-engine -> r0=target,
#   0x6F94 `strh r0,[state+6]`  ==> [0x20000494+6] is the TARGET (position "arrives" instantly, no motion process).
#   0x6134 mirror: ldr r3,[lit@0x6178] (=0x20000494); ldrh r2,[r3,#6]; strh->frame b[2..3]&[20..21].
# The SAME literal @0x6178 is referenced ONLY by that mirror load => repoint it to 0x20000368:
#   then [r3,#6] reads 0x2000036E = fn@0x6D2C output slot = travel-ledger x10 = ACTUAL position.
# H2 = E1(gate-open, per-call refresh) + literal repoint = full "honest trajectory" version (main shot).
# H1 = literal repoint only (gate still closed) = discriminates refresh-rate contribution.
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d0 = open(BIN, "rb").read()
assert len(d0) == 20172

LIT = 0x6178
assert d0[LIT-BASE:LIT-BASE+4] == struct.pack("<I", 0x20000494)
BEQ = 0x6D32
assert struct.unpack_from("<H", d0, BEQ - BASE)[0] == 0xD010

jobs = [
    ("H1", "20.1.0", 0x8D, [(LIT, struct.pack("<I", 0x20000368))]),
    ("H2", "20.2.0", 0x8E, [(LIT, struct.pack("<I", 0x20000368)),
                             (BEQ, struct.pack("<H", 0xBF00))]),
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
for tag, ver, nib, edits in jobs:
    a = bytearray(d0)
    for addr, by in edits:
        a[addr-BASE:addr-BASE+len(by)] = by
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 trajectory-honest %s VER %s (06 frame pos = actual ledger, base=V3)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = (sum_ck(b, I07, I07L) == struct.unpack_from("<H", b, I07+I07L-3)[0]) and \
            (sum_ck(b, I3F, I3FL) == struct.unpack_from("<H", b, I3F+I3FL-3)[0])
    print("%s ver=%s diff=%d ck_ok=%s" % (tag, ver, diff, ok_ck))

from capstone import *
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
for tag, ver, nib, edits in jobs:
    b = open(r"d:\work\techart\patches" + "\\EA9-%s.bin" % tag, "rb").read()
    print("\n%s disasm 0x6134..0x6140 (mirror with new source):" % tag)
    for ins in md.disasm(b[0x6134-BASE:0x6140-BASE], 0x6134):
        print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    print("  lit@6178=%08X" % struct.unpack_from("<I", b, LIT-BASE)[0])
