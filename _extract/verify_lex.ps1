$t = Get-Content "d:\work\techart\_extract\lex_constants.h" -Raw
$ms = [regex]::Matches($t, "const byte (init\w+)\[\]\s*=\s*\{([^}]*)\}")
foreach ($m in $ms) {
    $name = $m.Groups[1].Value
    $bytes = [regex]::Matches($m.Groups[2].Value, "0x([0-9A-Fa-f]{2})") | ForEach-Object { [Convert]::ToByte($_.Groups[1].Value, 16) }
    if ($bytes[0] -ne 0xF0) { Write-Output ($name + ": no frame header, skip"); continue }
    $len = [int]$bytes[1] + ([int]$bytes[2] * 256)
    $ck = [int]$bytes[$len-3] + ([int]$bytes[$len-2] * 256)
    $s = 0
    for ($i = 1; $i -le $len-4; $i++) { $s += [int]$bytes[$i] }
    $s = $s -band 0xFFFF
    $tag = if ($s -eq $ck) { "OK" } else { "MISMATCH" }
    $extra = $bytes.Length - $len
    Write-Output ("{0}: declaredLen={1} actualBytes={2} extra={3} storedCK=0x{4:X4} sumCK=0x{5:X4} {6}" -f $name, $len, $bytes.Length, $extra, $ck, $s, $tag)
}
