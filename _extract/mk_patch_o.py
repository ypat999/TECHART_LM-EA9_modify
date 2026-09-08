# mk_patch_o.py - O generation: FIRST-EVER fill of the REAL optical rows (author repo docs/optical_data.md + msg_0x05.md).
# INDEXING TRUTH BOMBSHELL: author's pl[] indices are DECIMAL; our old hex b-labels sat 24 bytes off:
#   our "b2E/b30/b38" = pl[46/48/56] = APERTURE DESCRIPTOR zone (pl44..59) - NOT optical rows!
#   I-gen brick real cause: hex b3D(=pl60) FOCUS DIRECTION byte corrupted (legal 00/01/FF, we wrote 50/4A..).
#   REAL slot A = pl[32..37]  = FILE 0x4B82+32..37 (our-hex b20..25)
#   REAL slot B = pl[38..43]  = FILE 0x4B82+38..43 (our-hex b26..2B)
# EA9 runtime (=template): slotB = 26 00 00 00 00 00 = flat-1.5 NULL ROW (author names LM-EA9/Viltrox alike); slotA ~ zeros.
# Real rows harvested from OUR captures (sig_rows.py): selp1650
#   slotA grid  = a0 ec 6d 49 22 10   (0.23..0.46 tangent grid)
#   slotB type0 = 14 0a e0 fe 18 04   (p ~= 1.01..1.06 gentle curve)
#   slotB type1 = e1 b9 12 a6 e1 f6   (C/F ~= 0.027-0.029, F3.5-5.6-ish - closest to M40/5.6 in our corpus)
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
SA = N05B + 32   # slot A, DECIMAL 32..37
SB = N05B + 38   # slot B, DECIMAL 38..43
print("EA9 template slotA orig:", d0[SA:SA+6].hex(" "))
print("EA9 template slotB orig:", d0[SB:SB+6].hex(" "))

ROW_A    = bytes.fromhex("a0ec6d492210")     # selp1650 grid (16mm wide)
ROW_A_LOX = bytes.fromhex("b0fe45473927")    # Loxia 21/2.8 grid VERBATIM from author's table (closest class to M40!)
ROW_B0  = bytes.fromhex("140ae0fe1804")
ROW_B1  = bytes.fromhex("e1b912a6e1f6")

jobs = [
    ("O1", "27.1.0", 0x3A, [(SA, ROW_A)]),
    ("O2", "27.2.0", 0x3B, [(SB, ROW_B0)]),
    ("O3", "27.3.0", 0x3C, [(SA, ROW_A), (SB, ROW_B0)]),
    ("O4", "27.4.0", 0x3D, [(SB, ROW_B1)]),
    ("O5", "27.5.0", 0x3E, [(SA, ROW_A_LOX), (SB, ROW_B0)]),   # Loxia grid + type0 pupil = best-guess combo
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E

def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF

def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF; a[off+ln-2] = (c >> 8) & 0xFF

os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, edits in jobs:
    a = bytearray(d0)
    for off, by in edits:
        a[off:off+6] = by
    a[I07B+6] = nib
    raw = b"TECHART LM-EA9-" + tag.encode()
    a[I3FB+1:I3FB+19] = raw + bytes(18 - len(raw))
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 REAL optical rows %s VER %s (slot A/B pl32-43, selp1650 donor)" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%d ck_ok=%s  pl32..37=%s pl38..43=%s" % (tag, ver, diff, ok_ck,
          b[N05B+32:N05B+38].hex(" "), b[N05B+38:N05B+44].hex(" ")))
