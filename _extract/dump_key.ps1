param([string]$Dir = "d:\work\techart\LM-EA9_firmware\bin")

function HexBytes([byte[]]$b) { ($b | ForEach-Object { $_.ToString("X2") }) -join "" }

$files = Get-ChildItem $Dir -Filter *.bin | Sort-Object Name
$want = @( @(2,0x01), @(2,0x35), @(2,0x07), @(2,0x0A), @(2,0x09), @(1,0x06) )

foreach ($f in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    Write-Output ("=== " + $f.Name + " ===")
    for ($i = 0; $i -lt $bytes.Length - 9; $i++) {
        if ($bytes[$i] -ne 0xF0) { continue }
        $len = [int]$bytes[$i+1] -bor ([int]$bytes[$i+2] -shl 8)
        if ($len -lt 10 -or $len -gt 900) { continue }
        $end = $i + $len - 1
        if ($end -ge $bytes.Length) { continue }
        if ($bytes[$end] -ne 0x55) { continue }
        $cls = $bytes[$i+3]; $typ = $bytes[$i+5]
        $match = $false
        foreach ($w in $want) { if ($w[0] -eq $cls -and $w[1] -eq $typ) { $match = $true } }
        if (-not $match) { continue }
        $bodyLen = $len - 9
        $body = $bytes[($i+6)..($i+5+$bodyLen)]
        $h = HexBytes $body
        # ascii render
        $a = ""
        foreach ($bb in $body) { if ($bb -ge 32 -and $bb -lt 127) { $a += [char]$bb } else { $a += "." } }
        Write-Output ("  cls{0:X2} typ{1:X2} len={2} off=0x{3:X}" -f $cls, $typ, $bodyLen, $i)
        Write-Output ("    HEX " + $h)
        Write-Output ("    ASC " + $a)
    }
}
