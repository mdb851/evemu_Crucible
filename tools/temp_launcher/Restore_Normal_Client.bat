@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Restore_EVEmu_Isolated_Client.ps1" %*
if errorlevel 1 pause
endlocal
