@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\validate_static.py
) else (
  python tools\validate_static.py
)
echo.
node --check js\app.js 2>nul
if errorlevel 1 echo Node.js syntax check skipped or failed. The Python validation above is still authoritative for the data package.
echo.
pause
