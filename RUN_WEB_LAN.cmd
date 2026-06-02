@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run SETUP_ENV.cmd first.
    pause
    exit /b 1
)

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4.*192\\." /C:"IPv4.*10\\." /C:"IPv4.*172\\."') do (
    set LAN_IP=%%A
    goto :found_ip
)

:found_ip
set LAN_IP=%LAN_IP: =%
if "%LAN_IP%"=="" (
    echo Could not detect LAN IP automatically.
    echo Open http://127.0.0.1:8000 on this computer.
) else (
    echo LAN URL:
    echo http://%LAN_IP%:8000
    start "" "http://%LAN_IP%:8000"
)

set FUEL_ALERT_HOST=0.0.0.0
set FUEL_ALERT_PORT=8000
".venv\Scripts\python.exe" -m fuel_alert_web.web
pause
