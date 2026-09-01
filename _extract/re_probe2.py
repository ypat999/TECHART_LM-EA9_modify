import struct
from capstone import *

path = r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin"
data = open(path, "rb").read()
n = len(data)
BASE = 0x6000
def fo(a): return a - BASE

# frame table lives at file 0x49D4..0x4E20  => address 0xA9D4..0xAE20
TBL_LO, TBL_HI = 0xA900, 0xAECC
print("== pointers to frame-table (addr 0xA900..0xAECC) ==")
ptrs = []
for off in range(0, n - 3, 4):
    w = struct.unpack_from("<I", data, off)[0]
    if TBL_LO <= w <= TBL_HI:
        ptrs.append((off, w))
        print("  @0x%04X (addr %04X) -> 0x%04X" % (off, BASE + off, w))

# also halfword / byte-aligned scan (literal pools sometimes odd)
print("\n== any-alignment ptrs to table ==")
seen = set()
for off in range(0, n - 3):
    w = struct.unpack_from("<I", data, off)[0]
    if TBL_LO <= w <= TBL_HI and off not in [p[0] for p in ptrs]:
        if (w not in seen):
            print("  @0x%04X -> 0x%04X" % (off, w)); seen.add(w)

# disassemble functions referenced by vectors that look like the protocol handler
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
def disasm(addr, cnt=60, label=""):
    a = addr & ~1
    print("\n== %s @ 0x%04X (foff 0x%04X) ==" % (label, a, fo(a)))
    c = 0
    for ins in md.disasm(data[fo(a):fo(a)+cnt*4], a):
        note = ""
        if ins.mnemonic.startswith("bl") or ins.mnemonic == "b":
            note = "   ;->" + ins.op_str
        print("  %04X  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))
        c += 1
        if c >= cnt: break

# vec20/21/22/26/31/32/35 are real ISRs; dump a couple
for name, a in [("vec20", 0x7651), ("vec22", 0x7505), ("vec26", 0x7DF9)]:
    disasm(a, 40, name)
