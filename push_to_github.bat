@echo off
setlocal

cd /d "%~dp0"

echo ==============================================
echo   ERP-WEB - Push changes to GitHub
echo   Folder: %cd%
echo ==============================================
echo.

REM --- Make sure this folder is actually a git repository ---
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo ERROR: This folder is not a git repository.
    echo Make sure you are running this .bat file from INSIDE
    echo the ERP-WEB-git project folder, not a copy elsewhere.
    echo.
    pause
    exit /b 1
)

REM --- Make sure git knows who you are (only asks once, then remembers) ---
for /f "delims=" %%A in ('git config --global user.name 2^>nul') do set GIT_NAME=%%A
for /f "delims=" %%A in ('git config --global user.email 2^>nul') do set GIT_EMAIL=%%A

if "%GIT_NAME%"=="" (
    set /p GIT_NAME="Your name (for commit history, e.g. Thiwanka): "
    git config --global user.name "%GIT_NAME%"
)
if "%GIT_EMAIL%"=="" (
    set /p GIT_EMAIL="Your email (for commit history): "
    git config --global user.email "%GIT_EMAIL%"
)

echo.
echo Committing as: %GIT_NAME% ^<%GIT_EMAIL%^>
echo.

git status
echo.

set /p MSG="Commit message (describe what changed): "
if "%MSG%"=="" set MSG=Update

git add -A
git commit -m "%MSG%"
git push origin add-db-schema-15069424110250862180

echo.
echo ==============================================
echo   Done. If you see errors above, copy them
echo   and send them to Claude.
echo ==============================================
pause