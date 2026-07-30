@echo off
setlocal
cd /d "%~dp0"
set PORT=8877

rem Open the existing WARtool server when it is already running.
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:%PORT%/__wartool_health' -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
  start "" "http://localhost:%PORT%"
  exit /b 0
)

rem No server is running, so start it instead of opening a dead localhost page.
call "%~dp0START_WARTOOL.bat"
