@echo off
title SymbioSync
cd /d "%~dp0"
echo.
echo  SymbioSync, your private habitat supporting truthful interface:
echo  human ^<^-^> companion agents ^<^-^> devices ^<^-^> embodied state.
echo.
echo  Starting Windows-local server... browser will open automatically.
echo  Default bind is 127.0.0.1 so this stays on this machine.
echo  If port 8080 is already in use, SymbioSync will open the existing server
echo  or tell you what to stop instead of starting a second copy.
echo  Press Ctrl+C to stop, or run stop.bat from another window.
echo.
py -m symbiosync --host 127.0.0.1 %*
pause
