@echo off
setlocal
cd /d "%~dp0"
python --version >nul 2>&1
if %errorlevel%==0 (
  python server.py
) else (
  py server.py
)
echo.
echo BatteryTrace has stopped. If an error appeared above, check README.md.
pause
