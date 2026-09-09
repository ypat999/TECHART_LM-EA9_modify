# hid_probe7.py - 忠实复刻 btn_send_Click 握手时序 + ReadTable 轮询
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
CHECK = bytearray(bytes.fromhex("952768180101020002"))  # check_tab 9B
STATE = bytes.fromhex("952768180202")                    # state blob 前 6B
SPY = bytes.fromhex("952768180303")                      # spy_tab (read header)


def out(head):
    p = bytearray(65)
    p[1:1 + len(head)] = head
    return bytes(p)


def out_read(addr):
    p = bytearray(65)
    p[1:7] = SPY
    p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def drain(dev, ms=120):
    got = []
    while True:
        r = dev.read(64, ms)
        if not r:
            break
        got.append(bytes(r))
    return got


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    # 握手 1: 原样 check_tab
    dev.write(out(CHECK))
    print("hs1 resp:", [g.hex(" ")[:40] for g in drain(dev, 250)])
    time.sleep(0.5)
    # 握手 2: check_tab[6..8] = state[0..2]
    c2 = bytearray(CHECK)
    c2[6:9] = STATE[0:3]
    dev.write(out(c2))
    print("hs2 resp:", [g.hex(" ")[:40] for g in drain(dev, 250)])
    time.sleep(0.5)
    # ReadTableData 轮询: 从 0x08005000 起, 每次 +64, 共 8 块
    addr = 0x08005000
    for k in range(8):
        dev.write(out_read(addr + 64 * k))
        rs = drain(dev, 200)
        for b in rs:
            echo = b[0:6] == SPY and b[6:10] == struct.pack("<I", addr + 64 * k)
            print("  blk#%d %s %s" % (k, "回显" if echo else "★非回显", b.hex(" ")[:60]))
        if not rs:
            print("  blk#%d <无应答>" % k)
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
