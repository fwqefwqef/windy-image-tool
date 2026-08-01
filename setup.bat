@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "UV_CACHE_DIR=%CD%\.uv-cache"

if exist "%VENV_PYTHON%" goto :check_dependencies

where uv >nul 2>&1
if errorlevel 1 goto :missing_uv

echo Creating the project Python environment...
uv venv --python 3.14 .venv
if errorlevel 1 goto :error

:check_dependencies
"%VENV_PYTHON%" -c "import PIL, pillow_avif" >nul 2>&1
if not errorlevel 1 exit /b 0

where uv >nul 2>&1
if errorlevel 1 goto :missing_uv

echo Installing application dependencies...
uv pip install --python "%VENV_PYTHON%" -r requirements.txt
if errorlevel 1 goto :error
exit /b 0

:missing_uv
echo.
echo Python setup could not continue because uv is not installed.
echo Install uv from https://docs.astral.sh/uv/ and run this file again.
exit /b 1

:error
echo.
echo Python environment setup failed.
exit /b 1
