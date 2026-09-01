import struct
from capstone import *

path = r"d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin"
data = open(path, "rb").read()
n = len(data)
BASE = 0x6000          # app linked at 0x6000; file offset = addr - BASE
def fo(a): return a - BASE
def sane(x): return BASE <= x < BASE + n

sp, reset, nmi, hf = struct.unpack_from("<4I", data, 0)
print("SP %08X RESET %08X NMI %08X HF %08X" % (sp, reset, nmi, hf))
print("valid vectors (-> file off):")
for i in range(0, 0xC0, 4):
    w = struct.unpack_from("<I", data, i)[0]
    if sane(w):
        print("  vec%-2d -> 0x%04X (foff 0x%04X)" % (i // 4, w, fo(w)))

md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
addr = (reset & ~1)
print("\n--- reset handler @ 0x%04X (foff 0x%04X) ---" % (addr, fo(addr)))
cnt = 0
for ins in md.disasm(data[fo(addr):fo(addr) + 120], addr):
    tag = ""
    if ins.mnemonic in ("bl","blx","b","ldr") and "0x" in ins.op_str:
        tag = "   ; ref"
    print("  %04X  %-8s %s%s" % (ins.address, ins.mnemonic, ins.op_str, tag))
    cnt += 1
    if cnt > 55: break

# pointers into frame-table region, reported as table-relative
lo, hi = 0x4900, 0x4E20
print("\nword-ptrs into frame table:")
for off in range(0, n - 3, 4):
    w = struct.unpack_from("<I", data, off)[0]
    if lo <= w <= hi:
        print("  @0x%04X -> 0x%04X" % (off, w))
