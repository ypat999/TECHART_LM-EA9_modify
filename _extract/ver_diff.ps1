
param()
function HexBytes([byte[]]$b) { ($b | ForEach-Object { $_.ToString("X2") }) -join "" }

$files = @(
 "d:\work\techart\LM-EA9_firmware\bin\v1.0.0_EA9-VER-1-0-0.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.2.0_EA9-VER-1-2-0.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.4.0_LM-EA9VER14.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.5.0_EA9-VER-1-5-0.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.6.0_EA9-VER-1-6-0.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.7.0_EA9-VER-1-7-0.bin",
 "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin"
)
$tags = @("1.0","1.2","1.4","1.5","1.6","1.7","1.8")

function Scan([string]$File) {
  $bytes = [System.IO.File]::ReadAllBytes($File)
  $out = New-Object System.Collections.ArrayList
  for ($i = 0; $i -lt $bytes.Length - 9; $i++) {
    if ($bytes[$i] -ne 0xF0) { continue }
    $len = [int]$bytes[$i+1] -bor ([int]$bytes[$i+2] -shl 8)
    if ($len -lt 10 -or $len -gt 900) { continue }
    $end = $i + $len - 1
    if ($end -ge $bytes.Length) { continue }
    if ($bytes[$end] -ne 0x55) { continue }
    $cls = $bytes[$i+3]; $seq = $bytes[$i+4]; $typ = $bytes[$i+5]
    $bodyLen = $len - 9
    if ($bodyLen -lt 1) { continue }
    $body = $bytes[($i+6)..($i+5+$bodyLen)]
    [void]$out.Add([pscustomobject]@{ Key=("c{0:X2}s{1:X2}t{2:X2}l{3}" -f $cls,$seq,$typ,$bodyLen); Body=(HexBytes $body); Off=$i })
  }
  return $out
}

$all = @()
foreach ($f in $files) { $all += ,(Scan $f) }

# keys in v1.8.0 order, plus keys only in older versions
$keys = @()
$seen = @{}
for ($v = 0; $v -lt $all.Count; $v++) {
  $counts = @{}
  foreach ($fr in $all[$v]) {
    $k = $fr.Key
    if (-not $counts.ContainsKey($k)) { $counts[$k] = 0 }
    $counts[$k]++
    $kk = $k + "#" + $counts[$k]
    if (-not $seen.ContainsKey($kk)) { $seen[$kk] = $true; $keys += $kk }
  }
}

Write-Output "FRAME      " + ($tags -join "  ") + "   verdict"
foreach ($kk in $keys) {
  $parts = $keys.IndexOf($kk)  # dummy
  $bodies = @()
  for ($v = 0; $v -lt $all.Count; $v++) {
    $counts = @{}; $found = $null
    foreach ($fr in $all[$v]) {
      $k = $fr.Key
      if (-not $counts.ContainsKey($k)) { $counts[$k] = 0 }
      $counts[$k]++
      if (($k + "#" + $counts[$k]) -eq $kk) { $found = $fr.Body; break }
    }
    $bodies += $found
  }
  $present = @($bodies | Where-Object { $_ -ne $null })
  $distinct = @($present | Select-Object -Unique)
  $verdict = if ($present.Count -ne $all.Count) { "MISSING-in-some" } elseif ($distinct.Count -gt 1) { "VARIES" } else { "const" }
  Write-Output ("{0}  [{1}]  {2}" -f $kk, $verdict.PadRight(15), ($(if ($distinct.Count -gt 0) { $distinct[0].Substring(0, [Math]::Min(40, $distinct[0].Length)) + ".." } else { "-" })))
  if ($distinct.Count -gt 1) {
    for ($v = 0; $v -lt $all.Count; $v++) {
      $b = $bodies[$v]
      if ($b -eq $null) { Write-Output ("     v" + $tags[$v] + ": --") ; continue }
      $ref = $bodies[6]
      $mark = ""
      if ($b.Length -eq $ref.Length) {
        if ($ref -eq $null) { $ref = $present[0] }
        for ($p = 0; $p -lt $b.Length; $p += 2) {
          if ($b.Substring($p,2) -ne $ref.Substring($p,2)) { $mark += (" @" + [convert]::ToInt32($p/2,10) + ":" + $b.Substring($p,2)) }
        }
      } else { $mark = " (len " + ($b.Length/2) + " vs v1.8 " + ($ref.Length/2) + ")" }
      Write-Output ("     v" + $tags[$v] + ": diff-of-v1.8" + $mark)
    }
  }
}
