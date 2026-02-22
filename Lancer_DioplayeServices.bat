@echo off
setlocal

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

start "" http://127.0.0.1:5000
python app.py

echo.
echo L'application s'est arretee.
pause
