# re_ledger.py - disassemble the position-ledger chain:
#   fn@0x6CC0 (refreshes [0x20000494+6] = position, called from 0x6F92)
#   fn@0x6F48 (called after delta calc at 0x9A76 = motor drive?)
#   resolve remaining blx literal @0x6F96
import struct
from capstone import *

d = open(r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin", "rb").read()
BASE = 0x6000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def dump(lo, hi, label):
    print("\n======== %s : 0x%04X..0x%04X ========" % (label, lo, hi))
    for ins in md.disasm(d[lo-BASE:hi-BASE], lo):
        note = ""
        if ins.mnemonic.startswith("blx") or ins.mnemonic == "bl":
            note = "   ;CALL " + ins.op_str
        print("  %04X %-9s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))

dump(0x6CC0, 0x6D90, "fn@0x6CC0 position-refresh")
dump(0x6F48, 0x6F88, "fn@0x6F48 drive?")

print("\n== literal @0x704E..0x7060 (for ldr at 0x6F96 pc-rel) ==")
for a in range(0x7018, 0x7064, 4):
    print("  0x%04X -> 0x%08X" % (a, struct.unpack_from("<I", d, a-BASE)[0]))
