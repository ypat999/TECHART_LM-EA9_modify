# sig_abs3.py - verify the THIRD focus field (0x06 frame body[26..27], dpreview "bytes 31/32")
# Entropy512 2015: native lenses fill absolute focus position ~ 110.85*sqrt(fp_mm), fp>=focal,
# grows as lens focuses closer; old Techart hardcodes 0x0162(354); LM-EA9 template = 0x0000 (never tried).
# Print per-frame sequence of 0x06 w[0x1A](b26/27), plus w2(b2/3) & w20(b20/21) for context.
import zipfile, sys, struct

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
        bs = uart_decode(rxd, spb)
        fr = frames(bytes(v for _, v in bs))
        if best is None or len(fr) > best[1]:
            best = (spb, len(fr), fr)
    spb, _, fr = best
    f06 = [f for f in fr if f[1] == 0x06 and len(f[2]) >= 28]
    print("\n== %s  (06 frames=%d)" % (path.split("\\")[-1], len(f06)))
    if f06:
        W = lambda b, j: struct.unpack_from("<H", b, j)[0]
        u26 = len(set(W(f[2], 26) for f in f06))
        print("  b[26..27] uniq=%d  seq: %s" % (u26, " ".join("%04X" % W(f[2], 26) for f in f06[:30])))
        print("  b[2..3]        seq: %s" % " ".join("%04X" % W(f[2], 2) for f in f06[:30]))
        print("  b[20..21]      seq: %s" % " ".join("%04X" % W(f[2], 20) for f in f06[:30]))
        print("  first full body: %s" % f06[0][2].hex(" "))
