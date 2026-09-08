# upx_strings.py - 拆 TECHART_Updater(USB).exe: 找 HID 通道与协议指纹
# 目标: (1) VID/PID 与设备打开方式(CreateFile \\?\hid#... / HidD_* API);
#       (2) 报文封装(是否有 0xF0 帧、64 字节 report、命令码如 'W'/'R'/'E');
#       (3) URL/清单解析 -> 下发给环的命令序列线索; (4) 任何"读版本/读回"字样。
import re
import sys

P = r"d:\work\techart\TECHART_Updater(USB).exe"
d = open(P, "rb").read()
print("size", len(d))

pat_a = re.compile(rb"[\x20-\x7e]{5,}")
pat_w = re.compile(rb"(?:[\x20-\x7e]\x00){5,}")


def show(title, rx, filt=None, limit=200):
    print("\n=== %s ===" % title)
    seen = set()
    n = 0
    for m in rx.finditer(d):
        s = m.group(0)
        try:
            t = s.decode("utf-16-le") if b"\x00" in s else s.decode("ascii")
        except Exception:
            continue
        t = t.strip()
        if t in seen or len(t) < 5:
            continue
        seen.add(t)
        if filt and not any(k in t.lower() for k in filt):
            continue
        print("  0x%06X  %s" % (m.start(), t[:160]))
        n += 1
        if n > limit:
            break


KEYS = ["hid", "vid", "pid", "0483", "575a", "usb", "device", "open", "write", "read",
        "send", "recv", "report", "feature", "ioctl", "version", "ver", "firmware", "flash",
        "erase", "sector", "boot", "crc", "checksum", "techart", "http", ".bin", ".txt",
        "lst", "product", "error", "fail", "cmd", "reset", "jump", "serial", "com"]

show("ASCII 字符串(含关键词)", pat_a, KEYS)
show("UTF-16 字符串(含关键词)", pat_w, KEYS)
show("疑似 VID/PID 数字串", pat_a, ["0x04", "0x57", "vid_", "pid_"], 40)
