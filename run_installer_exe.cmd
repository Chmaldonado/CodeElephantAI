@echo off
setlocal

set "EXE=release\CodeElephantInstaller.exe"
if not exist "%EXE%" (
  echo Missing installer exe: %EXE%
  echo Build it first with:
  echo   build_installer_exe.cmd
  exit /b 1
)

start "" "%EXE%"
