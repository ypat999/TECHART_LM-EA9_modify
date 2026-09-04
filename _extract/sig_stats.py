# sig_stats.py - per-field time series of Viltrox 0x05/0x06 frames (byte-aligned, device-specific)
import zipfile, collections, sys

def load(path):
    z = zipfile.ZipFile(path)
    names = [i.filename for i in z.infolist() if i.filename.startswith("logic-1-")]
    names.sort(key=lambda s: int(s.split("-")[-1]))
    return b"".join(z.read(n) for n in names)

def bits(buf, bit):
    m = 1 << bit
    return bytes(1 if (b & m) else 0 for b in buf)

def uart_decode(sig, spb=4):
    out = []
    i, n = 1, len(sig)
    half = spb // 2
    while i < n - spb * 10:
        if sig[i] == 0 and sig[i - 1] == 1 and sig[i + half] == 0:
            val = 0; ok = True
            for b in range(8):
                c = i + spb * (b + 1) + half
                if c >= n: ok = False; break
                val |= sig[c] << b
            sb = i + spb * 9 + half
            if ok and sb < n and sig[sb] == 1:
                out.append((i, val)); i += spb * 10; continue
        i += 1
    return out

def frames(data):
    fs = []; i = 0; n = len(data)
    while i < n - 10:
        if data[i] == 0xF0:
            ln = data[i+1] | (data[i+2] << 8)
            if 10 <= ln <= 300 and i + ln <= n and data[i+ln-1] == 0x55 and data[i+3] in (0,1,2):
                ck = data[i+ln-3] | (data[i+ln-2] << 8)
                s = sum(data[i+1:i+ln-3]) & 0xFFFF
                fs.append((i, ln, data[i+4], data[i+5], data[i+6:i+ln-3], ck == s))
                i += ln; continue
        i += 1
    return fs

path = sys.argv[1] if len(sys.argv) > 1 else r"d:\work\techart\_sigrok\lens_mounts\sony_emount\a6000_ef50_viltrox_init.sr"
buf = load(path)
print("FILE:", path.split("\\")[-1])
# sigrok fx2lafw probe1=bit0 => probe4 RXD=bit3 (lens->body), probe5 TXD=bit4 (body->lens)
rxd = bits(buf, 3)
txd = bits(buf, 4)
bs = uart_decode(rxd)
fb = bytes(v for _, v in bs)
fr = frames(fb)
f05 = [f for f in fr if f[3] == 0x05 and f[5]]
f06 = [f for f in fr if f[3] == 0x06 and f[5]]
print("frames total=%d  0x05=%d  0x06=%d" % (len(fr), len(f05), len(f06)))
if f05:
    L = len(f05[0][4])
    print("\n0x05 body len=%d, per-byte variation over %d frames:" % (L, len(f05)))
    for j in range(L):
        vals = [f[4][j] for f in f05]
        u = sorted(set(vals))
        if len(u) > 1:
            print("  b[%02d] %3d uniq  min=0x%02X max=0x%02X seq=%s" % (j, len(u), min(vals), max(vals),
                  " ".join("%02X" % v for v in vals[:24])))
    statics = [j for j in range(L) if len(set(f[4][j] for f in f05)) == 1]
    print("  constant bytes:", " ".join("%02d:%02X" % (j, f05[0][4][j]) for j in statics))
if f06:
    L = len(f06[0][4])
    print("\n0x06 body len=%d, per-byte variation over %d frames:" % (L, len(f06)))
    for j in range(L):
        vals = [f[4][j] for f in f06]
        u = sorted(set(vals))
        if len(u) > 1:
            print("  b[%02d] %3d uniq  min=0x%02X max=0x%02X seq=%s" % (j, len(u), min(vals), max(vals),
                  " ".join("%02X" % v for v in vals[:28])))
    statics = [j for j in range(L) if len(set(f[4][j] for f in f06)) == 1]
    print("  constant bytes:", " ".join("%02d:%02X" % (j, f06[0][4][j]) for j in statics))
    # LE16 pairs view
    print("\n0x06 LE16 pairs (byte j,j+1):")
    for j in range(0, L - 1, 2):
        vals = [f[4][j] | (f[4][j+1] << 8) for f in f06]
        if len(set(vals)) > 1:
            print("  w[%02d] %s" % (j, " ".join("%04X" % v for v in vals[:28])))

# TXD side: body->lens 0x03/0x04 commands, is DEL per-frame?
bt = uart_decode(txd)
ft = frames(bytes(v for _, v in bt))
f04 = [f for f in ft if f[3] == 0x04 and f[5]]
f03 = [f for f in ft if f[3] == 0x03 and f[5]]
print("\nTXD 0x04 cmds=%d 0x03=%d" % (len(f04), len(f03)))
for tag, lst in (("0x04", f04), ("0x03", f03)):
    if not lst: continue
    L = len(lst[0][4])
    print(" %s body len=%d varying bytes:" % (tag, L))
    for j in range(L):
        vals = [f[4][j] for f in lst]
        if len(set(vals)) > 1:
            print("  b[%02d] seq=%s" % (j, " ".join("%02X" % v for v in vals[:24])))
    for j in range(0, L - 1, 2):
        vals = [f[4][j] | (f[4][j+1] << 8) for f in lst]
        if len(set(vals)) > 1:
            print("  w[%02d] %s" % (j, " ".join("%04X" % v for v in vals[:24])))
