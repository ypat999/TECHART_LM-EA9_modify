function HexBytes([byte[]]$b) { ($b | ForEach-Object { $_.ToString("X2") }) -join "" }

$files = Get-ChildItem "d:\work\techart\LM-EA9_firmware\bin" -Filter *.bin | Sort-Object Name
foreach ($f in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    $out = @()
    for ($i = 0; $i -lt $bytes.Length - 9; $i++) {
        if ($bytes[$i] -ne 0xF0) { continue }
        $len = [int]$bytes[$i+1] -bor ([int]$bytes[$i+2] -shl 8)
        if ($len -lt 10 -or $len -gt 900) { continue }
        $end = $i + $len - 1
        if ($end -ge $bytes.Length) { continue }
        if ($bytes[$end] -ne 0x55) { continue }
        $cls = $bytes[$i+3]; $typ = $bytes[$i+5]
        if ($cls -ne 2) { continue }
        if ($typ -ne 0x01 -and $typ -ne 0x07 -and $typ -ne 0x3F -and $typ -ne 0x08) { continue }
        $bodyLen = $len - 9
        $body = $bytes[($i+6)..($i+5+$bodyLen)]
        $nz = 0; foreach ($bb in $body) { if ($bb -ne 0) { $nz++ } }
        $show = $bodyLen
        if ($show -gt 20) { $show = 20 }
        $pre = HexBytes $body[0..($show-1)]
        $a = ""
        foreach ($bb in $body) { if ($bb -ge 32 -and $bb -lt 127) { $a += [char]$bb } else { $a += " " } }
        $out += ("   cls02 typ{0:X2} len={1} nz={2}  {3}  [{4}]" -f $typ, $bodyLen, $nz, $pre, $a.TrimEnd())
    }
    Write-Output ("=== " + $f.Name)
    $out | ForEach-Object { Write-Output $_ }
}
