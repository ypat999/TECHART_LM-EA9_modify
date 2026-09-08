# sig_rows.py - extract DECIMAL-indexed optical rows from real-lens 0x05 frames in our captures:
# slotA = pl[32..37], slotB = pl[38..43]  (author's index base is DECIMAL - our old hex b-labels were offset by 24!)
# Decode with author's block-float: v0=((b0&0xF)<<8)|b1; E=(b0>>4)&7 (wraps, per-slot anchor b=11 for A);
# deltas signed; value=v*2^-E. type = b0 bit7.
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

def s8(b):
    return b - 256 if b > 127 else b

def decode_row(r, Eabs):
    v = (r[0] & 0xF) << 8 | r[1]
    out = [v]
    for b in r[2:6]:
        v += s8(b); out.append(v)
    return [x / 2.0 ** Eabs for x in out]

for path in sys.argv[1:]:
    buf = load(path)
    rxd = bits(buf, 3)
    best = None
    for spb in (8, 4):
        fr = frames(bytes(v for _, v in uart_decode(rxd, spb)))
        if best is None or len(fr) > best[0]:
            best = (len(fr), fr)
    fr = best[1]
    f05 = [f for f in fr if f[1] == 0x05 and len(f[2]) >= 44]
    print("== %s  05 frames=%d" % (path.split("\\")[-1], len(f05)))
    seen = set()
    for f in f05:
        A = f[2][32:38]; B = f[2][38:44]
        key = (A.hex(), B.hex())
        if key in seen:
            continue
        seen.add(key)
        ta = "T1" if A[0] & 0x80 else "T0"; tb = "T1" if B[0] & 0x80 else "T0"
        Ea = ((A[0] >> 4) & 7); Eb = ((B[0] >> 4) & 7)
        # print raw + decoded under anchor E=11 for type1 slot A/B (author convention)
        s = "%s | A=%s(%s e%d) B=%s(%s e%d)" % (
            "init" if len(seen) <= 3 else "    ", A.hex(" "), ta, Ea, B.hex(" "), tb, Eb)
        try:
            if A != bytes(6) and A[0] != 0:
                s += "  A->%s" % ["%.4f" % x for x in decode_row(A, 11 if ta == "T1" else Ea)]
        except Exception:
            pass
        try:
            if B != bytes(6) and B[0] != 0:
                # anchor empirically: type1 E_abs = nibble (Loxia f4 -> 15 -> 0.0364 matches author);
                # type0 E_abs = nibble + 10 (selp1650 nibble1 -> 11 -> 2.02 = author's table p)
                EB = (B[0] >> 4) if tb == "T1" else (B[0] >> 4) + 10
                s += "  B->%s" % ["%.4f" % x for x in decode_row(B, EB)]
        except Exception:
            pass
        print("  " + s)
