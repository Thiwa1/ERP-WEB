@echo off
cd /d C:\Users\Srithiwankara\Desktop\Calude\ERP-WEB
echo ==== Sending the mapping page fix to GitHub ====
git add templates/management_account_mapping.html
git commit -m "Mapping page: show duplicate mappings with untick boxes"
git push origin add-db-schema-15069424110250862180
echo.
echo ==== Done. Copy everything above and send it to Claude. ====
pause
