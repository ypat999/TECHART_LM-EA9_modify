# mk_patch_q.py - Q generation: HONEST APERTURE DECLARATION (user's aperture-sweet-spot observation
# + author's msg_0x05 field table cross-locked).
# Facts: pl[44..59]=aperture descriptor, Canon EF convention F=2^((v-8)/16, verified: VX EF50 pl[51]=0x16
# -> F1.83 = its true max aperture = CERTAIN semantics). EA9 template: pl[44]=0x20(F2.83) pl[46]=0x18(F2.00)
# pl[51]=0x20(F2.83) -- declares ~F2.8 for ANY mounted lens (35/2.8 legacy). M40 true F5.6 -> v=48=0x30.
# K-gen lesson (pl51 0x20->0x18 "harmful") re-read: pushing declaration FURTHER from reality hurt =>
# symmetric prediction: declaring reality (F5.66) should HELP. Also user body-side: AF success peaks at
# F1.8 set-value on M40 (body strategy input) - independent channel, keep fixed during tests!
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
p44, p46, p48, p51 = N05B+44, N05B+46, N05B+48, N05B+51
assert d0[p44] == 0x20 and d0[p46] == 0x18 and d0[p48] == 0xA0 and d0[p51] == 0x20

V566 = 0x30   # F5.66  (M40 truth)
V734 = 0x36   # F7.34  (bracket overshoot)

jobs = [
    ("Q1", "28.1.0", 0x3F, [(p51, V566)]),                                   # honest max-aperture decl
    ("Q2", "28.2.0", 0x40, [(p51, V566), (p44, V566), (p46, V566)]),         # full triple alignment
    ("Q3", "28.3.0", 0x41, [(p51, V734)]),                                   # bracket (overshoot)
    ("Q4", "28.4.0", 0x42, [(p51, V566), (p48, 0x88)]),                      # honest + K4 live byte = final recipe candidate
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
    for off, bv in edits:
        a[off] = bv
    a[I07B+6] = nib
    raw = b"TECHART LM-EA9-" + tag.encode()
    a[I3FB+1:I3FB+19] = raw + bytes(18 - len(raw))
    write_ck(a, I07, I07L); write_ck(a, I3F, I3FL); write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn, r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 honest aperture decl %s VER %s" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%d ck_ok=%s  pl44=%02X pl46=%02X pl48=%02X pl51=%02X" % (tag, ver, diff, ok_ck,
          b[p44], b[p46], b[p48], b[p51]))
