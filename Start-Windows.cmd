@echo off
setlocal
title Lens local patch - Windows wizard
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0windows_wizard.py"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Install Python 3.10+ from python.org and enable Add Python to PATH.
        echo Zainstaluj Python 3.10+ z python.org i wlacz Add Python to PATH.
        pause
        exit /b 1
    )
    python "%~dp0windows_wizard.py"
)
set "wizard_result=%errorlevel%"
echo.
pause
exit /b %wizard_result%
