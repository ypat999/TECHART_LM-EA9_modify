# Z-generation: stack positives (Z0) + decompile Y2 into single-byte groups (Z1~Z3)
# Base = EA9-P23-A5UP.bin. Frames: norm05@0x4B7C(L105,B0x4B82) init07@0x4A38(L43,B0x4A3E)
#        init01@0x4A0C(L41,B0x4A12) init3F@0x4C08(L74,B0x4C0E)
function Sum-FrameCk($arr, [int]$off, [int]$len) { $s = 0; for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }; return ($s -band 0xFFFF) }
function Write-FrameCk($arr, [int]$off, [int]$len) { $new = Sum-FrameCk $arr $off $len; $arr[$off+$len-3] = [byte]($new -band 0xFF); $arr[$off+$len-2] = [byte](($new -shr 8) -band 0xFF); return $new }
function Set-Bytes($arr, [int]$off, [int[]]$vals) { for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] } }
function Assert-Bytes($arr, [int]$off, [int[]]$expect) { for ($i = 0; $i -lt $expect.Count; $i++) { if ([int]$arr[$off + $i] -ne $expect[$i]) { throw ("assert @0x{0:X} got {1:X2} want {2:X2}" -f ($off+$i),$arr[$off+$i],$expect[$i]) } } }
function Get-NameBytes([string]$tag) { $raw = [System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-" + $tag); if ($raw.Length -gt 18) { throw "name too long" }; $bs = @(0) * 18; for ($i = 0; $i -lt $raw.Length; $i++) { $bs[$i] = $raw[$i] }; return ,$bs }

$N05 = 0x4B7C; $N05L = 105; $N05B = $N05 + 6
$I07 = 0x4A38; $I07L = 43;  $I07B = $I07 + 6
$I01 = 0x4A0C; $I01L = 41;  $I01B = $I01 + 6
$I3F = 0x4C08; $I3FL = 74;  $I3FB = $I3F + 6
$NAT_D_LO = @(0xB1,0x28,0x47,0x51,0x4B,0x38)
$NAT_D_HI = @(0x08,0x35,0x30,0x40,0x39)

$base = [System.IO.File]::ReadAllBytes("d:\work\techart\patches\EA9-P23-A5UP.bin")
Assert-Bytes $base $N05 @(0xF0,0x69,0x00,0x01,0x64,0x05)
Assert-Bytes $base $I07 @(0xF0,0x2B,0x00,0x02,0x00,0x07)
Assert-Bytes $base $I01 @(0xF0,0x29,0x00,0x02,0x00,0x01)
Assert-Bytes $base $I3F @(0xF0,0x4A,0x00,0x02,0x00,0x3F)

$outDir = "d:\work\techart\patches"; $kitFw = "d:\work\techart\flash_kit\product\firmware\LM-EA9"; $kitLst = "d:\work\techart\flash_kit\lsts"

# edits: list of @{f=<frameOff>; b=<bodyOff>; o=<idx>; v=<vals>}
$jobs = @(
 @{ tag="Z0"; bcd=0x81; ver="8.1.0"; dist=$true;  i07edit=@(); i01=@(0x10) },   # Y1 + @6=10 stacked
 @{ tag="Z1"; bcd=0x82; ver="8.2.0"; dist=$false; i07edit=@(@{o=2; v=@(0x60)}); i01=@() },
 @{ tag="Z2"; bcd=0x83; ver="8.3.0"; dist=$false; i07edit=@(@{o=9; v=@(0x30,0xC7)}); i01=@() },
 @{ tag="Z3"; bcd=0x84; ver="8.4.0"; dist=$false; i07edit=@(@{o=0; v=@(0x01,0x01)}, @{o=5; v=@(0x01)}, @{o=7; v=@(0x00)}); i01=@() }
)

foreach ($j in $jobs) {
    $a = $base.Clone()
    if ($j.dist) { Set-Bytes $a ($N05B + 32) $NAT_D_LO; Set-Bytes $a ($N05B + 39) $NAT_D_HI }
    foreach ($e in $j.i07edit) { Set-Bytes $a ($I07B + $e.o) $e.v }
    if ($j.i01.Count -gt 0) { Set-Bytes $a ($I01B + 6) $j.i01 }
    $a[$I07B + 6] = [byte]$j.bcd
    Set-Bytes $a ($I3FB + 1) (Get-NameBytes $j.tag)
    $touched = @(@($I3F,$I3FL), @($I07,$I07L))
    if ($j.dist) { $touched += ,@($N05,$N05L) }
    if ($j.i01.Count -gt 0) { $touched += ,@($I01,$I01L) }
    foreach ($fr in $touched) { $c = Write-FrameCk $a $fr[0] $fr[1]; Write-Output ($j.tag + " frame@0x" + ('{0:X}' -f $fr[0]) + " newck=0x" + $c.ToString("X4")) }
    $fn = "EA9-" + $j.tag + ".bin"; $fp = Join-Path $outDir $fn
    [System.IO.File]::WriteAllBytes($fp, $a)
    Copy-Item $fp (Join-Path $kitFw $fn) -Force
    [System.IO.File]::WriteAllText((Join-Path $kitFw ($fn -replace "\.bin$",".txt")), ("LM-EA9 patch " + $j.tag + " VER " + $j.ver + " base=P23"))
    $line = "TECHART LM-EA9;0483;575A;VER " + $j.ver + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $fn + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + ($fn -replace "\.bin$",".txt")
    [System.IO.File]::WriteAllText((Join-Path $kitLst ("TECHART_LST_" + $j.tag + ".txt")), ($line + [Environment]::NewLine))
    # verify all touched frames from file
    $b = [System.IO.File]::ReadAllBytes($fp); $allok = $true
    foreach ($fr in $touched) { $st = [int]$b[$fr[0]+$fr[1]-3] + ([int]$b[$fr[0]+$fr[1]-2]*256); if ($st -ne (Sum-FrameCk $b $fr[0] $fr[1])) { $allok = $false } }
    $pn = [System.Text.Encoding]::ASCII.GetString($b, ($I3FB + 1), ($j.tag.Length + 14))
    Write-Output ($j.tag + " name=[" + $pn + "] ck_all_ok=" + $allok)
}
Write-Output "done"
