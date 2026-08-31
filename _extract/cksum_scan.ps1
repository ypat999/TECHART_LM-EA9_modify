# cksum_scan.ps1 - structural frame scan of LM-EA9 v1.8.0 bin
# Emit each candidate frame: offset, full frame hex, stored cksum (LE16 at len-3..len-2)
param(
    [string]$Bin = "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin",
    [int]$From = 0,
    [int]$To = -1
)

$bytes = [System.IO.File]::ReadAllBytes($Bin)
Write-Output ("filesize=" + $bytes.Length)

# Scan whole file for frame structure:
#   byte[off]=0xF0, len=LE16 at off+1..2, class=off+3 in {0x00,0x01,0x02},
#   10 <= len <= 300, byte[off+len-1]=0x55
for ($off = $From; $off -lt ($bytes.Length - 10); $off++) {
    if ($To -ge 0 -and $off -gt $To) { break }
    if ($bytes[$off] -ne 0xF0) { continue }
    $len = $bytes[$off+1] -bor ($bytes[$off+2] -shl 8)
    if ($len -lt 10 -or $len -gt 300) { continue }
    if ($off + $len -gt $bytes.Length) { continue }
    $cls = $bytes[$off+3]
    if ($cls -ne 0x00 -and $cls -ne 0x01 -and $cls -ne 0x02) { continue }
    if ($bytes[$off+$len-1] -ne 0x55) { continue }
    # stored checksum = last 2 bytes before terminator
    $ckL = $bytes[$off+$len-3]
    $ckH = $bytes[$off+$len-2]
    $ck  = ([int]$ckL) + ([int]$ckH * 256)
    # candidate: sum(frame[1 .. len-4]) & 0xFFFF
    $s = 0
    for ($i = 1; $i -le $len-4; $i++) { $s += $bytes[$off+$i] }
    $s = $s -band 0xFFFF
    $tag = if ($s -eq $ck) { "OK    " } else { "MISMATCH" }
    $seq = $bytes[$off+4]
    $typ = $bytes[$off+5]
    $hex = ($bytes[$off..($off+$len-1)] | ForEach-Object { $_.ToString("X2") }) -join ""
    Write-Output ("{0:X6} len={1:D3} cls={2:X2} seq={3:X2} typ={4:X2} ck={5:X4} sum={6:X4} {7} frame={8}" -f $off, $len, $cls, $seq, $typ, $ck, $s, $tag, $hex)
}
