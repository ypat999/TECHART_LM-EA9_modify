param([string]$Dir = "d:\work\techart\LM-EA9_firmware\bin")

function HexBytes([byte[]]$b) { ($b | ForEach-Object { $_.ToString("X2") }) -join "" }

$files = Get-ChildItem $Dir -Filter *.bin | Sort-Object Name
foreach ($f in $files) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    Write-Output ("=== " + $f.Name + "  len=" + $bytes.Length + " ===")

    # locate candidate frames: F0 <len16le> <class> <seq> <type> ... <ck16le> 55
    $hits = @{}
    $frames = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $bytes.Length - 9; $i++) {
        if ($bytes[$i] -ne 0xF0) { continue }
        $len = [int]$bytes[$i+1] -bor ([int]$bytes[$i+2] -shl 8)
        if ($len -lt 10 -or $len -gt 900) { continue }
        $end = $i + $len - 1
        if ($end -ge $bytes.Length) { continue }
        if ($bytes[$end] -ne 0x55) { continue }
        $cls = $bytes[$i+3]; $seq = $bytes[$i+4]; $typ = $bytes[$i+5]
        if ($cls -gt 2 -or $typ -gt 0x40) { continue }
        $bodyLen = $len - 9
        if ($bodyLen -lt 1) { continue }
        $body = $bytes[($i+6)..($i+5+$bodyLen)]
        $key = ("class{0:X2} type{1:X2} body{2}" -f $cls, $typ, $bodyLen)
        $h = HexBytes $body
        if (-not $hits.ContainsKey($key)) { $hits[$key] = @{} }
        $hits[$key][$h] = 1
        [void]$frames.Add([pscustomobject]@{ Off = $i; Cls = $cls; Typ = $typ; BodyLen = $bodyLen; Hex = $h })
    }
    Write-Output ("  frames found: " + $frames.Count)
    foreach ($k in ($hits.Keys | Sort-Object)) {
        Write-Output ("  {0}  distinct={1}" -f $k, $hits[$k].Count)
    }
    # dump the longest / most interesting frames
    $top = $frames | Sort-Object BodyLen -Descending | Select-Object -First 6
    foreach ($t in $top) {
        Write-Output ("  --- off=0x{0:X} cls={1:X2} typ={2:X2} bodylen={3}" -f $t.Off, $t.Cls, $t.Typ, $t.BodyLen)
        for ($p = 0; $p -lt $t.Hex.Length; $p += 128) {
            $s = [Math]::Min(128, $t.Hex.Length - $p)
            Write-Output ("      " + $t.Hex.Substring($p, $s))
        }
    }
}
