# hid_probe5.py - 区分"纯 loopback" vs "识别协议族": 发随机字节/其他头看是否仍回显
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A


def rd(dev, ms=250):
    r = dev.read(64, ms)
    return bytes(r) if r else None


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    tests = [
        ("随机 A5 填充", bytes([0x00]) + b"\xA5" * 64),
        ("全 0x00", bytes(65)),
        ("E-mount F0 头", bytes([0x00, 0xF0, 0x40, 0x00, 0x01, 0x00, 0x0D]) + struct.pack("<I", 0x08006000) + bytes(54)),
        ("magic+0000", bytes([0x00]) + bytes.fromhex("952768180000") + struct.pack("<I", 0x08006000) + bytes(54)),
        ("magic+0101", bytes([0x00]) + bytes.fromhex("952768180101") + struct.pack("<I", 0x08006000) + bytes(54)),
        ("magic+0202", bytes([0x00]) + bytes.fromhex("952768180202") + struct.pack("<I", 0x08006000) + bytes(54)),
        ("magic+0303", bytes([0x00]) + bytes.fromhex("952768180303") + struct.pack("<I", 0x08006000) + bytes(54)),
    ]
    for name, pkt in tests:
        # 先清积压
        while rd(dev, 30):
            pass
        try:
            n = dev.write(pkt)
        except Exception as e:
            print("%-14s 写失败: %s" % (name, e))
            continue
        time.sleep(0.15)
        resp = rd(dev, 300)
        print("%-14s wrote=%d resp=%s" % (name, n, (resp.hex(" ")[:70] if resp else "<无>")))
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
