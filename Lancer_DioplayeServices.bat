@echo off
setlocal enabledelayedexpansion
title Dioplaye Services - Laverie
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo    DIOPLAYE SERVICES - Gestion de Laverie
echo  ============================================================
echo.

:: ---- Trouver Python + Flask ----
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
    color 0C
    echo  [ERREUR] Flask n'est pas installe.
    echo.
    echo  Executez cette commande pour l'installer :
    echo    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: ---- Ouvrir le navigateur apres 4 secondes ----
start /min "" cmd /c "ping -n 5 127.0.0.1 >nul & start http://127.0.0.1:5000"

echo  Demarrage de l'application...
echo  URL : http://127.0.0.1:5000
echo.
echo  Pour arreter l'application, fermez cette fenetre ou appuyez sur CTRL+C.
echo  ============================================================
echo.

:: ---- Lancer le serveur local de test de facon stable ----
if exist "run_local_server.py" (
    "%PYTHON_EXE%" run_local_server.py
) else (
    "%PYTHON_EXE%" app.py
)

:: ---- Fin ----
echo.
color 0E
echo  L'application s'est arretee.
echo.
pause
