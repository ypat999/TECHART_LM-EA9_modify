# T-generation: norm06 focus-position field (body[2..3], LE16) - last untouched frame with field evidence.
# Base = EA9-V3.bin (current champion: P23 + dist table + 272). Only norm06 differs => clean single variable.
# Current template body[2..3] = 00 10 (=0x1000 const). dpreview: Techart ITR reported 0x0162 and body accepted it.
# T1 = V3 + pos=0x0162 (proven-accepted value)
# T2 = V3 + pos=0x0000 (zero / nearest end)
# T3 = V3 + pos=0x1300 (4864 = matches norm05 declared range low value, internal consistency)
function Sum-FrameCk($arr, [int]$off, [int]$len) { $s = 0; for ($i = 1; $i -le $len - 4; $i++) { $s += [int]$arr[$off + $i] }; return ($s -band 0xFFFF) }
function Write-FrameCk($arr, [int]$off, [int]$len) { $new = Sum-FrameCk $arr $off $len; $arr[$off+$len-3] = [byte]($new -band 0xFF); $arr[$off+$len-2] = [byte](($new -shr 8) -band 0xFF); return $new }
function Set-Bytes($arr, [int]$off, [int[]]$vals) { for ($i = 0; $i -lt $vals.Count; $i++) { $arr[$off + $i] = [byte]$vals[$i] } }
function Assert-Bytes($arr, [int]$off, [int[]]$expect) { for ($i = 0; $i -lt $expect.Count; $i++) { if ([int]$arr[$off + $i] -ne $expect[$i]) { throw ("assert @0x{0:X} got {1:X2} want {2:X2}" -f ($off+$i),$arr[$off+$i],$expect[$i]) } } }
function Get-NameBytes([string]$tag) { $raw = [System.Text.Encoding]::ASCII.GetBytes("TECHART LM-EA9-" + $tag); if ($raw.Length -gt 18) { throw "name too long" }; $bs = @(0) * 18; for ($i = 0; $i -lt $raw.Length; $i++) { $bs[$i] = $raw[$i] }; return ,$bs }

$N06 = 0x49D4; $N06L = 48;  $N06B = $N06 + 6
$I07 = 0x4A38; $I07L = 43;  $I07B = $I07 + 6
$I3F = 0x4C08; $I3FL = 74;  $I3FB = $I3F + 6
$N05 = 0x4B7C; $N05B = $N05 + 6

$base = [System.IO.File]::ReadAllBytes("d:\work\techart\patches\EA9-V3.bin")
Assert-Bytes $base $N06 @(0xF0,0x30,0x00,0x01,0x08,0x06)
Assert-Bytes $base $I07 @(0xF0,0x2B,0x00,0x02,0x00,0x07)
Assert-Bytes $base $I3F @(0xF0,0x4A,0x00,0x02,0x00,0x3F)
Assert-Bytes $base ($N05B + 28) @(0x10,0x01)   # V3 must carry 272 alignment

$outDir = "d:\work\techart\patches"; $kitFw = "d:\work\techart\flash_kit\product\firmware\LM-EA9"; $kitLst = "d:\work\techart\flash_kit\lsts"

$jobs = @(
 @{ tag="T1"; bcd=0xC1; ver="12.1.0"; pos=@(0x62,0x01) },
 @{ tag="T2"; bcd=0xC2; ver="12.2.0"; pos=@(0x00,0x00) },
 @{ tag="T3"; bcd=0xC3; ver="12.3.0"; pos=@(0x00,0x13) }
)

foreach ($j in $jobs) {
    $a = $base.Clone()
    Set-Bytes $a ($N06B + 2) $j.pos                       # focus position LE16
    $a[$I07B + 6] = [byte]$j.bcd                          # version nibble probe
    Set-Bytes $a ($I3FB + 1) (Get-NameBytes $j.tag)
    $touched = @(@($I3F,$I3FL), @($I07,$I07L), @($N06,$N06L))
    foreach ($fr in $touched) { $c = Write-FrameCk $a $fr[0] $fr[1] }
    $fn = "EA9-" + $j.tag + ".bin"; $fp = Join-Path $outDir $fn
    [System.IO.File]::WriteAllBytes($fp, $a)
    Copy-Item $fp (Join-Path $kitFw $fn) -Force
    [System.IO.File]::WriteAllText((Join-Path $kitFw ($fn -replace "\.bin$",".txt")), ("LM-EA9 patch " + $j.tag + " VER " + $j.ver + " base=V3"))
    $line = "TECHART LM-EA9;0483;575A;VER " + $j.ver + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $fn + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + ($fn -replace "\.bin$",".txt")
    [System.IO.File]::WriteAllText((Join-Path $kitLst ("TECHART_LST_" + $j.tag + ".txt")), ($line + [Environment]::NewLine))
    $b = [System.IO.File]::ReadAllBytes($fp); $allok = $true
    foreach ($fr in $touched) { $st = [int]$b[$fr[0]+$fr[1]-3] + ([int]$b[$fr[0]+$fr[1]-2]*256); if ($st -ne (Sum-FrameCk $b $fr[0] $fr[1])) { $allok = $false } }
    $pn = [System.Text.Encoding]::ASCII.GetString($b, ($I3FB + 1), 17)
    $pp = ($b[$N06B+2]).ToString("X2") + " " + ($b[$N06B+3]).ToString("X2")
    Write-Output ($j.tag + " name=[" + $pn + "] ck_all_ok=" + $allok + " n06pos=" + $pp)
}
Write-Output "done"
