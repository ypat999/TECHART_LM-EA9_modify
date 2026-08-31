@echo off
rem repairs hosts entries glued onto a previous line without trailing newline
net session >nul 2>&1
if errorlevel 1 (
  echo Run as Administrator.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='C:\Windows\System32\drivers\etc\hosts'; [IO.File]::Copy($p,($p+'.bak_techart'),$true); $c=[IO.File]::ReadAllText($p,[Text.Encoding]::Default); $c=($c -replace '\s*127\.0\.0\.1\s+www\.techart-logic\.com',''); $c=$c.TrimEnd([char]32,[char]9,[char]13,[char]10)+[char]13+[char]10+'127.0.0.1 www.techart-logic.com'+[char]13+[char]10; [IO.File]::WriteAllText($p,$c,[Text.Encoding]::Default); Write-Host '--- last 4 lines ---'; Get-Content $p | Select-Object -Last 4"
ipconfig /flushdns
echo.
echo now check:  curl.exe http://www.techart-logic.com/product/TECHART_LST.txt
pause
