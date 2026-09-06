# re_af_engine.py - disassemble fn@0x6CC0 (AF command engine feeding [state+6]) + caller 0x6F48..0x6FA0,
# and re-verify who writes 0x20000494+6 and what the 0x06 position actually tracks.
# Context: E1(gate-open) flat + canary dead (no live focal/dist display in AF mode). Before closing the
# position-report direction entirely, must know if [state+6] already updates per-round (driven by body 0x04 cmds).
import struct
from capstone import *

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d = open(BIN, "rb").read()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def lit_at(addr):
    """resolve 4B literal pool value at addr"""
    return struct.unpack_from("<I", d, addr - BASE)[0]

def disasm(lo, hi, note):
    print("\n=== %s  (0x%04X..0x%04X) ===" % (note, lo, hi))
    for ins in md.disasm(d[lo - BASE:hi - BASE], lo):
        ann = ""
        if ins.mnemonic == "ldr" and "[pc," in ins.op_str:
            try:
                imm = int(ins.op_str.split("#")[1], 16)
                la = ((ins.address + 4) & ~3) + imm
                v = lit_at(la)
                if 0x20000000 <= v < 0x20008000:
                    ann = "   ; ->RAM %08X" % v
            except Exception:
                pass
        if ins.mnemonic in ("bl", "blx") and "#" in ins.op_str:
            try:
                ann = "   ; call %s" % ins.op_str.split("#")[-1]
            except Exception:
                pass
        print("  %04X %-8s %-22s%s" % (ins.address, ins.mnemonic, ins.op_str, ann))

disasm(0x6CC0, 0x6D2C, "fn@0x6CC0 AF engine (dispatch)")
disasm(0x6F40, 0x6FB0, "caller region 0x6F40..0x6FB0 (blx 0x6CC1 / 0x8D95, strh [r4,#6])")

# who writes/reads 0x20000494 (literal sites) - compact list
print("\n=== literal 0x20000494 sites ===")
pat = struct.pack("<I", 0x20000494)
i = 0
while True:
    j = d.find(pat, i)
    if j < 0:
        break
    print("  @%04X" % (BASE + j))
    i = j + 1
