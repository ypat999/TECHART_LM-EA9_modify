# re_ledger3.py - xref the raw stroke counter @0x2000067C(+4 = 0x20000680), dump fn@0x8D94, fn@0x8E28
import struct
from capstone import *

d = open(r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin", "rb").read()
BASE = 0x6000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def dump(lo, hi, label):
    print("\n======== %s ========" % label)
    for ins in md.disasm(d[lo-BASE:hi-BASE], lo):
        note = ""
        if ins.mnemonic.startswith("bl"): note = "  ;CALL " + ins.op_str
        if ins.mnemonic.startswith("str"): note = "  ;W" + ins.op_str
        print("  %04X %-9s %s%s" % (ins.address, ins.mnemonic, ins.op_str, note))

# where is 0x2000067C / 0x20000680 / 0x20000678 referenced (literal scan)
targets = {0x2000067C: "cnt-base+0", 0x20000680: "cnt+4", 0x20000678: "ptr-var", 0x20000674: "nb674", 0x20000668: "nb668"}
for off in range(0, len(d) - 3):
    w = struct.unpack_from("<I", d, off)[0]
    if w in targets:
        print("lit @0x%04X = 0x%08X (%s)" % (BASE + off, w, targets[w]))

dump(0x8D94, 0x8E28, "fn@0x8D94 (second getter at 6F96)")
dump(0x8E28, 0x8EC0, "fn@0x8E28 (mode-0xF handler from 6CFA)")
