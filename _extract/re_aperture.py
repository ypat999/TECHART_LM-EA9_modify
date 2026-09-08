# re_aperture.py - 找"光圈家族"运行期写点: Q1 改了 pl[44]/46/51/52 模板值, 机身仍显示 F2.0
# => 要么开机例程覆写这四个字节(作者记载 0x20->0x18 / 0x50->0x70), 要么显示另有源头。
# 思路: (1) 全镜像找 32 位字面量 = norm05 帧地址/载荷地址(谁引用模板);
#       (2) 找 Thumb movs #0x18 与 #0x70 同处一个函数(成对写"加宽后光圈对"的指纹);
#       (3) 找数据区里 18..70 / 20..50 相邻成对的小表(可能是"每预设一组光圈对"的静态表=>可零成本改)。
import struct

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)
N05 = 0x4B7C          # norm05 帧起始
N05B = 0x4B82         # norm05 载荷起始(pl[0])
print("size", N)

# (1) 字面量池里指向 05 模板的指针
print("\n--- [1] 32-bit literals pointing at the 05 template ---")
for target in (N05, N05B, N05 + 1, N05B + 1, 0x4B78, 0x4B80):
    for a in range(0, N - 3, 4):
        if struct.unpack_from("<I", d, a)[0] == target:
            print("  lit@0x%04X -> 0x%X" % (a, target))

# (2) movs #imm 指纹: (0x18 & 0x70) 或 (0x20 & 0x50) 在同一条码窗口内成对出现
print("\n--- [2] movs #0x18/#0x70 (or #0x20/#0x50) pairs inside one small window ---")


def movs(addr):
    hw = struct.unpack_from("<H", d, addr)[0]
    if (hw & 0xF800) == 0x2000:
        return (hw & 0xFF, (hw >> 8) & 7)          # (imm8, Rd)
    return None


hits = []
for a in range(0, N - 1, 2):
    m = movs(a)
    if not m or m[0] not in (0x18, 0x20):
        continue
    for b in range(a - 24, a + 25, 2):
        if 0 <= b < N - 1 and b != a:
            n = movs(b)
            if n and n[0] in (0x70, 0x50):
                hits.append((a, m, b, n))
seen = set()
for a, m, b, n in hits:
    key = min(a, b) // 0x40
    if key in seen:
        continue
    seen.add(key)
    print("  0x%04X movs r%d,#0x%02X   <->   0x%04X movs r%d,#0x%02X" % (
        a, m[1], m[0], b, n[1], n[0]))
print("  total windows:", len(seen))

# (3) 数据区小表: 同窗口内同时含 (X, X-8) 与 (X, X+0x30)
print("\n--- [3] static pairs (X, X-8) / (X, X+0x30) in a 16-byte window ---")


def isef(v):
    return 0x08 <= v <= 0x78


cand = []
for a in range(0, N - 16):
    w = d[a:a + 16]
    for i in range(16):
        for j in range(i + 1, 16):
            x, y = w[i], w[j]
            if isef(x) and y == x - 8 and j - i <= 6:
                if any(isef(v) and v == x + 0x30 and abs(k - i) <= 12 for k, v in enumerate(w)):
                    cand.append((a, i, j, x))
uniq = [c for c in cand if c[0] % 2 == 0]
print("  candidates:", len(uniq))
for a, i, j, x in uniq[:40]:
    print("  @0x%04X  X=0x%02X bytes: %s" % (a, x, d[a:a + 16].hex(" ")))
