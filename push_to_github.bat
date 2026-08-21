@echo off
setlocal

cd /d "%~dp0"

echo ==============================================
echo   ERP-WEB - Push changes to GitHub
echo   Folder: %cd%
echo ==============================================
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
