@echo off
cd /d C:\Users\Srithiwankara\Desktop\Calude\ERP-WEB
echo ==== Sending the Management Account mapping changes to GitHub ====
git add templates/management_account_mapping.html push_mapping_fix.bat
git commit -m "Management Account mapping: compact one-line sources"
git push origin add-db-schema-15069424110250862180
echo.
echo ==== Done. Copy everything above and send it to Claude. ====
pause
