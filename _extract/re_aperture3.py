# re_aperture3.py - Q1 改了 pl[44..52] 机身显示不动, 而"加宽后"那一对(0x18/0x70)在镜像里不存在
# => 值是运行期算/从别处拷来的。本脚本找来源:
#   (a) 0x18 与 0x70 近距离相邻; (b) u16 0x0018 与 0x0070 靠近;
#   (c) 列出镜像里所有 0xF0 帧模板 + 哪些帧载荷带光圈家族指纹;
#   (d) 代码区 movs #0x18/#0x70/#0x20/#0x50 同窗口成对。
import struct

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)

print("--- (a) 0x18 与 0x70 相邻 <=8 字节 ---")
for i in range(N - 8):
    if d[i] == 0x18:
        for k in range(1, 9):
            if d[i + k] == 0x70:
                print("  @0x%04X gap=%d ctx: %s" % (i, k, d[max(0, i - 8):i + 16].hex(" ")))
                break

print("\n--- (b) u16 18 00 与 70 00 相距 <=16 字节 ---")
p18 = [m for m in range(N - 1) if struct.unpack_from("<H", d, m)[0] == 0x18]
p70 = [m for m in range(N - 1) if struct.unpack_from("<H", d, m)[0] == 0x70]
for a in p18:
    for b in p70:
        if 0 < abs(a - b) <= 16:
            lo = min(a, b)
            print("  @0x%04X (18@0x%04X,70@0x%04X) ctx: %s" % (lo, a, b, d[max(0, lo - 8):lo + 24].hex(" ")))

print("\n--- (c) 所有 0xF0 帧模板 ---")
i = 0
frames = []
while i < N - 8:
    if d[i] == 0xF0:
        ln = struct.unpack_from("<H", d, i + 1)[0]
        if 8 <= ln <= 200 and i + ln <= N and d[i + ln - 1] == 0x55:
            frames.append((i, ln, d[i + 3], d[i + 4]))
            i += ln
            continue
    i += 1
print("  count =", len(frames))
for off, ln, cls, typ in frames:
    print("  frame@0%X len=%3d cls=%02X typ=%02X" % (off, ln, cls, typ))

print("\n--- (c2) 载荷带光圈家族指纹 (pl44=20,pl46=18,pl48=A0) 的帧 ---")
for off, ln, cls, typ in frames:
    pl = off + 6
    if pl + 60 < N and d[pl + 44] == 0x20 and d[pl + 46] == 0x18 and d[pl + 48] == 0xA0:
        print("  MATCH frame@0x%04X len=%d cls=%02X typ=%02X pl44@0x%04X: %s" % (
            off, ln, cls, typ, pl + 44, d[pl + 44:pl + 60].hex(" ")))

print("\n--- (d) 代码区 movs #0x18/#0x70/#0x20/#0x50 同窗口成对 ---")


def movs(addr):
    hw = struct.unpack_from("<H", d, addr)[0]
    if (hw & 0xF800) == 0x2000:
        return (hw & 0xFF, (hw >> 8) & 7)
    return None


for a in range(0, 0x4900, 2):
    m = movs(a)
    if not m or m[0] not in (0x18, 0x70, 0x20, 0x50):
        continue
    partner = {0x18: 0x70, 0x70: 0x18, 0x20: 0x50, 0x50: 0x20}[m[0]]
    for b in range(a, min(a + 24, N - 1), 2):
        n = movs(b)
        if n and n[0] == partner:
            print("  @0x%04X movs r%d,#0x%02X  ...  @0x%04X movs r%d,#0x%02X" % (
                a, m[1], m[0], b, n[1], n[0]))
            break
