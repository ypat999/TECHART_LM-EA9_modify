# re_ram_state_map.py - 静态层翻篇的根据: 帧模板区在 app 代码里 0 引用(字面量池/MOVW-MOVT/ADR/
# 全立即数扫皆零), 说明 05/06 载荷是 RAM 里现拼的。本脚本按"已知 06 帧锚点"的方法找 05 帧缓冲:
#   1) 列出所有指向 RAM 窗口(0x20000000..0x20002AB0)的字面量及其引用者;
#   2) 对每个引用者, 在其后 160 条指令里找 strb/str [同一寄存器, #偏移], 打印被写过的偏移;
#   3) 重点看偏移 24/26(焦距) 32/38(光学行) 44/46/48/51/52(光圈家族) 是否被写 => 那就是覆写者。
import struct
from capstone import *

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)
BASE = 0x6000
RAM_LO, RAM_HI = 0x20000000, 0x20002AB0
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
CODE_END = 0x4900


def lit(file_off):
    return struct.unpack_from("<I", d, file_off)[0]


# 1) RAM 指针字面量 -> 引用它的代码位置
lit_hits = {}          # ram_addr -> [code_va...]
for a in range(0, N - 1, 2):
    hw = struct.unpack_from("<H", d, a)[0]
    if (hw & 0xF800) != 0x4800:
        continue
    imm = (hw & 0xFF) * 4
    va = a + BASE
    la = ((va + 4) & ~3) + imm
    o = la - BASE
    if 0 <= o <= N - 4:
        v = lit(o)
        if RAM_LO <= v < RAM_HI:
            lit_hits.setdefault(v, []).append(va)

print("--- RAM 基址字面量(引用者数) ---")
for v in sorted(lit_hits):
    print("  RAM 0x%08X  被 %d 处引用: %s" % (v, len(lit_hits[v]), ["0x%04X" % x for x in lit_hits[v][:6]]))

# 2) 每个引用者函数内, 用该寄存器做的 [reg,#imm] 存储偏移
WANT = {24, 25, 26, 27, 32, 38, 44, 45, 46, 47, 48, 49, 51, 52, 54, 60, 62}
print("\n--- 引用点之后 160 条指令内的 [rN,#offset] 存储 (关注 %s) ---" % sorted(WANT))
for v, codes in sorted(lit_hits.items()):
    for cva in codes:
        fo = cva - BASE
        buf = d[max(0, fo - 8):min(N, fo + 320)]
        offs = []
        for ins in md.disasm(buf, max(0, fo - 8)):
            if ins.mnemonic.startswith("str"):
                # op_str 形如 "r2, [r3, #0x2c]"
                if "[" in ins.op_str and "#0x" in ins.op_str.split("[")[1]:
                    try:
                        o = int(ins.op_str.split("[")[1].split("#")[1].split("]")[0], 16)
                    except Exception:
                        continue
                    offs.append(o)
        hot = sorted(set(o for o in offs if o in WANT))
        if hot:
            print("  RAM 0x%08X @code 0x%04X -> 写过的关注偏移: %s  (全部偏移: %s)" % (
                v, cva, hot, sorted(set(offs))[:24]))
