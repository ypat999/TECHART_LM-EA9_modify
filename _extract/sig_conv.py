# sig_conv.py - merged timeline dialogue log (RXD+TXD) for sigrok sony_emount captures.
# Goal: answer "when does the BODY consume lens position" - query cadence, 0x04 move cmd bursts,
#       whether 0x06/0x05 position frames interleave with body commands during motion.
# NOTE channel map (verified via sig_stats.py): RXD(lens->body)=bit3, TXD(body->lens)=bit4.
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

def frames_ts(byte_ts):  # [(idx,val)] -> [(idx, ln, cls, seq, typ, body, ckok, raw)]
    bs = [v for _, v in byte_ts]
    idxs = [i for i, _ in byte_ts]
    data = bytes(bs); fs = []; i = 0; n = len(data)
    while i < n - 10:
        if data[i] == 0xF0:
            ln = data[i+1] | (data[i+2] << 8)
            if 10 <= ln <= 300 and i + ln <= n and data[i+ln-1] == 0x55 and data[i+3] in (0,1,2):
                ck = data[i+ln-3] | (data[i+ln-2] << 8)
                s = sum(data[i+1:i+ln-3]) & 0xFFFF
                fs.append((idxs[i], ln, data[i+3], data[i+4], data[i+5], data[i+6:i+ln-3], ck == s, data[i:i+ln]))
                i += ln; continue
        i += 1
    return fs

def spb_for(sig, cands=(8, 4, 13)):
    best = None
    for spb in cands:
        n = len(uart_decode(sig, spb))
        if best is None or n > best[1]:
            best = (spb, n)
    return best[0]

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 120
buf = load(path)
dur_ms = len(buf) / 6e3
print("FILE: %s  samples=%d  dur=%.1fms" % (path.split("\\")[-1], len(buf), dur_ms))
rxd, txd = bits(buf, 3), bits(buf, 4)
sr = spb_for(rxd); st = spb_for(txd)
fr = frames_ts(uart_decode(rxd, sr))
ft = frames_ts(uart_decode(txd, st))
print("RXD spb=%d frames=%d ck_ok=%d | TXD spb=%d frames=%d ck_ok=%d" % (
    sr, len(fr), sum(1 for f in fr if f[6]), st, len(ft), sum(1 for f in ft if f[6])))
ev = [(f[0], "L>B", f) for f in fr] + [(f[0], "B>L", f) for f in ft]  # f[0]=sample idx = true time
ev.sort(key=lambda e: e[0])
tcnt = collections.Counter()
for _, d, f in ev:
    tcnt[(d, f[2], f[4])] += 1
print("\ntype hist (dir,cls,typ):")
for k, v in sorted(tcnt.items()):
    print("  %s cls%02X typ%02X x%d" % (k[0], k[1], k[2], v))
print("\ntimeline (t_ms dir cls.seq.typ body[:20]):")
for e in ev[:limit]:
    i, d, f = e
    t = i / 6000.0
    print("  %9.2f %s %02X.%02X.%02X len=%3d %s" % (t, d, f[2], f[3], f[4], f[1], f[5][:20].hex(" ")))
