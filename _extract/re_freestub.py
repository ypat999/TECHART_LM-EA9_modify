# re_freestub.py - find code-segment padding suitable for a ~48-byte H-gen stub (interpolation trampoline).
# Also decode the 0x6CC0 dispatch-handler literals (0x6D12..0x6D2A) and 0x701C vicinity (state base confirm).
import struct

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d = open(BIN, "rb").read()

# 1) runs of >=32 bytes of 0x00 or 0xFF inside code area [0x6000, table_start=0x6000+0x49D4)
code_end = 0x49D4  # file offset of first frame table (norm06#1) - tables from here
runs = []
i = 0
while i < code_end - 32:
    b = d[i]
    if b in (0x00, 0xFF):
        j = i
        while j < code_end and d[j] == b:
            j += 1
        if j - i >= 32:
            runs.append((BASE + i, j - i, hex(b)))
        i = j
    else:
        i += 1
print("free runs >=32B in code area:")
for a, l, v in runs:
    print("  @%04X len=%d fill=%s" % (a, l, v))

# 2) literal words at 0x6D12..0x6D2E (dispatch handlers) and 0x7010..0x7060 (state-base area)
def words(lo, hi):
    for a in range(lo, hi, 4):
        print("  %04X = %08X" % (a, struct.unpack_from("<I", d, a - BASE)[0]))
print("\nliterals 0x6D12..0x6D2E:")
words(0x6D14, 0x6D2C)
print("literals 0x7010..0x7060:")
words(0x7010, 0x7060)

# 3) disasm the three dispatch handlers heads to see their return semantics (r0 = target?)
from capstone import *
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
def dis(lo, hi, note):
    print("\n=== %s ===" % note)
    for ins in md.disasm(d[lo - BASE:hi - BASE], lo):
        print("  %04X %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
for tgt, note in [(0x5A94, "handler cmd 0x24"), (0x5B98, "alt?"), (0x5C08, "alt?"), (0x8E28, "handler cmd 0x1B big")]:
    dis(tgt, tgt + 0x30, "%s @0x%04X (first 0x30)" % (note, tgt))
