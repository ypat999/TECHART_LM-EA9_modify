# hid_probe3.py - 流水线: 边连续发 spy_tab+addr 递增请求, 边持续读, 找 b0 2a 00 20 向量表
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
SPY = bytes.fromhex("952768180303")
VT = bytes.fromhex("b02a0020")  # EA9 固件向量表首 4B(初值 SP), 任意应答里出现=读通


def req(addr, head=SPY):
    p = bytearray(65)
    p[1:1 + len(head)] = head
    p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def collect(dev, secs=1.0):
    out = []
    t0 = time.time()
    while time.time() - t0 < secs:
        r = dev.read(64, 100)
        if r:
            out.append(bytes(r))
    return out


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    for base in (0x08005000, 0x08004000, 0x08006000, 0x08000000):
        print("\n=== 流水线读 base=0x%08X ===" % base)
        # 先发一发握手
        dev.write(req(base, bytes.fromhex("95276818010102")))
        collect(dev, 0.3)
        hits = 0
        for k in range(30):
            dev.write(req(base + 64 * k))
            rs = collect(dev, 0.15)
            for b in rs:
                if VT in b:
                    print("  ★★ 向量表命中 #%d @0x%08X: %s" % (k, base + 64 * k, b.hex(" ")))
                    hits += 1
                elif b[:4] != SPY[:4] or b[6:10] != struct.pack("<I", base + 64 * k):
                    print("  非回显 #%d: %s" % (k, b.hex(" ")[:100]))
        print("  本 base 命中 %d 条" % hits)
        if hits:
            break
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
