@echo off
cd /d C:\Users\Srithiwankara\Desktop\Calude\ERP-WEB
echo ==== Sending the Management Account changes to GitHub ====
git add app.py templates/management_account.html templates/management_account_print.html push_mapping_fix.bat
git commit -m "Management Account: Variance Analysis tab, print menu with Excel-style printouts"
git push origin add-db-schema-15069424110250862180
echo.
echo ==== Done. Copy everything above and send it to Claude. ====
pause
