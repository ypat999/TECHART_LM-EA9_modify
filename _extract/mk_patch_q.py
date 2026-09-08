# mk_patch_q.py - Q generation v2: APERTURE DESCRIPTOR FAMILY (rewritten after user clarification)
#
# User facts (2026-09-08): (a) the EA9 CANNOT read the physical aperture ring -> the body always
# receives F2.0; (b) M40 true max aperture is F1.8 or faster; (c) all historical tests ran at F2.0
# (=> no hidden noise variable, past verdicts stand).
# Consequence: the "F1.8 > F2.0" sweet spot is a PURE OPTICAL effect, not a declaration effect, so
# v1's "declare honestly F5.6" premise was wrong (0x30 would be a lie in the narrower direction).
#
# Author msg_0x05 aperture table (authoritative):
#   pl[44] = maximum aperture        EA9 template 0x20 (F2.83), boot widens to 0x18 (F2.00)
#   pl[46] = pl[44]-8 (one stop wider, all 3 devices that use it)
#   pl[48] = 0xA0 constant, UNKNOWN  <- our K4 lives here (proven to affect AF speed on M40)
#   pl[51] = second copy of pl[44]
#   pl[52] = minimum aperture        EA9 0x50 (F22.6) -> boot 0x70 (F90)
#   "zeroing these six bytes made an a9 II display F1.0 and refuse to AF at all" => field IS read.
# Family invariants (from the template): pl[46]=pl[44]-8, pl[51]=pl[44], pl[52]=pl[44]+0x30?
#   (0x20/0x18/0x20/0x50 -> for max X: pl44=X, pl46=X-8, pl51=X, pl52=X+0x30)
# K-gen lesson re-read: K1 set pl[51] 0x20->0x18 ALONE => broke the pl[51]==pl[44] invariant =>
# "harmful" is explained by INCONSISTENCY, not by direction. So Q v2 always writes the whole family.
#
# FREE READOUT CHANNEL: unlike focal length / focus distance, the aperture value IS shown live on
# the body => note the displayed F-number after each flash: it attributes which byte feeds the body.
import struct, shutil, os

BIN = r"d:\work\techart\patches\EA9-V3.bin"
d0 = open(BIN, "rb").read()
assert len(d0) == 20172
N05B = 0x4B82
p44, p46, p48, p51, p52 = N05B+44, N05B+46, N05B+48, N05B+51, N05B+52
assert (d0[p44], d0[p46], d0[p48], d0[p51], d0[p52]) == (0x20, 0x18, 0xA0, 0x20, 0x50)
F = lambda v: 2 ** ((v - 8) / 16.0)

jobs = [
    ("Q1", "29.1.0", 0x43, [(p44, 0x16), (p46, 0x0E), (p51, 0x16), (p52, 0x46)],
     "family: declare F1.83 (=M40 true max / optical sweet spot)"),
    ("Q2", "29.2.0", 0x44, [(p44, 0x10), (p46, 0x08), (p51, 0x10), (p52, 0x40)],
     "family: declare F1.41 (faster-than-truth; if M40 is a 1.4 lens this is the honest value)"),
    ("Q3", "29.3.0", 0x45, [(p44, 0x28), (p46, 0x20), (p51, 0x28), (p52, 0x58)],
     "family: declare F4.00 (declared NARROWER = predicted worse => falsification control)"),
    ("Q4", "29.4.0", 0x46, [(p44, 0x16), (p46, 0x0E), (p51, 0x16), (p52, 0x46), (p48, 0x88)],
     "Q1 family + K4(pl48=88) = final recipe candidate"),
    ("Q5", "29.5.0", 0x47, [(p46, 0x16)],
     "single-point attribution: only pl[46] -> F1.83 (pl[44] stays F2.83) - display value tells who feeds the body"),
    # ---- Q1 VERDICT (user, 2026-09-08): body STILL shows F2.0 after Q1 => the displayed max
    # aperture is NOT fed by any byte we can reach statically. Flash image scan (re_aperture2/3.py):
    # the family copy exists exactly ONCE (@0x4BAE) and the widened pair 0x18/0x70 is nowhere in the
    # image => the ring's code recomputes pl[44]/pl[51] (and pl[52]) at runtime; author's own capture
    # agrees (table 0x20/0x50 vs wire 0x18/0x70). So: which offsets are table-sourced and survive onto
    # the wire? pl[48] is our only alleged hit (I7/K4) and the whole "pupil axis" rests on it.
    # Q6 = liveness-or-placebo probe on that byte: degenerate 0x00 (author: zeroing this region made
    # an a9 II refuse to AF at all). CLEAR degradation/no-AF => pl[48] is wire-live => I7/K4 legit.
    # Indistinguishable from V3 => pl[48] is dead static data => I7/K4 were impressions => the pupil
    # axis must be re-established by A/B counting or dropped, and the real work is code-level.
    ("Q6", "29.6.0", 0x48, [(p48, 0x00)],
     "liveness probe: pl[48]=0x00 (degenerate)"),
    # ---- Q6 VERDICT (user, 2026-09-08): version display showed "48" (=our init07 nibble marker,
    # so the flash init-frame template IS reaching the body = good self-check channel) but
    # "对焦没有明显差异" => three readings, all still open:
    #  (i) pl[48] never reaches the wire (norm05 assembled by code) => I7/K4 were impressions;
    # (ii) pl[48] reaches it but the body/code treats 0x00 as "use default" (very common!) =>
    #      my probe value was self-defeating;
    # (iii) it is live but the AF-impression criterion is too noisy to resolve it.
    # => Q7/Q8 re-probe with NONZERO absurd values on the whole u16 (both directions), so a
    # zero-default fallback cannot mask them:
    #   Q7: pl[48..49] = 02 00  -> u16 2   -> /128 = 0.016 (absurd low, nonzero)
    #   Q8: pl[48..49] = FF FF  -> u16 65535 -> /128 = 512  (absurd high)
    # If BOTH are flat => (i) confirmed: the norm05 payload region we have been editing for 6
    # generations does not reach the body; every I/J/K/L/M/N verdict is void; static work stops.
    ("Q7", "29.7.0", 0x49, [(p48, 0x02), (p48 + 1, 0x00)],
     "nonzero absurd-low probe: u16 pl[48..49]=2 (no zero-default escape)"),
    ("Q8", "29.8.0", 0x4A, [(p48, 0xFF), (p48 + 1, 0xFF)],
     "absurd-high probe: u16 pl[48..49]=65535"),
    # ---- ★Canary upgrade: is the norm05 PAYLOAD served from our flash table at all?
    # F1 wrote focal=280 (28mm) but 28mm is a real EA9 preset -> a "28" readout would be ambiguous
    # (preset path could produce it). D-gen proved the body displays the ring's focal value
    # verbatim including off-list numbers (44/56/64/80mm), so use a value NO preset can make:
    # pl[24..25]=pl[26..27]=137 -> 13.7mm.
    #   shows 13.7/14 => norm05 payload IS table-sourced => static layer alive, and the aperture /
    #                    optical-row nulls are per-field runtime writes (targeted code patches);
    #   still 40      => this field is code-filled (preset path) => static norm05 edits unreliable
    #                    => I/J/K/L/M/N verdicts treated as unproven, go code-level.
    ("Q9", "29.9.0", 0x4B, [(N05B + 24, 137 & 0xFF), (N05B + 25, 137 >> 8),
                            (N05B + 26, 137 & 0xFF), (N05B + 27, 137 >> 8)],
     "★HARD-READOUT CANARY: declared focal length 400 -> 137 (13.7mm, no preset can produce it)"),
]

I07, I07L, I07B = 0x4A38, 43, 0x4A3E
I3F, I3FL, I3FB = 0x4C08, 74, 0x4C0E


def sum_ck(a, off, ln):
    return sum(a[off+1: off+ln-3]) & 0xFFFF


def write_ck(a, off, ln):
    c = sum_ck(a, off, ln)
    a[off+ln-3] = c & 0xFF
    a[off+ln-2] = (c >> 8) & 0xFF


os.makedirs(r"d:\work\techart\flash_kit\product\firmware\LM-EA9", exist_ok=True)
for tag, ver, nib, edits, note in jobs:
    a = bytearray(d0)
    for off, bv in edits:
        a[off] = bv
    a[I07B+6] = nib
    raw = b"TECHART LM-EA9-" + tag.encode()
    a[I3FB+1:I3FB+19] = raw + bytes(18 - len(raw))
    write_ck(a, I07, I07L)
    write_ck(a, I3F, I3FL)
    write_ck(a, N05B - 6, 105)
    fn = "EA9-%s.bin" % tag
    open(r"d:\work\techart\patches" + "\\" + fn, "wb").write(bytes(a))
    shutil.copy(r"d:\work\techart\patches" + "\\" + fn,
                r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn)
    open(r"d:\work\techart\flash_kit\product\firmware\LM-EA9" + "\\" + fn.replace(".bin", ".txt"), "w").write(
        "LM-EA9 aperture family %s VER %s" % (tag, ver))
    lst = ("TECHART LM-EA9;0483;575A;VER %s;Copyright TECHART Inc.;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s;"
           "http://www.techart-logic.com/product/firmware/LM-EA9/%s") % (ver, fn, fn.replace(".bin", ".txt"))
    open(r"d:\work\techart\flash_kit\lsts\TECHART_LST_%s.txt" % tag, "w").write(lst + "\n")
    b = open(r"d:\work\techart\patches" + "\\" + fn, "rb").read()
    assert len(b) == 20172
    diff = sum(1 for x, y in zip(d0, b) if x != y)
    ok_ck = all(sum_ck(b, off, ln) == struct.unpack_from("<H", b, off+ln-3)[0]
                for off, ln in ((I07, I07L), (I3F, I3FL), (N05B - 6, 105)))
    print("%s ver=%s diff=%2d ck_ok=%s | pl44=%02X(%s) pl46=%02X(%s) pl48=%02X pl51=%02X(%s) pl52=%02X(%s)  # %s" % (
        tag, ver, diff, ok_ck,
        b[p44], "F%.2f" % F(b[p44]), b[p46], "F%.2f" % F(b[p46]), b[p48],
        b[p51], "F%.2f" % F(b[p51]), b[p52], "F%.2f" % F(b[p52]), note))
