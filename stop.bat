@echo off
title Stop SymbioSync
cd /d "%~dp0"

set PORT=%~1
if "%PORT%"=="" set PORT=8080

echo.
echo  SymbioSync - stopping local server on port %PORT%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_symbiosync.ps1" -Port %PORT%

echo.
