# parse_hidlog.py - 解析 frida hidlog: 按时序输出 W/R/IO, 并统计唯一写包
import ast
import re
import sys
from collections import Counter

LOG = r"d:\work\techart\_extract\hidlog.txt"
rows = []
for line in open(LOG, encoding="utf-8"):
    m = re.search(r"(\d\d:\d\d:\d\d\.\d+)\s+(\{.*\})\s*$", line)
    if not m:
        continue
    ts, d = m.group(1), m.group(2)
    try:
        top = ast.literal_eval(d)
    except Exception:
        continue
    if top.get("type") != "send":
        continue
    p = top.get("payload", {})
    if p.get("t") == "ready":
        continue
    rows.append((ts, p))

print("总事件 %d 条;  时间跨度 %s .. %s" % (len(rows), rows[0][0] if rows else "-", rows[-1][0] if rows else "-"))
wc = Counter(p.get("d", "") for ts, p in rows if p["t"] == "W")
rc = Counter(p.get("d", "") for ts, p in rows if p["t"] == "R")
ioc = Counter((p["t"], p.get("c")) for ts, p in rows if p["t"] in ("IOin", "IOout"))
print("\n== 唯一写包(W) %d 种 ==" % len(wc))
for d, c in wc.most_common(20):
    print("  x%-3d %s" % (c, d))
print("\n== 唯一读包(R) %d 种 ==" % len(rc))
for d, c in rc.most_common(20):
    print("  x%-3d %s" % (c, d))
print("\n== HID DeviceIoControl 统计 ==")
for (t, c), n in ioc.most_common():
    print("  %-6s %-12s x%d" % (t, c, n))

print("\n== 前 40 条时序 ==")
for ts, p in rows[:40]:
    t = p["t"]
    if t in ("W", "R"):
        print("  %s %s n=%s %s" % (ts, t, p.get("n"), p.get("d", "")[:50]))
    else:
        print("  %s %s %s n=%s %s" % (ts, t, p.get("c"), p.get("n"), p.get("d", "")[:50]))
