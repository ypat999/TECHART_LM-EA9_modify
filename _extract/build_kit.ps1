$kit = "d:\work\techart\flash_kit"
$prod = Join-Path $kit "product"
$fw = Join-Path $prod "product_fw_placeholder"
$fwDir = Join-Path $prod "firmware\LM-EA9"
New-Item -ItemType Directory -Force -Path (Join-Path $kit "lsts") | Out-Null
New-Item -ItemType Directory -Force -Path $fwDir | Out-Null
Remove-Item $fw -ErrorAction SilentlyContinue

$pairs = @(
    @("P1",   "1.8.1", "EA9-P1-F12.bin",    "aperture 400->144 (F1.2 reported to body)"),
    @("P2a",  "1.8.2", "EA9-P2a-F10.bin",   "aperture 400->100 (F1.0 reported to body)"),
    @("P2b",  "1.8.3", "EA9-P2b-F095.bin",  "aperture 400->90  (F0.95 reported to body)"),
    @("P3",   "1.8.4", "EA9-P3-INIT01N.bin","init01 body replaced with native EA-series values"),
    @("P4",   "1.8.5", "EA9-P4-RANGE.bin",  "norm05 focus range 4864->5205, 271->272 (native)"),
    @("P5",   "1.8.6", "EA9-P5-INIT08N.bin","init08 replaced with native frame (HIGH RISK motor profiles)"),
    @("ORIG", "1.8.0", "EA9-VER-1-8-0.bin", "stock v1.8.0 firmware (rollback / baseline)")
)

# copy bins
foreach ($p in $pairs) {
    $name = $p[2]
    if ($p[0] -eq "ORIG") {
        Copy-Item "d:\work\techart\LM-EA9_firmware\bin\v1.8.0_EA9-VER-1-8-0.bin" (Join-Path $fwDir $name) -Force
    } else {
        Copy-Item (Join-Path "d:\work\techart\patches" $name) (Join-Path $fwDir $name) -Force
    }
    $txt = $name -replace "\.bin$", ".txt"
    $note = "LM-EA9 patch " + $p[0] + " (listed as VER " + $p[1] + ")" + [Environment]::NewLine + $p[3] + [Environment]::NewLine
    [System.IO.File]::WriteAllText((Join-Path $fwDir $txt), $note)
}

# LST files: one per selectable patch + combined list is intentionally NOT used (avoid wrong flash)
foreach ($p in $pairs) {
    $bin = $p[2]
    $txt = $bin -replace "\.bin$", ".txt"
    $line = "TECHART LM-EA9;0483;575A;VER " + $p[1] + ";Copyright TECHART Inc.;http://www.techart-logic.com/product/firmware/LM-EA9/" + $bin + ";http://www.techart-logic.com/product/firmware/LM-EA9/" + $txt
    $lstName = Join-Path $kit ("lsts\TECHART_LST_" + $p[0] + ".txt")
    [System.IO.File]::WriteAllText($lstName, $line + [Environment]::NewLine)
}
# default active LST = P1
Copy-Item (Join-Path $kit "lsts\TECHART_LST_P1.txt") (Join-Path $prod "TECHART_LST.txt") -Force

# serve.bat
$bat1 = "@echo off`r`ncd /d %~dp0`r`necho Serving on http://127.0.0.1 (port 80). Close this window to stop.`r`npython -m http.server 80`r`n"
[System.IO.File]::WriteAllText((Join-Path $kit "serve.bat"), $bat1)

# hosts helpers (run as admin)
$bat2 = "@echo off`r`nnet session >nul 2>&1`r`nif errorlevel 1 (`r`n  echo Run as Administrator.`r`n  pause`r`n  exit /b 1`r`n)`r`nfindstr /c:""www.techart-logic.com"" %WINDIR%\System32\drivers\etc\hosts >nul 2>&1`r`nif errorlevel 1 (`r`n  echo.>> %WINDIR%\System32\drivers\etc\hosts`r`n  echo 127.0.0.1 www.techart-logic.com>> %WINDIR%\System32\drivers\etc\hosts`r`n)`r`nipconfig /flushdns`r`necho hosts entry added.`r`npause`r`n"
[System.IO.File]::WriteAllText((Join-Path $kit "hosts_add.bat"), $bat2)

$bat3 = "@echo off`r`nnet session >nul 2>&1`r`nif errorlevel 1 (`r`n  echo Run as Administrator.`r`n  pause`r`n  exit /b 1`r`n)`r`ncopy %WINDIR%\System32\drivers\etc\hosts %WINDIR%\System32\drivers\etc\hosts.bak /y >nul`r`npowershell -NoProfile -Command ""(Get-Content 'C:\Windows\System32\drivers\etc\hosts') | Where-Object { `$_ -notmatch 'techart-logic' } | Set-Content 'C:\Windows\System32\drivers\etc\hosts'""`r`nipconfig /flushdns`r`necho hosts entry removed (backup: hosts.bak).`r`npause`r`n"
[System.IO.File]::WriteAllText((Join-Path $kit "hosts_remove.bat"), $bat3)

Get-ChildItem $kit -Recurse | ForEach-Object { Write-Output ($_.FullName.Replace($kit, "") + $(if ($_.PSIsContainer) {"\" } else { " " + $_.Length })) }
Write-Output "kit built"
