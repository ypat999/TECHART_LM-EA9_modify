# hid_probe6.py - 测试"命令触发重枚举/进模式"假说:
# 依次发候选握手包, 每个之后: 等 -> 重新枚举对比 -> 发 spy 读命令看应答形态是否变化
import struct
import sys
import time

import hid

VID, PID = 0x0483, 0x575A


def snap():
    return sorted((d.get("serial_number") or "", d.get("instance_path") or "") for d in hid.enumerate(VID, PID))


def sendpkt(dev, head, addr=None, total=9):
    p = bytearray(65)
    p[1:1 + len(head)] = head
    if addr is not None:
        p[1 + 6:1 + 6 + 4] = struct.pack("<I", addr)
    dev.write(bytes(p))


SPY = bytes.fromhex("952768180303")
CANDS = [
    ("check9", bytes.fromhex("952768180101020002"), None),
    ("state6+addr", bytes.fromhex("952768180202"), 0x08005000),
    ("check6+952768", bytes.fromhex("952768180101" + "952768"), None),
    ("start?", bytes.fromhex("9527681800000a0000"), None),
    ("spy+addr x2", SPY, 0x08005000),
]


def main():
    print("枚举快照0:", snap())
    for name, head, addr in CANDS:
        dev = hid.device()
        try:
            dev.open(VID, PID)
        except OSError as e:
            print("[%s] 打不开: %s" % (name, e))
            time.sleep(1.0)
            continue
        sendpkt(dev, head, addr)
        time.sleep(1.0)
        r = None
        try:
            r = dev.read(64, 400)
        except Exception:
            pass
        # spy 读命令
        sendpkt(dev, SPY, 0x08005000)
        time.sleep(0.2)
        r2 = None
        try:
            r2 = dev.read(64, 600)
        except Exception:
            pass
        dev.close()
        b2 = bytes(r2) if r2 else None
        echo = b2 is not None and b2[0:6] == SPY and b2[6:10] == struct.pack("<I", 0x08005000)
        print("[%s] 握手resp=%s | spy应答=%s%s" % (
            name,
            bytes(r).hex(" ")[:40] if r else "<无>",
            (b2.hex(" ")[:40] if b2 else "<无>"),
            " (纯回显)" if echo else " ★非回显!"))
        s = snap()
        print("    枚举快照:", s)
        time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
