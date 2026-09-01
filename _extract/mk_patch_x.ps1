# Generate X-generation patches (lens = Leica-M 40mm exploration round), base = EA9-P23-A5UP.bin
# Conventions identical to P6~P28: probe = init07 body[6] BCD + init3F lens name; every touched frame gets recomputed cksum.

function Sum-FrameCk($arr, [int]$off, [int]$len) {
    $s = 0
    for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }
    return ($s -band 0xFFFF)
}
function Write-FrameCk($arr, [int]$off, [int]$len) {
    $new = Sum-FrameCk $arr $off $len
    $arr[$off + $len - 3] = [byte]($new -band 0xFF)
    $arr[$off + $len - 2] = [byte](($new -shr 8) -band 0xFF)
    return $new
}
function Assert-Bytes($arr, [int]$off, [int[]]$expect) {
    for ($i = 0; $i -lt $expect.Count; $i++) {
        if ([int]$arr[$off + $i] -ne $expect[$i]) {
            throw ("assert fail @0x{0:X}: got {1:X2} want {2:X2}" -f ($off + $i), $arr[$off + $i], $expect[$i])
        }
    }
}
function Set-Bytes($arr, [int]$off, [int[]]$vals) {
    for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] }
}

# frames
$I01 = 0x4A0C; $I01L = 41
$I07 = 0x4A38; $I07L = 43
$I08 = 0x4A88; $I08L = 210
$N05 = 0x4B7C; $N05L = 105
$I3F = 0x4C08; $I3FL = 74
$I01B = $I01 + 6; $I07B = $I07 + 6; $I08B = $I08 + 6; $N05B = $N05 + 6; $I3FB = $I3F + 6

$base = [System.IO.File]::ReadAllBytes("d:\work\techart\patches\EA9-P23-A5UP.bin")
if ($base.Length -ne 20172) { throw "base size" }
# base anchors: P23 state of init01 body[1..7] and probe
Assert-Bytes $base ($I01B + 1) @(0x9F,0x60,0x7D,0x80,0x80,0x08,0x00)
Assert-Bytes $base ($I07B + 6) @(0x35)
Assert-Bytes $base ($I3FB + 1) (0x54,0x45,0x43,0x48,0x41,0x52,0x54,0x20,0x4C,0x4D,0x2D,0x45,0x41,0x39,0x2D,0x50,0x32,0x33)
# current norm05 TechArt-only fields and init08 flags
Assert-Bytes $base ($N05B + 9)  @(0x2A,0x00,0x2A,0x00,0x54,0x01,0x54,0x01)
Assert-Bytes $base ($I08B + 13) @(0x20,0x01,0x00,0x00,0x40)

# name template: "TECHART LM-EA9-Xn" at init3F body[1..17], then zero
function Get-NameBytes([string]$tag) {
    $s = "TECHART LM-EA9-" + $tag
    $raw = [System.Text.Encoding]::ASCII.GetBytes($s)
    if ($raw.Length -gt 18) { throw ("name too long: " + $s) }
    $bs = @(0) * 18
    for ($i = 0; $i -lt $raw.Length; $i++) { $bs[$i] = $raw[$i] }
    return ,$bs
}

# patch table: each = name, verBCD, verString, touchedFrames, edits(list of (off,bytes))
$pats = @()
$pats += @{ tag="X1"; bcd=0x51; ver="5.1.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+1); v=@(0x9F,0x78,0x5D,0x82,0x60,0x18,0x7E) }) }   # full Sigma 15/1.4 row
$pats += @{ tag="X2"; bcd=0x52; ver="5.2.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+2); v=@(0x78,0x5D) }) }                            # P23 + Sigma @2@3
$pats += @{ tag="X3"; bcd=0x53; ver="5.3.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+4); v=@(0x82) }) }                                 # P23 + Sigma @4
$pats += @{ tag="X4"; bcd=0x54; ver="5.4.0"; frames=@($I08,$I07,$I3F); edits=@(
    @{ off=($I08B+13); v=@(0xE1) }) }                                # P23 + init08[13]=E1
$pats += @{ tag="X5"; bcd=0x55; ver="5.5.0"; frames=@($I08,$I07,$I3F); edits=@(
    @{ off=($I08B+13); v=@(0xE1) }; @{ off=($I08B+17); v=@(0x15) }) } # + init08[17]=15
$pats += @{ tag="X6"; bcd=0x56; ver="5.6.0"; frames=@($N05,$I07,$I3F); edits=@(
    @{ off=($N05B+9); v=@(0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00) }) } # norm05 2A/54 -> 0
$pats += @{ tag="X7"; bcd=0x57; ver="5.7.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+5); v=@(0x40,0x08,0x00) }) }                       # P15 byte set (@5=40,@7=00)
$pats += @{ tag="X8"; bcd=0x58; ver="5.8.0"; frames=@($N05,$I07,$I3F); edits=@(
    @{ off=($N05B+24); v=@(0x90,0x00,0x90,0x00) }) }                 # P23 + norm05 F144 (recheck on new lens)
# --- 2nd batch after X1~X4 verdicts (M40 round) ---
$pats += @{ tag="X9";  bcd=0x61; ver="6.1.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+7); v=@(0x7E) }) }                                 # P23 + @7=7E (real-lens value, only free axis left)
$pats += @{ tag="X10"; bcd=0x62; ver="6.2.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+6); v=@(0x10) }) }                                 # P23 + @6=10 (native; weak-pos on 35mm, untested axis on M40)
$pats += @{ tag="X11"; bcd=0x63; ver="6.3.0"; frames=@($I08,$I07,$I3F); edits=@(
    @{ off=($I08B+17); v=@(0x15) }) }                                # P23 + init08[17]=15 ONLY (X4 killed [13]=E1; isolate [17])
# --- 3rd batch after X9~X11 verdicts: @6=10 becomes M40 base (only positive so far), reopen @5 ladder on top ---
$pats += @{ tag="X12"; bcd=0x64; ver="6.4.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+5); v=@(0xA0,0x10,0x00) }) }                       # @5=A0 + @6=10 (@7=00 kept)
$pats += @{ tag="X13"; bcd=0x65; ver="6.5.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+5); v=@(0xC0,0x10,0x00) }) }                       # @5=C0 + @6=10
$pats += @{ tag="X14"; bcd=0x66; ver="6.6.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+5); v=@(0x40,0x10,0x00) }) }                       # @5=40 + @6=10 (low anchor)
$pats += @{ tag="X15"; bcd=0x67; ver="6.7.0"; frames=@($I01,$I07,$I3F); edits=@(
    @{ off=($I01B+6); v=@(0x18) }) }                                 # @6=18 (Sigma value) alone

$outDir = "d:\work\techart\patches"
$kitFw = "d:\work\techart\flash_kit\product\firmware\LM-EA9"
$kitLst = "d:\work\techart\flash_kit\lsts"

foreach ($p in $pats) {
    $a = $base.Clone()
    Set-Bytes $a ($I07B + 6) @([int]$p.bcd)
    Set-Bytes $a ($I3FB + 1) (Get-NameBytes $p.tag)
    foreach ($e in $p.edits) { Set-Bytes $a ([int]$e.off) $e.v }
    foreach ($fr in $p.frames) {
        $len = switch ($fr) { $I01 {$I01L} $I07 {$I07L} $I08 {$I08L} $N05 {$N05L} $I3F {$I3FL} }
        $ck = Write-FrameCk $a $fr $len
        Write-Output ("{0} frame@0x{1:X4} newck=0x{2:X4}" -f $p.tag, $fr, $ck)
    }
    $fn = "EA9-" + $p.tag + ".bin"
    $fp = Join-Path $outDir $fn
    [System.IO.File]::WriteAllBytes($fp, $a)
    Copy-Item $fp (Join-Path $kitFw $fn) -Force
    $note = "LM-EA9 patch " + $p.tag + " (VER " + $p.ver + ") base=P23, target lens = Leica-M 40mm round"
    [System.IO.File]::WriteAllText((Join-Path $kitFw ($fn -replace "\.bin$",".txt")), $note)
    $line = "TECHART LM-EA9;0483;575A;VER " + $p.ver + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $fn + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + ($fn -replace "\.bin$",".txt")
    [System.IO.File]::WriteAllText((Join-Path $kitLst ("TECHART_LST_" + $p.tag + ".txt")), ($line + [Environment]::NewLine))
    $d = 0
    for ($i = 0; $i -lt $a.Length; $i++) { if ($a[$i] -ne $base[$i]) { $d++ } }
    Write-Output ($p.tag + " saved " + $fp + " diffvsP23=" + $d)
}

# self-verify: every touched frame passes cksum; residual MISMATCH set identical to base (4 stale official frames)
Write-Output "--- verify ---"
foreach ($p in $pats) {
    $b = [System.IO.File]::ReadAllBytes((Join-Path $outDir ("EA9-" + $p.tag + ".bin")))
    $bad = 0
    foreach ($fr in @(@($I01,$I01L),@($I07,$I07L),@($I08,$I08L),@($N05,$N05L),@($I3F,$I3FL))) {
        $off = $fr[0]; $len = $fr[1]
        $stored = [int]$b[$off+$len-3] + ([int]$b[$off+$len-2]*256)
        $calc = Sum-FrameCk $b $off $len
        if ($stored -ne $calc) { $bad++; Write-Output ($p.tag + " BAD frame@0x" + $off.ToString("X4")) }
    }
    $pn = [System.Text.Encoding]::ASCII.GetString($b, ($I3FB + 1), 18)
    Write-Output ($p.tag + " probeBCD=0x" + ([int]$b[$I07B+6]).ToString("X2") + " name=[" + $pn + "] frames_ok=" + (5-$bad) + "/5")
}
Write-Output "done"
