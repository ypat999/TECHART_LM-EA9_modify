# re_preset_table.py - 光圈家族被开机例程改写(模板值不上链) => 它一定从别处取值。
# 作者注:"EA9 报的是 Canon EF 40mm f/2.8 的身份, 开机再放宽到 f/2.0..f/90", 而用户可用
# "光圈值选焦距"在机身侧切 12/40/75mm 档 => 环内很可能有一张【预设表】: {焦距x10, 最大/最小光圈码}。
# 若存在, 直接改表 = 零成本(无需代码 patch)就能改声明光圈。本脚本按"焦距 x10 的 u16"当锚点找表。
import struct

d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)
FOCAL = [120, 150, 180, 210, 240, 250, 280, 350, 400, 500, 550, 750, 850]
EF = set(range(0x08, 0x79))          # 合法 EF 1/8 档光圈码区间


def F(v):
    return 2 ** ((v - 8) / 16.0)


print("--- 焦距x10 u16 锚点 + 附近光圈码 ---")
found = 0
for a in range(0, N - 1):
    v = struct.unpack_from("<H", d, a)[0]
    if v not in FOCAL:
        continue
    win = d[max(0, a - 20):a + 28]
    # 窗口里是否出现"成对出现的合法光圈码"(至少两个, 且相距 <=8)
    efpos = [(i, b) for i, b in enumerate(win) if b in EF and b >= 0x10]
    pairs = [(x, y) for i, x in efpos for j, y in efpos if i < j and 0 < j - i <= 8]
    if not pairs:
        continue
    found += 1
    print("@0x%04X f=%4d (x10=%d)  ctx: %s" % (a, v // 10, v, win.hex(" ")))
print("total:", found)

print("\n--- 重复结构扫描: 同一 8 字节模式出现 >=3 次(可能是每档一条的预设表) ---")
from collections import defaultdict
seen = defaultdict(list)
for a in range(0, N - 8):
    seen[d[a:a + 8]].append(a)
rep = [(k, v) for k, v in seen.items() if len(v) >= 3 and k.count(0) < 5]
rep.sort(key=lambda t: -len(t[1]))
for k, v in rep[:12]:
    print("  %s x%d @ %s" % (k.hex(" "), len(v), ["0x%04X" % x for x in v[:8]]))
