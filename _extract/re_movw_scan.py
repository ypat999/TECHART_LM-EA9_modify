# re_movw_scan.py - 帧模板区没有任何 32 位字面量指向它(re_frame_refs/re_base2 已证),
# 说明代码用 MOVW/MOVT 现场拼地址(Thumb 32-bit 立即数), 而不是从字面量池取指针。
# 本脚本: 扫遍镜像找 MOVW+MOVT 指令对, 拼出 32 位值, 报告落在帧模板区(VA 0xA900..0xAF00,
# BASE=0x6000 已由向量表 Reset=0x6145 定死)的所有构造点 => 那就是"帧表访问入口"。
import struct
from capstone import *

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)
BASE = 0x6000
LO, HI = 0xA900, 0xB000
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = True

print("--- MOVW/MOVT 拼出的地址落在帧模板区的构造点 ---")
found = 0
for a in range(0, N - 6, 2):
    hw = struct.unpack_from("<H", d, a)[0]
    # MOVW.W imm16: 11110 i 0 10010 S Rd(4) imm4 | 0 imm3 Rd imm8
    if (hw & 0xFBF0) == 0xF0B0 or (hw & 0xFBF0) == 0xF0A0:
        hw2 = struct.unpack_from("<H", d, a + 2)[0]
        if (hw2 & 0xF500) == 0x0000:
            rd = ((hw & 0x000F) << 1) | ((hw2 >> 8) & 1)
            imm4 = (hw >> 16 if False else (hw >> 0)) & 0  # placeholder
            imm4 = (hw >> 10) & 0xF
            imm3 = (hw2 >> 12) & 0x7
            imm8 = hw2 & 0xFF
            val = (imm4 << 12) | (imm3 << 9) | imm8
            # 下一条是否 MOVT (11110 i 10100 1 Rd imm4)
            hw3 = struct.unpack_from("<H", d, a + 4)[0]
            hw4 = struct.unpack_from("<H", d, a + 6)[0] if a + 7 < N else 0
            if (hw3 & 0xFBF0) == 0xF2C0 and (hw4 & 0xF500) == 0x0000:
                imm4b = (hw3 >> 10) & 0xF
                val |= imm4b << 16
            if LO <= val < HI:
                print("  @file 0x%04X (VA 0x%04X): 拼出 0x%04X = 文件 0x%04X  r%d" % (
                    a, a + BASE, val, val - BASE, rd))
                found += 1
print("  hits:", found)

print("\n--- 兜底: 反汇编全码区, 从 op_str 里抠十六进制立即数(不依赖 operand API) ---")
CODE_END = 0x4900
cnt = 0
import re
for ins in md.disasm(d[0:CODE_END], BASE):
    for m in re.finditer(r"#(0x)?([0-9a-fA-F]+)", ins.op_str):
        try:
            v = int(m.group(2), 16)
        except ValueError:
            continue
        if LO <= v < HI:
            print("  0x%04X  %-8s %-28s  ; #%s -> 文件 0x%04X" % (
                ins.address, ins.mnemonic, ins.op_str, m.group(0)[1:], v - BASE))
            cnt += 1
print("  立即数命中:", cnt)

# 也扫 ADR/ADD 型 PC 相对访问: ADR T2 = 11110 i 0 10111 1 Rd imm12
print("\n--- ADR 指向帧模板区? ---")
h2 = 0
for a in range(0, CODE_END - 6, 2):
    hw = struct.unpack_from("<H", d, a)[0]
    if (hw & 0xFBFF) == 0xF8AF or (hw & 0xF01F) == 0xA000:
        va = a + BASE
        if (hw & 0xF01F) == 0xA000:          # ADR (A1) add pc + imm8*4
            tgt = ((va + 4) & ~3) + (hw & 0xFF) * 4
        else:
            hw2 = struct.unpack_from("<H", d, a + 2)[0]
            i = (hw >> 10) & 1
            imm3 = (hw2 >> 12) & 7
            imm8 = hw2 & 0xFF
            imm12 = (i << 11) | (imm3 << 8) | imm8
            tgt = ((va + 4) & ~3) + imm12
        if LO <= tgt < HI:
            print("  @file 0x%04X ADR -> 0x%04X (文件 0x%04X)" % (a, tgt, tgt - BASE))
            h2 += 1
print("  ADR 命中:", h2)

print("\n--- 对照: 帧模板真实 VA 区间 = 0x%X..0x%X (文件 0x49D4..0x4EF0 + 0x6000) ---" % (
    0x49D4 + BASE, 0x4EF0 + BASE))
