@echo off
setlocal

set "USER_ID=%~1"
if "%USER_ID%"=="" set "USER_ID=alice"

set "PY=.venv_local\Scripts\python.exe"
if not exist "%PY%" (
  echo Missing .venv_local Python environment.
  echo Run these first:
  echo   python -m venv .venv_local
  echo   .venv_local\Scripts\python -m pip install -e .
  exit /b 1
)

"%PY%" -m tutor_agent.main chat --user-id "%USER_ID%" --color

