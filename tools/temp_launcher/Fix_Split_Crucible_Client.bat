@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Fix_Split_Crucible_Client.ps1" %*
if errorlevel 1 pause
