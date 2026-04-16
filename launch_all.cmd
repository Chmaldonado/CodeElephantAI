@echo off
setlocal

set "USER_ID=%~1"
if "%USER_ID%"=="" set "USER_ID=learner"

set "ROOT=%~dp0"
cd /d "%ROOT%"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker CLI not found. Please install Docker Desktop first.
  exit /b 1
)

echo Starting terminal stack (Ollama + Tutor)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%run_docker.ps1" -Action up
if errorlevel 1 (
  echo Failed to start Docker stack.
  exit /b 1
)

echo Opening terminal tutor chat...
start "Tutor Chat" cmd /k "cd /d %ROOT% && powershell -NoProfile -ExecutionPolicy Bypass -File .\run_docker.ps1 -Action chat -UserId %USER_ID%"

echo.
echo All set.
echo Chat window user: %USER_ID%
