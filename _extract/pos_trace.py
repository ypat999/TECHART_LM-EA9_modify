# pos_trace.py - disassemble every code site referencing the 0x06-frame RAM buffer
import struct
from capstone import *

d = open(r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin", "rb").read()
BASE = 0x6000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
TARGET = 0x20000494

sites = []
for off in range(0, len(d) - 3):
    if struct.unpack_from("<I", d, off)[0] == TARGET:
        sites.append(BASE + off)
print("literal sites:", [hex(s) for s in sites])

for s in sites:
    fo = s - BASE
    start = max(0, fo - 0x70)
    print("\n======== literal @0x%04X  (context 0x%04X..0x%04X) ========" % (s, BASE + start, BASE + fo + 0x50))
    for ins in md.disasm(d[start:min(len(d), fo + 0x50)], BASE + start):
        note = ""
        if ins.mnemonic.startswith("str") and (", #6]" in ins.op_str or ", #7]" in ins.op_str or ", #8]" in ins.op_str or ", #0x1a]" in ins.op_str):
            note = "   <==POS-WRITE"
        if ins.mnemonic.startswith("ldr") and ("#6]" in ins.op_str or "#8]" in ins.op_str or "#0xa]" in ins.op_str) :
            note += "   [pos-read?]"
        print("  %04X %-9s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))
