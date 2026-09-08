# re_base.py - 帧模板区(文件 0x49D4..0x4EF0)到底以什么 VA 被代码引用?
# 上一版按 BASE=0x6000 搜字面量零命中 => 要么数据段另有加载基址, 要么经二级描述表寻址。
# 做法: 对若干候选基址, 统计"看起来像指向本镜像的指针"的数量, 并单独报告指向
#       norm05(0x4B7C)/其 pl[0](0x4B82)/其 pl[44](0x4BAE)/init07(0x4A38) 的那些。
import struct
from collections import Counter

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)
TARGETS = {"norm05": 0x4B7C, "pl0": 0x4B82, "pl24": 0x4B9A, "pl44": 0x4BAE,
           "init07": 0x4A38, "init07b": 0x4A3E, "init3F": 0x4C08, "norm06": 0x49D4}

CAND = [0, 0x1000, 0x2000, 0x4000, 0x6000, 0x8000, 0xA000, 0xC000, 0x10000,
        0x08000000, 0x08004000, 0x08006000, 0x08008000, 0x0800C000,
        0x08010000, 0x20000000, 0x20001000, 0x10000000, 0x1FFF0000]

cnt = Counter()
for a in range(0, N - 3, 4):
    w = struct.unpack_from("<I", d, a)[0]
    for b in CAND:
        o = w - b
        if 0 <= o < N:
            cnt[b] += 1

print("--- 候选加载基址命中数(指针状字数量) ---")
for b, c in cnt.most_common(12):
    print("  base=0x%08X  count=%d" % (b, c))

print("\n--- 各基址下是否有指针精确指向关键帧 ---")
for b in CAND:
    got = []
    for name, off in TARGETS.items():
        for a in range(0, N - 3, 4):
            if struct.unpack_from("<I", d, a)[0] == b + off:
                got.append("%s@0x%04X" % (name, a))
    if got:
        print("  base=0x%08X : %s" % (b, ", ".join(got)))

# 半字(16bit)指针/偏移表: 直接找值 = 关键帧偏移本身的半字
print("\n--- 16-bit 偏移表候选(值 == 帧文件偏移) ---")
for name, off in TARGETS.items():
    hits = [a for a in range(0, N - 1, 2) if struct.unpack_from("<H", d, a)[0] == off]
    if hits:
        print("  %-8s 0x%04X : %s" % (name, off, ["0x%04X" % h for h in hits[:10]]))

# 帧区自身的头部结构: 打印 norm05 前后 128B, 看是否存在描述符数组(索引->偏移)
print("\n--- 0x49B0..0x4A00 与 0x4B40..0x4B90 原文 ---")
for lo, hi in ((0x49B0, 0x4A00), (0x4B40, 0x4B90)):
    print("  @0x%04X: %s" % (lo, d[lo:hi].hex(" ")))
