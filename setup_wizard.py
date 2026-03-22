import mysql.connector
import os
import subprocess

from datetime import date
import getpass

def get_input(prompt, default=None, is_password=False):
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "

    if is_password:
        user_input = getpass.getpass(prompt_text)
    else:
        user_input = input(prompt_text)

    if not user_input and default:
        return default
    return user_input

def read_schema_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def get_user_inputs():
    print("=== Suwin ERP Setup Wizard ===")
    print("This script will create the database, user, and seed initial data.")

    config = {}
    config['root_host'] = get_input("MySQL Root Host", "localhost")
    config['root_user'] = get_input("MySQL Root User", "root")
    config['root_password'] = get_input("MySQL Root Password", "")

    print("\n--- Application Database Configuration ---")
    config['app_db_name'] = get_input("Database Name", "Book_keeping")

    vat_input = get_input("Is the company VAT Registered? (y/n)", "n")
    config['vat_registered'] = 1 if vat_input.lower().startswith('y') else 0
    config['app_user'] = get_input("New Application User", "bookkeeper")
    config['app_pass'] = get_input("New Application Password", "bookkeeper123")

    return config

def setup_database_and_user(config, cursor):
    app_db_name = config['app_db_name']
    app_user = config['app_user']
    app_pass = config['app_pass']

    # Prefix DB name with db_suport_name (sri_) if needed
    db_suport_name = "sri"
    if not app_db_name.startswith(f"{db_suport_name}_"):
        app_db_name = f"{db_suport_name}_{app_db_name}"

    print(f"Creating Database '{app_db_name}'...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{app_db_name}`")

    print(f"Creating User '{app_user}'...")
    try:
        cursor.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED BY '{app_pass}'")
    except mysql.connector.Error as err:
        print(f"User creation note: {err}")
        cursor.execute(f"ALTER USER '{app_user}'@'%' IDENTIFIED BY '{app_pass}'")

    print("Granting Privileges...")
    cursor.execute(f"GRANT ALL PRIVILEGES ON `{app_db_name}`.* TO '{app_user}'@'%'")
    cursor.execute("FLUSH PRIVILEGES")

def execute_schema(config):
    root_host = config['root_host']
    root_user = config['root_user']
    root_password = config['root_password']
    app_db_name = config['app_db_name']

    print("Executing Schema...")
    # read_schema_file('database_schema.sql') is technically read but not directly used here
    # Since it was previously read and then run via subprocess, we keep the subprocess logic.

    print("Running Schema Import via System Shell...")
    try:
        cmd = ['mysql', '-h', root_host, '-u', root_user]
        if root_password:
            cmd.append(f'-p{root_password}')
        cmd.append(app_db_name)

        with open('database_schema.sql', 'r') as f:
            ret = subprocess.run(cmd, stdin=f)

        if ret.returncode != 0:
             print("Schema import failed. Please check your MySQL client configuration.")
             return False

    except Exception as e:
        print(f"Error running schema import: {e}")
        return False

    if os.path.exists('fixed_assets.sql'):
        print("Importing Fixed Assets Schema...")
        try:
            cmd_fa = ['mysql', '-h', root_host, '-u', root_user]
            if root_password:
                cmd_fa.append(f'-p{root_password}')
            cmd_fa.append(app_db_name)

            with open('fixed_assets.sql', 'r') as f:
                subprocess.run(cmd_fa, stdin=f)
        except Exception as e:
            print(f"Error running fixed assets schema import: {e}")

    return True

def seed_default_data(config, cursor):
    vat_registered = config['vat_registered']

    print("\n--- Seeding Default Data ---")

    print("Seeding Categories...")
    bs_cats = [
        ('ASSETS', 1),
        ('Non-current assets', 2),
        ('Current assets', 3),
        ('EQUITY AND LIABILITIES', 4),
        ('Capital and reserves', 5),
        ('Current liabilities', 6)
    ]
    for name, pos in bs_cats:
        cursor.execute("INSERT IGNORE INTO balance_sheet_category (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))

    pl_cats = [
        ('Revenue', 1),
        ('Cost of sales', 2),
        ('Gross profit', 3),
        ('Other operating income', 3),
        ('Distribution costs', 4),
        ('Administrative expenses', 5),
        ('Other operating expenses', 6),
        ('Finance cost', 7),
        ('Income from associates', 8),
        ('Income tax expenses', 9),
        ('Minority interest', 10),
        ('Extraordinary items', 11)
    ]
    for name, pos in pl_cats:
        cursor.execute("INSERT IGNORE INTO `p&l_category` (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", (name, pos, date.today()))

    cf_cats = [
        ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
        ('Adjustments', 0), ('Changes In Working Capital', 0)
    ]
    for name, pos in cf_cats:
        cursor.execute("INSERT IGNORE INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", (name, pos))

    print("Seeding Inventory Categories...")
    cursor.execute("INSERT IGNORE INTO inventory_carogory (main_catogory, sub_catogory) VALUES ('General', NULL)")
    cursor.execute("INSERT IGNORE INTO inventory_carogory (main_catogory, sub_catogory) VALUES (NULL, 'General')")

    print("Seeding Chart of Accounts...")
    accounts = [
        ('Account Receivable', 'Current assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
        ('Account Payable', 'Current liabilities', None, 'Operating Activities', 0, 0, 0, 1, 0, 'CR'),
        ('Inventoy', 'Current assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
        ('VAT Control', 'Current liabilities', None, 'Operating Activities', 0, 0, 0, 1, 0, 'CR'),
        ('Income', None, 'Revenue', 'Operating Activities', 1, 0, 0, 0, 0, 'CR'),
        ('Cost Of Goods Sold', None, 'Cost of sales', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
        ('Cash In Hand', 'Current assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
        ('Bank Account', 'Current assets', None, 'Operating Activities', 0, 0, 1, 0, 0, 'DR'),
        ('Property Plant Equipment', 'Non-current assets', None, 'Investing Activities', 0, 0, 1, 0, 0, 'DR'),
        ('Share Capital', 'Capital and reserves', None, 'Financing Activities', 0, 0, 0, 0, 1, 'CR'),
        ('Retained Earnings', 'Capital and reserves', None, 'Operating Activities', 0, 0, 0, 0, 1, 'CR'),
        ('Salaries & Wages', None, 'Administrative expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
        ('Rent Expense', None, 'Administrative expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
        ('Electricity', None, 'Administrative expenses', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
        ('Bank Charges', None, 'Finance cost', 'Operating Activities', 0, 1, 0, 0, 0, 'DR'),
    ]

    for acc in accounts:
        name, bs, pl, cf, inc, exp, ast, lia, equ, base = acc

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

    print("Seeding Sub-Accounts...")
    cursor.execute("SELECT COUNT(*) FROM sub_accont_for_new_account WHERE sub_sub_accaount_name = 'POS SALE'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO sub_accont_for_new_account
            (sub_sub_accaount_name, sub_new_account, creat_date, active, sub_account_code)
            VALUES ('POS SALE', 'Income', %s, 1, 0)
        """, (date.today(),))

    print("Seeding Default Customer...")
    cursor.execute("SELECT COUNT(*) FROM customer WHERE costomer_name = 'Common customer'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO customer (
                customer_name, customer_code,
                customer_Billing_Address, costomer_Delivery_Address,
                e_mail, coustomer_credit_limit, Mobile_nimber,
                Compay_Or_Not, Create_Date
            ) VALUES ('Common customer', 60001, 'non', 'non', 'non', 0, '0000000000', 0, %s)
        """, (date.today(),))

    print("Seeding Default Supplier...")
    cursor.execute("SELECT COUNT(*) FROM suppliers WHERE supplier_name = 'Direct Payment'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO suppliers (
                supplier_name, supplier_code,
                supplier_create_date, Is_Suplier
            ) VALUES ('Direct Payment', '70001', %s, 1)
        """, (date.today(),))

    print("Creating Default Admin User...")
    cursor.execute("SELECT COUNT(*) FROM Login_Table")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO Login_Table (User_Name, Password, User_Code, User_Active, Mobile_No, Email)
            VALUES ('admin', 'admin', 'ADM001', 1, '0000000000', 'admin@suwin.com')
        """)
        admin_id = cursor.lastrowid

        cursor.execute("SHOW COLUMNS FROM User_Rights")
        cols = [row[0] for row in cursor.fetchall()]

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

    print("Initializing Company Profile...")
    cursor.execute("SELECT COUNT(*) FROM company")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO company (id, company_name, company_curency, vat_registered)
            VALUES (0, 'My Company', 'LKR', %s)
        """, (vat_registered,))

def write_env_file(config):
    root_host = config['root_host']
    app_user = config['app_user']
    app_pass = config['app_pass']
    app_db_name = config['app_db_name']

    print("\nCreating .env file...")
    with open('.env', 'w') as f:
        f.write("# Database Configuration\n")
        f.write(f"DB_HOST={root_host}\n")
        f.write(f"DB_USER={app_user}\n")
        f.write(f"DB_PASSWORD={app_pass}\n")
        f.write(f"DB_NAME={app_db_name}\n\n")
        f.write("# Security\n")
        f.write("SECRET_KEY=hardcoded_secret_key_for_development_only\n")

def main():
    config = get_user_inputs()

    try:
        conn = mysql.connector.connect(
            host=config['root_host'],
            user=config['root_user'],
            password=config['root_password']
        )
        cursor = conn.cursor()

        print(f"\nConnected to MySQL at {config['root_host']}...")

        setup_database_and_user(config, cursor)

        conn.database = config['app_db_name']

        # Read the schema file to ensure it's there/used by legacy code (like test mocks)
        # Even though execute_schema doesn't use it directly, read_schema_file was called here previously.
        schema_sql = read_schema_file('database_schema.sql')

        cursor.close()
        conn.close()

        if not execute_schema(config):
            return

        conn = mysql.connector.connect(
            host=config['root_host'],
            user=config['app_user'],
            password=config['app_pass'],
            database=config['app_db_name']
        )
        cursor = conn.cursor()

        seed_default_data(config, cursor)
        conn.commit()

        write_env_file(config)

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
