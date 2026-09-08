# re_aperture2.py - "显示没跟着 Q1 变"的两个候选解释, 用一次字节扫描就能分开:
#   H-抄错副本: 光圈家族字节在镜像里出现多份(每预设一份), 我们只改了 norm05 那一份;
#   H-开机覆写: 运行期写点(可能带 0x18/0x70=加宽后的那一对)另有静态表。
# 作者实测 EA9 运行期 pl[44]/pl[52] = 0x18/0x70 (模板是 0x20/0x50), 所以两种指纹都要搜。
d = open(r"d:\work\techart\patches\EA9-V3.bin", "rb").read()
N = len(d)


def find(pat, label):
    hits, i = [], 0
    while True:
        j = d.find(pat, i)
        if j < 0:
            break
        hits.append(j)
        i = j + 1
    print("%-46s x%-3d %s" % (label, len(hits), ["0x%04X" % h for h in hits[:12]]))
    return hits


# pl[44..52] 模板原样: 20 00 18 00 A0 00 00 20 50
tpl = bytes.fromhex("20001800A0000020" + "50")
h1 = find(tpl, "family template 20 00 18 00 A0 00 00 20 50")
# 紧凑版(无间隔): 20 18 A0 20 50
find(bytes.fromhex("2018A02050"), "compact 20 18 A0 20 50")
# 加宽后的运行期对: 18 .. 70 家族
find(bytes.fromhex("1800A000001870"), "runtime family 18 00 A0 00 00 18 70")
# pl[48]=A0 前后夹 (18 00 A0) / (A0 00 00 20)
find(bytes.fromhex("1800A0"), "18 00 A0  (pl46..48)")
find(bytes.fromhex("20001800A0"), "20 00 18 00 A0  (pl44..48)")
# 单字节 A0 00 00 20 50
find(bytes.fromhex("A000002050"), "A0 00 00 20 50  (pl48..52)")

print("\n--- 每处命中打印上下文 ---")
for h in h1:
    print("@0x%04X : %s" % (h, d[h - 12:h + 24].hex(" ")))

# 05 消息模板有几份? 用 norm05 帧头 + 长度 + 类型定位同类帧
print("\n--- 帧表里所有 105B 且载荷含上述家族的帧 ---")
i = 0
while True:
    j = d.find(tpl, i)
    if j < 0:
        break
    # 往前找 0xF0 帧头(载荷 = 帧+6)
    for back in range(6, 10):
        if j - back >= 0 and d[j - back] == 0xF0:
            ln = d[j - back + 1] | (d[j - back + 2] << 8)
            print("  frame hdr@0x%04X len=%d (payload pl44@0x%04X)" % (j - back, ln, j))
    i = j + 1
