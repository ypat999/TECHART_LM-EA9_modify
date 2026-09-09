# peek.py - 看 hidlog 里 R/W 事件计数与头部
import ast
import re

L = open(r"d:\work\techart\_extract\hidlog.txt", encoding="utf-8").read().splitlines()
rs, ws = [], []
for line in L:
    m = re.search(r"(\d\d:\d\d:\d\d\.\d+)\s+(\{.*\})\s*$", line)
    if not m:
        continue
    try:
        top = ast.literal_eval(m.group(2))
    except Exception:
        continue
    p = top.get("payload", {}) if top.get("type") == "send" else {}
    if p.get("t") == "R":
        rs.append((m.group(1), p))
    elif p.get("t") == "W":
        ws.append((m.group(1), p))
print("R=%d W=%d" % (len(rs), len(ws)))
print("--- 前 10 个 R ---")
for ts, p in rs[:10]:
    print("  %s h=%s n=%s %s" % (ts, p.get("h"), p.get("n"), p.get("d", "")[:56]))
print("--- 前 8 个 W ---")
for ts, p in ws[:8]:
    print("  %s h=%s %s" % (ts, p.get("h"), p.get("d", "")[:56]))
