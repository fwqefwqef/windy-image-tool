@echo off
setlocal
cd /d "%~dp0"

where gh >nul 2>&1
if errorlevel 1 (
  echo GitHub CLI is not installed. Install it with: winget install GitHub.cli
  exit /b 1
)

gh auth status >nul 2>&1
if errorlevel 1 (
  echo Not logged into GitHub. Run this first:
  echo   gh auth login
  exit /b 1
)

echo Building portable exe...
call build.bat
if errorlevel 1 exit /b 1

echo Creating GitHub repository and pushing source...
gh repo view windy-image-tool >nul 2>&1
if errorlevel 1 (
  gh repo create windy-image-tool --public --source=. --remote=origin --push
) else (
  git push -u origin master
)

echo Creating GitHub release with exe...
gh release create v1.0.0 "dist\Windy Image Tool.exe" --title "Windy Image Tool v1.0.0" --notes "Portable Windows build of Windy Image Tool. Download Windy Image Tool.exe — no Python install required."

echo.
echo Done.
for /f "delims=" %%i in ('gh repo view --json url -q .url') do echo Repository: %%i/releases
