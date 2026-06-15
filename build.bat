@echo off
cd /d "%~dp0"

echo Installing build dependencies...
python -m pip install -r requirements.txt -r requirements-build.txt -q
if errorlevel 1 goto :error

echo Building Windy Image Tool.exe...
python -m PyInstaller ^
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
