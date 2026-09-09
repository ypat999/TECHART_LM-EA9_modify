# hid_probe.py - 按升级程序真实流程审讯环: 先发 check_tab 握手, 再发 spy_tab+addr 读命令
# check_tab(9B) = 95 27 68 18 01 01 02 00 02   (img_Title_Click 第一发)
# spy_tab (6B)  = 95 27 68 18 03 03            (ReadFirmwareFromAdapter/ReadTableData 帧头)
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
CHECK = bytes.fromhex("95276818010102 0002".replace(" ", ""))
SPY = bytes.fromhex("952768180303")


def pkt64(head, addr=None):
    p = bytearray(65)   # [0]=reportID 0, [1..64]=64B 逻辑报文
    p[1:1 + len(head)] = head
    if addr is not None:
        p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def drain(dev, n=8, ms=300, label=""):
    got = []
    for i in range(n):
        try:
            r = dev.read(64, ms)
        except Exception:
            r = None
        if r:
            b = bytes(r)
            got.append(b)
            print("    %s#%02d %s" % (label, i, b.hex(" ")[:120]))
        else:
            break
    return got


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    print("[1] 握手: 发 check_tab")
    dev.write(pkt64(CHECK))
    time.sleep(0.6)
    drain(dev, 8, 300, "hs ")
    print("[2] 再发一发(img_Title 连写两次)")
    dev.write(pkt64(CHECK))
    time.sleep(0.6)
    drain(dev, 8, 300, "hs ")
    for addr in (0x08006000, 0x08004000, 0x08005000, 0x08000000):
        print("[3] 读命令 @0x%08X" % addr)
        dev.write(pkt64(SPY, addr))
        time.sleep(0.3)
        got = drain(dev, 6, 400, "rd ")
        for b in got:
            if b[0:6] != SPY:
                print("  ★ 非回显应答! 内容见上")
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
