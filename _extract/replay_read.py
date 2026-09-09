# replay_read.py - 复刻官方握手, 尝试用 python 读回真数据(目标: 看到 a5 2b 33 开头的设备应答)
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A
STATE = bytes.fromhex("952768180202")            # 解锁
CHECK = bytes.fromhex("952768180101") + struct.pack("<I", 0x419)  # check_tab + 参数
SPY = bytes.fromhex("952768180303")             # 读


def pkt(head):
    p = bytearray(65)
    p[1:1 + len(head)] = head
    return bytes(p)


def read_n(dev, k=6, ms=250):
    out = []
    for _ in range(k):
        try:
            r = dev.read(64, ms)
        except Exception:
            r = None
        if not r:
            break
        out.append(bytes(r))
    return out


def show(tag, reps):
    if not reps:
        print("  %-22s <无>" % tag)
        return False
    got = False
    for b in reps:
        real = b[0:5] == bytes.fromhex("a52b33010f")
        print("  %-22s %s%s" % (tag, b.hex(" ")[:64], "  ★真数据!" if real else ""))
        got = got or real
    return got


def main():
    dev = hid.device()
    dev.open(VID, PID)
    print("已连接:", dev.get_product_string())
    # 1) 开设备即读(不写)
    print("[1] 纯读(不写):")
    if show("open-read", read_n(dev, 6, 300)):
        return 0
    # 2) state 解锁 -> 读
    print("[2] 发 state(02 02) -> 读:")
    dev.write(pkt(STATE))
    time.sleep(0.3)
    if show("state", read_n(dev, 6, 300)):
        return 0
    # 3) check_tab(01 01 19 04 00 00) -> 读
    print("[3] 发 check_tab+0x419 -> 读:")
    dev.write(pkt(CHECK))
    time.sleep(0.3)
    if show("check", read_n(dev, 6, 300)):
        return 0
    # 4) spy_tab + 配置基址 0x8004000 -> 读
    print("[4] 发 spy_tab+0x08004000 -> 读:")
    dev.write(pkt(SPY + struct.pack("<I", 0x08004000)))
    time.sleep(0.3)
    if show("spy@4000", read_n(dev, 8, 300)):
        return 0
    # 5) 组合: state -> check -> spy 连续
    print("[5] state->check->spy 连发再读:")
    dev.write(pkt(STATE)); time.sleep(0.15)
    dev.write(pkt(CHECK)); time.sleep(0.15)
    dev.write(pkt(SPY + struct.pack("<I", 0x08004000))); time.sleep(0.2)
    show("combo", read_n(dev, 10, 300))
    dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
