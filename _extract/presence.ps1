
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
# byte patterns (hex, contiguous in file)
$pats = [ordered]@{
  "init01#2(FF9F7F5F)" = "FF9F7F5F80070A00";
  "init08#2(byte13=23)" = "001300190000001600020000102300000085";
  "norm06#2(92B,F40F)"  = "1000F40F000010001000";
  "len0-frame t1B"      = "F0000002001B60116011";
  "len0-frame t28"      = "F00000020028000700FF";
  "t3F-str EF40mm"      = "454634306D6D20662F322E38";
  "t3F-str LM-EA9"      = "54454348415254204C4D2D454139";
  "norm05 F400"         = "900190010F01"
}
for ($v = 0; $v -lt $files.Count; $v++) {
  $b = [System.IO.File]::ReadAllBytes($files[$v])
  $h = HexBytes $b
  $line = "v" + $tags[$v] + ": "
  foreach ($k in $pats.Keys) {
    $found = $h.Contains($pats[$k])
    $line += ("[" + $k + "=" + $(if ($found) {"YES"} else {"no"}) + "] ")
  }
  Write-Output $line
}
