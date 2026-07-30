@echo off
setlocal
set PORT=8877
echo Checking WARtool at http://localhost:%PORT%/__wartool_health
echo.
powershell -NoProfile -Command "try { $r = Invoke-RestMethod 'http://localhost:%PORT%/__wartool_health' -TimeoutSec 3; $r | ConvertTo-Json -Compress } catch { Write-Host 'WARtool is not running on port %PORT%.'; exit 1 }"
echo.
pause
