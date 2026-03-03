@echo off
setlocal enabledelayedexpansion
title Build - Dioplaye Services Installer
color 0B
cd /d "%~dp0"

echo.
echo  ============================================================
echo    BUILD - Installateur Dioplaye Services
echo  ============================================================
echo.

:: ---- Chercher Inno Setup ----
set "ISCC="

for %%P in (
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
  "C:\Program Files\Inno Setup 6\ISCC.exe"
  "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
  "C:\Program Files\Inno Setup 5\ISCC.exe"
) do (
  if exist %%P set "ISCC=%%~P"
)

if not defined ISCC (
  color 0E
  echo  [!] Inno Setup n'est pas installe.
  echo.
  echo  Telechargez-le gratuitement sur :
  echo    https://jrsoftware.org/isdl.php
  echo.
  echo  Apres installation, relancez ce script.
  echo.
  pause
  start "" "https://jrsoftware.org/isdl.php"
  exit /b 1
)

echo  Inno Setup trouve : %ISCC%
echo.

:: ---- Creer le dossier de sortie ----
if not exist dist mkdir dist

:: ---- Compiler ----
echo  Compilation en cours...
echo.
"%ISCC%" /Q "setup.iss"

if errorlevel 1 (
  color 0C
  echo.
  echo  [ERREUR] La compilation a echoue.
  echo  Verifiez le fichier setup.iss et relancez.
  echo.
  pause
  exit /b 1
)

echo.
color 0A
echo  ============================================================
echo    Installateur cree avec succes !
echo  ============================================================
echo.
echo  Fichier : installer\dist\Setup_DioplayeServices_v1.0.0.exe
echo.
echo  Vous pouvez distribuer ce fichier sur n'importe quel
echo  PC Windows (Python 3.10+ requis sur le PC cible).
echo.
pause

:: Ouvrir le dossier dist
explorer dist
