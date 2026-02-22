@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE="
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import flask" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=venv\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    python -c "import flask" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo Flask n'est installe ni dans le venv ni dans Python global.
    echo Execute d'abord: python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

start "" cmd /c "timeout /t 5 /nobreak >nul & start \"\" http://127.0.0.1:5000"
"%PYTHON_EXE%" app.py

echo.
echo L'application s'est arretee.
pause
