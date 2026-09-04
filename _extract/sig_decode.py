# sigrok sony_emount .sr(v2, per-chunk zip members) -> samples -> UART decode -> E-mount frames
# probe bit map (sigrok fx2lafw, probe1=bit7 MSB): probe1 VD=bit7, VCC=bit6, LENS_CS=bit5,
# RXD(lens->body)=bit4, TXD(body->lens)=bit3, BODY_CS=bit2. 6MHz, 8N1 lsb-first.
# Usage: python sig_decode.py <file.sr> [max_frames]
import zipfile, sys, collections

def load_samples(path):
    z = zipfile.ZipFile(path)
    names = [i.filename for i in z.infolist() if i.filename.startswith("logic-1-")]
    def keyf(s): return int(s.split("-")[-1])
    names.sort(key=keyf)
    buf = b"".join(z.read(n) for n in names)   # zipfile inflates each member
    return buf

def bits(buf, bit):
    m = 1 << bit
    return bytes(1 if (b & m) else 0 for b in buf)

def uart_decode(sig, spb, idle=1):
    # returns list of (start_idx, byte)
    out = []
    i, n = 0, len(sig)
    half = spb // 2
    while i < n - spb * 9:
        if i > 0 and sig[i] == 0 and sig[i - 1] == idle:  # falling edge = start bit
            # frame validity: check start bit stays low at center
            if sig[i + half] != 0:
                i += 1; continue
            val = 0
            ok = True
            for b in range(8):
                c = i + spb * (b + 1) + half
                if c >= n: ok = False; break
                bit = sig[c]
                val |= bit << b
            sb = i + spb * 9 + half
            if ok and sb < n and sig[sb] == 1:
                out.append((i, val))
                i += spb * 10  # past stop + margin
                continue
        i += 1
    return out

def estimate_spb(sig):
    # histogram of low-pulse widths (run lengths) -> common divisor
    runs = []
    i, n = 0, len(sig)
    cur = 0
    for v in sig:
        if v == 0: cur += 1
        else:
            if cur > 0: runs.append(cur); cur = 0
    hist = collections.Counter(runs)
    if not runs: return None, hist
    modes = [r for r, c in hist.items() if c >= 5]
    if not modes: return None, hist
    return min(modes), hist  # shortest common low run ~ 1 bit (start bit) at given baud

def frames_from_bytes(byte_stream):
    # scan for F0 ... 55 frames of E-mount protocol
    fs = []
    data = byte_stream
    i = 0
    n = len(data)
    while i < n - 10:
        if data[i] == 0xF0:
            ln = data[i+1] | (data[i+2] << 8)
            if 10 <= ln <= 300 and i + ln <= n and data[i+ln-1] == 0x55:
                cls, seq, typ = data[i+3], data[i+4], data[i+5]
                if cls in (0,1,2):
                    body = data[i+6:i+ln-3]
                    ck = data[i+ln-3] | (data[i+ln-2] << 8)
                    s = sum(data[i+1:i+ln-3]) & 0xFFFF
                    fs.append((i, ln, cls, seq, typ, body, ck, ck == s))
                    i += ln
                    continue
        i += 1
    return fs

def main():
    path = sys.argv[1]
    buf = load_samples(path)
    print("samples:", len(buf), "= %.3fs @6MHz" % (len(buf)/6e6))
    rxd = bits(buf, 4); txd = bits(buf, 3)
    lcs = bits(buf, 5); bcs = bits(buf, 2)
    for name, sig, cs in (("RXD(lens->body)", rxd, lcs), ("TXD(body->lens)", txd, bcs)):
        spb_est, hist = estimate_spb(sig)
        print("\n==== %s: shortest-low-run est=%s run_hist(top10)=%s" % (name, spb_est, sorted(hist.items())[:10]))
        for spb in (8, 4, 13):
            bs = uart_decode(sig, spb)
            fb = bytes(v for _, v in bs)
            fr = frames_from_bytes(fb)
            good = [f for f in fr if f[7]]
            print("  spb=%d: bytes=%d frames=%d ck_ok=%d" % (spb, len(fb), len(fr), len(good)))
            if good:
                types = collections.Counter(f[4] for f in good)
                print("   type hist:", dict(sorted(types.items())))
                # dump 0x05/0x06 positions
                shown = 0
                for f in good:
                    if f[4] in (0x05, 0x06) and shown < 12:
                        pos1 = f[5][2] | (f[5][3] << 8) if len(f[5]) > 3 else None
                        pos2 = f[5][20] | (f[5][21] << 8) if len(f[5]) > 21 else None
                        print("   t=0x%02X len=%d pos1=0x%04X(%d) pos2=%s body=%s" % (
                            f[4], f[1], pos1 or 0, pos1 or 0,
                            ("0x%04X(%d)" % (pos2, pos2)) if pos2 is not None else "-",
                            f[5][:28].hex(" ")))
                        shown += 1
main()
