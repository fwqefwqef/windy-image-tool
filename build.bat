@echo off
cd /d "%~dp0"

call setup.bat
if errorlevel 1 goto :error

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "UV_CACHE_DIR=%CD%\.uv-cache"

echo Installing build dependencies...
uv pip install --python "%VENV_PYTHON%" -r requirements-build.txt -q
if errorlevel 1 goto :error

echo Building Windy Image Tool.exe...
"%VENV_PYTHON%" -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name "Windy Image Tool" ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import pillow_avif ^
  --collect-all pillow_avif ^
  main.py
if errorlevel 1 goto :error

echo.
echo Done. Executable: dist\Windy Image Tool.exe
exit /b 0

:error
echo Build failed.
exit /b 1
