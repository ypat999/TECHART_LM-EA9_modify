# re_d2c_xref.py - locate every caller/consumer of fn@0x6D2C (the x10 converter) + focal-length table probe
# D-gen verdict side-discovery: body focal display F6.3 -> 44/56/64/80mm == 40*N/10 exact
#   => focal reporting rides the SAME xN chain => 0x6D2C is a shared converter (or focal derived from it).
import struct

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d = open(BIN, "rb").read()
N = len(d)

# ---- 1) immediate-form BL scan (Thumb2 32-bit bl) targeting 0x6D2C (even) or 0x6D2D (thumb-bit) ----
hits = []
for off in range(0, N - 4, 2):
    hw = struct.unpack_from("<H", d, off)[0]
    if not (0xF000 <= hw <= 0xF7FF):
        continue
    hw2 = struct.unpack_from("<H", d, off + 2)[0]
    if not (0xF800 <= hw2 <= 0xFBFF):
        continue
    s = (hw >> 10) & 1
    i1 = (hw >> 1) & 0x3FF
    i2 = (hw2 >> 1) & 0x7FF
    imm = (i2 | (i1 << 11) | (s << 22))
    if s:
        imm -= (1 << 23)
    pc = BASE + off
    tgt = pc + 4 + imm * 2
    if tgt in (0x6D2C, 0x6D2D):
        hits.append((pc, tgt))
print("BL->0x6D2C immediate hits:", ["%04X->%04X" % h for h in hits] or "none")

# ---- 2) literal pools containing 0x00006D2C / 0x6D2D (blx via ldr) ----
import re
for pat, name in [(struct.pack("<I", 0x6D2C), "0x6D2C"), (struct.pack("<I", 0x6D2D), "0x6D2D")]:
    for m in re.finditer(re.escape(pat), d):
        a = BASE + m.start()
        print("literal %s @ %04X (offset %04X)" % (name, a, m.start()))

# ---- 3) full disasm of fn@0x6D2C..0x6D90 (understand args: what feeds r2/r0) ----
from capstone import *
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = False
print("\n=== fn@0x6D2C full body ===")
for ins in md.disasm(d[0x6D2C-BASE:0x6DA0-BASE], 0x6D2C):
    print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))

# ---- 4) focal-length table probe: halfword 400(0x190, 0.1mm units) and 4000(0xFA0) in flash tables ----
print("\n=== halfword 0x0190(400) sites ===")
for off in range(0, N - 2, 2):
    if struct.unpack_from("<H", d, off)[0] == 400:
        print("  %04X (region=%s)" % (BASE + off, "code" if off < 0x4A0C - BASE else "tables"))
