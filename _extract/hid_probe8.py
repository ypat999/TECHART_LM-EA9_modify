# hid_probe8.py - 复刻 btn_cfg_Click 精确时序:
#   1) 发 check_tab(01 01)+地址(0x8004000) 解锁包, Sleep 500
#   2) 发 spy_tab(03 03)+地址 读块, 看应答是否变成"真数据"(非回显)
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
CHECK = bytes.fromhex("952768180101")   # check_tab 头 6B
SPY = bytes.fromhex("952768180303")     # spy_tab 头 6B
VT = bytes.fromhex("b02a0020")          # EA9 向量表首 4B(读通判据)


def pkt(head, addr):
    p = bytearray(65)
    p[1:7] = head
    p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def rd(dev, ms=400):
    r = dev.read(64, ms)
    return bytes(r) if r else None


def classify(b, head, addr):
    if b is None:
        return "<无应答>"
    echo = b[0:6] == head and b[6:10] == struct.pack("<I", addr)
    if VT in b:
        return "★★向量表命中! " + b.hex(" ")[:70]
    return ("回显 " if echo else "非回显 ") + b.hex(" ")[:70]


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    for unlock_addr in (0x08004000, 0x08005000):
        print("\n=== 解锁包 check_tab+0x%08X ===" % unlock_addr)
        dev.write(pkt(CHECK, unlock_addr))
        time.sleep(0.55)
        b = rd(dev, 400)
        print("  解锁应答:", classify(b, CHECK, unlock_addr))
        # 读几块看是否变真数据
        for k in range(4):
            a = 0x08005000 + 64 * k
            dev.write(pkt(SPY, a))
            b = rd(dev, 300)
            print("  spy blk#%d @0x%08X: %s" % (k, a, classify(b, SPY, a)))
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
