@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
  echo Git is not installed or is not available on PATH.
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo This folder is not a Git repository.
  exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo The GitHub remote named origin is not configured.
  exit /b 1
)

for /f "delims=" %%i in ('git branch --show-current') do set "BRANCH=%%i"
if not defined BRANCH (
  echo Cannot publish while Git is in detached HEAD state.
  exit /b 1
)

set "COMMIT_MESSAGE=%~1"
if not defined COMMIT_MESSAGE set "COMMIT_MESSAGE=Update Windy Image Tool"

echo Staging project changes...
git add --all
if errorlevel 1 goto :error

git diff --cached --quiet
if errorlevel 1 goto :commit
echo No new changes to commit.
goto :push

:commit
echo Committing as: %COMMIT_MESSAGE%
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 goto :error

:push
echo Pushing %BRANCH% to GitHub...
git push -u origin "%BRANCH%"
if errorlevel 1 goto :push_error

echo.
echo Published successfully.
for /f "delims=" %%i in ('git remote get-url origin') do echo Repository: %%i
exit /b 0

:push_error
echo.
echo GitHub rejected the push. Check your network, credentials, and whether the remote branch has newer commits.
exit /b 1

:error
echo.
echo Publishing failed before the push completed.
exit /b 1
