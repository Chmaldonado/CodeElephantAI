@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%build_installer_exe.ps1" %*
if errorlevel 1 (
  echo.
  echo Installer EXE build failed. Press any key to close.
  pause >nul
  exit /b 1
)
exit /b 0
