param([string]$File = "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin")

function HexBytes([byte[]]$b) { ($b | ForEach-Object { $_.ToString("X2") }) -join "" }

$bytes = [System.IO.File]::ReadAllBytes($File)
Write-Output ("=== " + $File + " len=" + $bytes.Length + " ===")
for ($i = 0; $i -lt $bytes.Length - 9; $i++) {
    if ($bytes[$i] -ne 0xF0) { continue }
    $len = [int]$bytes[$i+1] -bor ([int]$bytes[$i+2] -shl 8)
    if ($len -lt 10 -or $len -gt 900) { continue }
    $end = $i + $len - 1
    if ($end -ge $bytes.Length) { continue }
    if ($bytes[$end] -ne 0x55) { continue }
    $cls = $bytes[$i+3]; $seq = $bytes[$i+4]; $typ = $bytes[$i+5]
    $bodyLen = $len - 9
    $body = $bytes[($i+6)..($i+5+$bodyLen)]
    $nz = 0; foreach ($bb in $body) { if ($bb -ne 0) { $nz++ } }
    $h = HexBytes $body
    $a = ""
    foreach ($bb in $body) { if ($bb -ge 32 -and $bb -lt 127) { $a += [char]$bb } else { $a += "." } }
    Write-Output ("cls{0:X2} seq{1:X2} typ{2:X2} bodylen={3} nonzero={4} off=0x{5:X}" -f $cls, $seq, $typ, $bodyLen, $nz, $i)
    Write-Output ("   HEX " + $h)
    Write-Output ("   ASC " + $a)
}
