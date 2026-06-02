@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run SETUP_ENV.cmd first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m unittest discover -s tests
pause
