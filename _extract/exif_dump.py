# exif_dump.py - full standard EXIF dump (IFD0+ExifIFD+Interoperability) for Sony JPGs,
# plus targeted MakerNote scan for focus-related entries. Usage: python exif_dump.py file.JPG [...]
import struct, sys

TAGN = {0x010e:"ImageDescription",0x010f:"Make",0x0110:"Model",0x0112:"Orientation",0x011a:"XRes",0x011b:"YRes",
        0x0128:"ResUnit",0x0131:"Software",0x0132:"DateTime",0x829a:"ExposureTime",0x829d:"FNumber",
        0x8822:"ExposureProgram",0x8827:"ISOSpeed",0x8830:"SensitivityType",0x9003:"DateTimeOriginal",
        0x9004:"DateTimeDigitized",0x9201:"ShutterSpeed",0x9202:"Aperture",0x9203:"Brightness",
        0x9204:"ExposureBias",0x9205:"MaxAperture",0x9206:"SubjectDist",0x9207:"MeteringMode",
        0x9208:"LightSource",0x9209:"Flash",0x920a:"FocalLength",0x927c:"MakerNote",0x9286:"UserComment",
        0xa002:"PixWidth",0xa003:"PixHeight",0xa20e:"ScalePMF",0xa20f:"FocalXRes",0xa210:"FocalYRes",
        0xa20e:"ScalePM",0x000d:"FocusDistance!!",0x000c:"WhiteRatio",0x0100:"InteropIndex"}

def load_jpg_tiff(data):
    i = data.find(b"Exif\x00\x00")
    if i < 0: return None
    return data[i+6:]

class IFD:
    def __init__(self, t):
        self.t = t
        self.ltl = t[:2] == b"II"
        f = "<" if self.ltl else ">"
        self.u16 = lambda o: struct.unpack_from(f+"H", t, o)[0]
        self.u32 = lambda o: struct.unpack_from(f+"I", t, o)[0]
    def parse(self, off, label, depth=0):
        if off == 0 or off + 2 > len(self.t) or depth > 3: return
        n = self.u16(off)
        print("  [%s] %d entries" % (label, n))
        for k in range(n):
            e = off + 2 + k*12
            if e + 12 > len(self.t): break
            tag, typ, cnt = self.u16(e), self.u16(e+2), self.u32(e+4)
            sz = {1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8}.get(typ, 1) * cnt
            valoff = e + 8 if sz <= 4 else self.u32(e+8)
            def fmt_vals():
                try:
                    if typ == 2: return self.t[valoff:valoff+cnt].decode("ascii","replace").rstrip("\x00")
                    if typ == 3: return str(struct.unpack_from(("<" if self.ltl else ">")+str(cnt)+"H", self.t, valoff))
                    if typ == 4: return str(struct.unpack_from(("<" if self.ltl else ">")+str(cnt)+"I", self.t, valoff))
                    if typ == 5:
                        v = struct.unpack_from(("<" if self.ltl else ">")+str(cnt*2)+"I", self.t, valoff)
                        return " ".join("%d/%d" % (v[2*i], v[2*i+1]) for i in range(cnt))
                except Exception: pass
                return "?"
            name = TAGN.get(tag, "tag%04X" % tag)
            if typ in (1,7) and cnt > 40:
                print("    %-18s = <%d bytes raw>" % (name, cnt))
            else:
                print("    %-18s = %s" % (name, fmt_vals()))
            if tag == 0x8769: self.parse(self.u32(e+8), "ExifIFD", depth+1)
            if tag == 0xa005: self.parse(self.u32(e+8), "Interop", depth+1)
        # next ifd
        try:
            nxt = self.u16(off + 2 + n*12) if False else self.u32(off + 2 + n*12)
        except Exception:
            nxt = 0

def maker_note_scan(t, mnoff, mncnt):
    # scan maker note as u16 sequence: find 0x000d 0x0002? Sony MN is not standard IFD; brute:
    print("  [MakerNote scan] len=%d" % mncnt)
    mn = t[mnoff:mnoff+mncnt]
    # look for LE/BE RATIONAL with plausible focus values anywhere in MN
    for o in range(0, len(mn)-8):
        num, den = struct.unpack_from("<II", mn, o)
        if den and 0 < num/den < 60 and den % 1000000 == 0 and num % 1000000 == 0:
            print("    LE rational @%04X = %.2f" % (o, num/den))

for path in sys.argv[1:]:
    data = open(path, "rb").read()
    t = load_jpg_tiff(data)
    print("== %s" % path.split("\\")[-1])
    if t is None: print("  no exif"); continue
    ifd = IFD(t)
    try:
        ifd.parse(ifd.u32(4), "IFD0")
    except Exception as ex:
        print("  err", ex)
