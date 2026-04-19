@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%install_desktop_ui.ps1" %*
if errorlevel 1 (
  echo.
  echo Install failed. Press any key to close.
  pause >nul
  exit /b 1
)

exit /b 0
