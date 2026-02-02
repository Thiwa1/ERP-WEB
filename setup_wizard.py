import mysql.connector
import os
import sys
from datetime import date

def get_input(prompt, default=None, is_password=False):
    if default:
        user_input = input(f"{prompt} [{default}]: ")
    else:
        user_input = input(f"{prompt}: ")

    if not user_input and default:
        return default
    return user_input

def read_schema_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def main():
    print("=== Suwin ERP Setup Wizard ===")
    print("This script will create the database, user, and seed initial data.")

    # Root Credentials
    root_host = get_input("MySQL Root Host", "localhost")
    root_user = get_input("MySQL Root User", "root")
    root_password = get_input("MySQL Root Password", "")

    # New App Credentials
    print("\n--- Application Database Configuration ---")
    app_db_name = get_input("Database Name", "Book_keeping")
    app_user = get_input("New Application User", "bookkeeper")
    app_pass = get_input("New Application Password", "bookkeeper123")

    try:
        # Connect as Root
        conn = mysql.connector.connect(
            host=root_host,
            user=root_user,
            password=root_password
        )
        cursor = conn.cursor()

        print(f"\nConnected to MySQL at {root_host}...")

        # Create Database
        print(f"Creating Database '{app_db_name}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{app_db_name}`")

        # Create User & Grant Privileges
        print(f"Creating User '{app_user}'...")
        try:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED BY '{app_pass}'")
        except mysql.connector.Error as err:
            # If user exists with different password/host, simpler to grant or update.
            # For setup, we assume fresh or idempotent.
            print(f"User creation note: {err}")
            cursor.execute(f"ALTER USER '{app_user}'@'%' IDENTIFIED BY '{app_pass}'")

        print("Granting Privileges...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON `{app_db_name}`.* TO '{app_user}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")

        # Switch to App DB
        conn.database = app_db_name

        # Run Schema
        print("Executing Schema...")
        schema_sql = read_schema_file('database_schema.sql')
        # Split by semicolon, but be careful with triggers/procedures
        # The provided schema dump has DELIMITER commands.
        # mysql-connector doesn't handle DELIMITER natively in execute().
        # We might need to split manually or use a shell command.
        # Using shell command is safer for complex dumps.

        cursor.close()
        conn.close()

        # Write temporary credentials config for migration
        # Actually, running via mysql client is better for the schema dump
        cmd = f"mysql -h {root_host} -u {root_user} -p'{root_password}' {app_db_name} < database_schema.sql"
        if not root_password:
             cmd = f"mysql -h {root_host} -u {root_user} {app_db_name} < database_schema.sql"

        print("Running Schema Import via System Shell...")
        ret = os.system(cmd)
        if ret != 0:
            print("Schema import failed. Please check your MySQL client configuration.")
            return

        # Reconnect to seed data
        conn = mysql.connector.connect(
            host=root_host,
            user=app_user,
            password=app_pass,
            database=app_db_name
        )
        cursor = conn.cursor()

        print("\n--- Seeding Default Data ---")

        # 1. Categories
        print("Seeding Categories...")
        bs_cats = [
            ('Non-Current Assets', 1), ('Current Assets', 2), ('Equity', 3),
            ('Non-Current Liabilities', 4), ('Current Liabilities', 5)
        ]
        for name, pos in bs_cats:
            cursor.execute("INSERT IGNORE INTO balance_sheet_category (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))

        pl_cats = [
            ('Revenue', 1), ('Cost Of Sales', 2), ('Operating Expenses', 3),
            ('Other Income', 4), ('Financial Costs', 5)
        ]
        for name, pos in pl_cats:
            cursor.execute("INSERT IGNORE INTO `p&l_category` (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))

        cf_cats = [
            ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
            ('Adjustments', 0), ('Changes In Working Capital', 0)
        ]
        for name, pos in cf_cats:
            cursor.execute("INSERT IGNORE INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", (name, pos))

        # 2. Inventory Categories
        print("Seeding Inventory Categories...")
        cursor.execute("INSERT IGNORE INTO inventory_carogory (main_catogory, sub_catogory) VALUES ('General', NULL)")
        cursor.execute("INSERT IGNORE INTO inventory_carogory (main_catogory, sub_catogory) VALUES (NULL, 'General')")

        # 3. Default Accounts
        print("Seeding Chart of Accounts...")
        accounts = [
            # Name, BS_Cat, PL_Cat, CF_Cat, Inc, Exp, Ast, Lia, Equ, Basement
            ('Cash In Hand', 'Current Assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
            ('Petty Cash', 'Current Assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
            ('Bank Account', 'Current Assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
            ('Accounts Receivable', 'Current Assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
            ('Inventory', 'Current Assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
            ('Property Plant Equipment', 'Non-Current Assets', None, 'Investing Activities', 0, 0, 1, 0, 0, 'DR'),

            ('Accounts Payable', 'Current Liabilities', None, 'Operating Activities', 0, 0, 0, 1, 0, 'CR'),
            ('VAT Payable', 'Current Liabilities', None, 'Operating Activities', 0, 0, 0, 1, 0, 'CR'),
            ('Bank Loan', 'Non-Current Liabilities', None, 'Financing Activities', 0, 0, 0, 1, 0, 'CR'),

            ('Share Capital', 'Equity', None, 'Financing Activities', 0, 0, 0, 0, 1, 'CR'),
            ('Retained Earnings', 'Equity', None, 'Operating Activities', 0, 0, 0, 0, 1, 'CR'),

            ('Sales', None, 'Revenue', 'Operating Activities', 1, 0, 0, 0, 0, 'CR'),
            ('Discount Received', None, 'Other Income', 'Operating Activities', 1, 0, 0, 0, 0, 'CR'),

            ('Cost Of Goods Sold', None, 'Cost Of Sales', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Rent Expense', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Salaries & Wages', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Electricity', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Telephone & Internet', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Water', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Printing & Stationery', None, 'Operating Expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
            ('Bank Charges', None, 'Financial Costs', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
        ]

        for acc in accounts:
            name, bs, pl, cf, inc, exp, ast, lia, equ, base = acc

            # Get Positions
            bs_pos = None
            if bs:
                cursor.execute("SELECT holding_position FROM balance_sheet_category WHERE name_of_category=%s", (bs,))
                res = cursor.fetchone()
                if res: bs_pos = res[0]

            pl_pos = None
            if pl:
                cursor.execute("SELECT holding_position FROM `p&l_category` WHERE name_of_category=%s", (pl,))
                res = cursor.fetchone()
                if res: pl_pos = res[0]

            query = """
                INSERT IGNORE INTO new_account_table (
                    account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                    account_hold_possion_PL, account_name_of_catogory_PL,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    cf_catogory, accont_create_date, account_active, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """
            cursor.execute(query, (
                name, bs_pos, bs, pl_pos, pl,
                inc, exp, ast, lia, equ,
                cf, date.today(), base
            ))

        # 4. Default Admin User
        print("Creating Default Admin User...")
        cursor.execute("SELECT COUNT(*) FROM Login_Table")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO Login_Table (User_Name, Password, User_Code, User_Active, Mobile_No, Email)
                VALUES ('admin', 'admin', 'ADM001', 1, '0000000000', 'admin@suwin.com')
            """)
            admin_id = cursor.lastrowid

            # Admin Rights (Full Access)
            cursor.execute("SHOW COLUMNS FROM User_Rights")
            cols = [row[0] for row in cursor.fetchall()]

            # Construct dynamic insert based on columns available
            rights = {
                'Link_To_Loging_Tabke': admin_id,
                'Add_New_User': 1,
                'OP_Approved': 1,
                'Plus_Btn': 1
            }
            if 'Access_Inventory' in cols: rights['Access_Inventory'] = 1
            if 'Access_POS' in cols: rights['Access_POS'] = 1
            if 'Access_Accounting' in cols: rights['Access_Accounting'] = 1
            if 'Access_Reports' in cols: rights['Access_Reports'] = 1
            if 'Access_Reversals' in cols: rights['Access_Reversals'] = 1

            columns = ', '.join(rights.keys())
            placeholders = ', '.join(['%s'] * len(rights))
            values = tuple(rights.values())

            cursor.execute(f"INSERT INTO User_Rights ({columns}) VALUES ({placeholders})", values)

        # 5. Default Company Profile
        print("Initializing Company Profile...")
        cursor.execute("SELECT COUNT(*) FROM company")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO company (id, company_name, company_curency)
                VALUES (0, 'My Company', 'LKR')
            """)

        conn.commit()
        print("\n=== Setup Complete! ===")
        print(f"You can now run the app and login with:")
        print(f"User: admin")
        print(f"Pass: admin")

    except mysql.connector.Error as err:
        print(f"\nError: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
