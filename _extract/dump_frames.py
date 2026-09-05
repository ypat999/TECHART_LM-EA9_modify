# dump_frames.py - dump full hex of firmware frames by type byte, plus the known init34 region.
# Goal: find the F-step -> focal-length table (series like 250/350/400/500/550..., 0.1mm LE16).
import struct
BIN = r"d:\work\techart\patches\EA9-V3.bin"
d = open(BIN, "rb").read()
N = len(d)

def dump(off, ln, tag):
    print("\n%s @file %04X len=%d" % (tag, off, ln))
    for i in range(0, ln, 16):
        row = d[off+i:off+i+16]
        print("  %04X  %-47s  %s" % (off+i, row.hex(" "), "".join(chr(b) if 32 <= b < 127 else "." for b in row)))

dump(0x4CDC, 32, "init34 (orig-stale cksum)")

# scan all frames F0 .. 55 with type in {0x07,0x28,0x23,0x17,0x24} and full-frame hex
i = 0
seen = set()
while i < N - 10:
    if d[i] == 0xF0:
        ln = d[i+1] | (d[i+2] << 8)
        if 10 <= ln <= 300 and i + ln <= N and d[i+ln-1] == 0x55 and d[i+3] in (0,1,2):
            typ = d[i+5]
            if typ in (0x07, 0x28, 0x23, 0x17, 0x24) and (i+3, typ) not in seen:
                seen.add((i+3, typ))
                dump(i, min(ln, 220), "frame cls=%d seq=%d typ=0x%02X" % (d[i+3], d[i+4], typ))
            i += ln; continue
    i += 1
