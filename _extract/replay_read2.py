# replay_read2.py - 抓"刚打开即推送"的 a5 2b 33 配置: close/open 后立刻纯读, 多轮
import sys
import time

import hid

VID, PID = 0x0483, 0x575A


def scan_open_read(cycles=4, per_read=25, ms=120):
    for c in range(cycles):
        dev = hid.device()
        dev.open(VID, PID)
        got = []
        for _ in range(per_read):
            try:
                r = dev.read(64, ms)
            except Exception:
                r = None
            if r:
                b = bytes(r)
                got.append(b)
                if b[0:5] == bytes.fromhex("a52b33010f"):
                    print("  ★[%d] 真数据: %s" % (c, b.hex(" ")))
                    dev.close()
                    return True
                # 只打印前 3 条看形态
                if len(got) <= 3:
                    print("  [%d] %s" % (c, b.hex(" ")[:60]))
            else:
                break
        dev.close()
        time.sleep(0.4)
    return False


def main():
    print("close/open 后纯读, 抓连接即推送:")
    if scan_open_read():
        print("=> 读到真数据")
        return 0
    print("=> 仍未读到(设备不在连接即推模式)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
