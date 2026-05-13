@echo off
setlocal
cd /d "%~dp0"
title EVEmu isolated launcher
echo.
echo === EVEmu isolated client launcher ===
echo Folder: %~dp0
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch_EVEmu_Isolated.ps1" %*
set ERR=%ERRORLEVEL%
echo.
echo PowerShell finished with exit code: %ERR%
if exist "%~dp0backup\launcher_last_run.log" (
  echo.
  echo ----- Last lines of launcher_last_run.log -----
  powershell.exe -NoProfile -Command "Get-Content -LiteralPath '%~dp0backup\launcher_last_run.log' -Tail 15 -ErrorAction SilentlyContinue"
)
echo.
echo If the game did not appear: check Task Manager for ExeFile/eve, read the log above, and confirm Docker isolated stack is up ^(ports 26100/26101^).
echo To rewrite start.ini after a launcher update without full restore: Launch_EVEmu_Isolated.bat -ForceRefreshIni
echo.
pause
endlocal
