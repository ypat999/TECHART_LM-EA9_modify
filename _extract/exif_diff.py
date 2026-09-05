# exif_diff.py - 3-way EXIF + MakerNote binary diff (native55 vs V3 vs G1).
# Goal: (a) full standard-tag table; (b) MakerNote byte-diff V3<->G1 = "body consumed abs-field" fingerprint;
#       (c) native vs adapter MN structure delta (what does a native lens populate that LM-EA9 leaves 0).
import struct, sys

def get_tiff(path):
    data = open(path, "rb").read()
    i = data.find(b"Exif\x00\x00")
    return data[i+6:]

class T:
    def __init__(self, t):
        self.t = t
        self.ltl = t[:2] == b"II"
        f = "<" if self.ltl else ">"
        self.f16 = f + "H"; self.f32 = f + "I"
    def u16(self, o): return struct.unpack_from(self.f16, self.t, o)[0]
    def u32(self, o): return struct.unpack_from(self.f32, self.t, o)[0]
    def walk(self, off, out, label="", depth=0):
        n = self.u16(off)
        for k in range(n):
            e = off + 2 + k * 12
            tag, typ, cnt = self.u16(e), self.u16(e + 2), self.u32(e + 4)
            sz = {1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8}.get(typ, 1) * cnt
            raw = self.t[e+8:e+12]   # ALWAYS inline 4B: value itself if sz<=4 else absolute offset u32
            key = (label + "!" if label else "") + "0x%04X" % tag
            out.append((key, typ, cnt, raw))
            if tag in (0x8769, 0xa005, 0x8825) and depth < 3:
                self.walk(self.u32(e + 8), out, "sub", depth + 1)
        return out

def load(path):
    t = get_tiff(path)
    tr = T(t)
    entries = tr.walk(tr.u32(4), [])
    mn = next((e for e in entries if e[0].endswith("0x927C")), None)
    return t, entries, mn

P55, PV3, PG1 = sys.argv[1], sys.argv[2], sys.argv[3]
t55, e55, mn55 = load(P55)
tv3, ev3, mnv3 = load(PV3)
tg1, eg1, mng1 = load(PG1)

def get(t, e):
    typ, cnt = e[1], e[2]
    return e[3]

print("== standard tag table (PARSED values, only where the three differ) ==")
def valstr(t, e):
    if e is None: return "-"
    typ, cnt, raw = e[1], e[2], e[3]
    f = "<" if T(t).ltl else ">"
    def u32(o): return struct.unpack_from(f + "I", t, o)[0]
    def u16(o): return struct.unpack_from(f + "H", t, o)[0]
    try:
        if typ in (1, 7):
            if cnt > 40: return "<%dB>" % cnt
            src = (raw[:cnt] if cnt <= 4 else t[u32(e and 0) if False else struct.unpack_from(f+"I", raw, 0)[0]:][:cnt])
            return src.hex(" ")
        if typ == 2:
            off = struct.unpack_from(f + "I", raw, 0)[0] if cnt > 4 else 0
            src = (raw[:cnt] if cnt <= 4 else t[off:off + cnt])
            return repr(src.decode("ascii", "replace").rstrip("\x00"))[:28]
        if typ == 3:
            if cnt <= 2: return str([struct.unpack_from(f + "H", raw, 2 * i)[0] for i in range(cnt)])
            off = struct.unpack_from(f + "I", raw, 0)[0]
            return str([u16(off + 2 * i) for i in range(min(cnt, 6))])
        if typ == 4:
            return str(struct.unpack_from(f + "I", raw, 0)[0] if cnt == 1 else [u32(struct.unpack_from(f + "I", raw, 0)[0] + 4 * i) for i in range(min(cnt, 4))])
        if typ == 5:
            off = struct.unpack_from(f + "I", raw, 0)[0]
            return " ".join("%d/%d" % (u32(off + 8 * i), u32(off + 8 * i + 4)) for i in range(min(cnt, 4)))
        if typ == 10:
            off = struct.unpack_from(f + "I", raw, 0)[0]
            return "%d/%d" % (u32(off), u32(off + 4))
    except Exception as ex:
        return "err:%s" % ex
    return raw.hex(" ")
d55 = {e[0]: e for e in e55}; d3 = {e[0]: e for e in ev3}; dg1 = {e[0]: e for e in eg1}
keys = sorted(set(d55) | set(d3) | set(dg1))
for k in keys:
    a, b, c = d3.get(k), dg1.get(k), d55.get(k)
    va, vb, vc = valstr(tv3, a), valstr(tg1, b), valstr(t55, c)
    if not (va == vb == vc):
        print("  %-16s V3=%-26s G1=%-26s NAT=%s" % (k, va[:26], vb[:26], vc[:34]))

def mnbytes(t, e):
    if e is None: return b""
    typ, cnt = e[1], e[2]
    if typ == 7 and cnt > 4:
        off = struct.unpack_from("<I", t, 0)[0]  # placeholder
    return e[3]  # only 16 bytes captured; get full from entry offset instead

print("\n== MakerNote V3 vs G1 byte diff (full) ==")
def mn_full(t, entries):
    e = next(x for x in entries if x[0].endswith("0x927C"))
    typ, cnt = e[1], e[2]
    off = e[3][:4]
    o = struct.unpack_from("<I", t, 0)  # not used
    # recompute: value offset stored in entry; entry raw[3] holds first-16 if >4, else inline.
    return o
# --- simpler: locate MN by searching for its known header 'SONY CAM ' / by absolute offset via u32 at entry
def mn_at(t, entries):
    # entry inline 4B (raw) IS the absolute offset u32 when cnt>4 (walk now always stores inline)
    for x in entries:
        if x[0].endswith("0x927C"):
            cnt = x[2]
            o = struct.unpack_from("<I", x[3] + b"\x00\x00\x00\x00", 0)[0] if cnt > 4 else 0
            return o, cnt
    return 0, 0
o3, l3 = mn_at(tv3, ev3); o1, l1 = mn_at(tg1, eg1); o5, l5 = mn_at(t55, e55)
print("  MN head check: V3=%r G1=%r NAT=%r" % (tv3[o3:o3+16], tg1[o1:o1+16], t55[o5:o5+16]))
print("  MN offsets/len: V3=%d/%d G1=%d/%d NAT=%d/%d" % (o3, l3, o1, l1, o5, l5))
m3 = tv3[o3:o3+l3]; m1 = tg1[o1:o1+l1]
diffs = [(i, m3[i], m1[i]) for i in range(min(len(m3), len(m1))) if m3[i] != m1[i]]
print("  V3 vs G1 MN diffs=%d%s" % (len(diffs), ("  first40: " + "; ".join("@%X:%02X->%02X" % d for d in diffs[:40])) if diffs else ""))
m5 = t55[o5:o5+l5]
dn = [(i, m3[i], m5[i]) for i in range(min(len(m3), len(m5))) if m3[i] != m5[i]]
print("  V3 vs NAT MN diffs=%d (len %d vs %d) first20: %s" % (len(dn), len(m3), len(m5),
      "; ".join("@X%X:%02X->%02X" % (i, a, b) for i, a, b in dn[:20])))

print("\n== MakerNote structured scan (mini-TIFF inside MN, Sony V2 style) ==")
def mn_scan(label, t, o, l):
    mn = t[o:o + l]
    for i in range(0, len(mn) - 8):
        if mn[i:i + 4] in (b"II*\x00", b"MM\x00*"):
            print("  %s: mini-TIFF@MN+0x%X (%s) ifdptr=%d" % (
                label, i, mn[i:i + 2].decode(), struct.unpack_from("<I", mn, i + 4)[0]))
            base = i
            tr = T(mn[base:])
            try:
                out = []
                tr.walk(tr.u32(4), out, label, 1)
                for e in out[:120]:
                    print("    %-14s typ%d cnt%d %s" % (e[0], e[1], e[2], e[3].hex(" ")[:20]))
            except Exception as ex:
                print("    walk err", ex)
            return
    print("  %s: no II*/MM* marker found" % label)
mn_scan("V3 ", tv3, o3, l3)
mn_scan("G1 ", tg1, o1, l1)
mn_scan("NAT", t55, o5, l5)
