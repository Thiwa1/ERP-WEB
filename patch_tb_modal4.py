# The user's main complaint was: "if one account fail all other setups going".
# Currently, save_bulk_gl_accounts does this:
# try:
#   loop through all rows, append to to_insert
#   cursor.executemany
#   conn.commit()
# except:
#   conn.rollback()

# If any single row violates a constraint, the ENTIRE batch fails.
# The user wants to "quick create missing accounts or creat account as compleasiom"
# Meaning they only want to create the completed/valid setups and skip those that fail.
# Let's change `save_bulk_gl_accounts` from using `executemany` to iterating through `to_update` and `to_insert` row by row within a `try-except` block, OR handle failures gracefully.
# But it's better to just process them row by row, commit the successful ones, and ignore the failed ones, returning the count of successful operations.
# Actually, the user says "if one account fail all other setups going .therefor I need creat accouts only compleated setups account."
# Let's modify `save_bulk_gl_accounts` to use row-by-row execution and catch exceptions PER ROW so that the entire transaction doesn't rollback.
import re

with open('app.py', 'r') as f:
    content = f.read()

# Replace the executemany blocks in `save_bulk_gl_accounts`.
old_update_block = """        # Batch Update
        if to_update:
            cursor.executemany(\"\"\"
                UPDATE new_account_table SET
                    account_hold_possion_PL=%s, account_hold_possion_Balace_Sheet=%s,
                    account_name_of_catogory_PL=%s, account_name_of_catogory_Balace_sheet=%s,
                    account_income=%s, account_expenses=%s, account_assets=%s, account_liabilities=%s, account_equity=%s,
                    cf_catogory=%s, account_basment=%s
                WHERE id=%s
            \"\"\", to_update)

        # Batch Insert
        if to_insert:
            cursor.executemany(\"\"\"
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_PL, account_hold_possion_Balace_Sheet,
                    account_name_of_catogory_PL, account_name_of_catogory_Balace_sheet,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    cf_catogory, account_add_date, account_add_user, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            \"\"\", to_insert)"""

new_update_block = """        # Process Updates
        if to_update:
            for row in to_update:
                try:
                    cursor.execute(\"\"\"
                        UPDATE new_account_table SET
                            account_hold_possion_PL=%s, account_hold_possion_Balace_Sheet=%s,
                            account_name_of_catogory_PL=%s, account_name_of_catogory_Balace_sheet=%s,
                            account_income=%s, account_expenses=%s, account_assets=%s, account_liabilities=%s, account_equity=%s,
                            cf_catogory=%s, account_basment=%s
                        WHERE id=%s
                    \"\"\", row)
                except Exception as e:
                    # Log error or continue to save other accounts
                    pass

        # Process Inserts
        if to_insert:
            for row in to_insert:
                try:
                    cursor.execute(\"\"\"
                        INSERT INTO new_account_table (
                            account_name, account_hold_possion_PL, account_hold_possion_Balace_Sheet,
                            account_name_of_catogory_PL, account_name_of_catogory_Balace_sheet,
                            account_income, account_expenses, account_assets, account_liabilities, account_equity,
                            cf_catogory, account_add_date, account_add_user, account_basment
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    \"\"\", row)
                except Exception as e:
                    # Ignore the failed account so others can succeed
                    count -= 1
                    pass"""

if old_update_block in content:
    content = content.replace(old_update_block, new_update_block)
    with open('app.py', 'w') as f:
        f.write(content)
    print("Replaced executemany with row-by-row execution in save_bulk_gl_accounts")
else:
    print("Could not find the executemany blocks to replace in app.py")
