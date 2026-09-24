@echo off
cd /d C:\Users\Srithiwankara\Desktop\Calude\ERP-WEB
echo ==== Sending the Management Account mapping changes to GitHub ====
git add app.py migrations.py templates/management_account_mapping.html push_mapping_fix.bat
git commit -m "Management Account mapping: Ignore / Restore for not-mapped accounts"
git push origin add-db-schema-15069424110250862180
echo.
echo ==== Done. Copy everything above and send it to Claude. ====
pause
