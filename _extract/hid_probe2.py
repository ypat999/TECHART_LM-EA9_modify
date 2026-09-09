# hid_probe2.py - 流水线读探测: 模拟 app 的"请求k->应答k-1"节奏
# 依据 IL: usbHID_DataReceived4ReadFirmware 收到 report.Data 后才发下一条
#          ReadFirmwareFromAdapter(cursor), cursor 初值=0x8005000, 每次 +64
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
CHECK = bytes.fromhex("952768180101020002")   # 9B 握手模板
SPY = bytes.fromhex("952768180303")           # 6B 读头


def req(head, addr=None):
    p = bytearray(65)
    p[1:1 + len(head)] = head
    if addr is not None:
        p[7:11] = struct.pack("<I", addr)
    return bytes(p)


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    dev.write(req(CHECK))
    time.sleep(0.6)
    # 清空积压
    for _ in range(20):
        r = dev.read(64, 80)
        if not r:
            break
    base = 0x08005000
    nresp = 0
    interesting = 0
    for k in range(24):
        addr = base + 64 * k
        dev.write(req(SPY, addr))
        time.sleep(0.05)
        r = dev.read(64, 250)
        if not r:
            print("  #%02d addr=0x%08X  <无应答>" % (k, addr))
            continue
        b = bytes(r)
        nresp += 1
        # 分类: 全零 / 纯回显(含自己 addr) / 其他
        echo = (b[6:10] == struct.pack("<I", addr)) and b[0:6] == SPY
        if not echo:
            interesting += 1
            print("  #%02d  ★非回显  %s" % (k, b.hex(" ")))
        elif b[10:40].strip(b"\x00"):
            interesting += 1
            print("  #%02d  回显头+有内容  %s" % (k, b.hex(" ")))
        else:
            print("  #%02d addr=0x%08X  回显ACK" % (k, addr))
    print("应答 %d 条, 其中非纯回显 %d 条" % (nresp, interesting))
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
