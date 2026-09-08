# re_decl_src.py - 机身显示恒 F2.0 且改 norm05 模板无效 => 声明值另有静态来源(或纯硬编码运算)。
# 在【所有帧模板】里找 EF 光圈码指纹: 0x18(F2.0)/0x16/0x14/0x12/0x10 以及"最小光圈"伙伴 0x50/0x70。
import struct

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)


def F(v):
    return 2 ** ((v - 8) / 16.0) if v else 0.0


FR = {}
i = 0
while i < N - 8:
    if d[i] == 0xF0:
        ln = struct.unpack_from("<H", d, i + 1)[0]
        if 8 <= ln <= 200 and i + ln <= N and d[i + ln - 1] == 0x55:
            FR[i] = ln
            i += ln
            continue
    i += 1

WANT = (0x18, 0x16, 0x14, 0x12, 0x10, 0x20)
MINC = (0x70, 0x50)
print("帧数:", len(FR))
for off, ln in sorted(FR.items()):
    pl = off + 6
    body = d[pl:pl + (ln - 9)]
    w = [k for k, b in enumerate(body) if b in WANT]
    m = [k for k, b in enumerate(body) if b in MINC]
    if not w:
        continue
    print("\nframe@0x%04X len=%d typ=%02X cls=%02X 载荷宽=%d" % (off, ln, d[off + 4], d[off + 3], len(body)))
    for k in w:
        ctx = body[max(0, k - 6):k + 7].hex(" ")
        print("   pl[%3d]=%02X (F%.2f)  ctx: %s  %s" % (
            k, body[k], F(body[k]), ctx,
            "<= 附近有最小光圈码" if any(abs(k - j) <= 12 for j in m) else ""))
