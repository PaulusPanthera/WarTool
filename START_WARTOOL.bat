@echo off
setlocal
cd /d "%~dp0"
title WARtool v0.8.6 local server
set PORT=8877

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
  goto python_found
)

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=python"
  goto python_found
)

echo.
echo Python was not found, so WARtool cannot start its local server.
echo Install Python 3 from python.org and enable "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found
echo.
echo Starting WARtool v0.8.6 at http://localhost:%PORT%
echo Keep this window open while using the tool.
echo Press CTRL+C to stop it.
echo.

%PYTHON% server.py
if errorlevel 1 (
  echo.
  echo WARtool could not start its local server.
  echo Close any old WARtool server window and try again.
  echo You can also run CHECK_SERVER.bat to identify what is active.
  pause
)
