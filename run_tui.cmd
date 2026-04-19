@echo off
setlocal

rem Backward-compatible alias for run_aim.cmd.
call "%~dp0run_aim.cmd" %*
exit /b %errorlevel%
