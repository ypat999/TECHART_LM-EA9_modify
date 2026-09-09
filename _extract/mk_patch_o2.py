# mk_patch_o2.py - O 系第 2 代: 按作者库 principled 计算 M40(Voigtländer 40/1.2) 的正确光学行
# 依据 docs_ref\E-mount-protocol-RE\docs\optical_data.md:
#   §3 block-float: byte0=type(bit7)|Efield(bits6..4)|start高4位; byte1=start低8; byte2..5=4×有符号delta
#                   v0=((b0&0xF)<<8)|b1; value[i]=v[i]*2^-Eabs
#   §5 slot B type0 = 出瞳放大率 p (EPD/f, 无穷端); 锚点 Eabs = nibble+8 (1->E9,2->E10,3->E11)
#   §7 根因: LM-EA9 发 slotB type0 = 26 00 00 00 00 00 = 平坦 p=1.5 (宣称出瞳 60mm), 对 M 头太短不出瞳=错输入
#            slotA = 全零 = 无视场网格
#   Voigt 40/1.2 双高斯类 -> p≈1.0~1.2 (作者参照: 对称 YN50=1.16, SEL55210@55=1.00)
#   slotA 用作者语料里最贴 40mm 的 FF 正常头 SEL5518Z 首帧网格 b0 f4 46 46 3f 25 (value0=0.119,比=1.98)
import os
import shutil
import struct

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
SA = N05B + 32   # slot A pl[32..37]
SB = N05B + 38   # slot B pl[38..43]
print("V3 slotA:", d0[SA:SA + 6].hex(" "), " slotB:", d0[SB:SB + 6].hex(" "))


def flat_p(p, nibble=2):
    """slot B type0 平坦行 = 出瞳放大率 p; Eabs=nibble+8; 返回 6 字节"""
    Eabs = nibble + 8
    v0 = int(round(p * (2 ** Eabs)))
    b0 = (nibble << 4) | ((v0 >> 8) & 0x0F)   # type0 => bit7=0
    return bytes([b0, v0 & 0xFF, 0x00, 0x00, 0x00, 0x00])


def decode(row):
    v = (row[0] & 0xF) << 8 | row[1]
    out = [v]
    for b in row[2:6]:
        v += b - 256 if b > 127 else b
        out.append(v)
    return out


# 自检: p=1.0 应还原 1.0; p=1.2 应还原 1.2
for tp in (1.0, 1.2):
    r = flat_p(tp)
    Eabs = ((r[0] >> 4) & 7) + 8
    val = decode(r)[0] / 2 ** Eabs
    print("  flat_p(%.2f) -> %s  反解 p=%.3f" % (tp, r.hex(" "), val))

GRID_55 = bytes.fromhex("b0f446463f25")   # SEL5518Z 55mm 首帧 slotA (作者 §4.2, 最贴 40mm 的 FF 正常头)
ZERO = bytes(6)

jobs = [
    ("O6", "27.6.0", 0x5A, [(SA, GRID_55), (SB, flat_p(1.0))]),   # 主攻: 正确网格 + p=1.0
    ("O7", "27.7.0", 0x5B, [(SA, GRID_55), (SB, flat_p(1.2))]),   # p 上夹
    ("O8", "27.8.0", 0x5C, [(SA, ZERO), (SB, flat_p(1.0))]),      # 隔离: 只修出瞳, slotA 归零
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E


def sum_ck(a, off, ln):
    return sum(a[off + 1: off + ln - 3]) & 0xFFFF


def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off + ln - 3] = c & 0xFF
    a[off + ln - 2] = (c >> 8) & 0xFF


os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, edits in jobs:
    a = bytearray(d0)
    for off, by in edits:
        a[off:off + 6] = by
    a[I07B + 6] = nib
    raw = b"TECHART LM-EA9-" + tag.encode()
    a[I3FB + 1:I3FB + 19] = raw + bytes(18 - len(raw))
    write_ck(a, I07, I07L)
    write_ck(a, I3F, I3FL)
    write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn,
                r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 principled optical %s VER %s (Voigt40/1.2: slotA 55mm-grid, slotB type0 pupil p)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off + ln - 3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s nibble=%02X diff=%d ck_ok=%s  pl32..37=%s pl38..43=%s" % (
        tag, ver, nib, diff, ok_ck, b[N05B + 32:N05B + 38].hex(" "), b[N05B + 38:N05B + 44].hex(" ")))
