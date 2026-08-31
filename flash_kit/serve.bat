@echo off
cd /d %~dp0
echo Serving on http://127.0.0.1 (port 80). Close this window to stop.
python -m http.server 80
