@echo off
title habitat
cd /d "%~dp0"
echo.
echo  habitat - a private space for truthful interface:
echo  connection ^<^-^> understanding.
echo.
echo  starting the local server... your browser will open automatically.
echo  Default bind is 127.0.0.1 so this stays on this machine.
echo  If port 8080 is already in use, SymbioSync will open the existing server
echo  or tell you what to stop instead of starting a second copy.
echo  Press Ctrl+C to stop, or run stop.bat from another window.
echo.
set "PYTHONPATH=%~dp0code"
py -m habitat --host 127.0.0.1 %*
pause
