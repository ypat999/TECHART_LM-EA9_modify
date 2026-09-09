# hid_probe9.py - 试 GET_REPORT(控制传输)通道 + SET_REPORT feature, 排除"应答走控制传输"
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
SPY = bytes.fromhex("952768180303")
CHECK = bytes.fromhex("952768180101")


def pkt(head, addr):
    p = bytearray(65)
    p[1:7] = head
    p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    addr = 0x08005000
    dev.write(pkt(CHECK, addr))
    time.sleep(0.4)
    # 排空
    while dev.read(64, 50):
        pass
    dev.write(pkt(SPY, addr))
    time.sleep(0.2)
    # A) 中断 IN
    r = dev.read(64, 300)
    print("A) 中断IN:", bytes(r).hex(" ")[:60] if r else "<无>")
    # B) GET_REPORT input (report id 0)
    try:
        g = dev.get_input_report(0x00, 64)
        print("B) get_input_report:", bytes(g).hex(" ")[:60] if g else "<无>")
    except Exception as e:
        print("B) get_input_report 失败:", e)
    # C) FEATURE 6B+addr 发送后 get_input_report
    f = bytearray(65)
    f[0] = 0x00
    f[1:7] = SPY
    f[7:11] = struct.pack("<I", addr)
    try:
        dev.send_feature_report(bytes(f))
        time.sleep(0.2)
        g2 = dev.get_input_report(0x00, 64)
        print("C) feature->get_input:", bytes(g2).hex(" ")[:60] if g2 else "<无>")
    except Exception as e:
        print("C) feature 失败:", e)
    # D) 直接 feature 读(1B 与 3B 两个 feature 报告)
    for rid in (0x00, 0x01, 0x02, 0x03):
        try:
            fr = dev.get_feature_report(rid, 64)
            if fr:
                print("D) feature id=%d:" % rid, bytes(fr).hex(" ")[:60])
        except Exception as e:
            print("D) feature id=%d 失败: %s" % (rid, e))
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
