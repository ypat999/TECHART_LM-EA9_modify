# xhs_extract.py - extract readable post text from saved Xiaohongshu HTML pages.
import re, sys, html

def extract(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "gbk"):
        try:
            t = raw.decode(enc, "replace"); break
        except Exception:
            pass
    # remove script/style but keep JSON strings inside (xhs embeds article in INITIAL_STATE)
    txt = re.sub(r"<script[^>]*>(.*?)</script>", r"\n\1\n", t, flags=re.S)
    # try find "desc": "..." or noteCotent
    out = []
    for m in re.finditer(r'"desc"\s*:\s*"((?:[^"\\]|\\.)*)"', t):
        s = m.group(1)
        s = s.encode().decode("unicode_escape", "replace")
        out.append(s)
    for m in re.finditer(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', t):
        s = m.group(1)
        try:
            s = bytes(s, "utf-8").decode("unicode_escape", "ignore")
        except Exception:
            pass
        if len(s) > 80:
            out.append(s)
    # fallback: strip tags
    if not out:
        body = re.sub(r"<[^>]+>", " ", txt)
        body = html.unescape(body)
        body = re.sub(r"\s+", " ", body)
        out = [body]
    seen = set(); uniq = []
    for s in out:
        k = s[:60]
        if k not in seen:
            seen.add(k); uniq.append(s)
    return uniq

p = sys.argv[1]
print("###### %s ######" % p.split("\\")[-1])
for s in extract(p):
    s2 = s.replace("\\n", "\n").replace('\\u0026amp;', "&").replace("\u200b", "")
    if len(s2) > 60:
        print(s2[:6000])
        print("-----")
