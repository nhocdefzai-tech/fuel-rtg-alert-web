@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run SETUP_ENV.cmd first.
    pause
    exit /b 1
)

start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" -m fuel_alert_web.web
pause
