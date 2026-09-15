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
        _migrate_invoice_currency(cursor)
        _migrate_pl_account_sort(cursor)
        _migrate_report_subtotals(cursor)
        _migrate_postdated_cheques(cursor)
        _migrate_report_period_prefs(cursor)
        _migrate_grn_payment_method(cursor)
        _migrate_grn_payment_ready(cursor)
        _migrate_daily_sales_entry(cursor)
        _migrate_daily_sales_sheet10(cursor)
        _migrate_daily_sales_card_banks(cursor)
        _migrate_daily_sales_sub_accounts(cursor)
        _migrate_daily_sales_advances_reports(cursor)
        _migrate_bar_inventory(cursor)
        _migrate_bar_inventory_item_code(cursor)
        _migrate_bar_inventory_ignored_codes(cursor)
        _migrate_bar_inventory_categories(cursor)
        _migrate_bar_inventory_sheet_amount(cursor)
        _migrate_bar_inventory_missing_items(cursor)
        _migrate_bar_inventory_adjustment(cursor)
        _migrate_bar_inventory_counted_qty(cursor)

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
            'Access_Inventory', 'Access_POS', 'Access_Accounting', 'Access_Reports', 'Access_Reversals',
            'Access_Daily_Sales', 'Access_Daily_Sales_Mapping'
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

def _migrate_report_subtotals(cursor):
    """Custom subtotal rows for the P&L and Balance Sheet (e.g. Gross Profit)."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_subtotals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_type VARCHAR(5) NOT NULL,
                label VARCHAR(100) NOT NULL,
                after_category VARCHAR(150) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_postdated_cheques(cursor):
    """Postdated Cheque (PDC) register: cheques recorded now (Bank Payment or
    Customer Receipt) that only post to the GL/bank book on their post date,
    instead of immediately. `payload` holds everything needed to post it
    later (payments list, WHT, currency, etc.) as JSON."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS postdated_cheques (
                id INT AUTO_INCREMENT PRIMARY KEY,
                pdc_type VARCHAR(10) NOT NULL,
                party_name VARCHAR(255),
                account_name VARCHAR(150),
                cheque_no VARCHAR(255),
                post_date DATE NOT NULL,
                issue_date DATE,
                amount DECIMAL(18,2) NOT NULL DEFAULT 0,
                narration TEXT,
                payload LONGTEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_by INT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                cleared_jv INT NULL,
                cleared_date DATE NULL
            )
        """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass


def _migrate_report_period_prefs(cursor):
    """Remembers each user's last-used Period 1/2/3 date ranges per report
    (e.g. Profit & Loss), so the report opens pre-filled with what they last
    generated instead of always resetting to the current month."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_period_prefs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                report_type VARCHAR(20) NOT NULL,
                periods_json TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_report_period_prefs_user_report (user_id, report_type)
            )
        """)
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_grn_payment_method(cursor):
    """Add a Payment Method tag (Cash / Cheque / etc) to GRN-created supplier
    invoices, and an optional default payment method per supplier that
    pre-fills it on the GRN screen."""
    try:
        cursor.execute("SHOW COLUMNS FROM suppliers_invoice_data LIKE 'suppliers_invoice_payment_method'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE suppliers_invoice_data ADD COLUMN suppliers_invoice_payment_method VARCHAR(20) NULL")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

    try:
        cursor.execute("SHOW COLUMNS FROM suppliers LIKE 'suppliers_default_payment_method'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE suppliers ADD COLUMN suppliers_default_payment_method VARCHAR(20) NULL")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_grn_payment_ready(cursor):
    """A manual 'Ready' flag on a GRN supplier invoice: some cheques/cash for
    supplier payments are physically prepared by another division (working
    off their own paper/offline document, not connected to this system) and
    the user gets a list from them — this flag lets the user check off which
    outstanding invoices already have their cheque/cash ready, without
    changing anything about the actual payment posting."""
    try:
        cursor.execute("SHOW COLUMNS FROM suppliers_invoice_data LIKE 'suppliers_invoice_payment_ready'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE suppliers_invoice_data ADD COLUMN suppliers_invoice_payment_ready TINYINT(1) NOT NULL DEFAULT 0")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_pl_account_sort(cursor):
    """Add per-account display order within its P&L / Balance Sheet category."""
    try:
        cursor.execute("SHOW COLUMNS FROM new_account_table LIKE 'account_pl_sort'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE new_account_table ADD COLUMN account_pl_sort INT NULL")
        cursor.execute("SHOW COLUMNS FROM new_account_table LIKE 'account_bs_sort'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE new_account_table ADD COLUMN account_bs_sort INT NULL")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_invoice_currency(cursor):
    """Add currency + exchange rate columns to Invoice_Oustanding for multi-currency sales invoices."""
    try:
        cursor.execute("SHOW COLUMNS FROM Invoice_Oustanding")
        cols = [row[0] for row in cursor.fetchall()]
        if 'invoice_currency' not in cols:
            cursor.execute("ALTER TABLE Invoice_Oustanding ADD COLUMN invoice_currency VARCHAR(10) NULL")
        if 'invoice_exchange_rate' not in cols:
            cursor.execute("ALTER TABLE Invoice_Oustanding ADD COLUMN invoice_exchange_rate DOUBLE DEFAULT 1")
    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

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

def _migrate_daily_sales_entry(cursor):
    """Front Office Daily Sales Entry (bar/restaurant/rooms daily sales sheet).

    Front office records the day's sales by category (rooms, food, beverage,
    buffet, discount, service charge, etc.) plus the cash/card/bank
    reconciliation, saves it as 'Parked' (draft), then whoever assigns the GL
    account posts it to the General Ledger (creates a jv_numbers + entry_details
    entry, same as every other posting module in this app).

    daily_sales_categories: the fixed list of sale lines (admin-assignable GL
      account per line - the 'assign / change GL account' requirement).
    daily_sales_entries: one header row per calendar day.
    daily_sales_entry_lines: the per-category amounts for that day.
    """
    try:
        cursor.execute("SHOW TABLES LIKE 'daily_sales_categories'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_categories table")
            cursor.execute("""
                CREATE TABLE daily_sales_categories (
                  id INT NOT NULL AUTO_INCREMENT,
                  category_key VARCHAR(50) NOT NULL,
                  description VARCHAR(150) NULL,
                  particulars VARCHAR(150) NULL,
                  display_order INT NOT NULL DEFAULT 0,
                  entry_side VARCHAR(2) NOT NULL DEFAULT 'CR',
                  gl_account_name VARCHAR(60) NULL,
                  is_active TINYINT NOT NULL DEFAULT 1,
                  PRIMARY KEY (id),
                  UNIQUE KEY category_key_UNIQUE (category_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

            # Seed with the categories from the front office's existing
            # "Daily Sales" Excel sheet, in the same order. entry_side is CR
            # (adds to Total Income) for every line except Discount, which
            # deducts from it.
            seed_rows = [
                ('ROOM1_NORMAL',   'Non A/C Rooms', 'Normal',          10, 'CR'),
                ('ROOM1_WEDDING',  'Non A/C Rooms', 'Wedding Couples', 20, 'CR'),
                ('ROOM1_EXTRABED', 'Non A/C Rooms', 'Extra Bed',       30, 'CR'),
                ('ROOM1_FOREIGN',  'Non A/C Rooms', 'Foreign',         40, 'CR'),
                ('ROOM2_NORMAL',   'A/C Rooms', 'Normal',          50, 'CR'),
                ('ROOM2_WEDDING',  'A/C Rooms', 'Wedding Couples', 60, 'CR'),
                ('ROOM2_EXTRABED', 'A/C Rooms', 'Extra Bed',       70, 'CR'),
                ('ROOM2_FOREIGN',  'A/C Rooms', 'Foreign',         80, 'CR'),
                ('ROOM_FOOD_SALE', 'Room Food Sale', None,             90, 'CR'),
                ('RESTAURANT_FOOD_SALES', 'Restaurant Food Sales', None, 100, 'CR'),
                ('DESSERT_DESSERT', 'Dessert Sales', 'Dessert',        110, 'CR'),
                ('DESSERT_FRUITS',  'Dessert Sales', 'Fruits',         120, 'CR'),
                ('TAKE_AWAY_SALES', 'Take Away Sales', None,           130, 'CR'),
                ('PICK_ME_SALES',   'Pick Me Sales', None,             140, 'CR'),
                ('FOOD_HUT_SALES',  'Food Hut Sales', None,            150, 'CR'),
                ('BEVERAGE_SALE',   'Beverage Sale', None,             160, 'CR'),
                ('SUNDRY_FOOD_DELIVERY', 'Sundry Sale', 'Food Delivery', 170, 'CR'),
                ('SUNDRY_WASHROOMS', 'Sundry Sale', 'Wash Rooms',      180, 'CR'),
                ('RESTAURANT_SALES', 'Restaurant Sales', None,         190, 'CR'),
                ('AERATED_WATER',   'RH Aerated Water & M/Water', None, 200, 'CR'),
                ('LOTUS_FOOD',      'Lotus Rooms', 'Food',             210, 'CR'),
                ('LOTUS_LIQUOR',    'Lotus Rooms', 'Liquor',           220, 'CR'),
                ('BUFFET_BREAKFAST','Buffet', 'Breakfast',             230, 'CR'),
                ('BUFFET_LUNCH',    'Buffet', 'Lunch',                 240, 'CR'),
                ('DISCOUNT',        'Discount', None,                  250, 'DR'),
                ('SERVICE_CHARGE',  'Service Charge', None,            260, 'CR'),
            ]
            cursor.executemany("""
                INSERT INTO daily_sales_categories
                    (category_key, description, particulars, display_order, entry_side)
                VALUES (%s, %s, %s, %s, %s)
            """, seed_rows)

        cursor.execute("SHOW TABLES LIKE 'daily_sales_entries'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_entries table")
            cursor.execute("""
                CREATE TABLE daily_sales_entries (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_date DATE NOT NULL,
                  narration VARCHAR(300) NULL,
                  total_income DOUBLE NOT NULL DEFAULT 0,
                  total_expenditure DOUBLE NOT NULL DEFAULT 0,
                  balance DOUBLE NOT NULL DEFAULT 0,
                  cash_float DOUBLE NOT NULL DEFAULT 0,
                  cash_amount DOUBLE NOT NULL DEFAULT 0,
                  credit_card_amount DOUBLE NOT NULL DEFAULT 0,
                  bank_transfer_amount DOUBLE NOT NULL DEFAULT 0,
                  status VARCHAR(10) NOT NULL DEFAULT 'Parked',
                  jv_id BIGINT NULL,
                  created_by INT NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_by INT NULL,
                  updated_date DATETIME NULL,
                  posted_by INT NULL,
                  posted_date DATETIME NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY entry_date_UNIQUE (entry_date),
                  INDEX idx_dse_status (status),
                  INDEX idx_dse_jv (jv_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        cursor.execute("SHOW TABLES LIKE 'daily_sales_entry_lines'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_entry_lines table")
            cursor.execute("""
                CREATE TABLE daily_sales_entry_lines (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_id BIGINT NOT NULL,
                  category_id INT NOT NULL,
                  nos DOUBLE NULL,
                  bill_no VARCHAR(100) NULL,
                  amount DOUBLE NOT NULL DEFAULT 0,
                  gl_account_name VARCHAR(60) NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY entry_category_UNIQUE (entry_id, category_id),
                  INDEX idx_dsel_entry (entry_id),
                  CONSTRAINT fk_dsel_entry FOREIGN KEY (entry_id)
                    REFERENCES daily_sales_entries(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        # Payment-method control accounts (which GL account Cash / Credit Card /
        # Bank Transfer collections are debited to when posting). Stored in the
        # existing generic system_settings key/value table.
        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        if cursor.fetchone():
            for key, desc in (
                ('daily_sales_cash_account', 'Daily Sales Entry: GL account for Cash collections'),
                ('daily_sales_card_account', 'Daily Sales Entry: GL account for Credit Card collections'),
                ('daily_sales_bank_account', 'Daily Sales Entry: GL account for Bank Transfer collections'),
            ):
                cursor.execute("SELECT id FROM system_settings WHERE setting_key = %s", (key,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO system_settings (setting_key, setting_value, description) VALUES (%s, '', %s)",
                        (key, desc)
                    )

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_daily_sales_sheet10(cursor):
    """Extends Daily Sales Entry with the other registers from the front
    office's daily sheet (Sheet10 of their Excel workbook), all sharing the
    same date/Park/Post lifecycle as the Sheet9 sales categories:

      - Complimentary Food & Liquor Register: free food/liquor given to
        MD, Management, Excise Dept, Police, Tour Guide, Entertainment.
        Reuses daily_sales_categories (new 'category_group'/'subgroup'
        columns) so it gets a GL account per line the same way sales lines
        do - but posts as its own balanced Dr Expense / Cr Food-or-Liquor-Cost
        pair, entirely separate from the Total Income / cash reconciliation.

      - Credit Received / Credit Given ledger: a simple named log (invoice
        no, party name, amount) - recorded for reference, NOT posted to the
        GL (the correct double-entry for a receivables sub-ledger needs
        more input from the business before automating it).

      - Income & Expenditure Summary: a handful of extra manual fields on
        the day's header (Telephone, Advance Received, Petty Cash, 3 misc
        expense lines) - also recorded for reference only, not GL-posted.
    """
    try:
        # 1. Categories: which "chart" a line belongs to, and (for
        #    Complimentary) whether it's Food or Liquor - decides which
        #    control account gets credited when posted.
        cursor.execute("SHOW COLUMNS FROM daily_sales_categories LIKE 'category_group'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_categories ADD COLUMN category_group VARCHAR(20) NOT NULL DEFAULT 'SALES'")
        cursor.execute("SHOW COLUMNS FROM daily_sales_categories LIKE 'subgroup'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_categories ADD COLUMN subgroup VARCHAR(20) NULL")

        # Seed the 12 Complimentary lines (6 recipients x Food/Liquor) if not already present
        cursor.execute("SELECT COUNT(*) FROM daily_sales_categories WHERE category_group = 'COMPLIMENTARY'")
        if cursor.fetchone()[0] == 0:
            print("Migrating: Seeding Complimentary Food & Liquor categories")
            recipients = ['MD', 'Management', 'Excise Department', 'Police', 'Tour Guide', 'Entertainment']
            seed_rows = []
            order = 500
            for subgroup in ('FOOD', 'LIQUOR'):
                for recipient in recipients:
                    key = f"COMP_{subgroup}_{recipient.upper().replace(' ', '_')}"
                    seed_rows.append((key, f"Complimentary {subgroup.title()}", recipient, order, 'DR', 'COMPLIMENTARY', subgroup))
                    order += 10
            cursor.executemany("""
                INSERT INTO daily_sales_categories
                    (category_key, description, particulars, display_order, entry_side, category_group, subgroup)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, seed_rows)

        # 2. Credit Received / Credit Given ledger (dynamic rows, one day can have many)
        cursor.execute("SHOW TABLES LIKE 'daily_sales_credit_lines'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_credit_lines table")
            cursor.execute("""
                CREATE TABLE daily_sales_credit_lines (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_id BIGINT NOT NULL,
                  credit_type VARCHAR(10) NOT NULL,
                  invoice_no VARCHAR(100) NULL,
                  party_name VARCHAR(200) NULL,
                  amount DOUBLE NOT NULL DEFAULT 0,
                  PRIMARY KEY (id),
                  INDEX idx_dscl_entry (entry_id),
                  CONSTRAINT fk_dscl_entry FOREIGN KEY (entry_id)
                    REFERENCES daily_sales_entries(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        # 3. Income & Expenditure Summary - extra manual fields on the day's header
        cursor.execute("SHOW COLUMNS FROM daily_sales_entries")
        dse_cols = [row[0] for row in cursor.fetchall()]
        extra_cols = [
            ('telephone_income',     "DOUBLE NOT NULL DEFAULT 0"),
            ('advance_received',     "DOUBLE NOT NULL DEFAULT 0"),
            ('petty_cash',           "DOUBLE NOT NULL DEFAULT 0"),
            ('misc_expense_1_label', "VARCHAR(100) NULL"),
            ('misc_expense_1_amount',"DOUBLE NOT NULL DEFAULT 0"),
            ('misc_expense_2_label', "VARCHAR(100) NULL"),
            ('misc_expense_2_amount',"DOUBLE NOT NULL DEFAULT 0"),
            ('misc_expense_3_label', "VARCHAR(100) NULL"),
            ('misc_expense_3_amount',"DOUBLE NOT NULL DEFAULT 0"),
        ]
        for col, ddl in extra_cols:
            if col not in dse_cols:
                cursor.execute(f"ALTER TABLE daily_sales_entries ADD COLUMN {col} {ddl}")

        # 4. Control accounts credited when Complimentary Food/Liquor is posted
        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        if cursor.fetchone():
            for key, desc in (
                ('daily_sales_food_cost_account', 'Daily Sales Entry: GL account credited for Complimentary Food'),
                ('daily_sales_liquor_cost_account', 'Daily Sales Entry: GL account credited for Complimentary Liquor'),
            ):
                cursor.execute("SELECT id FROM system_settings WHERE setting_key = %s", (key,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO system_settings (setting_key, setting_value, description) VALUES (%s, '', %s)",
                        (key, desc)
                    )

        # 5. Fix-up: the front office's original Excel sheet mislabelled the
        # second room block as "Non A/C Rooms" again (copy-paste error) when
        # it should read "A/C Rooms". Any daily_sales_categories table
        # created before this fix landed still has the old wrong label -
        # correct it every time (harmless / idempotent if already correct).
        cursor.execute("""
            UPDATE daily_sales_categories SET description = 'A/C Rooms'
            WHERE category_key IN ('ROOM2_NORMAL', 'ROOM2_WEDDING', 'ROOM2_EXTRABED', 'ROOM2_FOREIGN')
        """)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_daily_sales_card_banks(cursor):
    """Splits the single 'Credit Card' collection figure into the two
    merchant/bank facilities the front office actually settles card
    payments through (Sampath Bank, HNB Bank) - each posts to its own bank
    GL account. The old credit_card_amount column is left in place
    (unused going forward) so historical posted entries keep their data."""
    try:
        cursor.execute("SHOW COLUMNS FROM daily_sales_entries")
        dse_cols = [row[0] for row in cursor.fetchall()]
        for col in ('credit_card_sampath_amount', 'credit_card_hnb_amount', 'advance_given'):
            if col not in dse_cols:
                cursor.execute(f"ALTER TABLE daily_sales_entries ADD COLUMN {col} DOUBLE NOT NULL DEFAULT 0")
        # Reference/bill numbers for Advance Received and Advance Given
        for col in ('advance_received_bill_no', 'advance_given_bill_no'):
            if col not in dse_cols:
                cursor.execute(f"ALTER TABLE daily_sales_entries ADD COLUMN {col} VARCHAR(100) NULL")

        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        if cursor.fetchone():
            for key, desc in (
                ('daily_sales_card_sampath_account', 'Daily Sales Entry: GL account for Credit Card (Sampath Bank) collections'),
                ('daily_sales_card_hnb_account', 'Daily Sales Entry: GL account for Credit Card (HNB Bank) collections'),
            ):
                cursor.execute("SELECT id FROM system_settings WHERE setting_key = %s", (key,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO system_settings (setting_key, setting_value, description) VALUES (%s, '', %s)",
                        (key, desc)
                    )

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_daily_sales_sub_accounts(cursor):
    """Adds Sub-Account selection alongside the GL Account, matching how
    Journal Entry / Service Entry already pair Account + Sub-Account
    (sub_accont_for_new_account, scoped per account_name)."""
    try:
        cursor.execute("SHOW COLUMNS FROM daily_sales_categories LIKE 'gl_sub_account_code'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_categories ADD COLUMN gl_sub_account_code INT NULL")

        cursor.execute("SHOW COLUMNS FROM daily_sales_entry_lines LIKE 'gl_sub_account_code'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_entry_lines ADD COLUMN gl_sub_account_code INT NULL")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory(cursor):
    """Bar Item perpetual stock ledger (Sheet1 of the front office's Excel
    workbook): a running day-to-day Bottle/Ml stock balance per bar item.

    Each day: Opening Balance (auto-carried from the previous day's Closing
    Balance - or the item's own starting Opening Balance on day 1) + RF.Stock
    (received today) = Total Available; minus Today's Sales Bar Qty,
    Restaurant Sale Qty and ENT Qty (complimentary) = Closing Balance.

    unit_type on the item decides how the balance displays:
      'UNIT'      - whole units (cans, bottles counted as one each) - no ml split.
      'BOTTLE_ML' - a bottle holds bottle_size_ml (e.g. 750ml) - balance shown
                    as whole bottles + leftover ml from an opened bottle.
      'ML_ONLY'   - balance shown purely as a total ml figure, no bottle split.
    All quantities/balances are stored in the item's own base unit (ml for
    BOTTLE_ML/ML_ONLY, whole units for UNIT) so the arithmetic is always a
    plain running total - only the *display* differs by unit_type.
    """
    try:
        cursor.execute("SHOW TABLES LIKE 'bar_inventory_items'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_items table")
            cursor.execute("""
                CREATE TABLE bar_inventory_items (
                  id INT NOT NULL AUTO_INCREMENT,
                  item_name VARCHAR(150) NOT NULL,
                  display_order INT NOT NULL DEFAULT 0,
                  unit_type VARCHAR(10) NOT NULL DEFAULT 'UNIT',
                  bottle_size_ml DOUBLE NULL,
                  unit_price DOUBLE NOT NULL DEFAULT 0,
                  unit_price_restaurant DOUBLE NOT NULL DEFAULT 0,
                  opening_balance DOUBLE NOT NULL DEFAULT 0,
                  is_active TINYINT NOT NULL DEFAULT 1,
                  created_by INT NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  UNIQUE KEY item_name_UNIQUE (item_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        cursor.execute("SHOW TABLES LIKE 'bar_inventory_days'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_days table")
            cursor.execute("""
                CREATE TABLE bar_inventory_days (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_date DATE NOT NULL,
                  status VARCHAR(10) NOT NULL DEFAULT 'Draft',
                  created_by INT NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  verified_by INT NULL,
                  verified_date DATETIME NULL,
                  PRIMARY KEY (id),
                  UNIQUE KEY entry_date_UNIQUE (entry_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        cursor.execute("SHOW TABLES LIKE 'bar_inventory_day_lines'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_day_lines table")
            cursor.execute("""
                CREATE TABLE bar_inventory_day_lines (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  day_id BIGINT NOT NULL,
                  item_id INT NOT NULL,
                  opening_balance DOUBLE NOT NULL DEFAULT 0,
                  rf_stock DOUBLE NOT NULL DEFAULT 0,
                  total_available DOUBLE NOT NULL DEFAULT 0,
                  sales_bar_qty DOUBLE NOT NULL DEFAULT 0,
                  restaurant_sale_qty DOUBLE NOT NULL DEFAULT 0,
                  ent_qty DOUBLE NOT NULL DEFAULT 0,
                  closing_balance DOUBLE NOT NULL DEFAULT 0,
                  PRIMARY KEY (id),
                  UNIQUE KEY day_item_UNIQUE (day_id, item_id),
                  INDEX idx_bidl_item (item_id),
                  CONSTRAINT fk_bidl_day FOREIGN KEY (day_id)
                    REFERENCES bar_inventory_days(id) ON DELETE CASCADE,
                  CONSTRAINT fk_bidl_item FOREIGN KEY (item_id)
                    REFERENCES bar_inventory_items(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_item_code(cursor):
    """An optional, user-supplied external Item Code (e.g. the ID from
    another system being migrated from) - independent of this app's own
    auto-increment id, and usable as an alternate match key when uploading
    items or a day's quantities."""
    try:
        cursor.execute("SHOW COLUMNS FROM bar_inventory_items LIKE 'item_code'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bar_inventory_items ADD COLUMN item_code VARCHAR(50) NULL")
            cursor.execute("ALTER TABLE bar_inventory_items ADD UNIQUE KEY item_code_UNIQUE (item_code)")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_ignored_codes(cursor):
    """Codes that appear in the POS export but aren't bar stock at all
    (food, rooms, buffet, combo deals). Once a code is in here the upload
    preview lists it as 'Ignored - not a bar item' instead of flagging it
    as an error on every single upload."""
    try:
        cursor.execute("SHOW TABLES LIKE 'bar_inventory_ignored_codes'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_ignored_codes table")
            cursor.execute("""
                CREATE TABLE bar_inventory_ignored_codes (
                  id INT NOT NULL AUTO_INCREMENT,
                  code VARCHAR(50) NOT NULL,
                  label VARCHAR(200) NULL,
                  created_by INT NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  UNIQUE KEY code_UNIQUE (code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_categories(cursor):
    """Item categories (Beer, Arrack, Gin, ...) for grouping bar items on
    Manage Items, the day grid and the printout."""
    try:
        cursor.execute("SHOW TABLES LIKE 'bar_inventory_categories'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_categories table")
            cursor.execute("""
                CREATE TABLE bar_inventory_categories (
                  id INT NOT NULL AUTO_INCREMENT,
                  name VARCHAR(100) NOT NULL,
                  display_order INT NOT NULL DEFAULT 0,
                  is_active TINYINT(1) NOT NULL DEFAULT 1,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  UNIQUE KEY name_UNIQUE (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            defaults = ['Beer', 'Arrack', 'Gin', 'Brandy', 'Whisky', 'Rum', 'Vodka', 'Wine',
                        'Soft Drinks & Mixers', 'Water', 'Snacks', 'Cigarettes', 'Empties']
            for i, name in enumerate(defaults):
                cursor.execute("INSERT IGNORE INTO bar_inventory_categories (name, display_order) VALUES (%s, %s)",
                               (name, (i + 1) * 10))

        cursor.execute("SHOW COLUMNS FROM bar_inventory_items LIKE 'category_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bar_inventory_items ADD COLUMN category_id INT NULL")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_sheet_amount(cursor):
    """The day's sales figure from the POS/sales sheet, entered on the day
    grid so the stock-based Grand Total Sales Value can be checked against
    it (Difference = Grand Total - Sheet), as on the Excel Sheet1."""
    try:
        cursor.execute("SHOW COLUMNS FROM bar_inventory_days LIKE 'sheet_amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bar_inventory_days ADD COLUMN sheet_amount DOUBLE NULL")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_missing_items(cursor):
    """Items the barman sold but did not enter into the POS for a day. Each
    entry deducts from that day's stock (day line missing_qty = sum of the
    entries) and is valued at the item's bar price, so the amount can be
    followed up with the barman."""
    try:
        cursor.execute("SHOW TABLES LIKE 'bar_inventory_missing_items'")
        if not cursor.fetchone():
            print("Migrating: Creating bar_inventory_missing_items table")
            cursor.execute("""
                CREATE TABLE bar_inventory_missing_items (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  day_id BIGINT NOT NULL,
                  item_id INT NOT NULL,
                  qty DOUBLE NOT NULL DEFAULT 0,
                  unit_price DOUBLE NOT NULL DEFAULT 0,
                  amount DOUBLE NOT NULL DEFAULT 0,
                  barman VARCHAR(100) NULL,
                  remarks VARCHAR(255) NULL,
                  created_by INT NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  INDEX idx_bimi_day (day_id),
                  CONSTRAINT fk_bimi_day FOREIGN KEY (day_id)
                    REFERENCES bar_inventory_days(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        cursor.execute("SHOW COLUMNS FROM bar_inventory_day_lines LIKE 'missing_qty'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bar_inventory_day_lines ADD COLUMN missing_qty DOUBLE NOT NULL DEFAULT 0")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_adjustment(cursor):
    """Stock adjustment per item per day - a signed quantity (+ found / count
    up, - breakage, spillage, count short) added to the closing balance,
    with an optional reason for the audit trail."""
    try:
        cursor.execute("SHOW COLUMNS FROM bar_inventory_day_lines LIKE 'adjustment_qty'")
        if not cursor.fetchone():
            print("Migrating: Adding adjustment columns to bar_inventory_day_lines")
            cursor.execute("ALTER TABLE bar_inventory_day_lines ADD COLUMN adjustment_qty DOUBLE NOT NULL DEFAULT 0")

        cursor.execute("SHOW COLUMNS FROM bar_inventory_day_lines LIKE 'adjustment_note'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE bar_inventory_day_lines ADD COLUMN adjustment_note VARCHAR(255) NULL")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_bar_inventory_counted_qty(cursor):
    """Physical (manual) stock count per item per day, stored in the item's
    base unit (ml for Bottle+Ml / Ml items). NULL = not counted that day.
    Shown against the calculated closing balance as a variance."""
    try:
        cursor.execute("SHOW COLUMNS FROM bar_inventory_day_lines LIKE 'counted_qty'")
        if not cursor.fetchone():
            print("Migrating: Adding counted_qty to bar_inventory_day_lines")
            cursor.execute("ALTER TABLE bar_inventory_day_lines ADD COLUMN counted_qty DOUBLE NULL")

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass

def _migrate_daily_sales_advances_reports(cursor):
    """Advance and credit tracking + the MD's Daily Revenue Report (R1) /
    Cash Book (R2) on Daily Sales Entry.

      daily_sales_advances             - Advance Received (from guests: an
                                         "advance creditor") and Advance Given
                                         (paid out: an "advance debtor"), one
                                         row per advance with name + receipt no.
      daily_sales_advance_settlements  - later set-off / refund / recovery of
                                         an advance, linked to it, so every
                                         advance has a running balance.
      daily_sales_credit_lines         - Credit Received rows can point at the
                                         Credit Given row they settle
                                         (settles_credit_id) and say whether
                                         it was cash received or a set-off.
      daily_sales_report_rows          - which Daily Sales lines feed each row
                                         of the Daily Revenue Report (editable
                                         on the Report Row Mapping screen).
    """
    try:
        cursor.execute("SHOW TABLES LIKE 'daily_sales_advances'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_advances table")
            cursor.execute("""
                CREATE TABLE daily_sales_advances (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_id BIGINT NOT NULL,
                  entry_date DATE NOT NULL,
                  adv_type VARCHAR(10) NOT NULL,
                  party_name VARCHAR(200) NULL,
                  receipt_no VARCHAR(100) NULL,
                  amount DOUBLE NOT NULL DEFAULT 0,
                  remarks VARCHAR(255) NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  INDEX idx_dsa_entry (entry_id),
                  INDEX idx_dsa_date (entry_date, adv_type),
                  CONSTRAINT fk_dsa_entry FOREIGN KEY (entry_id)
                    REFERENCES daily_sales_entries(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            # Carry the old single Advance Received / Advance Given figures
            # into the new register so history isn't lost.
            cursor.execute("""
                INSERT INTO daily_sales_advances (entry_id, entry_date, adv_type, party_name, receipt_no, amount)
                SELECT id, entry_date, 'RECEIVED', NULL, advance_received_bill_no, advance_received
                FROM daily_sales_entries WHERE advance_received <> 0
            """)
            cursor.execute("""
                INSERT INTO daily_sales_advances (entry_id, entry_date, adv_type, party_name, receipt_no, amount)
                SELECT id, entry_date, 'GIVEN', NULL, advance_given_bill_no, advance_given
                FROM daily_sales_entries WHERE advance_given <> 0
            """)

        cursor.execute("SHOW TABLES LIKE 'daily_sales_advance_settlements'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_advance_settlements table")
            cursor.execute("""
                CREATE TABLE daily_sales_advance_settlements (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  entry_id BIGINT NOT NULL,
                  entry_date DATE NOT NULL,
                  advance_id BIGINT NOT NULL,
                  amount DOUBLE NOT NULL DEFAULT 0,
                  bill_no VARCHAR(100) NULL,
                  settle_mode VARCHAR(10) NOT NULL DEFAULT 'SETOFF',
                  remarks VARCHAR(255) NULL,
                  created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (id),
                  INDEX idx_dsas_entry (entry_id),
                  INDEX idx_dsas_advance (advance_id),
                  CONSTRAINT fk_dsas_entry FOREIGN KEY (entry_id)
                    REFERENCES daily_sales_entries(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        cursor.execute("SHOW COLUMNS FROM daily_sales_credit_lines LIKE 'settles_credit_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_credit_lines ADD COLUMN settles_credit_id BIGINT NULL")
        cursor.execute("SHOW COLUMNS FROM daily_sales_credit_lines LIKE 'settle_mode'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE daily_sales_credit_lines ADD COLUMN settle_mode VARCHAR(10) NULL")

        # New revenue lines the MD's report needs that the sales sheet lacked.
        for key, desc, order in (('BAR_REVENUE', 'Bar Revenue', 244), ('BAR_FOOD_REVENUE', 'Bar Food Revenue', 246)):
            cursor.execute("SELECT id FROM daily_sales_categories WHERE category_key = %s", (key,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO daily_sales_categories (category_key, description, particulars, display_order, entry_side)
                    VALUES (%s, %s, NULL, %s, 'CR')
                """, (key, desc, order))

        cursor.execute("SHOW TABLES LIKE 'daily_sales_report_rows'")
        if not cursor.fetchone():
            print("Migrating: Creating daily_sales_report_rows table")
            cursor.execute("""
                CREATE TABLE daily_sales_report_rows (
                  id INT NOT NULL AUTO_INCREMENT,
                  report VARCHAR(10) NOT NULL DEFAULT 'R1',
                  row_key VARCHAR(50) NOT NULL,
                  label VARCHAR(150) NOT NULL,
                  row_type VARCHAR(12) NOT NULL DEFAULT 'REVENUE',
                  category_keys VARCHAR(1000) NULL,
                  room_count INT NULL,
                  display_order INT NOT NULL DEFAULT 0,
                  PRIMARY KEY (id),
                  UNIQUE KEY row_key_UNIQUE (row_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            # row_type: OCCUPANCY (sum of Nos / rooms), NOS (sum of Nos),
            # REVENUE (sum of amounts). Total Revenue is computed.
            seed = [
                ('OCC_NONAC', 'Room Occupancy Rate (Non A/C)', 'OCCUPANCY', 'ROOM1_NORMAL,ROOM1_WEDDING,ROOM1_FOREIGN', 10),
                ('OCC_AC', 'AC Room Occupancy Rate', 'OCCUPANCY', 'ROOM2_NORMAL,ROOM2_WEDDING,ROOM2_FOREIGN', 20),
                ('NOS_BREAKFAST', "B'Buffet Nos", 'NOS', 'BUFFET_BREAKFAST', 30),
                ('NOS_LUNCH', 'Lunch Buffet Nos', 'NOS', 'BUFFET_LUNCH', 40),
                ('REV_NONAC_ROOMS', 'Non AC Rooms Revenue', 'REVENUE', 'ROOM1_NORMAL,ROOM1_WEDDING,ROOM1_EXTRABED,ROOM1_FOREIGN', 110),
                ('REV_AC_ROOMS', 'AC Room Revenue', 'REVENUE', 'ROOM2_NORMAL,ROOM2_WEDDING,ROOM2_EXTRABED,ROOM2_FOREIGN', 120),
                ('REV_ROOM_FOOD', 'Room Food Revenue', 'REVENUE', 'ROOM_FOOD_SALE', 130),
                ('REV_REST_FOOD', 'Restaurant Food Revenue', 'REVENUE', 'RESTAURANT_FOOD_SALES', 140),
                ('REV_DESSERT', 'Dessert Revenue', 'REVENUE', 'DESSERT_DESSERT', 150),
                ('REV_DESSERT_FRUIT', 'Dessert Fruit Revenue', 'REVENUE', 'DESSERT_FRUITS', 160),
                ('REV_BEVERAGE', 'Beverage Revenue', 'REVENUE', 'BEVERAGE_SALE', 170),
                ('REV_REST_BAR', 'Restaurant Bar Revenue', 'REVENUE', 'RESTAURANT_SALES', 180),
                ('REV_LOTUS', 'Lotus Food & Liquor Revenue', 'REVENUE', 'LOTUS_FOOD,LOTUS_LIQUOR', 190),
                ('REV_BUFFET_BREAKFAST', 'Buffet Breakfast Revenue', 'REVENUE', 'BUFFET_BREAKFAST', 200),
                ('REV_BUFFET_LUNCH', 'Buffet Lunch Revenue', 'REVENUE', 'BUFFET_LUNCH', 210),
                ('REV_TAKE_AWAY', 'Take Away Food Revenue', 'REVENUE', 'TAKE_AWAY_SALES', 220),
                ('REV_PICK_ME', 'Pick Me Food Revenue', 'REVENUE', 'PICK_ME_SALES', 230),
                ('REV_FOOD_HUT', 'Food Hut Revenue', 'REVENUE', 'FOOD_HUT_SALES', 240),
                ('REV_BAR', 'Bar Revenue', 'REVENUE', 'BAR_REVENUE', 250),
                ('REV_BAR_FOOD', 'Bar Food Revenue', 'REVENUE', 'BAR_FOOD_REVENUE', 260),
                ('REV_SERVICE_CHARGE', 'Service Charges', 'REVENUE', 'SERVICE_CHARGE', 270),
            ]
            cursor.executemany("""
                INSERT INTO daily_sales_report_rows (report, row_key, label, row_type, category_keys, display_order)
                VALUES ('R1', %s, %s, %s, %s, %s)
            """, seed)

    except mysql.connector.Error as e:
        if e.errno not in (1050, 1007, 1060, 1061, 1146, 1054, 1452, 1062):
            logging.error(f"Schema Migration Error: {e}")
    except Exception:
        pass
