# re_frame_refs.py - 谁引用了帧模板? (修正: 镜像加载基址 BASE=0x6000, 文件偏移 +0x6000 = VA,
# 之前按文件偏移搜字面量所以零命中。norm05 文件@0x4B7C => VA 0xAB7C, 载荷 pl[0] => 0xAB82)
# 目标: 找出 (a) 所有指向帧表区的 ldr [pc,#imm] 及其所属函数, (b) 05 帧载荷 pl[24]/pl[44..52]
#       这些偏移是被"整帧 memcpy"还是"逐字段计算写入"——这决定静态 patch 到底有没有救。
import struct
from capstone import *

BIN = r"d:\work\techart\patches\EA9-V3.bin"
BASE = 0x6000
d = open(BIN, "rb").read()
N = len(d)
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

LO, HI = 0xA900, 0xAF00        # 帧模板区 VA 窗口


def lit(addr):
    o = addr - BASE
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else 0


refs = []
for a in range(0, N - 1, 2):
    hw = struct.unpack_from("<H", d, a)[0]
    if (hw & 0xF800) != 0x4800:          # LDR (literal) T1: 01001 Rt imm8
        continue
    imm = (hw & 0xFF) * 4
    va = a + BASE
    la = ((va + 4) & ~3) + imm
    v = lit(la)
    if LO <= v < HI:
        refs.append((va, (hw >> 8) & 7, v, la))

print("--- 指向帧模板区(0x%04X..0x%04X)的字面量引用 ---" % (LO, HI))
for va, rt, v, la in refs:
    tag = ""
    for name, off in (("norm05", 0x4B7C), ("norm05+pl", 0x4B82), ("init07", 0x4A38),
                      ("init3F", 0x4C08), ("norm06", 0x49D4), ("init05b", 0x4B5C)):
        if v in (off + BASE, off + BASE + 6):
            tag = " <== %s" % name
    print("  code@0x%04X  ldr r%d,[pc] -> 0x%04X (file 0x%04X)%s" % (va, rt, v, v - BASE, tag))
print("total:", len(refs))

# 每个引用点所在函数的上下文反汇编(找 memcpy/逐字段写)
FUNC_STARTS = (0x6134, 0x6D2C, 0x6CC0, 0x6F48)
print("\n--- 引用点附近指令(前后 12 条) ---")
shown = set()
for va, rt, v, la in refs:
    key = va // 0x40
    if key in shown:
        continue
    shown.add(key)
    lo, hi = va - 24, va + 24
    print("\n@@ 0x%04X (载荷 pl 目标 0x%04X)" % (va, v))
    for ins in md.disasm(d[lo - BASE:hi - BASE], lo):
        ann = ""
        if ins.mnemonic == "ldr" and "[pc," in ins.op_str:
            try:
                im = int(ins.op_str.split("#")[1], 16)
                lv = lit(((ins.address + 4) & ~3) + im)
                ann = "   ; ->0x%08X (file 0x%04X)" % (lv, lv - BASE if lv > BASE else lv)
            except Exception:
                pass
        print("   0x%04X  %-8s %-24s%s" % (ins.address, ins.mnemonic, ins.op_str, ann))
