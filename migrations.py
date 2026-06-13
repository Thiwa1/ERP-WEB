import logging
import mysql.connector
def run_migrations(conn):
    """
    Orchestrates the execution of all schema migration steps.
    conn: Active database connection object.
    """
    if not conn:
        return

    try:
        cursor = conn.cursor()

        _ensure_migration_table(cursor)

        # Define helper function to check applied migrations
        def is_migration_applied(name):
            try:
                cursor.execute("SELECT id FROM migrations WHERE migration_name = %s", (name,))
                return cursor.fetchone() is not None
            except:
                return False

        # Define helper function to record applied migrations
        def record_migration(name):
            try:
                cursor.execute("INSERT INTO migrations (migration_name) VALUES (%s)", (name,))
                conn.commit()
            except mysql.connector.Error as e:
                if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
                    logging.error(f"Schema Migration Error: {e}")
            except Exception as e:
                pass # Ignore printing error for recording migration {name}

        # Execute individual migration steps
        _migrate_user_rights(cursor)
        _migrate_currency_table(cursor)
        _migrate_account_currency(cursor, conn, is_migration_applied, record_migration)
        _migrate_inventory_items(cursor)
        _migrate_suppliers_table(cursor)
        _migrate_company_table(cursor)
        _migrate_tax_rates(cursor)
        _migrate_cheque_print_settings(cursor)
        _migrate_wht_payable_account(cursor)
        _migrate_proforma_invoice(cursor)
        _migrate_approval_workflow(cursor)
        _migrate_pos_security_features(cursor)
        _migrate_password_length(cursor)
        _migrate_inventory_item_change_history(cursor)

        conn.commit()
        cursor.close()
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
        print(f"Schema Migration Error: {e}")

def _ensure_migration_table(cursor):
    """0. Create Migration Table if it doesn't exist."""
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS migrations (id INT AUTO_INCREMENT PRIMARY KEY, migration_name VARCHAR(255) UNIQUE NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for creating migrations table

def _migrate_user_rights(cursor):
    """1. Add columns to User_Rights table."""
    try:
        cursor.execute("SHOW COLUMNS FROM User_Rights")
        columns = [row[0] for row in cursor.fetchall()]

        new_columns = [
            'Access_Inventory', 'Access_POS', 'Access_Accounting', 'Access_Reports', 'Access_Reversals'
        ]

        for col in new_columns:
            if col not in columns:
                print(f"Migrating: Adding {col} to User_Rights")
                cursor.execute(f"ALTER TABLE User_Rights ADD COLUMN {col} TINYINT DEFAULT 0")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating User_Rights

def _migrate_currency_table(cursor):
    """2. Create currency_table if it doesn't exist."""
    try:
        cursor.execute("SHOW TABLES LIKE 'currency_table'")
        if not cursor.fetchone():
            print("Migrating: Creating currency_table")
            cursor.execute("""
                CREATE TABLE currency_table (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    currency_code VARCHAR(10) NOT NULL UNIQUE,
                    currency_name VARCHAR(100),
                    is_base_currency TINYINT DEFAULT 0
                )
            """)
            # Insert default if empty
            cursor.execute("INSERT INTO currency_table (currency_code, currency_name, is_base_currency) VALUES ('LKR', 'Sri Lankan Rupee', 1)")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating currency_table

def _migrate_account_currency(cursor, conn, is_migration_applied, record_migration):
    """3. Add currency_code to new_account_table."""
    if not is_migration_applied('add_currency_code_to_new_account'):
        try:
            cursor.execute("ALTER TABLE new_account_table ADD COLUMN currency_code VARCHAR(10) DEFAULT 'LKR'")
            record_migration('add_currency_code_to_new_account')
            print("Migrated: add_currency_code_to_new_account")
        except mysql.connector.Error as e:
            if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
                logging.error(f"Schema Migration Error: {e}")
        except Exception as e:
            if "Duplicate column" in str(e) or "1060" in str(e):
                record_migration('add_currency_code_to_new_account')
            else:
                print(f"Migration failed: {e}")

def _migrate_inventory_items(cursor):
    """4. Add UOM columns to inventoy_items."""
    try:
        cursor.execute("SHOW COLUMNS FROM inventoy_items")
        inv_columns = [row[0] for row in cursor.fetchall()]
        if 'uom_secondary' not in inv_columns:
            print("Migrating: Adding uom_secondary to inventoy_items")
            cursor.execute("ALTER TABLE inventoy_items ADD COLUMN uom_secondary VARCHAR(45) NULL")

        if 'uom_conversion_rate' not in inv_columns:
            print("Migrating: Adding uom_conversion_rate to inventoy_items")
            cursor.execute("ALTER TABLE inventoy_items ADD COLUMN uom_conversion_rate DOUBLE DEFAULT 1")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating inventoy_items

def _migrate_suppliers_table(cursor):
    """5. Add TIN and NIC columns to suppliers."""
    try:
        cursor.execute("SHOW COLUMNS FROM suppliers")
        sup_columns = [row[0] for row in cursor.fetchall()]

        if 'suppliers_TIN' not in sup_columns:
            print("Migrating: Adding suppliers_TIN to suppliers")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN suppliers_TIN VARCHAR(50) NULL")

        if 'suppliers_NIC' not in sup_columns:
            print("Migrating: Adding suppliers_NIC to suppliers")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN suppliers_NIC VARCHAR(20) NULL")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating suppliers table

def _migrate_company_table(cursor):
    """5b. Add vat_registered to company."""
    try:
        cursor.execute("SHOW COLUMNS FROM company")
        comp_columns = [row[0] for row in cursor.fetchall()]
        if 'vat_registered' not in comp_columns:
            print("Migrating: Adding vat_registered to company")
            cursor.execute("ALTER TABLE company ADD COLUMN vat_registered TINYINT DEFAULT 0")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating company table

def _migrate_tax_rates(cursor):
    """6. Create tax_rates table."""
    try:
        cursor.execute("SHOW TABLES LIKE 'tax_rates'")
        if not cursor.fetchone():
            print("Migrating: Creating tax_rates table")
            cursor.execute("""
                CREATE TABLE tax_rates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tax_name VARCHAR(100) NOT NULL,
                    rate DOUBLE NOT NULL,
                    description VARCHAR(255),
                    active TINYINT DEFAULT 1
                )
            """)
            # Default Data
            cursor.execute("INSERT INTO tax_rates (tax_name, rate, description) VALUES ('WHT - Interest', 10.0, 'Withholding Tax on Interest')")
            cursor.execute("INSERT INTO tax_rates (tax_name, rate, description) VALUES ('WHT - Rent', 10.0, 'Withholding Tax on Rent')")
            cursor.execute("INSERT INTO tax_rates (tax_name, rate, description) VALUES ('WHT - Professional Fees', 5.0, 'Withholding Tax on Professional Fees')")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating tax_rates table

def _migrate_cheque_print_settings(cursor):
    """7. Create cheque_print_settings table."""
    try:
        cursor.execute("SHOW TABLES LIKE 'cheque_print_settings'")
        if not cursor.fetchone():
            print("Migrating: Creating cheque_print_settings table")
            cursor.execute("""
                CREATE TABLE cheque_print_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bank_account VARCHAR(100) NULL,
                    paper_width_mm DOUBLE DEFAULT 175,
                    paper_height_mm DOUBLE DEFAULT 76,

                    date_x DOUBLE DEFAULT 140,
                    date_y DOUBLE DEFAULT 10,
                    date_font_size INT DEFAULT 10,

                    payee_x DOUBLE DEFAULT 20,
                    payee_y DOUBLE DEFAULT 25,
                    payee_font_size INT DEFAULT 11,

                    amount_words_x DOUBLE DEFAULT 25,
                    amount_words_y DOUBLE DEFAULT 35,
                    amount_words_font_size INT DEFAULT 10,
                    amount_words_width DOUBLE DEFAULT 130,

                    amount_digits_x DOUBLE DEFAULT 140,
                    amount_digits_y DOUBLE DEFAULT 35,
                    amount_digits_font_size INT DEFAULT 12,

                    is_cross_cheque TINYINT DEFAULT 1
                )
            """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating cheque_print_settings

def _migrate_wht_payable_account(cursor):
    """Add WHT Payable to new_account_table if missing."""
    try:
        cursor.execute("SELECT id FROM new_account_table WHERE account_name = 'WHT Payable'")
        if not cursor.fetchone():
            print("Migrating: Creating WHT Payable account")
            cursor.execute("""
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                    account_hold_possion_PL, account_name_of_catogory_PL,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    accont_create_date, account_create_user, account_active, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s, 1, %s)
            """, ('WHT Payable', 6, 'Current liabilities', None, None, None, None, None, 1, None, 0, 'CR'))
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating WHT Payable account

def _migrate_proforma_invoice(cursor):
    """8. Create Proforma Invoice Tables."""
    try:
        cursor.execute("SHOW TABLES LIKE 'proforma_invoice_header'")
        if not cursor.fetchone():
            print("Migrating: Creating proforma_invoice_header table")
            cursor.execute("""
                CREATE TABLE proforma_invoice_header (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pi_number VARCHAR(50) NOT NULL UNIQUE,
                    customer_name VARCHAR(200),
                    pi_date DATE,
                    expiry_date DATE,
                    subtotal DOUBLE,
                    vat_amount DOUBLE,
                    grand_total DOUBLE,
                    narration TEXT,
                    created_by INT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        cursor.execute("SHOW TABLES LIKE 'proforma_invoice_details'")
        if not cursor.fetchone():
            print("Migrating: Creating proforma_invoice_details table")
            cursor.execute("""
                CREATE TABLE proforma_invoice_details (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pi_id INT,
                    item_name VARCHAR(200),
                    description TEXT,
                    qty DOUBLE,
                    unit_price DOUBLE,
                    total DOUBLE,
                    FOREIGN KEY (pi_id) REFERENCES proforma_invoice_header(id) ON DELETE CASCADE
                )
            """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating proforma_invoice tables

def _migrate_password_length(cursor):
    """Update Password column length in Login_Table and Pose_Setting_Table to accommodate hashes."""
    try:
        print("Migrating: Extending Password column length in Login_Table")
        cursor.execute("ALTER TABLE Login_Table MODIFY COLUMN Password VARCHAR(255)")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating Password column length (Login_Table)

    try:
        print("Migrating: Extending Password column length in Pose_Setting_Table")
        cursor.execute("ALTER TABLE Pose_Setting_Table MODIFY COLUMN Password VARCHAR(255)")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating Password column length (Pose_Setting_Table)

def _migrate_inventory_item_change_history(cursor):
    """Create inventory_item_change_history table to track item detail edits."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_item_change_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id INT NOT NULL,
                item_name VARCHAR(255),
                field_changed VARCHAR(50) NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by_user_code VARCHAR(100),
                changed_by_user_pk INT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
        pass

def _migrate_pos_security_features(cursor):
    """10. POS Security & Expiry Date Updates."""
    try:
        # Pose_Setting_Table: failed_attempts, is_locked
        cursor.execute("SHOW COLUMNS FROM Pose_Setting_Table")
        pos_cols = [row[0] for row in cursor.fetchall()]

        if 'failed_attempts' not in pos_cols:
            print("Migrating: Adding failed_attempts to Pose_Setting_Table")
            cursor.execute("ALTER TABLE Pose_Setting_Table ADD COLUMN failed_attempts INT DEFAULT 0")

        if 'is_locked' not in pos_cols:
            print("Migrating: Adding is_locked to Pose_Setting_Table")
            cursor.execute("ALTER TABLE Pose_Setting_Table ADD COLUMN is_locked TINYINT DEFAULT 0")

        if 'must_change_password' not in pos_cols:
            print("Migrating: Adding must_change_password to Pose_Setting_Table")
            cursor.execute("ALTER TABLE Pose_Setting_Table ADD COLUMN must_change_password TINYINT DEFAULT 0")

        if 'Mobile_Number' not in pos_cols:
            print("Migrating: Adding Mobile_Number to Pose_Setting_Table")
            cursor.execute("ALTER TABLE Pose_Setting_Table ADD COLUMN Mobile_Number VARCHAR(20) NULL")

        # inventoy_items: expiry_date
        cursor.execute("SHOW COLUMNS FROM inventoy_items")
        inv_cols = [row[0] for row in cursor.fetchall()]
        if 'expiry_date' not in inv_cols:
            print("Migrating: Adding expiry_date to inventoy_items")
            cursor.execute("ALTER TABLE inventoy_items ADD COLUMN expiry_date DATE NULL")

        # Fixed Assets vendor and write-off extensions
        try:
            cursor.execute("SHOW COLUMNS FROM fixed_assets_register")
            fa_cols = [row[0] for row in cursor.fetchall()]
            if 'supplier_id' not in fa_cols:
                print("Migrating: Adding supplier_id to fixed_assets_register")
                cursor.execute("ALTER TABLE fixed_assets_register ADD COLUMN supplier_id BIGINT NULL")
                cursor.execute("ALTER TABLE fixed_assets_register ADD CONSTRAINT fk_supplier_fa FOREIGN KEY (supplier_id) REFERENCES suppliers(sup_id) ON DELETE SET NULL ON UPDATE CASCADE")
            if 'write_off_amount' not in fa_cols:
                print("Migrating: Adding write_off_amount to fixed_assets_register")
                cursor.execute("ALTER TABLE fixed_assets_register ADD COLUMN write_off_amount DOUBLE DEFAULT 0")
            if 'is_written_off' not in fa_cols:
                print("Migrating: Adding is_written_off to fixed_assets_register")
                cursor.execute("ALTER TABLE fixed_assets_register ADD COLUMN is_written_off TINYINT DEFAULT 0")
            if 'jv_id' not in fa_cols:
                print("Migrating: Adding jv_id to fixed_assets_register")
                cursor.execute("ALTER TABLE fixed_assets_register ADD COLUMN jv_id BIGINT NULL")
        except mysql.connector.Error as e:
            pass # Table might not exist yet

        # pos_user_devices
        cursor.execute("SHOW TABLES LIKE 'pos_user_devices'")
        if not cursor.fetchone():
            print("Migrating: Creating pos_user_devices table")
            cursor.execute("""
                CREATE TABLE pos_user_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    user_agent VARCHAR(255) NOT NULL,
                    last_login DATETIME NOT NULL
                )
            """)


        cursor.execute("SHOW TABLES LIKE 'sms_delivery_logs'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE sms_delivery_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mobile VARCHAR(20),
                    message TEXT,
                    status VARCHAR(50),
                    api_response TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        # pos_2fa_codes
        cursor.execute("SHOW TABLES LIKE 'pos_2fa_codes'")
        if not cursor.fetchone():
            print("Migrating: Creating pos_2fa_codes table")
            cursor.execute("""
                CREATE TABLE pos_2fa_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    code VARCHAR(6) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    is_used TINYINT DEFAULT 0
                )
            """)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating pos security features


def _migrate_approval_workflow(cursor):
    """9. Approval Workflow Updates."""
    try:
        # OP_NO_Table (Purchase Orders)
        cursor.execute("SHOW COLUMNS FROM OP_NO_Table")
        op_cols = [row[0] for row in cursor.fetchall()]
        if 'status' not in op_cols:
            print("Migrating: Adding status to OP_NO_Table")
            cursor.execute("ALTER TABLE OP_NO_Table ADD COLUMN status TINYINT DEFAULT 1")
            # Default 1 (Posted) for existing data to avoid breaking current flow

        # jv_numbers (Journal Vouchers - covers JV, Payments, Receipts)
        cursor.execute("SHOW COLUMNS FROM jv_numbers")
        jv_cols = [row[0] for row in cursor.fetchall()]
        if 'status' not in jv_cols:
            print("Migrating: Adding status to jv_numbers")
            cursor.execute("ALTER TABLE jv_numbers ADD COLUMN status TINYINT DEFAULT 1")

        # System Settings Table (for toggles)
        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        if not cursor.fetchone():
            print("Migrating: Creating system_settings table")
            cursor.execute("""
                CREATE TABLE system_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    setting_key VARCHAR(100) UNIQUE,
                    setting_value VARCHAR(255),
                    description VARCHAR(255)
                )
            """)
            cursor.execute("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('enable_approval_workflow', '0', 'Enable Park & Post Workflow (0=Disabled, 1=Enabled)')")

        # Create cash_bank_payment_type
        cursor.execute("SHOW TABLES LIKE 'cash_bank_payment_type'")
        if not cursor.fetchone():
            print("Migrating: Creating cash_bank_payment_type table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cash_bank_payment_type (
                  id INT NOT NULL AUTO_INCREMENT,
                  manua_recipt_number VARCHAR(255) NULL,
                  onlie_payment_recived TINYINT NULL,
                  online_transaction_code VARCHAR(255) NULL,
                  credit_card_no VARCHAR(45) NULL,
                  bank_transfer TINYINT NULL,
                  bank_transfer_id VARCHAR(255) NULL,
                  bank_cheque VARCHAR(255) NULL,
                  JV INT NULL,
                  PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception as e:
                pass # Ignore printing error for migrating approval workflow
