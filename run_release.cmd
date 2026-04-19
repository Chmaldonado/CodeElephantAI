@echo off
setlocal

set "USER_ID=%~1"
if "%USER_ID%"=="" set "USER_ID=learner"

set "EXE=release\CodeElephantTutor\CodeElephantTutor.exe"
if not exist "%EXE%" (
  echo Built executable not found: %EXE%
  echo Build it first with:
  echo   build_desktop_exe.cmd
  exit /b 1
)

start "" "%EXE%" --user-id "%USER_ID%"
