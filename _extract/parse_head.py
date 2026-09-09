# parse_head.py - 打印 hidlog 开头若干事件的完整字节(找解锁握手包)
import ast
import re

LOG = r"d:\work\techart\_extract\hidlog.txt"
rows = []
for line in open(LOG, encoding="utf-8"):
    m = re.search(r"(\d\d:\d\d:\d\d\.\d+)\s+(\{.*\})\s*$", line)
    if not m:
        continue
    try:
        top = ast.literal_eval(m.group(2))
    except Exception:
        continue
    if top.get("type") != "send":
        continue
    p = top.get("payload", {})
    if p.get("t") == "ready":
        continue
    rows.append((m.group(1), p))

# 打印前 12 个 W 和所有 R 的完整 hex
wcount = 0
for ts, p in rows:
    if p["t"] == "W" and wcount < 12:
        print("W  %s  %s" % (ts, p.get("d")))
        wcount += 1
    elif p["t"] == "R":
        print("R  %s  n=%s  %s" % (ts, p.get("n"), p.get("d")))
    elif p["t"] in ("IOin", "IOout"):
        print("%s %s c=%s n=%s %s" % (p["t"], ts, p.get("c"), p.get("n"), p.get("d")))
