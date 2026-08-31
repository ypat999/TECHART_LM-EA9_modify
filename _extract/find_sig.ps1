param(
    [string]$File = "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin"
)
# Find all offsets of byte signatures; report whether each hit is inside the
# message-table region (0x49D4..0x4E00) or in code/data elsewhere.
$b = [IO.File]::ReadAllBytes($File)
Write-Output ("file = " + (Split-Path $File -Leaf) + "  len = " + $b.Length)

$sigs = [ordered]@{
    'norm05 header  F0 6A 01 64 05 01' = @(0xF0,0x6A,0x01,0x64,0x05,0x01)
    'norm05 body    00 13 00 13 00 00 10 00 07 2A' = @(0x00,0x13,0x00,0x13,0x00,0x00,0x10,0x00,0x07,0x2A)
    'aperture 400x2 90 01 90 01'       = @(0x90,0x01,0x90,0x01)
    'aperture 144x2 90 00 90 00'       = @(0x90,0x00,0x90,0x00)
    'LE16 400 raw   90 01'             = @(0x90,0x01)
    'LE16 144 raw   90 00'             = @(0x90,0x00)
}

foreach ($k in $sigs.Keys) {
    $p = $sigs[$k]
    $hits = @()
    for ($i = 0; $i -le $b.Length - $p.Length; $i++) {
        $ok = $true
        for ($j = 0; $j -lt $p.Length; $j++) {
            if ($b[$i + $j] -ne $p[$j]) { $ok = $false; break }
        }
        if ($ok) { $hits += $i; $i += $p.Length - 1 }
    }
    $inTbl = 0; $outTbl = 0
    foreach ($h in $hits) { if ($h -ge 0x49D4 -and $h -lt 0x4E00) { $inTbl++ } else { $outTbl++ } }
    Write-Output ("--- " + $k + "   hits=" + $hits.Count + "  (table=" + $inTbl + ", outside=" + $outTbl + ")")
    $shown = 0
    foreach ($h in $hits) {
        $where = if ($h -ge 0x49D4 -and $h -lt 0x4E00) { "TABLE" } else { "outside" }
        $ctx = ($b[$h..([Math]::Min($h + 11, $b.Length - 1))] | ForEach-Object { $_.ToString("X2") }) -join ' '
        Write-Output ("      0x" + $h.ToString("X4") + "  [" + $where + "]  " + $ctx)
        $shown++
        if ($shown -ge 40) { Write-Output "      ... (truncated)"; break }
    }
}
