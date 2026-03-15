import re

with open('app.py', 'r') as f:
    content = f.read()

# Instead of blindly replacing `executemany` with row-by-row, which might be slow and violates standard practices,
# The user specifically noted that if one fails, everything fails.
# By making it row-by-row with `try...except`, we can gracefully skip bad rows.
# Since it's a bulk upload, it shouldn't usually be more than a few hundred rows, so row-by-row is perfectly acceptable.
# Let's replace the `executemany` blocks and the `except Exception as e:` block.

old_blocks = """        # Batch Update
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
                    cf_catogory, accont_create_date, account_create_user, account_active, account_basment, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, 'LKR')
            \"\"\", to_insert)"""

new_blocks = """        # Process Updates row-by-row to skip failures
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
                    pass

        # Process Inserts row-by-row to skip failures
        if to_insert:
            for row in to_insert:
                try:
                    cursor.execute(\"\"\"
                        INSERT INTO new_account_table (
                            account_name, account_hold_possion_PL, account_hold_possion_Balace_Sheet,
                            account_name_of_catogory_PL, account_name_of_catogory_Balace_sheet,
                            account_income, account_expenses, account_assets, account_liabilities, account_equity,
                            cf_catogory, accont_create_date, account_create_user, account_active, account_basment, currency_code
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, 'LKR')
                    \"\"\", row)
                except Exception as e:
                    count -= 1
                    pass"""

content = content.replace(old_blocks, new_blocks)

with open('app.py', 'w') as f:
    f.write(content)
