# mk_patch_e.py - E generation: open the "one-shot gate" inside fn@0x6D2C so the travel ledger
# (which physically increments during motor phases) refreshes the 0x05 cur/tgt slots EVERY CALL.
# Rationale (sig_conv/sig_rounds analysis 2026-09-05): body polls lens at ~60Hz and re-reads
# self-reported position each round; Viltrox af50 shows cur converging frame-by-frame (5824->5568->4544)
# while LM-EA9 reports frozen template until motor-completion gate opens once (current==target, no glide).
# E1 = 0x6D32 `beq #0x6d56`(0xD010) -> `nop`(0xBF00): never early-return => refresh on every call.
#      (self-clear strb at 0x6D34-0x6D38 left intact: harmless.)
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
GATE_BR = 0x6D32   # file offset 0xD32

d0 = open(BIN, "rb").read()
assert len(d0) == 20172
orig = struct.unpack_from("<H", d0, GATE_BR - BASE)[0]
assert orig == 0xD010, hex(orig)   # beq #0x6d56

def h(v): return struct.pack("<H", v)
NOP = h(0xBF00)

jobs = [
    ("E1", "17.1.0", 0x61, [(GATE_BR, NOP)]),                       # gate always-open
    ("E2", "17.2.0", 0x62, [(GATE_BR, NOP),                          # E1 + x12 (stack C2 hint)
                             (0x6D42, h(0x1893) + h(0x189B) + h(0x009B))]),
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
        "LM-EA9 code-patch %s VER %s (gate-open per-call position refresh, base=V3)" % (tag, ver))
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
    print("\n%s disasm 0x6D2C..0x6D56:" % tag)
    for ins in md.disasm(b[0x6D2C-BASE:0x6D58-BASE], 0x6D2C):
        print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
