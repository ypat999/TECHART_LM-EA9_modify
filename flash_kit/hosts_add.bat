@echo off
net session >nul 2>&1
if errorlevel 1 (
  echo Run as Administrator.
  pause
  exit /b 1
)
findstr /c:"www.techart-logic.com" %WINDIR%\System32\drivers\etc\hosts >nul 2>&1
if errorlevel 1 (
  echo.>> %WINDIR%\System32\drivers\etc\hosts
  echo 127.0.0.1 www.techart-logic.com>> %WINDIR%\System32\drivers\etc\hosts
)
ipconfig /flushdns
echo hosts entry added.
pause
