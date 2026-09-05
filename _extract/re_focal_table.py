# re_focal_table.py - locate the lens focal-length step table in LM-EA9 firmware.
# Evidence: F6.3 slot shows 40mm at x10 and 40*N/10 at xN => slot value(0.1mm units)=400 rides the xN chain.
# Strategy: scan LE16 halfwords for focal-length step candidates and report clusters (contiguous runs).
import struct

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d = open(BIN, "rb").read()
N = len(d)

# common M/legacy focal lengths (0.1mm units): 12,15,16,18,21,24,25,28,32,35,40,45,50,55,58,65,73,75,85,90,100,105,127,135,200,300
CAND = [int(mm * 10) for mm in (12,15,16,18,21,24,25,28,32,35,40,45,50,55,58,65,73,75,85,90,100,105,127,135,200,300)]
CANDS = set(CAND)
hits = []
for off in range(0, N - 2, 2):
    v = struct.unpack_from("<H", d, off)[0]
    if v in CANDS:
        hits.append((off, v))

# group into clusters (<=16 bytes apart)
clusters = []
cur = []
for off, v in hits:
    if cur and off - cur[-1][0] > 16:
        clusters.append(cur); cur = []
    cur.append((off, v))
if cur: clusters.append(cur)

print("clusters (>=3 focal-like LE16 within 48B window):")
for c in clusters:
    span = c[-1][0] - c[0][0]
    if len(c) >= 3 and span <= 48:
        print("  off %04X..%04X n=%d: %s" % (c[0][0], c[-1][0], len(c),
              " ".join("%04X=%d" % (o, v) for o, v in c)))
        # hexdump the region
        s = max(0, c[0][0]-4); e = min(N, c[-1][0]+8)
        print("    raw:", d[s:e].hex(" "))

# dedicated: all 400 occurrences
print("\nhalfword==400 (F6.3 slot candidate):")
for off in range(0, N - 2, 2):
    if struct.unpack_from("<H", d, off)[0] == 400:
        print("  off %04X ctx: %s" % (off, d[off-8:off+10].hex(" ")))

# byte-unit candidates (values 12..300 as single bytes near repeats)? show regions with >=4 hits of byte==40
from collections import Counter
b40 = [i for i in range(N) if d[i] == 40]
print("\nbyte==40 count=%d positions(first 40): %s" % (len(b40), b40[:40]))
