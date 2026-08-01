@echo off
cd /d "%~dp0"

call setup.bat
if errorlevel 1 goto :error

"%CD%\.venv\Scripts\python.exe" main.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Windy Image Tool could not start.
pause
exit /b 1
