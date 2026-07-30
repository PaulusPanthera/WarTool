@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\import_google_sheet.py
) else (
  python tools\import_google_sheet.py
)
if errorlevel 1 (
  echo.
  echo Live-data import failed. See data\live\import-report.json
  pause
  exit /b 1
)
echo.
echo Live Sheet data imported successfully.
echo Start WARtool with START_HERE.bat.
pause
