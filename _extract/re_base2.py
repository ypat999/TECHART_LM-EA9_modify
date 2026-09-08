# re_base2.py - 定死加载基址(读向量表), 然后用正确基址重扫"谁引用帧模板区"。
# 动机: 之前按 BASE=0x6000 搜字面量零命中 => 基址猜错。文件 0x00 处若有 "00 05 00 20"(=0x20000500
# 初始 SP) 说明本 blob 自带向量表, 其 reset/NMI 立即数 = blob 的真实代码基址。
import struct

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)

print("--- 向量表(前 16 个字) ---")
for i in range(16):
    v = struct.unpack_from("<I", d, i * 4)[0]
    lbl = ["初始SP", "Reset", "NMI", "HardFault", "MPU", "BusFault", "UsageFault", "-", "-", "-", "-",
           "SVC", "DebugMon", "PendSV", "SysTick", "IRQ0"][i]
    print("  [%2d] %-10s 0x%08X" % (i, lbl, v))

rst = struct.unpack_from("<I", d, 4)[0]
for b in (0x08000000, 0x08004000, 0x08005000, 0x08006000, 0x5000, 0x6000, 0, 0x8000):
    if rst > b and rst - b < N:
        print("\n  Reset=0x%08X -> 若基址 0x%08X 则文件偏移 0x%04X" % (rst, b, rst - b))
# 常用代码地址反推: 之前认定 fn@0x6CC0/0x6D2C 是合法函数入口(以 0x...1 结尾且是 Thumb)
print("\n--- 用各候选基址检查 已知函数入口是否合法(奇数=Thumb, 且落在镜像内) ---")
for b in (0x5000, 0x6000, 0x4000, 0x08000000, 0x08004000, 0x08006000):
    ok = []
    for name, foff in (("0x4BE?", None),):
        pass
    for probe in (0xB5F8,):
        pass
    # 检查已知 Thumb 序言位置: 文件 0xCC0/0xD2C/0xF92 附近是否 push{..,lr}=0xB5xx
    cands = {"+0x6CC0(base0)": 0xCC0, "+0x6D2C(base0)": 0xD2C}
    s = []
    for k, fo in cands.items():
        hw = struct.unpack_from("<H", d, fo)[0]
        s.append("file 0x%04X hw=%04X %s" % (fo, hw, "<-push!" if (hw & 0xFF00) in (0xB400, 0xB500) else ""))
    print("  base=0x%08X : %s" % (b, " | ".join(s)))

FRAME_LO, FRAME_HI = 0x49B0, 0x4F00     # 帧模板区(文件偏移)
print("\n--- 重扫: 所有 ldr[pc] 字面量, 换算到文件偏移后落在帧模板区的 ---")
found = 0
for a in range(0, N - 1, 2):
    hw = struct.unpack_from("<H", d, a)[0]
    if (hw & 0xF800) != 0x4800:
        continue
    va_guess_bases = (0x5000, 0x6000, 0x08005000, 0x08006000, 0x4000)
    imm = (hw & 0xFF) * 4
    for b in va_guess_bases:
        va = a + b
        la = ((va + 4) & ~3) + imm
        o = la - b
        if 0 <= o <= N - 4:
            v = struct.unpack_from("<I", d, o)[0]
            for b2 in (0x0000, 0x5000, 0x6000, 0x08000000, 0x08004000, 0x08005000, 0x08006000):
                fo = v - b2
                if FRAME_LO <= fo < FRAME_HI and v > 0x1000:
                    print("  code file0x%04X (base0x%08X) -> 0x%08X = 文件 0x%04X  [%s]" % (
                        a, b2, v, fo, "norm05" if fo == 0x4B7C else
                        ("pl0/pl44" if fo in (0x4B82, 0x4BAE) else "init07" if fo in (0x4A38, 0x4A3E, 0x4A44)
                         else "init3F" if fo in (0x4C08, 0x4C0E) else "norm06" if fo == 0x49D4 else "帧区")))
                    found += 1
                break
print("  hits:", found)
