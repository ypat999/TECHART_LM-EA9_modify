# V-generation: edge-focused combos. Base = EA9-P23-A5UP.bin.
# Goal: edge also gets green box. Y1 (norm05 dist table) is the only edge-capable lever.
# V1 = P23 + norm05 dist table (Y1)                     [known-good, but verify edge]
# V2 = P23 + Y1 + norm05 range[0..1] 4864->5205 (P4)   [range-align + dist]
# V3 = P23 + Y1 + norm05 [28..29] 271->272 (P4b)       [focal-code align + dist]
# V4 = P23 + Y1 + @6=10 (X10)                           [dist + init01@6]
# V5 = P23 + Y1 + @2=60 (Z1 speed)                       [dist + speed]
# V6 = P23 + Y1 + range + 271/272 (full native pos-align)
function Sum-FrameCk($arr, [int]$off, [int]$len) { $s = 0; for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }; return ($s -band 0xFFFF) }
function Write-FrameCk($arr, [int]$off, [int]$len) { $new = Sum-FrameCk $arr $off $len; $arr[$off+$len-3] = [byte]($new -band 0xFF); $arr[$off+$len-2] = [byte](($new -shr 8) -band 0xFF); return $new }
function Set-Bytes($arr, [int]$off, [int[]]$vals) { for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] } }
function Assert-Bytes($arr, [int]$off, [int[]]$expect) { for ($i = 0; $i -lt $expect.Count; $i++) { if ([int]$arr[$off + $i] -ne $expect[$i]) { throw ("assert @0x{0:X} got {1:X2} want {2:X2}" -f ($off+$i),$arr[$off+$i],$expect[$i]) } } }
function Get-NameBytes([string]$tag) { $raw = [System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-" + $tag); if ($raw.Length -gt 18) { throw "name too long" }; $bs = @(0) * 18; for ($i = 0; $i -lt $raw.Length; $i++) { $bs[$i] = $raw[$i] }; return ,$bs }

$N05 = 0x4B7C; $N05L = 105; $N05B = $N05 + 6
$I01 = 0x4A0C; $I01L = 41;  $I01B = $I01 + 6
$I07 = 0x4A38; $I07L = 43;  $I07B = $I07 + 6
$I3F = 0x4C08; $I3FL = 74;  $I3FB = $I3F + 6
$NAT_D_LO = @(0xB1,0x28,0x47,0x51,0x4B,0x38)
$NAT_D_HI = @(0x08,0x35,0x30,0x40,0x39)

$base = [System.IO.File]::ReadAllBytes("d:\work\techart\patches\EA9-P23-A5UP.bin")
Assert-Bytes $base $N05 @(0xF0,0x69,0x00,0x01,0x64,0x05)
Assert-Bytes $base $I01 @(0xF0,0x29,0x00,0x02,0x00,0x01)
Assert-Bytes $base $I07 @(0xF0,0x2B,0x00,0x02,0x00,0x07)
Assert-Bytes $base $I3F @(0xF0,0x4A,0x00,0x02,0x00,0x3F)

$outDir = "d:\work\techart\patches"; $kitFw = "d:\work\techart\flash_kit\product\firmware\LM-EA9"; $kitLst = "d:\work\techart\flash_kit\lsts"

$jobs = @(
 @{ tag="V1"; bcd=0xA1; ver="10.1.0"; dist=$true;  rng=$false; foc=$false; i01=@(); i07=@() },
 @{ tag="V2"; bcd=0xA2; ver="10.2.0"; dist=$true;  rng=$true;  foc=$false; i01=@(); i07=@() },
 @{ tag="V3"; bcd=0xA3; ver="10.3.0"; dist=$true;  rng=$false; foc=$true;  i01=@(); i07=@() },
 @{ tag="V4"; bcd=0xA4; ver="10.4.0"; dist=$true;  rng=$false; foc=$false; i01=@(0x10); i07=@() },
 @{ tag="V5"; bcd=0xA5; ver="10.5.0"; dist=$true;  rng=$false; foc=$false; i01=@(); i07=@(@{o=2; v=@(0x60)}) },
 @{ tag="V6"; bcd=0xA6; ver="10.6.0"; dist=$true;  rng=$true;  foc=$true;  i01=@(); i07=@() }
)

foreach ($j in $jobs) {
    $a = $base.Clone()
    if ($j.dist) { Set-Bytes $a ($N05B + 32) $NAT_D_LO; Set-Bytes $a ($N05B + 39) $NAT_D_HI }
    if ($j.rng)  { Set-Bytes $a ($N05B + 0) @(0x55,0x14,0x55,0x14) }  # 4864->5205
    if ($j.foc)  { Set-Bytes $a ($N05B + 28) @(0x10,0x01) }            # 271->272
    if ($j.i01.Count -gt 0) { Set-Bytes $a ($I01B + 6) $j.i01 }
    foreach ($e in $j.i07) { Set-Bytes $a ($I07B + $e.o) $e.v }
    $a[$I07B + 6] = [byte]$j.bcd
    Set-Bytes $a ($I3FB + 1) (Get-NameBytes $j.tag)
    $touched = @(@($I3F,$I3FL), @($I07,$I07L), @($N05,$N05L))
    if ($j.i01.Count -gt 0) { $touched += ,@($I01,$I01L) }
    foreach ($fr in $touched) { $c = Write-FrameCk $a $fr[0] $fr[1] }
    $fn = "EA9-" + $j.tag + ".bin"; $fp = Join-Path $outDir $fn
    [System.IO.File]::WriteAllBytes($fp, $a)
    Copy-Item $fp (Join-Path $kitFw $fn) -Force
    [System.IO.File]::WriteAllText((Join-Path $kitFw ($fn -replace "\.bin$",".txt")), ("LM-EA9 patch " + $j.tag + " VER " + $j.ver + " base=P23"))
    $line = "TECHART LM-EA9;0483;575A;VER " + $j.ver + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $fn + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + ($fn -replace "\.bin$",".txt")
    [System.IO.File]::WriteAllText((Join-Path $kitLst ("TECHART_LST_" + $j.tag + ".txt")), ($line + [Environment]::NewLine))
    $b = [System.IO.File]::ReadAllBytes($fp); $allok = $true
    foreach ($fr in $touched) { $st = [int]$b[$fr[0]+$fr[1]-3] + ([int]$b[$fr[0]+$fr[1]-2]*256); if ($st -ne (Sum-FrameCk $b $fr[0] $fr[1])) { $allok = $false } }
    $pn = [System.Text.Encoding]::ASCII.GetString($b, ($I3FB + 1), 17)
    Write-Output ($j.tag + " name=[" + $pn + "] ck_all_ok=" + $allok + " n05@0..1=" + $b[$N05B..($N05B+1)].ForEach({$_.ToString("X2")}) -join " " + " n05@28..29=" + $b[($N05B+28)..($N05B+29)].ForEach({$_.ToString("X2")}) -join " ")
}
Write-Output "done"
