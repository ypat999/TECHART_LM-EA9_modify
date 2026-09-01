# Y-generation: NEW frames (not init01). Base = EA9-P23-A5UP.bin.
# Y1 = P23 + norm05 body[32..43] = native distance table segment
# Y2 = P23 + init07 body -> native (keep version byte @6)
# Y3 = Y1 + Y2 (both)
# Probe: init07 body[6] BCD + init3F name. cksum recomputed on every touched frame.

function Sum-FrameCk($arr, [int]$off, [int]$len) {
    $s = 0; for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }; return ($s -band 0xFFFF)
}
function Write-FrameCk($arr, [int]$off, [int]$len) {
    $new = Sum-FrameCk $arr $off $len
    $arr[$off + $len - 3] = [byte]($new -band 0xFF); $arr[$off + $len - 2] = [byte](($new -shr 8) -band 0xFF); return $new
}
function Set-Bytes($arr, [int]$off, [int[]]$vals) { for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] } }
function Assert-Bytes($arr, [int]$off, [int[]]$expect) {
    for ($i = 0; $i -lt $expect.Count; $i++) { if ([int]$arr[$off + $i] -ne $expect[$i]) { throw ("assert @0x{0:X} got {1:X2} want {2:X2}" -f ($off+$i),$arr[$off+$i],$expect[$i]) } }
}
function Get-NameBytes([string]$tag) { $raw = [System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-" + $tag); if ($raw.Length -gt 18) { throw "name too long" }; $bs = @(0) * 18; for ($i = 0; $i -lt $raw.Length; $i++) { $bs[$i] = $raw[$i] }; return ,$bs }

$N05 = 0x4B7C; $N05L = 105; $N05B = $N05 + 6
$I07 = 0x4A38; $I07L = 43;  $I07B = $I07 + 6
$I3F = 0x4C08; $I3FL = 74;  $I3FB = $I3F + 6

$base = [System.IO.File]::ReadAllBytes("d:\work\techart\patches\EA9-P23-A5UP.bin")
if ($base.Length -ne 20172) { throw "base size" }
# anchors on P23
Assert-Bytes $base $N05 @(0xF0,0x69,0x00,0x01,0x64,0x05)
Assert-Bytes $base $I07 @(0xF0,0x2B,0x00,0x02,0x00,0x07)
# norm05 body[32..43] real bytes (TechArt): [38]=0x26 is LIVE, must NOT clobber. Only zero slots are safe.
Assert-Bytes $base ($N05B + 32) @(0,0,0,0,0,0,0x26,0,0,0,0,0)  # body[32..43]; note idx6=body[38]=0x26
# native distance table body[32..43] = B1 28 47 51 4B 38 27 08 35 30 40 39
# safe write = only the currently-zero slots: body[32..37] and body[39..43] (skip body[38])
$NAT_D_LO = @(0xB1,0x28,0x47,0x51,0x4B,0x38)   # -> body[32..37]
$NAT_D_HI = @(0x08,0x35,0x30,0x40,0x39)        # -> body[39..43]  (native[38]=0x27 skipped: TechArt has live 0x26 there)
# native init07 body: 01 01 60 01 00 01 [01=version slot, keep base's] 00 A0 30 C7
$NAT_I07 = @(0x01,0x01,0x60,0x01,0x00,0x01,0x00,0xA0,0x30,0xC7)  # [0..5]=body@0..5, [6..9]=body@7..10

$outDir = "d:\work\techart\patches"
$kitFw  = "d:\work\techart\flash_kit\product\firmware\LM-EA9"
$kitLst = "d:\work\techart\flash_kit\lsts"

$jobs = @(
  @{ tag="Y1"; bcd=0x71; ver="7.1.0"; dist=$true;  i07=$false },
  @{ tag="Y2"; bcd=0x72; ver="7.2.0"; dist=$false; i07=$true  },
  @{ tag="Y3"; bcd=0x73; ver="7.3.0"; dist=$true;  i07=$true  }
)

foreach ($j in $jobs) {
    $a = $base.Clone()
    if ($j.dist) { Set-Bytes $a ($N05B + 32) $NAT_D_LO; Set-Bytes $a ($N05B + 39) $NAT_D_HI }
    if ($j.i07) {
        Set-Bytes $a ($I07B + 0) @($NAT_I07[0],$NAT_I07[1],$NAT_I07[2],$NAT_I07[3],$NAT_I07[4],$NAT_I07[5])
        # @6 kept (probe/version). then @7..@10
        Set-Bytes $a ($I07B + 7) @($NAT_I07[6],$NAT_I07[7],$NAT_I07[8],$NAT_I07[9])
    }
    # probe: version BCD + name
    $a[$I07B + 6] = [byte]$j.bcd
    Set-Bytes $a ($I3FB + 1) (Get-NameBytes $j.tag)
    # recompute cksum for touched frames
    $c1 = Write-FrameCk $a $I07 $I07L; Write-Output ($j.tag + " init07 newck=0x" + $c1.ToString("X4"))
    $c2 = Write-FrameCk $a $I3F $I3FL; Write-Output ($j.tag + " init3F newck=0x" + $c2.ToString("X4"))
    if ($j.dist) { $c3 = Write-FrameCk $a $N05 $N05L; Write-Output ($j.tag + " norm05 newck=0x" + $c3.ToString("X4")) }
    $fn = "EA9-" + $j.tag + ".bin"
    $fp = Join-Path $outDir $fn
    [System.IO.File]::WriteAllBytes($fp, $a)
    Copy-Item $fp (Join-Path $kitFw $fn) -Force
    $note = "LM-EA9 patch " + $j.tag + " (VER " + $j.ver + ") base=P23; " + $(if($j.dist){"norm05 dist-table native "}) + $(if($j.i07){"init07 native"})
    [System.IO.File]::WriteAllText((Join-Path $kitFw ($fn -replace "\.bin$",".txt")), $note)
    $line = "TECHART LM-EA9;0483;575A;VER " + $j.ver + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $fn + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + ($fn -replace "\.bin$",".txt")
    [System.IO.File]::WriteAllText((Join-Path $kitLst ("TECHART_LST_" + $j.tag + ".txt")), ($line + [Environment]::NewLine))
    $d = 0; for ($i=0;$i -lt $a.Length;$i++){ if ($a[$i] -ne $base[$i]) { $d++ } }
    Write-Output ($j.tag + " saved diffvsP23=" + $d)
}

# verify touched frames pass
Write-Output "--- verify ---"
foreach ($j in $jobs) {
    $b = [System.IO.File]::ReadAllBytes((Join-Path $outDir ("EA9-" + $j.tag + ".bin")))
    $ok = $true
    foreach ($fr in @(@($I07,$I07L),@($I3F,$I3FL)) + $(if($j.dist){@(@($N05,$N05L))}else{@()})) {
        $st = [int]$b[$fr[0]+$fr[1]-3] + ([int]$b[$fr[0]+$fr[1]-2]*256); $cl = Sum-FrameCk $b $fr[0] $fr[1]
        if ($st -ne $cl) { $ok=$false }
    }
    $pn = [System.Text.Encoding]::ASCII.GetString($b, ($I3FB + 1), 18)
    Write-Output ($j.tag + " name=[" + $pn + "] probeBCD=0x" + ([int]$b[$I07B+6]).ToString("X2") + " ck_ok=" + $ok)
}
Write-Output "done"
