# diff_lines.py - 关键对照: V3 / K4 / P23 / 官方 1.8.0 之间到底差在哪一帧哪一字节。
# 动机: P 世代冠军(P23 = init01 @5=80 @7=00, "又准又快")全部落在 **init 类帧**, 而我这两天
# 的 I~N/O/Q 全落在 norm05(class-01 周期帧) 且 P1/P6/P7 早就测出 norm05 字段改了没反应
# => 静态 patch 的"活性区"是 init 类帧, 不是 norm 周期帧。先把各版本差异落到字节上验证。
import struct

import os

DIRS = [r"d:\work\techart\patches", r"d:\work\techart\flash_kit\product\firmware\LM-EA9"]
FILES = {"ORIG": "EA9-VER-1-8-0.bin", "P23": "EA9-P23-A5UP.bin", "V3": "EA9-V3.bin",
         "K4": "EA9-K4.bin", "Q6": "EA9-Q6.bin", "I7": "EA9-I7.bin", "O5": "EA9-O5.bin",
         "Q1": "EA9-Q1.bin", "P19": "EA9-P19-A17.bin"}
IMGS = {}
for n, fn in FILES.items():
    for dirp in DIRS:
        p = os.path.join(dirp, fn)
        if os.path.exists(p):
            IMGS[n] = open(p, "rb").read()
            break
    else:
        print("缺文件:", n, fn)
NAMES = list(IMGS)


def region(fo):
    """把文件偏移归到某帧/区域名"""
    tabs = [("向量/代码", 0x0, 0x4900), ("norm06", 0x49D4, 0x4A0C), ("init01", 0x4A0C, 0x4A38),
            ("init07", 0x4A38, 0x4A64), ("init05b", 0x4A64, 0x4A7C), ("t??", 0x4A7C, 0x4B5C),
            ("norm05", 0x4B5C, 0x4BE8), ("init3F", 0x4BE8, 0x4C54), ("尾部帧", 0x4C54, 0x4EF0)]
    for nm, lo, hi in tabs:
        if lo <= fo < hi:
            return nm, fo - lo
    return "?", fo


def diff(a, b, la, lb, limit=40):
    A, B = IMGS[a], IMGS[b]
    out = []
    for i in range(min(len(A), len(B))):
        if A[i] != B[i]:
            out.append((i, A[i], B[i]))
    print("\n=== %s vs %s : %d 字节不同 ===" % (la, lb, len(out)))
    for i, x, y in out[:limit]:
        reg, off = region(i)
        extra = ""
        if reg == "init01":
            extra = "  <== init01 body @%d" % (i - 0x4A0C - 6)
        if reg == "norm05":
            extra = "  <== norm05 pl[%d]" % (i - 0x4B82)
        print("  file 0x%04X [%s] %02X -> %02X%s" % (i, reg, x, y, extra))


def safe(a, b, la, lb):
    if a in IMGS and b in IMGS:
        diff(a, b, la, lb)
    else:
        print("\n(跳过 %s vs %s: 文件缺失)" % (la, lb))


safe("ORIG", "P23", "官方1.8.0", "P23(init01 @5=80 @7=00)")
safe("ORIG", "V3", "官方1.8.0", "V3(40mm 基准)")
safe("P23", "V3", "P23", "V3")
safe("V3", "K4", "V3", "K4(唯一差异应=norm05 pl[48])")
safe("V3", "Q6", "V3", "Q6(pl[48]=0)")
safe("V3", "O5", "V3", "O5(光学行)")
safe("V3", "Q1", "V3", "Q1(光圈家族)")
