param(
  [string]$File  = 'd:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin',
  [int]$start    = 0x4CE0,
  [int]$end      = 0x4DE0
)
$bytes = [IO.File]::ReadAllBytes($File)
for ($r = $start; $r -lt $end; $r += 16) {
    $hex = ''
    $asc = ''
    for ($c = 0; $c -lt 16; $c++) {
        $b = $bytes[$r + $c]
        $hex += ('{0:X2} ' -f $b)
        if ($b -ge 32 -and $b -lt 127) { $asc += [char]$b } else { $asc += '.' }
    }
    Write-Output ('{0:X6}  {1} {2}' -f $r, $hex, $asc)
}
