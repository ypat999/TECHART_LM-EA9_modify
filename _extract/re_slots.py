# re_slots.py - connect fn@0x6D2C output slots (0x2000036E/0x20000370) to the 0x05/0x06 TX buffers,
# and find the 0x05 cur/tgt write sites. Prerequisite RE for "trajectory forging" (E-gen).
# Facts: 0x6D2C writes [r1+0x1E]/[r1+0x20] (r1=[0x20000678]) AND [0x20000364+0xA]/[+0xC].
#        If [0x20000678]=0x20000350 then both pairs alias to 0x2000036E/0x20000370.
#        0x6134 mirror writes frame buffer @0x20000000 body[2..3]+[20..21] (the 0x06 frame).
import struct
from capstone import *

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d = open(BIN, "rb").read()
N = len(d)
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def lit32(addr):  # decode 4 bytes at addr as RAM pointer candidate
    v = struct.unpack_from("<I", d, addr - BASE)[0]
    return v if 0x20000000 <= v < 0x20001000 else None

# 1) all literals equal to target RAM addresses of interest
targets = {0x2000036E: "slot36E", 0x20000370: "slot370", 0x20000350: "state350",
           0x20000300: "base300", 0x20000678: "ptr678", 0x2000067C: "ptr67C",
           0x20000364: "base364", 0x20000000: "buf0"}
print("== literal occurrences ==")
for off in range(0, N - 4, 4):
    v = struct.unpack_from("<I", d, off)[0]
    if v in targets:
        print("  @%04X -> %08X (%s)" % (BASE + off, v, targets[v]))

# 2) disasm windows around every ldr-literal that fetches those addresses:
#    find insns that then ldrh/strh [#0x1e/#0x20/#0xa/#0xc] etc. We brute-force: linear disasm whole
#    code, track last ldr-loaded literal per reg, report ldrh/strh touching offsets 0x1e/0x20/0xa/0xc.
print("\n== accesses to slot offsets (track ldr literal -> ldrh/strh) ==")
code_end = 0x4A0C - BASE  # before tables (heuristic)
loaded = {}  # reg -> literal value
for off in range(0, code_end, 2):
    chunk = d[off:off + 6]
    got = list(md.disasm(chunk, BASE + off))
    if not got:
        continue
    ins = got[0]
    m, ops = ins.mnemonic, ins.op_str
    if m == "ldr" and "[pc," in ops:
        rd = ops.split(",")[0].strip()
        try:
            imm = int(ops.split("#")[1], 16)
        except Exception:
            continue
        lit_addr = ((ins.address + 4) & ~3) + imm
        v = struct.unpack_from("<I", d, lit_addr - BASE)[0] if lit_addr - BASE + 4 <= N else 0
        loaded[rd] = v
    elif (m in ("ldrh", "strh", "ldr", "str")) and ops:
        for rd, v in list(loaded.items()):
            if ("[%s," % rd) in ops or ("[%s]" % rd) in ops:
                # extract offset
                try:
                    tail = ops.rsplit("#", 1)[1]
                    offv = int(tail, 16) if tail.startswith("0x") else int(tail)
                except Exception:
                    offv = None
                if v in (0x20000350, 0x20000364, 0x20000300, 0x20000000) or (v and 0x20000000 <= v < 0x20001000):
                    if offv in (0x1e, 0x20, 0xa, 0xc, 8, 0x1a) and (v + (offv or 0)) in (
                            0x2000036E, 0x20000370, 0x20000308, 0x2000031A, 0x20000008, 0x2000001A):
                        print("  %04X %-6s %-18s  base=%08X eff=%08X" % (
                            ins.address, m, ops, v, v + (offv or 0)))

# 3) full disasm of 0x6100..0x6170 (mirror function region) to see buffer layout
print("\n== 0x6100..0x6180 ==")
for ins in md.disasm(d[0x6100 - BASE:0x6180 - BASE], 0x6100):
    print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
