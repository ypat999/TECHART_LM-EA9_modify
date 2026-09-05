# mk_patch_g.py - G generation: fill the THIRD focus field (0x06 frame body[26..27]) = absolute focus position.
# Evidence (dpreview Entropy512 RE 2015 + our sig_abs3 re-verification of the 5 sigrok captures 2026-09-05):
#   every REAL lens populates it ~110.85*sqrt(fp_mm) (fp>=focal, grows focusing closer):
#     SEL55210@55inf=0x0319 @210inf=0x0694/5  SELP1650@16=0x01FE  Viltrox EF50=0x02B3  EFS24=0x03C8
#   LM-EA9 template = 0x0000 (ONLY device never filling it). Old Techart EF-adapter hardcoded 0x0162(=354)
#   and Entropy linked that field to MF-assist not triggering, no distance display, worsening AF at long FL.
# Runtime mirror 0x6134 overwrites only b[2..3]/b[20..21] => b[26..27] stays at template => static patch is clean.
# M40 (fl=40mm): inf -> 110.85*sqrt(40)=701.6=0x02BE ; 1m -> fp=41.67mm -> 715.7=0x02CB ; 0.5m -> 731=0x02DB
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172

# locate ALL class01 typ06 48B frames (norm06 copies) and assert b[26..27]==0
sites = []
i = 0
while i < len(d0) - 10:
    if d0[i] == 0xF0:
        ln = d0[i+1] | (d0[i+2] << 8)
        if 10 <= ln <= 300 and i + ln <= len(d0) and d0[i+ln-1] == 0x55 and d0[i+3] == 1 and d0[i+5] == 0x06:
            b26 = struct.unpack_from("<H", d0, i + 6 + 26)[0]
            assert b26 == 0, (hex(i), hex(b26))
            sites.append(i)
            i += ln; continue
    i += 1
print("norm06 sites:", [hex(s) for s in sites])
assert sites == [0x49D4], sites

jobs = [
    ("G1", "19.1.0", 0x8A, 0x02BE),   # 702  = M40 @ infinity
    ("G2", "19.2.0", 0x8B, 0x02CB),   # 715  = M40 @ ~1m
    ("G3", "19.3.0", 0x8C, 0x0162),   # 354  = old Techart EF-II hardcode (tests "any nonzero")
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E
N06, N06L = 0x49D4, 48

def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF

def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF; a[off+ln-2] = (c >> 8) & 0xFF

def name18(tag):
    raw = b"TECHART LM-EA9-" + tag.encode()
    assert len(raw) <= 18
    return raw + bytes(18 - len(raw))

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, absv in jobs:
    a = bytearray(d0)
    for s in sites:
        struct.pack_into("<H", a, s + 6 + 26, absv)
    a[I07B+6] = nib
    a[I3FB+1:I3FB+19] = name18(tag)
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N06, N06L)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 abs-focus-fill %s VER %s (06 b26/27=%d, base=V3)" % (tag, ver, absv))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N06, N06L)))
    got = struct.unpack_from("<H", b, N06 + 6 + 26)[0]
    print("%s ver=%s abs=%d(0x%04X) diff=%d ck_ok=%s" % (tag, ver, got, got, diff, ok_ck))
