@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\validate_static.py || goto :fail
  py -3 tools\build_static_site.py || goto :fail
) else (
  python tools\validate_static.py || goto :fail
  python tools\build_static_site.py || goto :fail
)
echo.
echo GitHub Pages artifact created in _site\
pause
exit /b 0
:fail
echo.
echo Build failed. Read the validation error above.
pause
exit /b 1
