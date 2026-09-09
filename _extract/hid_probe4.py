# hid_probe4.py - 看报告描述符(OUT/IN/FEATURE 的 ID 和长度), 再试 feature 通道发命令
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
SPY = bytes.fromhex("952768180303")
HEADS = [bytes.fromhex("952768180101020002"),  # check_tab 9B 假设
         bytes.fromhex("952768180202"),        # 6B 变体
         bytes.fromhex("952768180303")]        # spy_tab


TAGS = {0x04: "UsagePage", 0x08: "Usage", 0x10: "LogicalMin", 0x14: "LogicalMax",
        0x18: "PhysMin", 0x1C: "PhysMax", 0x24: "UnitExponent", 0x28: "Unit",
        0x30: "ReportSize", 0x34: "ReportID", 0x38: "ReportInput", 0x44: "StringIndex",
        0x48: "StringMin", 0x54: "ReportOutput", 0x60: "Separator", 0x74: "ReportCount",
        0x78: "Push", 0x80: "Pop", 0x84: "SetPrefix", 0x88: "ModeRangeMin",
        0x8C: "Collection", 0x90: "Read", 0x94: "Write", 0x98: "Idle", 0x9C: "Shutdown",
        0xA0: "HIDCollection", 0xC0: "HIDEndCollection", 0xA4: "Input",
        0xB4: "Output", 0xA8: "Input", 0xB8: "Output", 0xC4: "Feature", 0xC8: "EndCollection"}
MAIN = {0x80: "Input", 0x90: "Output", 0xA0: "Collection", 0xB0: "Feature", 0xC0: "EndCollection"}


def dump_descriptor(dev):
    d = dev.get_report_descriptor()
    print("descriptor len:", len(d))
    i = 0
    while i < len(d):
        b = d[i]
        bsize = b & 0x03
        if bsize == 3:
            bsize = 4
        tag = b & 0xFC
        typ = (b >> 2) & 0x03
        val = int.from_bytes(d[i + 1:i + 1 + bsize], "little", signed=(typ == 2)) if bsize else 0
        if typ == 0:  # main
            nm = MAIN.get(tag & 0xF0, "Main%02X" % tag)
            print("  %-12s %s" % (nm, val))
        elif typ == 1:  # global
            print("  G %-10s %d" % (TAGS.get(tag, "%02X" % tag), val))
        elif typ == 2:  # local
            print("  L %-10s %d" % (TAGS.get(tag, "%02X" % tag), val))
        i += 1 + bsize


def try_write_variants(dev, addr):
    for hidid in (0x00,):
        pass
    # 1) OUTPUT(现状): 65B [0]+64B
    p = bytearray(65)
    p[1:7] = SPY
    p[7:11] = struct.pack("<I", addr)
    print("-- output write (65B)"); dev.write(bytes(p)); time.sleep(0.2)
    r = dev.read(64, 300); print("   resp:", bytes(r).hex(" ")[:80] if r else "<无>")
    # 2) FEATURE: send_feature_report [id]+data
    for fid in (0x00, 0x01, 0x02, 0x03):
        f = bytearray(65)
        f[0] = fid
        f[1:7] = SPY
        f[7:11] = struct.pack("<I", addr)
        try:
            n = dev.send_feature_report(bytes(f))
            print("-- feature id=%d 发送 ok(%s)" % (fid, n))
            r = dev.get_input_report(bytes([fid]), 64, )
            print("   get_input_report:", bytes(r).hex(" ")[:80] if r else "<无>")
        except Exception as e:
            print("-- feature id=%d 失败: %s" % (fid, e))
    # 3) 握手后读: 先发 check 再发 spy
    h = bytearray(65)
    h[1:10] = HEADS[0]
    dev.write(bytes(h)); time.sleep(0.4)
    r = dev.read(64, 200); print("-- 握手 echo:", bytes(r).hex(" ")[:60] if r else "<无>")
    dev.write(bytes(p)); time.sleep(0.2)
    for i in range(10):
        r = dev.read(64, 150)
        if not r:
            break
        b = bytes(r)
        echo = b[0:6] == SPY and b[6:10] == struct.pack("<I", addr)
        print("   #%d %s%s" % (i, "回显" if echo else "★非回显", " " + b.hex(" ")[:80]))


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    dump_descriptor(dev)
    print()
    try_write_variants(dev, 0x08005000)
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
