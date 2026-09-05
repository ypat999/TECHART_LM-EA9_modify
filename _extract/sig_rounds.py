# sig_rounds.py - per-round AF waveform from sigrok captures:
# each dialogue round = B>L 03(target..) + B>L 04(move) + L>B 05(cur/tgt) + L>B 06(status)
# prints compact table: t_ms | 03.w0 | 03.w2 | 03.w4 | 04.b0..b7 | 05.w0(cur) | 05.w2(tgt) | 06.w0 | 06.w2 | 06.w4 | 06.w8
import zipfile, sys, collections

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

def frames_ts(byte_ts):
    bs = [v for _, v in byte_ts]; idxs = [i for i, _ in byte_ts]
    data = bytes(bs); fs = []; i = 0; n = len(data)
    while i < n - 10:
        if data[i] == 0xF0:
            ln = data[i+1] | (data[i+2] << 8)
            if 10 <= ln <= 300 and i+ln <= n and data[i+ln-1] == 0x55 and data[i+3] in (0,1,2):
                ck = data[i+ln-3] | (data[i+ln-2] << 8)
                s = sum(data[i+1:i+ln-3]) & 0xFFFF
                fs.append((idxs[i], ln, data[i+3], data[i+4], data[i+5], data[i+6:i+ln-3], ck == s))
                i += ln; continue
        i += 1
    return fs

def spb_for(sig, cands=(8, 4, 13)):
    best = None
    for spb in cands:
        n = len(uart_decode(sig, spb))
        if best is None or n > best[1]: best = (spb, n)
    return best[0]

def W(b, j): return b[j] | (b[j+1] << 8) if len(b) > j+1 else -1

path = sys.argv[1]
buf = load(path)
rxd, txd = bits(buf, 3), bits(buf, 4)
fr = frames_ts(uart_decode(rxd, spb_for(rxd)))
ft = frames_ts(uart_decode(txd, spb_for(txd)))
print("FILE:", path.split("\\")[-1], " L>B frames=%d  B>L frames=%d" % (len(fr), len(ft)))
print("%9s | 03.w0 03.w2 03.w4 | 05.cur 05.tgt  d(cur) | 06.w0  06.w2  06.w4  06.w8 | 04.body" % "t_ms")
# interleave by seq: group rounds by body>lens 03+04 pair, attach following lens 05/06
c3 = [f for f in ft if f[4] == 0x03]
c4 = [f for f in ft if f[4] == 0x04]
r5 = [f for f in fr if f[4] == 0x05]
r6 = [f for f in fr if f[4] == 0x06]
def nxt(lst, t):
    for f in lst:
        if f[0] >= t: return f
    return None
for a in c3:
    t = a[0]
    b4 = nxt(c4, t); b5 = nxt(r5, t); b6 = nxt(r6, t)
    cur = W(b5[5], 0) if b5 else -1
    tgt = W(b5[5], 2) if b5 else -1
    d = cur - tgt if cur >= 0 and tgt >= 0 else 0
    print("%9.2f | %5d %5d %5d | %6d %6d %5d | %5d %5d %5d %5d | %s" % (
        t/6000.0, W(a[5],0), W(a[5],2), W(a[5],4), cur, tgt, d,
        W(b6[5],0) if b6 else -1, W(b6[5],2) if b6 else -1, W(b6[5],4) if b6 else -1, W(b6[5],8) if b6 else -1,
        (b4[5][:8].hex(" ") if b4 else "-")))
