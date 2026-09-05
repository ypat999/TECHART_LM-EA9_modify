# focus_exif.py - zero-dep EXIF FocusDistance reader (canary for "does the body consume abs-focus field").
# Usage: python focus_exif.py <file.ARW|file.JPG> [...]
# IFD0 tag 0x000D = FocusDistance (RATIONAL, meters; 0/0 typically = unknown/not reported).
# Sony ARW: TIFF header at offset 0; JPG: after APP1 "Exif\0\0". Walk IFD0 + ExifSubIFD; dump 0x000D
# plus nearby AF-ish tags. Also grep the whole file for any RATIONAL whose value is in 0.1..50 m.
import struct, sys

def find_tiff(data):
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return 0
    i = data.find(b"Exif\x00\x00")
    if i >= 0:
        return i + 6
    return None

def walk(tiff, name):
    e = tiff[:2]
    if e not in (b"II", b"MM"):
        print("  %s: bad endian %r" % (name, e)); return
    ltl = (e == b"II")
    fmt16 = "<H" if ltl else ">H"
    fmt32 = "<I" if ltl else ">I"
    def u16(o): return struct.unpack_from(fmt16, tiff, o)[0]
    def u32(o): return struct.unpack_from(fmt32, tiff, o)[0]
    def walk_ifd(ifd, label):
        if ifd == 0 or ifd + 2 > len(tiff):
            return
        n = u16(ifd)
        sub = None
        for k in range(n):
            ent = ifd + 2 + k * 12
            if ent + 12 > len(tiff):
                break
            tag, typ, cnt = u16(ent), u16(ent + 2), u32(ent + 4)
            if tag == 0x000D and typ == 0x000A:      # FocusDistance RATIONAL
                off = ent + 8 if cnt * 8 <= 4 else u32(ent + 8)
                if off + 8 <= len(tiff):
                    num, den = u32(off), u32(off + 4)
                    print("  %s tag0x000D FocusDistance = %d/%d = %s m" % (
                        label, num, den, ("%.3f" % (num / den) if den else "inf")))
            elif tag == 0x8769 and typ == 0x0004 and cnt == 1:
                sub = u32(ent + 8)
        if sub is not None and label != "ExifIFD":
            walk_ifd(sub, "ExifIFD")
    try:
        walk_ifd(u32(4), "IFD0")   # TIFF: 4-byte header then u32 IFD0 pointer @ offset 4
    except Exception as ex:
        print("  parse err:", ex)

def scan_rationals(tiff):
    # brute-force: any RATIONAL pair in-file with 0.05..100 m (sanity band for focus distance)
    hits = []
    for o in range(0, len(tiff) - 8, 2):
        for ltl in (True, False):
            f = "<II" if ltl else ">II"
            num, den = struct.unpack_from(f, tiff, o)
            if den and 0 < num / den < 100 and num < 1000000 and den < 100000:
                # want 'nice' rationals only (avoid noise): keep small den
                if den <= 10000 and (num % 10 == 0 or den % 10 == 0):
                    hits.append((o, num, den))
    return hits[:20]

for path in sys.argv[1:]:
    data = open(path, "rb").read()
    off = find_tiff(data)
    print("== %s (tiff@%s)" % (path.split("\\")[-1], off))
    if off is None:
        print("  no EXIF/TIFF found"); continue
    walk(data[off:], "EXIF")
