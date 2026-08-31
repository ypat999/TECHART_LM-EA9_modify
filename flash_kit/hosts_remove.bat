@echo off
net session >nul 2>&1
if errorlevel 1 (
  echo Run as Administrator.
  pause
  exit /b 1
)
copy %WINDIR%\System32\drivers\etc\hosts %WINDIR%\System32\drivers\etc\hosts.bak /y >nul
powershell -NoProfile -Command "(Get-Content 'C:\Windows\System32\drivers\etc\hosts') | Where-Object { $_ -notmatch 'techart-logic' } | Set-Content 'C:\Windows\System32\drivers\etc\hosts'"
ipconfig /flushdns
echo hosts entry removed (backup: hosts.bak).
pause
