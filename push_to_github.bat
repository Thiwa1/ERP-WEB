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

REM (asked outside an if-block: inside one, %GIT_NAME% would still be the old, empty value)
if not "%GIT_NAME%"=="" goto have_name
set /p GIT_NAME="Your name (for commit history, e.g. Thiwanka): "
if "%GIT_NAME%"=="" set GIT_NAME=Thiwanka
git config --global user.name "%GIT_NAME%"
:have_name
if not "%GIT_EMAIL%"=="" goto have_email
set /p GIT_EMAIL="Your email (for commit history): "
if "%GIT_EMAIL%"=="" set GIT_EMAIL=srithiwankara@gmail.com
git config --global user.email "%GIT_EMAIL%"
:have_email

echo.
echo Committing as: %GIT_NAME% ^<%GIT_EMAIL%^>
echo.

REM Bring in what was pushed from the other computer first, so the push is not rejected
git pull --no-edit origin add-db-schema-15069424110250862180
echo.
git status
echo.

REM Nothing changed here - nothing to push
git status --porcelain | findstr . >nul
if errorlevel 1 (
    echo Nothing to commit - this folder already matches GitHub.
    echo.
    pause
    exit /b 0
)

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