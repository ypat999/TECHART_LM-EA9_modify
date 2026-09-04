# re_ledger2.py - resolve literal pools around 0x6CC0/0x6D2C/0x6F48, xref the raw counter, TIM context
import struct
from capstone import *

d = open(r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin", "rb").read()
BASE = 0x6000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def lit(a):
    return struct.unpack_from("<I", d, a - BASE)[0]

print("== raw literal words ==")
for a in (0x6D14, 0x6D18, 0x6D1C, 0x6D20, 0x6D24, 0x6D28,
          0x6D58, 0x6D5C, 0x6D60, 0x6D64, 0x6D68,
          0x7018, 0x701C, 0x7020, 0x7024, 0x7028, 0x702C, 0x7030, 0x7034, 0x7038,
          0x703C, 0x7040, 0x7044, 0x7048, 0x704C, 0x7050, 0x7054, 0x7058, 0x705C, 0x7060):
    print("  0x%04X -> 0x%08X" % (a, lit(a)))

# blx targets of fn@0x6CC0: 6CFA ldr[pc,#0x20]->6CFE+0x20=0x6D1E?? recompute per-instruction properly
print("\n== resolve pc-relative ldr in fn windows ==")
def pc_lit(addr, off):
    pc = (addr + 4) & ~3
    return pc + off
for addr, off, lab in [(0x6CCA,0x48,'6CC0 gate struct'),(0x6CD2,0x40,''),(0x6CDA,0x3C,''),(0x6CF2,0x20,'r4'),
                       (0x6CF8,0x20,'blx1'),(0x6D00,0x1C,'blx2'),(0x6D06,0x1C,'blx3'),(0x6D0C,0x18,'blx4'),
                       (0x6D2C,0x28,'mode-gate'),(0x6D36,0x20,''),(0x6D3A,0x20,'r3-cnt-base'),(0x6D3E,0x20,'r3b'),
                       (0x6D4A,0x18,'r2-dst'),(0x6F48,0xF0,'blx-A'),(0x6F52,0xEC,'r2-src'),(0x6F60,0xE0,'blx-B'),(0x6F96,0xB4,'blx-C')]:
    la = pc_lit(addr, off)
    try:
        print("  @0x%04X -> lit@0x%04X = 0x%08X  %s" % (addr, la, lit(la), lab))
    except Exception as e:
        print("  @0x%04X -> lit@0x%04X ERR %s" % (addr, la, e))
