@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%build_desktop_exe.ps1" %*
if errorlevel 1 (
  echo.
  echo Build failed. Press any key to close.
  pause >nul
  exit /b 1
)
exit /b 0
