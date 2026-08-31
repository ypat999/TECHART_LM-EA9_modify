param(
    [string]$Bin = "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin",
    [string]$OutDir = "d:\work\techart\patches"
)

# ---------- helpers ----------
function Get-LexArray([string]$name) {
    $t = Get-Content "d:\work\techart\_extract\lex_constants.h" -Raw
    $m = [regex]::Match($t, "const byte $name\[\]\s*=\s*\{([^}]*)\}")
    if (-not $m.Success) { throw ("lex array not found: " + $name) }
    $bs = @()
    foreach ($h in [regex]::Matches($m.Groups[1].Value, "0x([0-9A-Fa-f]{2})")) {
        $bs += [Convert]::ToByte($h.Groups[1].Value, 16)
    }
    return ,$bs
}

function Sum-FrameCk($arr, [int]$off, [int]$len) {
    $s = 0
    for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }
    return ($s -band 0xFFFF)
}

function Write-FrameCk($arr, [int]$off, [int]$len) {
    $old = [int]$arr[$off + $len - 3] + ([int]$arr[$off + $len - 2] * 256)
    $new = Sum-FrameCk $arr $off $len
    $arr[$off + $len - 3] = [byte]($new -band 0xFF)
    $arr[$off + $len - 2] = [byte](($new -shr 8) -band 0xFF)
    return (@($old, $new))
}

function Assert-Bytes($arr, [int]$off, [int[]]$expect) {
    for ($i = 0; $i -lt $expect.Count; $i++) {
        if ([int]$arr[$off + $i] -ne $expect[$i]) {
            throw ("byte assert failed at 0x{0:X} : got {1:X2} expect {2:X2}" -f ($off + $i), $arr[$off + $i], $expect[$i])
        }
    }
}

function Set-Bytes($arr, [int]$off, [int[]]$vals) {
    for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] }
}

function Hex-Bytes($arr, [int]$off, [int]$count) {
    ($arr[$off..($off + $count - 1)] | ForEach-Object { $_.ToString("X2") }) -join ""
}

function Save-Patch($arr, [string]$file) {
    [System.IO.File]::WriteAllBytes($file, $arr)
    Write-Output ("saved " + $file + " size=" + $arr.Length)
}

# ---------- frame anchors (verified by cksum_scan.ps1) ----------
$N05_OFF = 0x4B7C; $N05_LEN = 105     # norm05  cls01 seq64 typ05
$I01_OFF = 0x4A0C; $I01_LEN = 41      # init01  cls02 typ01
$I08_OFF = 0x4A88; $I08_LEN = 210     # init08  cls02 typ08
$BODY_N05 = $N05_OFF + 6              # norm05 body start
$BODY_I01 = $I01_OFF + 6              # init01 body start

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$orig = [System.IO.File]::ReadAllBytes($Bin)
Write-Output ("orig size=" + $orig.Length)
if ($orig.Length -ne 20172) { throw "unexpected bin size" }

# anchor sanity
Assert-Bytes $orig $N05_OFF @(0xF0,0x69,0x00,0x01,0x64,0x05)
Assert-Bytes $orig $I01_OFF @(0xF0,0x29,0x00,0x02,0x00,0x01)
Assert-Bytes $orig $I08_OFF @(0xF0,0xD2,0x00,0x02,0x00,0x08)
Write-Output ("anchors ok; orig ck: norm05=0x{0:X4} init01=0x{1:X4} init08=0x{2:X4}" -f (Sum-FrameCk $orig $N05_OFF $N05_LEN), (Sum-FrameCk $orig $I01_OFF $I01_LEN), (Sum-FrameCk $orig $I08_OFF $I08_LEN))

# native reference frames
$lex01 = Get-LexArray "init01"
$lex08 = Get-LexArray "init08"
if ($lex01.Count -ne 41 -or $lex08.Count -ne 210) { throw "lex array size mismatch" }

# ---------- P1: aperture 400 -> 144 (F1.2) ----------
$a = $orig.Clone()
Assert-Bytes $a ($BODY_N05 + 24) @(0x90,0x01,0x90,0x01)
$a[$BODY_N05 + 25] = 0x00
$a[$BODY_N05 + 27] = 0x00
$r = Write-FrameCk $a $N05_OFF $N05_LEN
Write-Output ("P1 ck: 0x{0:X4} -> 0x{1:X4}" -f $r[0], $r[1])
Save-Patch $a (Join-Path $OutDir "EA9-P1-F12.bin")

# ---------- P2a: aperture 400 -> 100 (F1.0) ----------
$a = $orig.Clone()
Set-Bytes $a ($BODY_N05 + 24) @(0x64,0x00,0x64,0x00)
$r = Write-FrameCk $a $N05_OFF $N05_LEN
Write-Output ("P2a ck: 0x{0:X4} -> 0x{1:X4}" -f $r[0], $r[1])
Save-Patch $a (Join-Path $OutDir "EA9-P2a-F10.bin")

# ---------- P2b: aperture 400 -> 90 (F0.949) ----------
$a = $orig.Clone()
Set-Bytes $a ($BODY_N05 + 24) @(0x5A,0x00,0x5A,0x00)
$r = Write-FrameCk $a $N05_OFF $N05_LEN
Write-Output ("P2b ck: 0x{0:X4} -> 0x{1:X4}" -f $r[0], $r[1])
Save-Patch $a (Join-Path $OutDir "EA9-P2b-F095.bin")

# ---------- P3: init01 body -> native EA6450 series ----------
$a = $orig.Clone()
Set-Bytes $a ($BODY_I01) ($lex01[6..13])
$r = Write-FrameCk $a $I01_OFF $I01_LEN
Write-Output ("P3 ck: 0x{0:X4} -> 0x{1:X4} (native stores 0x031F)" -f $r[0], $r[1])
Assert-Bytes $a $I01_OFF $lex01[0..($lex01.Count-1)]
Save-Patch $a (Join-Path $OutDir "EA9-P3-INIT01N.bin")

# ---------- P4: norm05 position range 4864 -> 5205, 271 -> 272 ----------
$a = $orig.Clone()
Assert-Bytes $a $BODY_N05 @(0x00,0x13,0x00,0x13)
Set-Bytes $a $BODY_N05 @(0x55,0x14,0x55,0x14)
Assert-Bytes $a ($BODY_N05 + 28) @(0x0F,0x01)
$a[$BODY_N05 + 28] = 0x10
$r = Write-FrameCk $a $N05_OFF $N05_LEN
Write-Output ("P4 ck: 0x{0:X4} -> 0x{1:X4}" -f $r[0], $r[1])
Save-Patch $a (Join-Path $OutDir "EA9-P4-RANGE.bin")

# ---------- P5: init08 -> full native frame (HIGH RISK, motor profiles) ----------
$a = $orig.Clone()
Set-Bytes $a $I08_OFF $lex08[0..209]
$r = Write-FrameCk $a $I08_OFF $I08_LEN
Write-Output ("P5 ck: 0x{0:X4} -> 0x{1:X4} (native stores 0x1A9F)" -f $r[0], $r[1])
Save-Patch $a (Join-Path $OutDir "EA9-P5-INIT08N.bin")

# ---------- P6: P1 aperture(144) + LANDING PROBES ----------
# probe A: init07 body[6] version BCD 0x18(1.8) -> 0x19(1.9)  => updater readback proof
# probe B: init3F lens name "TECHART LM-EA9" -> "TECHART LM-EA9-P6" => body/EXIF visible proof
$I07_OFF = 0x4A38; $I07_LEN = 43     # init07 cls02 typ07
$I3F_OFF = 0x4C08; $I3F_LEN = 74     # init3F cls02 typ3F (lens name)
$a = $orig.Clone()
Assert-Bytes $a ($BODY_N05 + 24) @(0x90,0x01,0x90,0x01)
Set-Bytes $a ($BODY_N05 + 24) @(0x90,0x00,0x90,0x00)
[void](Write-FrameCk $a $N05_OFF $N05_LEN)
Assert-Bytes $a $I07_OFF @(0xF0,0x2B,0x00,0x02,0x00,0x07)
Assert-Bytes $a ($I07_OFF + 12) @(0x18)          # header(6)+body[6]
$a[$I07_OFF + 12] = 0x19
[void](Write-FrameCk $a $I07_OFF $I07_LEN)
Assert-Bytes $a $I3F_OFF @(0xF0,0x4A,0x00,0x02,0x00,0x3F)
Assert-Bytes $a ($I3F_OFF + 7) ([int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9"))
$name = [int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-P6")
Set-Bytes $a ($I3F_OFF + 7) $name
$a[$I3F_OFF + 7 + $name.Length] = 0x00
[void](Write-FrameCk $a $I3F_OFF $I3F_LEN)
Save-Patch $a (Join-Path $OutDir "EA9-P6-P1PROBE.bin")

# ---------- P7: init08 aperture candidate + P1 + PROBES ----------
# P6 proved: flash channel OK, norm05=144 landed yet body still shows F2.0, AF unchanged.
# => display source candidate: init08 body[29..30] 0x0F94=3988 (~1000*f^2 @ F2.0) -> 1440 (F1.2)
# probe A: init07 version BCD 0x18 -> 0x20 (2.0); probe B: init3F name -> "TECHART LM-EA9-P7"
$BODY_I08 = $I08_OFF + 6
$a = $orig.Clone()
Assert-Bytes $a ($BODY_N05 + 24) @(0x90,0x01,0x90,0x01)
Set-Bytes $a ($BODY_N05 + 24) @(0x90,0x00,0x90,0x00)
[void](Write-FrameCk $a $N05_OFF $N05_LEN)
Assert-Bytes $a ($BODY_I08 + 29) @(0x94,0x0F)
Set-Bytes $a ($BODY_I08 + 29) @(0xA0,0x05)
$r = Write-FrameCk $a $I08_OFF $I08_LEN
Write-Output ("P7 init08 ck: 0x{0:X4} -> 0x{1:X4}" -f $r[0], $r[1])
Assert-Bytes $a $I07_OFF @(0xF0,0x2B,0x00,0x02,0x00,0x07)
Assert-Bytes $a ($I07_OFF + 12) @(0x18)
$a[$I07_OFF + 12] = 0x20
[void](Write-FrameCk $a $I07_OFF $I07_LEN)
Assert-Bytes $a $I3F_OFF @(0xF0,0x4A,0x00,0x02,0x00,0x3F)
Assert-Bytes $a ($I3F_OFF + 7) ([int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9"))
$name = [int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-P7")
Set-Bytes $a ($I3F_OFF + 7) $name
$a[$I3F_OFF + 7 + $name.Length] = 0x00
[void](Write-FrameCk $a $I3F_OFF $I3F_LEN)
Save-Patch $a (Join-Path $OutDir "EA9-P7-INIT08A.bin")

# ---------- P5 post-mortem / protected region below init3F ----------
# P5 did NOT overflow: native init08 has same len=210 and was replaced in place.
# Verified frame map after init08: init09@0x4B5C ... init3F ends 0x4C52,
#   typ5A@0x4C9C(len64), init34@0x4CDC(len32, orig cksum stale), init19@0x4CFC(len field 0),
#   init0A@0x4D08(len25).
# => P5 kill mechanism = native init08 CONTENT (motor profile 55 14 55 14, 79 AB 04)
#    mismatching TechArt calibration (00 13 00 19); first AF press -> comms hang.
# Lesson: never full-replace motor-profile frames; range alignment only via norm05 (P4/P9).
$I34_OFF = 0x4CDC; $I34_LEN = 32
Assert-Bytes $orig $I34_OFF @(0xF0,0x20,0x00,0x02,0x00,0x34)

# ---------- P9..P12: ride the P3 signal (init01 capability = ONLY patch that changed behavior) ----------
# P7 result: init08 3988->1440 did NOT change body F-display => aperture display source not in static table; drop display as metric.
# P5 result: native init08 breaks comms at first AF press => init08-native line CLOSED.
# P9  = P3 + P4 (capability switch + norm05 range align 5205/272)
# P10 = init01 @1 only          (9F->97, single bit3)
# P11 = init01 @2+@3 only       (60 7D -> 78 15)
# P12 = init01 @5+@6+@7 only    (07 08 50 -> 40 10 00)
# All carry landing probes: init07 BCD -> 0x21..0x24 (updater readback 2.1..2.4), init3F name -> -Pn
function Set-Probes([object]$arr, [byte]$ver, [string]$tag) {
    Assert-Bytes $arr $I07_OFF @(0xF0,0x2B,0x00,0x02,0x00,0x07)
    Assert-Bytes $arr ($I07_OFF + 12) @(0x18)
    $arr[$I07_OFF + 12] = $ver
    [void](Write-FrameCk $arr $I07_OFF $I07_LEN)
    Assert-Bytes $arr $I3F_OFF @(0xF0,0x4A,0x00,0x02,0x00,0x3F)
    Assert-Bytes $arr ($I3F_OFF + 7) ([int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9"))
    $nm = [int[]][System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-" + $tag)
    Set-Bytes $arr ($I3F_OFF + 7) $nm
    $arr[$I3F_OFF + 7 + $nm.Length] = 0x00
    [void](Write-FrameCk $arr $I3F_OFF $I3F_LEN)
}

$a = $orig.Clone()
Set-Bytes $a ($BODY_I01) ($lex01[6..13])
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Assert-Bytes $a $BODY_N05 @(0x00,0x13,0x00,0x13)
Set-Bytes $a $BODY_N05 @(0x55,0x14,0x55,0x14)
Assert-Bytes $a ($BODY_N05 + 28) @(0x0F,0x01)
$a[$BODY_N05 + 28] = 0x10
[void](Write-FrameCk $a $N05_OFF $N05_LEN)
Set-Probes $a 0x21 "P9"
Save-Patch $a (Join-Path $OutDir "EA9-P9-P34.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 1] = $lex01[7]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x22 "P10"
Save-Patch $a (Join-Path $OutDir "EA9-P10-A1.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 2] = $lex01[8]; $a[$BODY_I01 + 3] = $lex01[9]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x23 "P11"
Save-Patch $a (Join-Path $OutDir "EA9-P11-A23.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 5] = $lex01[11]; $a[$BODY_I01 + 6] = $lex01[12]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x24 "P12"
Save-Patch $a (Join-Path $OutDir "EA9-P12-A567.bin")

# ---------- P13..P16: single-byte bisect inside the P12 active group ----------
# Bench data (1~1.5m): P9 ~= orig (worse than P3), P10 ~= orig, P11 WORST, P12 ~= P3.
# => @5@6@7 is the active group; @2@3 actively harmful; @1 inert alone; P4 add-on harmful.
# P13 = @5 only (07->40) ; P14 = @6 only (08->10) ; P15 = @7 only (50->00)
# P16 = @1+@5+@6+@7  ("P3 minus poison": drop harmful @2@3, keep everything else)
$a = $orig.Clone()
$a[$BODY_I01 + 5] = $lex01[11]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x25 "P13"
Save-Patch $a (Join-Path $OutDir "EA9-P13-A5.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 6] = $lex01[12]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x26 "P14"
Save-Patch $a (Join-Path $OutDir "EA9-P14-A6.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x27 "P15"
Save-Patch $a (Join-Path $OutDir "EA9-P15-A7.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 1] = $lex01[7]
$a[$BODY_I01 + 5] = $lex01[11]; $a[$BODY_I01 + 6] = $lex01[12]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x28 "P16"
Save-Patch $a (Join-Path $OutDir "EA9-P16-NOP23.bin")

# ---------- P17..P20: second-order search around the NEW CHAMPION @7 ----------
# Bench data (1~1.5m): P16 > P3 (detox confirmed); P15 > P16 (@7 alone beats the combo,
# @1/@5/@6 dilute); P13 ~= P16 slightly worse but STEADIER at extreme edge (@5 = edge byte);
# P14 clearly worse than P16 yet > orig (@6 = weak positive, redundant next to @7).
# => KEY BYTE = @7 (50 -> 00). New baseline = P15.
# P17 = @5+@7  (champion + edge byte: keep P15 overall, add P13 edge steadiness)  -- try first
# P18 = @6+@7  (does @6 add anything on top of @7?)
# P19 = @1+@7  (does @1 add anything on top of @7?)
# P20 = @7 = 28 (midpoint 50<->00 value probe: half effect = continuous calibration,
#       full effect = threshold/binary semantics)
# Probes: init07 BCD 0x29/0x30/0x31/0x32 (readback 2.9/3.0/3.1/3.2), init3F name -> -Pn
$a = $orig.Clone()
$a[$BODY_I01 + 5] = $lex01[11]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x29 "P17"
Save-Patch $a (Join-Path $OutDir "EA9-P17-A57.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 6] = $lex01[12]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x30 "P18"
Save-Patch $a (Join-Path $OutDir "EA9-P18-A67.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 1] = $lex01[7]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x31 "P19"
Save-Patch $a (Join-Path $OutDir "EA9-P19-A17.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 7] = 0x28
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x32 "P20"
Save-Patch $a (Join-Path $OutDir "EA9-P20-A7HALF.bin")

# ---------- P21..P24: combine winners + push past native ----------
# Bench data (1~1.5m): P17(@5+@7) > P15, extreme edge now HITS sometimes;
# P20(@7=28) < P15 unstable => @7 is a graded value, monotone toward 00 (lower=better);
# P18(@6+@7) > P20 but < P17 => @6 stays out; P19(@1+@7) ~ P17 rate but FASTER focus,
# best overall => @1 is inert alone yet SYNERGISTIC with @7=00.
# Ranking: P19 >= P17 > P15 > P18 > P20. @6 is the P16 dilutant (P16 = this minus @6... minus @1@5).
# P21 = @1+@5+@7  (merge the two winners; = P16 minus harmful @6)  -- try first, new champion candidate
# P22 = @7 = FF   (beyond-native: if @7 read signed, FF < 00 => possible further gain; else regression)
# P23 = @5=80 + @7=00 (push @5 past native 40; @4=80 shows 80 is in-domain)
# P24 = @1=17 + @5+@7 (push @1 one bit past native: does more of @1 help or is 97 the sweet spot?)
# Probes: init07 BCD 0x33..0x36 (readback 3.3..3.6), init3F name -> -Pn
$a = $orig.Clone()
$a[$BODY_I01 + 1] = $lex01[7]; $a[$BODY_I01 + 5] = $lex01[11]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x33 "P21"
Save-Patch $a (Join-Path $OutDir "EA9-P21-A157.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 7] = 0xFF
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x34 "P22"
Save-Patch $a (Join-Path $OutDir "EA9-P22-A7FF.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 5] = 0x80; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x35 "P23"
Save-Patch $a (Join-Path $OutDir "EA9-P23-A5UP.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 1] = [byte]($lex01[7] -band 0xDF)
$a[$BODY_I01 + 5] = $lex01[11]; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x36 "P24"
Save-Patch $a (Join-Path $OutDir "EA9-P24-A1DN.bin")

# ---------- P25..P28: chase the @5 ceiling (NEW CHAMPION = P23) ----------
# Bench data (1~1.5m): P21(@1+@5=40+@7) < P19 + overshoots past the box => @1 and @5=40
#   mutually harmful together; P22(@7=FF) ~ P19 => FF equivalent to 00 (wraparound-adjacent,
#   both are the safe low end); P23(@5=80+@7=00) ACCURATE AND FAST => new champion, pushing
#   @5 past native 40 wins and @1 is not needed; P24(@1=17) fast but unstable lock => 97 sweet spot confirmed.
# P25 = @5=A0 + @7=00  (keep climbing @5, step 1)
# P26 = @5=C0 + @7=00  (step 2; P25/P26 together bracket the @5 optimum in one round)
# P27 = @1 + @5=80 + @7=00  (does @1 help again once @5 is high? watch for overshoot)
# P28 = @5=80 alone, @7 stays 50  (control: is @7=00 still needed at high @5?)
# Probes: init07 BCD 0x37/0x38/0x39/0x40 (readback 3.7/3.8/3.9/4.0), init3F name -> -Pn
$a = $orig.Clone()
$a[$BODY_I01 + 5] = 0xA0; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x37 "P25"
Save-Patch $a (Join-Path $OutDir "EA9-P25-A5A0.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 5] = 0xC0; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x38 "P26"
Save-Patch $a (Join-Path $OutDir "EA9-P26-A5C0.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 1] = $lex01[7]
$a[$BODY_I01 + 5] = 0x80; $a[$BODY_I01 + 7] = $lex01[13]
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x39 "P27"
Save-Patch $a (Join-Path $OutDir "EA9-P27-A157UP.bin")

$a = $orig.Clone()
$a[$BODY_I01 + 5] = 0x80
[void](Write-FrameCk $a $I01_OFF $I01_LEN)
Set-Probes $a 0x40 "P28"
Save-Patch $a (Join-Path $OutDir "EA9-P28-A5ONLY.bin")

# ---------- self-verify: a patch may only break cksums that orig already had broken ----------
Write-Output "--- verify ---"
$FRAMES = @(,@($N05_OFF,$N05_LEN)) + @(,@($I01_OFF,$I01_LEN)) + @(,@($I08_OFF,$I08_LEN)) + @(,@($I07_OFF,$I07_LEN)) + @(,@($I3F_OFF,$I3F_LEN)) + @(,@($I34_OFF,$I34_LEN))
$origBad = @{}
foreach ($fr in $FRAMES) {
    $o = $fr[0]; $l = $fr[1]
    $st = [int]$orig[$o+$l-3] + ([int]$orig[$o+$l-2]*256)
    $origBad[$o] = ($st -ne (Sum-FrameCk $orig $o $l))
}
$files = Get-ChildItem $OutDir -Filter "EA9-P*.bin"
foreach ($f in $files) {
    $b = [System.IO.File]::ReadAllBytes($f.FullName)
    if ($b.Length -ne 20172) { throw ($f.Name + " bad size") }
    $ok = $true
    foreach ($fr in $FRAMES) {
        $off = $fr[0]; $len = $fr[1]
        $stored = [int]$b[$off+$len-3] + ([int]$b[$off+$len-2]*256)
        $calc = Sum-FrameCk $b $off $len
        if (($stored -ne $calc) -and (-not $origBad[$off])) { $ok = $false }
        $tag = if ($stored -eq $calc) {"OK"} elseif ($origBad[$off]) {"orig-stale"} else {"BAD"}
        Write-Output ("{0} frame@0x{1:X4}: stored=0x{2:X4} calc=0x{3:X4} {4} body={5}" -f $f.Name, $off, $stored, $calc, $tag, (Hex-Bytes $b $off 6))
    }
    # protected region: init34..init0A area must stay byte-identical to orig
    for ($i = $I34_OFF; $i -lt ($I34_OFF + 84); $i++) {
        if ($b[$i] -ne $orig[$i]) { $ok = $false; Write-Output ("{0} MUTATED protected byte at 0x{1:X4}" -f $f.Name, $i) }
    }
    # diff count vs orig
    $d = 0
    for ($i = 0; $i -lt $b.Length; $i++) { if ($b[$i] -ne $orig[$i]) { $d++ } }
    Write-Output ("{0} diffbytes={1} ALL={2}" -f $f.Name, $d, $(if ($ok) {"PASS"} else {"FAIL"}))
}
Write-Output "done"
