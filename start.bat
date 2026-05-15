@echo off
title SymbioSync
cd /d "%~dp0"
echo.
echo  SymbioSync - Privacy-first BLE device controller
echo  No cloud. No accounts. No telemetry. Just Bluetooth.
echo.
echo  Starting Windows-local server... browser will open automatically.
echo  Default bind is 127.0.0.1 so this stays on this machine.
echo  Press Ctrl+C to stop, or run stop.bat from another window.
echo.
py -m symbiosync --host 127.0.0.1 %*
pause
