# sig_pupil.py - inspect the xhs-#5 "pupil-magnification" region: 0x05 message body bytes ~32..47
# across the 5 real-lens captures. Author: EA9 writes fixed 1.5 + four 0 increments; real lenses
# 0..2-ish, decrease center->edge AND near->far; 6 bytes = u16 init + 4x increments.
# Dump per-frame byte windows + look for u16@/128 or @/256 values in 1.0..2.0 range.
import zipfile, struct, sys

def load(path):
    z = zipfile.ZipFile(path)
    names = [i.filename for i in z.infolist() if i.filename.startswith("logic-1-")]
    names.sort(key=lambda s: int(s.split("-")[-1]))
    return b"".join(z.read(n) for n in names)

def bits(buf, bit):
    m = 1 << bit
    return bytes(1 if (b & m) else 0 for b in buf)

def uart_decode(sig, spb):
    out = []; i, n = 1, len(sig); half = spb // 2
    while i < n - spb * 10:
        if sig[i] == 0 and sig[i-1] == 1 and sig[i+half] == 0:
            val = 0; ok = True
            for b in range(8):
                c = i + spb*(b+1) + half
                if c >= n: ok = False; break
                val |= sig[c] << b
            sb = i + spb*9 + half
            if ok and sb < n and sig[sb] == 1:
                out.append((i, val)); i += spb*10; continue
        i += 1
    return out

def frames(data):
    fs = []; i = 0; n = len(data)
    while i < n - 10:
        if data[i] == 0xF0:
            ln = data[i+1] | (data[i+2] << 8)
            if 10 <= ln <= 300 and i+ln <= n and data[i+ln-1] == 0x55 and data[i+3] in (0,1,2):
                fs.append((data[i+4], data[i+5], data[i+6:i+ln-3]))
                i += ln; continue
        i += 1
    return fs

for path in sys.argv[1:]:
    buf = load(path)
    rxd = bits(buf, 3)
    best = None
    for spb in (8, 4):
        fr = frames(bytes(v for _, v in uart_decode(rxd, spb)))
        if best is None or len(fr) > best[0]:
            best = (len(fr), fr)
    fr = best[1]
    f05 = [f for f in fr if f[1] == 0x05 and len(f[2]) >= 48]
    print("== %s  05 frames=%d" % (path.split("\\")[-1], len(f05)))
    if not f05:
        continue
    b0 = f05[0][2]
    print("  body[30..47] first: %s" % b0[0x30:0x48].hex(" "))
    print("  body[30..47] last : %s" % f05[-1][2][0x30:0x48].hex(" "))
    # per-byte variation in window
    for j in range(0x30, 0x48):
        vals = [f[2][j] for f in f05]
        u = sorted(set(vals))
        if len(u) > 1:
            print("   b%02X uniq=%d %02X..%02X seq=%s" % (j, len(u), min(vals), max(vals), " ".join("%02X" % v for v in vals[:20])))
    # u16@/128 interpretation in 1.0..2.0?
    for j in range(0x30, 0x46, 2):
        v = struct.unpack_from("<H", b0, j)[0]
        for den in (128, 256, 16, 32, 64):
            if 0.8 <= v / den <= 2.2:
                print("   ? u16@b%02X=%d  /%d=%.3f" % (j, v, den, v / den))
