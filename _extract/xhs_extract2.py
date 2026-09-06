# xhs_extract2.py - dump rendered text of saved xiaohongshu HTML (strip tags), show region around keywords.
import re, html, sys

path = sys.argv[1]
raw = open(path, "rb").read()
t = raw.decode("utf-8", "replace")
t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S)
t = re.sub(r"<[^>]+>", "\n", t)
t = html.unescape(t)
t = re.sub(r"[ \t\r\f\v]+", " ", t)
lines = [l.strip() for l in t.split("\n") if len(l.strip()) > 2]
print("###### %s  (%d text lines)" % (path.split("\\")[-1], len(lines)))
# print lines that look like prose (CJK ratio high) - that's the note body
def cjk_ratio(s):
    c = sum(1 for ch in s if '\u4e00' <= ch <= '\u9fff')
    return c / max(1, len(s))
body = [l for l in lines if cjk_ratio(l) > 0.30 and len(l) > 8]
seen = set(); out = []
for l in body:
    if l not in seen:
        seen.add(l); out.append(l)
for l in out:
    print(l)
