import flask
from flask import render_template, request, redirect, url_for, flash, session, make_response, Response, stream_with_context
from database import Database
from datetime import datetime, date
from functools import wraps
from jinja2 import pass_context
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import io
import json
import os

import difflib
import time
import knowledge_base
import random # For mocking exchange rate
import subprocess
import requests
import string
from datetime import timedelta
import mysql.connector
import urllib.request
import typing
from dataclasses import dataclass

app = flask.Flask(__name__)

# Global cache for exchange rates
exchange_rate_cache = {}
CACHE_DURATION = 3600  # 1 hour
import tempfile

# Global cache for categories
_category_cache = {}

def get_cached_categories(db):
    global _category_cache
    if not _category_cache:
        bs = db.execute_query("SELECT name_of_category, holding_position FROM balance_sheet_category")
        pl = db.execute_query("SELECT name_of_category, holding_position FROM `p&l_category`")
        cf = db.execute_query("SELECT catogory_name FROM cf_catogory ORDER BY hold_level, catogory_name")
        _category_cache = {'bs_cats': bs, 'pl_cats': pl, 'cf_cats': cf}
    return _category_cache['bs_cats'], _category_cache['pl_cats'], _category_cache['cf_cats']

def clear_category_cache():
    global _category_cache
    _category_cache.clear()

import services
from num2words import num2words
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import logging
import shutil
import re
import os
import PyPDF2
import io

import migrations
import secrets

app = flask.Flask(__name__)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Set a secret key for session management.
# In production, this should be set via environment variable.
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    # Ensure a secret key is explicitly set in the environment
    raise RuntimeError("No SECRET_KEY set for Flask application. This is a required environment variable for security.")

app.config['SECRET_KEY'] = app.secret_key

# Theme Configuration
THEMES = {
    'default': {
        'name': 'Professional (Default)',
        'primary': '#0f172a',
        'secondary': '#1e293b',
        'accent': '#2563eb'
    },
    'ocean': {
        'name': 'Ocean Blue',
        'primary': '#003366',
        'secondary': '#004080',
        'accent': '#0073e6'
    },
    'pro_blue': {
        'name': 'Pro Sky Blue',
        'primary': '#0070F2',
        'secondary': '#4DB1FF',
        'accent': '#0057D2'
    },
    'forest': {
        'name': 'Forest Green',
        'primary': '#143d14',
        'secondary': '#1f5c1f',
        'accent': '#2eb82e'
    },
    'ruby': {
        'name': 'Ruby Red',
        'primary': '#4d0000',
        'secondary': '#800000',
        'accent': '#e60000'
    },
    'midnight': {
        'name': 'Midnight Dark',
        'primary': '#000000',
        'secondary': '#1a1a1a',
        'accent': '#ffcc00'
    },
    'sap_neutral_deep': {
        'name': 'SAP Neutral Deep',
        'primary': '#00305D',
        'secondary': '#003B72',
        'accent': '#0055A5'
    },
    'sap_neutral_mid': {
        'name': 'SAP Neutral Mid',
        'primary': '#0065C3',
        'secondary': '#0074E2',
        'accent': '#168EFF'
    },
    'sap_neutral_light': {
        'name': 'SAP Neutral Light',
        'primary': '#3FA2FF',
        'secondary': '#62B3FF',
        'accent': '#8BC7FF'
    }
}

# Database Configuration
# Credentials should be set in .env file or environment variables for security.
db_suport_name = "sri"

# Force prefix onto database name to handle shared hosting constraints
_raw_db_name = os.environ.get('DB_NAME', 'Book_keeping')
if _raw_db_name.startswith(f"{db_suport_name}_"):
    _final_db_name = _raw_db_name
else:
    _final_db_name = f"{db_suport_name}_{_raw_db_name}"

db_config = {
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '21219125'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': _final_db_name,
    'raise_on_warnings': True
}


# Ensure critical database configuration is present
if not db_config['user']:
    print("Warning: DB_USER not set in environment variables.")

db = Database(db_config)
MASTER_DB_NAME = f"{db_suport_name}_Book_keeping_Master"

def get_session_db_name():
    """Returns the correct database name based on session."""
    # If standard user
    if 'db_name' in session:
        return session['db_name']
    return db_config['database']

db.set_db_name_getter(get_session_db_name)

# Master DB Connection (Dedicated)
master_db_config = db_config.copy()
master_db_config['database'] = MASTER_DB_NAME
master_db = Database(master_db_config)

def setup_master_db():
    """Ensure the Master DB and its tables exist."""
    try:
        # Connect without DB to create Master DB if needed
        temp_config = db_config.copy()
        if 'database' in temp_config:
            del temp_config['database']

        try:
            conn = mysql.connector.connect(**temp_config)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MASTER_DB_NAME}")
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            if e.errno in (1007, 1044):
                logging.warning(f"Ignored DB creation error {e.errno} for Master DB: {e.msg}")
            else:
                raise e

        # Now create tables in Master DB
        master_db.execute_query("""
            CREATE TABLE IF NOT EXISTS tenants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL UNIQUE,
                db_name VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        master_db.execute_query("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                tenant_id INT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            )
        """)
        print("Master DB setup complete.")

        # 3. Setup Default/Fallback Database if missing tables (e.g. Login_Table)
        default_db_name = db_config['database']

        # Check if default DB has Login_Table
        try:
            try:
                default_conn = mysql.connector.connect(**temp_config)
                default_cursor = default_conn.cursor()
                default_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{default_db_name}`")
                default_cursor.close()
                default_conn.close()
            except mysql.connector.Error as e:
                if e.errno in (1007, 1044):
                    logging.warning(f"Ignored DB creation error {e.errno} for default DB: {e.msg}")
                else:
                    raise e

            # Connect to default DB to check for tables
            check_config = db_config.copy()
            check_conn = mysql.connector.connect(**check_config)
            check_cursor = check_conn.cursor()

            # Try selecting from Login_Table to see if it exists
            table_exists = False
            try:
                check_cursor.execute("SELECT 1 FROM Login_Table LIMIT 1")
                check_cursor.fetchall()
                table_exists = True
            except mysql.connector.errors.ProgrammingError:
                pass

            if not table_exists:
                import re
                print(f"Initializing schema for default database: {default_db_name}")
                if os.path.exists('database_schema.sql'):
                    with open('database_schema.sql', 'r') as f:
                        content = re.sub(r'(?i)Book_keeping', default_db_name, f.read())
                        parse_and_execute_sql(check_cursor, content)

                if os.path.exists('fixed_assets.sql'):
                    with open('fixed_assets.sql', 'r') as f:
                        content = re.sub(r'(?i)Book_keeping', default_db_name, f.read())
                        parse_and_execute_sql(check_cursor, content)

                check_conn.commit()

                # Run application-level migrations on this default database to ensure all dynamic columns are present
                run_schema_migrations(check_conn)

                # Insert default admin user into fallback db
                try:
                    check_cursor.execute("""
                        INSERT INTO Login_Table (User_Name, Password, Email, User_Code, User_Active)
                        VALUES ('admin', 'admin', 'admin@example.com', '1001', 1)
                    """)
                    check_conn.commit()
                    user_id = check_cursor.lastrowid

                    check_cursor.execute("""
                        INSERT INTO User_Rights (
                            Link_To_Loging_Tabke, Add_New_User, OP_Approved, Access_Inventory,
                            Access_POS, Access_Accounting, Access_Reports, Access_Reversals
                        )
                        VALUES (%s, 1, 1, 1, 1, 1, 1, 1)
                    """, (user_id,))
                    check_conn.commit()
                except Exception as e:
                    print(f"Could not insert default admin: {e}")

            check_cursor.close()
            check_conn.close()

        except Exception as default_db_err:
            print(f"Error initializing default DB ({default_db_name}): {default_db_err}")

    except Exception as e:
        print(f"Error setting up Master DB: {e}")

def parse_and_execute_sql(cursor, content):
    """Parses SQL content with DELIMITER support and executes it."""
    delimiter = ';'
    statement = ""

    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()

        if stripped.upper().startswith('DELIMITER '):
            delimiter = stripped.split()[1]
            continue

        if stripped.startswith('--') or stripped.startswith('#'):
            continue

        if not statement and not stripped:
            continue

        statement += line + "\n"

        if statement.strip().endswith(delimiter):
            sql_to_run = statement.strip()
            if sql_to_run.endswith(delimiter):
                 sql_to_run = sql_to_run[:-len(delimiter)]

            if sql_to_run.strip():
                try:
                    cursor.execute(sql_to_run)
                    while cursor.nextset(): pass
                except mysql.connector.Error as e:
                    # If this is a CREATE SCHEMA/DATABASE statement and we hit 1007/1044, safely ignore
                    upper_sql = sql_to_run.upper()
                    if e.errno in (1007, 1044) and ("CREATE SCHEMA" in upper_sql or "CREATE DATABASE" in upper_sql):
                        logging.warning(f"Ignored DB/Schema creation error in parse_and_execute_sql: {e.msg}")
                    else:
                        print(f"SQL Error: {e} | Statement: {sql_to_run[:50]}...")
                        raise e
                except Exception as e:
                    print(f"SQL Error: {e} | Statement: {sql_to_run[:50]}...")
                    raise e
            statement = ""

def create_tenant_db(company_name, username, password, email, mobile=None):
    """Creates a new tenant DB, runs schema, and registers in Master DB."""
    import re

    safe_name = re.sub(r'[^a-z0-9]', '_', company_name.lower())
    db_name = f"{db_suport_name}_{safe_name}"

    existing_user = master_db.execute_query("SELECT id FROM users WHERE username = %s", (username,))
    if existing_user: return False, "Username already exists."

    existing_tenant = master_db.execute_query("SELECT id FROM tenants WHERE company_name = %s", (company_name,))
    if existing_tenant: return False, "Company already registered."

    try:
        # Create DB
        temp_config = db_config.copy()
        if 'database' in temp_config: del temp_config['database']
        try:
            conn = mysql.connector.connect(**temp_config)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            # 1007: Can't create database; database exists
            # 1044: Access denied for user to database (on shared hosting where DB must be pre-created)
            if e.errno in (1007, 1044):
                logging.warning(f"Ignored DB creation error {e.errno}: {e.msg} - assuming DB '{db_name}' is already created.")
            else:
                raise e

        # Connect to New DB
        t_config = db_config.copy()
        t_config['database'] = db_name
        t_conn = mysql.connector.connect(**t_config)
        t_cursor = t_conn.cursor()

        # Execute Schema
        if os.path.exists('database_schema.sql'):
            with open('database_schema.sql', 'r') as f:
                content = re.sub(r'(?i)Book_keeping', db_name, f.read())
                parse_and_execute_sql(t_cursor, content)

        if os.path.exists('fixed_assets.sql'):
            with open('fixed_assets.sql', 'r') as f:
                content = re.sub(r'(?i)Book_keeping', db_name, f.read())
                parse_and_execute_sql(t_cursor, content)

        t_conn.commit()

        # Run application-level migrations on this new database to ensure all dynamic columns are present
        run_schema_migrations(t_conn)

        t_conn.close()

        # Insert Admin User
        t_db_conf = db_config.copy()
        t_db_conf['database'] = db_name
        t_db = Database(t_db_conf)

        user_id = t_db.execute_query("""
            INSERT INTO Login_Table (User_Name, Password, Email, Mobile_No, User_Code, User_Active)
            VALUES (%s, %s, %s, %s, '1001', 1)
        """, (username, password, email, mobile), commit=True)

        # Grant all rights to the initial tenant admin user
        t_db.execute_query("""
            INSERT INTO User_Rights (
                Link_To_Loging_Tabke, Add_New_User, OP_Approved, Access_Inventory,
                Access_POS, Access_Accounting, Access_Reports, Access_Reversals
            )
            VALUES (%s, 1, 1, 1, 1, 1, 1, 1)
        """, (user_id,), commit=True)

        t_db.execute_query("INSERT INTO company (id, company_name) VALUES (1, %s)", (company_name,), commit=True)

        ensure_default_categories(t_db)
        ensure_default_accounts(t_db)

        # Insert into Master
        tenant_id = master_db.execute_query(
            "INSERT INTO tenants (company_name, db_name) VALUES (%s, %s)",
            (company_name, db_name),
            commit=True
        )

        master_db.execute_query("""
            INSERT INTO users (username, password, email, tenant_id)
            VALUES (%s, %s, %s, %s)
        """, (username, password, email, tenant_id), commit=True)

        return True, "Registration successful."

    except Exception as e:
        logging.error("Registration Error occurred.")
        return False, "An error occurred during registration."

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        company_name = request.form['company_name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        mobile = request.form.get('mobile')

        success, message = create_tenant_db(company_name, username, password, email, mobile)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')

    return render_template('register.html')

# Context Processor for Currency & Theme
@app.context_processor
def inject_globals():
    globals_dict = {}

    # Currency
    try:
        res = db.execute_query("SELECT company_curency FROM company LIMIT 1")
        globals_dict['company_currency'] = res[0]['company_curency'] if res and res[0]['company_curency'] else 'LKR'
    except:
        globals_dict['company_currency'] = 'LKR'

    # Theme
    try:
        res = db.execute_query("SELECT setting_value FROM system_settings WHERE setting_key = 'system_theme'")
        theme_key = res[0]['setting_value'] if res else 'default'
        globals_dict['current_theme'] = THEMES.get(theme_key, THEMES['default'])
        globals_dict['theme_key'] = theme_key
    except:
        globals_dict['current_theme'] = THEMES['default']
        globals_dict['theme_key'] = 'default'

    return globals_dict

# Custom Filter for Currency Formatting
@app.template_filter('currency')
@pass_context
def currency_filter(context, value, symbol=True):
    try:
        if value is None:
            value = 0

        # Format: 1,234.56
        formatted = "{:,.2f}".format(float(value))

        if not symbol:
            return formatted

        # Get symbol from context
        curr_symbol = context.get('company_currency', '')
        if curr_symbol:
            return f"{curr_symbol} {formatted}"
        return formatted
    except (ValueError, TypeError):
        return "0.00"

@app.template_filter('amount_in_words')
def amount_in_words(amount):
    """Converts a numeric amount to words (Rupees and Cents)."""
    try:
        amount = float(amount)
        if amount == 0:
            return "Zero Rupees Only"

        # num2words supports USD which formats as "dollars" and "cents"
        # We will use that and replace the currency names
        words = num2words(amount, to='currency', currency='USD', lang='en')

        # Replace currency names with local context (LKR)
        # Handle singular/plural variations just in case, though usually 'dollars' covers it
        # num2words output example: "one hundred dollars, fifty cents"

        words = words.replace('dollars', 'Rupees')
        words = words.replace('dollar', 'Rupee')
        words = words.replace('cents', 'Cents')
        words = words.replace('cent', 'Cent')

        # Capitalize for Cheque format (Title Case looks better)
        return words.title()
    except Exception as e:
        return f"Error converting amount: {e}"

def parse_float(value):
    """Safely parses a string or number into a float, handling commas and None."""
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.replace(',', '').strip()
            if not value: return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def parse_csv_file(file_storage, required_columns=None):
    """
    Parses a file-like object (e.g., Flask FileStorage) into a list of dictionaries.
    Handles multiple encodings and optional column validation.

    Args:
        file_storage: A Flask FileStorage object or similar with a .stream attribute or read() method.
        required_columns: A list of strings representing column headers that must be present.

    Returns:
        A list of dictionaries representing the CSV rows.

    Raises:
        ValueError: If decoding fails or required columns are missing.
    """
    try:
        # Read file bytes. If it's a FileStorage, use .stream.read() or .read()
        if hasattr(file_storage, 'stream'):
            file_bytes = file_storage.stream.read()
        elif hasattr(file_storage, 'read'):
            file_bytes = file_storage.read()
        else:
            raise ValueError("Invalid file object")

        # If file_bytes is empty, decoded_str will be empty, and csv.DictReader might not return headers
        # We need to handle this.
        if not file_bytes:
             if required_columns:
                 raise ValueError("File is empty, missing required columns: " + ", ".join(required_columns))
             return []

        decoded_str = None
        # Try multiple encodings
        for encoding in ['utf-8-sig', 'utf-16', 'utf-8', 'cp1252', 'latin1']:
            try:
                decoded_str = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded_str is None:
            raise ValueError("Unable to determine file encoding (tried utf-8, latin1, cp1252, utf-16)")

        stream = io.StringIO(decoded_str, newline=None)
        csv_input = csv.DictReader(stream)

        # Validate Headers
        if required_columns:
            # csv.DictReader reads headers on access to fieldnames or iteration
            headers = csv_input.fieldnames
            if not headers:
                 # Should have been caught by empty check unless file is only newlines?
                 raise ValueError("Missing required columns: " + ", ".join(required_columns))

            # Use strip() on headers for comparison?
            clean_headers = [h.strip() for h in headers if h]
            missing = [col for col in required_columns if col not in clean_headers]
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")

        rows = []
        for row in csv_input:
            # Clean keys/values
            clean_row = {k.strip(): (v.strip() if v else '') for k, v in row.items() if k}
            if not clean_row: continue # Skip empty rows

            rows.append(clean_row)

        return rows

    except Exception as e:
        # Re-raise ValueError directly, or wrap other exceptions
        if isinstance(e, ValueError): raise e
        raise ValueError(f"CSV Parsing Error: {str(e)}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def pos_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # A user can access POS endpoints if they are logged in via the dedicated POS login
        if session.get('pos_logged_in'):
            return f(*args, **kwargs)

        # Or if they are a standard web ERP user who has the 'Access_POS' permission
        if 'user_id' in session and check_permission('Access_POS'):
            return f(*args, **kwargs)

        # Otherwise, redirect to the specific POS login
        return redirect(url_for('pos_login'))
    return decorated_function

def get_current_user_id():
    return session.get('user_id', 0)

def get_current_user_pk():
    try:
        pk = session.get('user_pk', 0)
        return int(pk)
    except (ValueError, TypeError):
        return 0

def check_permission(perm_name):
    """Checks if current user has specific permission."""
    user_pk = session.get('user_pk')
    if not user_pk: return False

    try:
        # Fetch all rights for the user to handle potentially missing columns gracefully
        # This prevents SQL errors if schema isn't fully migrated or perm_name is invalid
        query = "SELECT * FROM User_Rights WHERE Link_To_Loging_Tabke = %s"
        res = db.execute_query(query, (user_pk,))

        # Check if permission exists in the row and is enabled
        if res and res[0].get(perm_name) == 1:
            return True

    except Exception as e:
        logging.error("Permission check error.")
        return False
    return False

def has_permission(perm):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))

            if not check_permission(perm):
                flash(f'Access Denied: Required permission {perm}', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return redirect(url_for('login'))

        # Check credentials
        # 1. Try Login via Master DB (Multi-Tenant)
        try:
            # Query Master DB for user and tenant DB
            master_user_res = master_db.execute_query("""
                SELECT u.username, u.password, t.db_name
                FROM users u
                JOIN tenants t ON u.tenant_id = t.id
                WHERE u.username = %s
            """, (username,))

            if master_user_res:
                master_user = master_user_res[0]
                if master_user['password'] == password:
                    # Login Successful on Master
                    session['db_name'] = master_user['db_name']
                    session['username'] = username

                    # Fetch User Details from Tenant DB (for permissions/FKs)
                    # Note: db instance now points to tenant_db via session
                    tenant_user_res = db.execute_query("SELECT id, User_Code FROM Login_Table WHERE User_Name = %s", (username,))

                    if tenant_user_res:
                        tenant_user = tenant_user_res[0]
                        session['user_id'] = tenant_user['User_Code']
                        session['user_pk'] = tenant_user['id']
                        return redirect(url_for('index'))
                    else:
                        flash('User record missing in tenant database.', 'danger')
                        session.pop('db_name', None)
                        return redirect(url_for('login'))
                else:
                    flash('Incorrect password.', 'danger')
                    return redirect(url_for('login'))
        except Exception as e:
            logging.error("Master Login Error occurred.")
            # Fallthrough to legacy

        # 2. Fallback to Legacy Login (Default DB)
        # Ensure clean session regarding tenant
        session.pop('db_name', None)

        query = "SELECT id, User_Code, Password FROM Login_Table WHERE User_Name = %s"
        users = db.execute_query(query, (username,))

        if users is None:
            error_msg = f"Database connection failed: {db.last_error}" if db.last_error else "Database connection failed."
            flash(error_msg, 'danger')
        elif users:
            user = users[0]
            stored_password = user['Password']

            verified = False
            migrated = False

            # 1. Try Hash Verification
            from werkzeug.security import check_password_hash, generate_password_hash
            try:
                if stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:'):
                    if check_password_hash(stored_password, password):
                        verified = True
                else:
                    raise ValueError("Not a valid hash")
            except Exception:
                # stored_password might not be a valid hash format (e.g. plain text)
                pass

            # 2. Fallback to Plain Text (Legacy Support & Migration)
            if not verified:
                if stored_password == password:
                    verified = True
                    # Upgrade to Hash
                    try:
                        new_hash = generate_password_hash(password)
                        db.execute_query("UPDATE Login_Table SET Password = %s WHERE id = %s", (new_hash, user['id']), commit=True)
                        migrated = True
                    except Exception as e:
                        logging.error("Error migrating password for user")

            if verified:
                session['user_id'] = user['User_Code']
                session['user_pk'] = user['id']
                session['username'] = username
                if migrated:
                    flash('Login successful. Your password security has been upgraded.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('User not found.', 'danger')

        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('register'))

    # Check if critical migration table exists, if not, force install page
    # In production, use a more robust check (e.g. system_settings table)
    try:
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES LIKE 'migrations'")
            if not cursor.fetchone():
                return redirect(url_for('installing'))
    except Exception as e:
        logging.error(f"Error checking for migrations table: {e}")
    return render_template('index.html')

@app.route('/installing')
def installing():
    return render_template('installing.html')

@app.route('/install_stream')
def install_stream():
    def generate():
        yield f"data: {json.dumps({'message': 'Starting schema migration...', 'progress': 10})}\n\n"

        # We invoke run_schema_migrations logic step-by-step or call it and capture output
        # For simplicity, we assume run_schema_migrations is modified to yield or we check state.
        # But run_schema_migrations is synchronous. We can't yield from it easily without refactoring it into a generator.
        # Let's verify DB connection first.

        try:
            conn = db.get_connection()
            if not conn:
                yield f"data: {json.dumps({'message': 'Database connection failed!', 'status': 'error', 'progress': 100, 'done': True})}\n\n"
                return

            yield f"data: {json.dumps({'message': 'Database connected.', 'progress': 20})}\n\n"

            # Execute Migrations (Sync call, but fast enough for this demo or we refactor)
            # Actually, `run_schema_migrations` prints to console.
            # We will call it here.

            try:
                run_schema_migrations()
                yield f"data: {json.dumps({'message': 'Schema migrations applied successfully.', 'status': 'success', 'progress': 60})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'message': f'Migration Error: {str(e)}', 'status': 'error', 'progress': 100, 'done': True})}\n\n"
                return

            # Default User
            create_default_user()
            yield f"data: {json.dumps({'message': 'Default user checked/created.', 'progress': 80})}\n\n"

            # Default Accounts
            ensure_default_accounts()
            yield f"data: {json.dumps({'message': 'Default accounts verified.', 'progress': 90})}\n\n"

            yield f"data: {json.dumps({'message': 'Installation complete!', 'status': 'success', 'progress': 100, 'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'message': f'Critical Error: {str(e)}', 'status': 'error', 'progress': 100, 'done': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/placeholder')
@login_required
def placeholder():
    title = request.args.get('title', 'Feature')
    return render_template('placeholder.html', title=title)

# --- Add Customer (Existing) ---
@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        try:
            supplier_name = request.form.get('supplier_name')
            salutation = request.form.get('salutation')
            supplier_code = request.form.get('supplier_code')
            credit_limit = request.form.get('credit_limit', 0)
            vat_no = request.form.get('vat_no')

            address_no = request.form.get('address_no')
            address_line_1 = request.form.get('address_line_1')
            address_line_2 = request.form.get('address_line_2')
            address_line_3 = request.form.get('address_line_3')
            address_line_4 = request.form.get('address_line_4')

            contact_1 = request.form.get('contact_1')
            contact_2 = request.form.get('contact_2')
            email = request.form.get('email')

            if not supplier_name or not supplier_code:
                flash('Supplier Name and Code are required.', 'danger')
                return redirect(url_for('add_customer'))

            current_user = get_current_user_id()
            current_user_pk = get_current_user_pk()
            current_date = datetime.now().date()

            query_supplier = """
                INSERT INTO suppliers (
                    sup_id, supplier_name, supplier_code,
                    supplier_address_1, supplier_address_2, supplier_address_3, supplier_address_4,
                    suppliers_credit_fasility, suppliers_teli_1, suppliers_teli_2,
                    supplier_create_date, suppliers_create_user,
                    suppliers_last_edit_user, suppliers_last_edit_date,
                    suppliers_e_mail, suppliers_vat_regidter_no, suppliers_salution,
                    Is_Suplier, Is_Customer
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_supplier = (
                0, supplier_name, supplier_code,
                address_no, address_line_1, address_line_2, address_line_3,
                parse_float(credit_limit), contact_1, contact_2,
                current_date, current_user_pk,
                current_user_pk, current_date,
                email, vat_no, salutation,
                0, 1 # Is_Suplier=0, Is_Customer=1
            )

            query_sub_account = """
                INSERT INTO sub_accont_for_new_account (
                    id_sub, sub_sub_accaount_name, sub_new_account,
                    creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            try:
                with db.transaction_cursor() as cursor:
                    cursor.execute(query_supplier, params_supplier)
                    cursor.execute(query_sub_account, (
                        0, supplier_name, "Account Receivable",
                        current_user, current_date, 1, 0
                    ))
                    last_sub_id = cursor.lastrowid
                    new_sub_code = last_sub_id + 10001
                    cursor.execute(
                        "UPDATE sub_accont_for_new_account SET sub_account_code = %s WHERE id_sub = %s",
                        (new_sub_code, last_sub_id)
                    )
                flash('Customer added successfully!', 'success')
            except Exception as e:
                print(f"Transaction failed: {e}")
                logging.error(f"Transaction failed: {e}")
                flash(f'Error adding customer: {str(e)}', 'danger')

            return redirect(url_for('add_customer'))

        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return redirect(url_for('add_customer'))

    salutations = []
    try:
        salutations_data = db.execute_query("SELECT salutation FROM suplier_suporting_1")
        salutations = [row['salutation'] for row in salutations_data]
    except Exception as e:
        logging.error(f"Error loading salutations: {e}")
    return render_template('add_customer.html', salutations=salutations)

# --- Add Supplier (New) ---

@app.route('/api/extract_vat_from_pdf', methods=['POST'])
@login_required
def extract_vat_from_pdf():
    if 'document' not in request.files:
        return jsonify({'success': False, 'message': 'No document uploaded'}), 400

    file = request.files['document']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Only PDF files are supported'}), 400

    try:
        # Read PDF content
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "

        # "AI" Regex to find VAT Numbers
        # Matches common VAT formats (e.g., VAT NO: 123456789, VAT: GB123456789)
        vat_pattern = r'(?i)VAT\s*(?:NO|NUMBER|#)?\s*[:\-\s]?\s*([A-Z0-9]{8,15})'
        matches = re.findall(vat_pattern, text)

        if matches:
            # Return first distinct match
            vat_no = matches[0].strip()
            return jsonify({'success': True, 'vat_no': vat_no, 'message': 'VAT extracted successfully'})
        else:
            return jsonify({'success': False, 'message': 'No VAT number found in the document'})

    except Exception as e:
        app.logger.error(f"Error extracting VAT: {e}")
        return jsonify({'success': False, 'message': 'Failed to process document'}), 500


@app.route('/add_supplier', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        try:
            supplier_name = request.form.get('supplier_name')
            salutation = request.form.get('salutation')
            supplier_code = request.form.get('supplier_code')
            credit_limit = request.form.get('credit_limit', 0)
            vat_no = request.form.get('vat_no')

            address_no = request.form.get('address_no')
            address_line_1 = request.form.get('address_line_1')
            address_line_2 = request.form.get('address_line_2')
            address_line_3 = request.form.get('address_line_3')
            address_line_4 = request.form.get('address_line_4')

            contact_1 = request.form.get('contact_1')
            contact_2 = request.form.get('contact_2')
            email = request.form.get('email')

            tin = request.form.get('tin_no')
            nic = request.form.get('nic_no')

            if not supplier_name or not supplier_code:
                flash('Supplier Name and Code are required.', 'danger')
                return redirect(url_for('add_supplier'))

            current_user = get_current_user_id()
            current_user_pk = get_current_user_pk()
            current_date = datetime.now().date()

            query_supplier = """
                INSERT INTO suppliers (
                    sup_id, supplier_name, supplier_code,
                    supplier_address_1, supplier_address_2, supplier_address_3, supplier_address_4,
                    suppliers_credit_fasility, suppliers_teli_1, suppliers_teli_2,
                    supplier_create_date, suppliers_create_user,
                    suppliers_last_edit_user, suppliers_last_edit_date,
                    suppliers_e_mail, suppliers_vat_regidter_no, suppliers_salution,
                    Is_Suplier, Is_Customer, suppliers_TIN, suppliers_NIC
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params_supplier = (
                0, supplier_name, supplier_code,
                address_no, address_line_1, address_line_2, address_line_3,
                parse_float(credit_limit), contact_1, contact_2,
                current_date, current_user_pk,
                current_user_pk, current_date,
                email, vat_no, salutation,
                1, 0, tin, nic
            )

            query_sub_account = """
                INSERT INTO sub_accont_for_new_account (
                    id_sub, sub_sub_accaount_name, sub_new_account,
                    creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            try:
                with db.transaction_cursor() as cursor:
                    cursor.execute(query_supplier, params_supplier)
                    cursor.execute(query_sub_account, (
                        0, supplier_name, "Account Payable",
                        current_user, current_date, 1, 0
                    ))
                    last_sub_id = cursor.lastrowid
                    new_sub_code = last_sub_id + 10001
                    cursor.execute(
                        "UPDATE sub_accont_for_new_account SET sub_account_code = %s WHERE id_sub = %s",
                        (new_sub_code, last_sub_id)
                    )
                flash('Supplier added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding supplier: {str(e)}', 'danger')

            return redirect(url_for('add_supplier'))

        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return redirect(url_for('add_supplier'))

    salutations = []
    try:
        salutations_data = db.execute_query("SELECT salutation FROM suplier_suporting_1")
        salutations = [row['salutation'] for row in salutations_data]
    except Exception as e:
        logging.error(f"Error loading salutations: {e}")
    return render_template('add_supplier.html', salutations=salutations)

@app.route('/add_salutation', methods=['POST'])
@login_required
def add_salutation():
    new_salutation = request.form.get('new_salutation')
    if new_salutation:
        try:
            db.execute_query(
                "INSERT INTO suplier_suporting_1 (id, salutation) VALUES (%s, %s)",
                (0, new_salutation), commit=True
            )
            flash('Salutation added.', 'success')
        except Exception as e:
            flash(f'Error adding salutation: {e}', 'danger')
    return redirect(url_for('add_customer'))

@app.route('/add_salutation_ajax', methods=['POST'])
@login_required
def add_salutation_ajax():
    new_salutation = request.form.get('new_salutation')
    if new_salutation:
        try:
            db.execute_query(
                "INSERT INTO suplier_suporting_1 (id, salutation) VALUES (%s, %s)",
                (0, new_salutation), commit=True
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False}

# --- Inventory Category Management ---
@app.route('/inventory_category')
@login_required
@has_permission('Access_Inventory')
def inventory_category():
    main_cats = db.execute_query("SELECT * FROM inventory_carogory WHERE main_catogory IS NOT NULL AND main_catogory != ''")
    sub_cats = db.execute_query("SELECT * FROM inventory_carogory WHERE sub_catogory IS NOT NULL AND sub_catogory != ''")
    return render_template('inventory_category.html', main_categories=main_cats, sub_categories=sub_cats)

@app.route('/inventory_category/main', methods=['POST'])
@login_required
def add_main_category():
    name = request.form.get('main_category')
    if name:
        db.execute_query("INSERT INTO inventory_carogory (id, main_catogory, sub_catogory) VALUES (0, %s, NULL)", (name,), commit=True)
        flash('Main category added', 'success')
    return redirect(url_for('inventory_category'))

@app.route('/inventory_category/sub', methods=['POST'])
@login_required
def add_sub_category():
    name = request.form.get('sub_category')
    if name:
        db.execute_query("INSERT INTO inventory_carogory (id, main_catogory, sub_catogory) VALUES (0, NULL, %s)", (name,), commit=True)
        flash('Sub category added', 'success')
    return redirect(url_for('inventory_category'))

@app.route('/inventory_category/main/toggle', methods=['POST'])
@login_required
def toggle_main_category():
    cat_id = request.form.get('id')
    current = int(request.form.get('current_status'))
    new_status = 0 if current == 1 else 1
    db.execute_query("UPDATE inventory_carogory SET dis_continue_main = %s WHERE id = %s", (new_status, cat_id), commit=True)
    return redirect(url_for('inventory_category'))

@app.route('/inventory_category/sub/toggle', methods=['POST'])
@login_required
def toggle_sub_category():
    cat_id = request.form.get('id')
    current = int(request.form.get('current_status'))
    new_status = 0 if current == 1 else 1
    db.execute_query("UPDATE inventory_carogory SET dis_continue_sub = %s WHERE id = %s", (new_status, cat_id), commit=True)
    return redirect(url_for('inventory_category'))

# --- Add Inventory Item ---
@app.route('/add_inventory_item', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Inventory')
def add_inventory_item():
    if request.method == 'POST':
        try:
            import base64

            # 1. Extract Data
            name = request.form.get('item_name')
            code = request.form.get('item_code')
            supplier_code = request.form.get('supplier_code')
            batch_code = request.form.get('batch_code')
            unit = request.form.get('measurement_unit')
            main_cat = request.form.get('main_category')
            sub_cat = request.form.get('sub_category')
            min_qty = parse_float(request.form.get('min_qty', 0))
            selling_price = parse_float(request.form.get('selling_price', 0))
            cost_price = parse_float(request.form.get('cost_price', 0))

            # 2. Handle Image
            img_data = None
            if 'item_image' in request.files:
                file = request.files['item_image']
                if file.filename != '':
                    # C# code saves as JpegBitmapEncoder buffer (bytes)
                    # We store as LONGBLOB or MEDIUMBLOB.
                    # MySQL Connector handles bytes object directly for BLOBs.
                    # Wait, some tables expect base64 string because of C# legacy handling.
                    # Let's save as base64 string to avoid 'Invalid utf8mb4 character string' error
                    # when passing raw bytes to a query that expects text/string.
                    img_data = base64.b64encode(file.read()).decode('utf-8')

            if not name or not code or not unit:
                flash('Name, Code, and Unit are required.', 'danger')
                return redirect(url_for('add_inventory_item'))

            try:
                current_user = get_current_user_id()
                current_user_pk = get_current_user_pk()
                today_date = date.today()

                with db.transaction_cursor() as cursor:
                    # 3. Insert Item
                    query_item = """
                        INSERT INTO inventoy_items (
                            id, inventoy_name, inventoy_code, inventoy_suplier_code, inventoy_bach_code,
                            inventoy_img, inventoy_creat_user_id, inventoy_items_creat_date,
                            inventoy_items_messurment_unit, Main_Catogry, Sub_Catogory, min_qty, active
                        ) VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """
                    cursor.execute(query_item, (
                        name, code, supplier_code, batch_code, img_data,
                        current_user_pk, today_date, unit, main_cat, sub_cat, min_qty
                    ))
                    item_id = cursor.lastrowid

                    # 4. Insert Price
                    query_price = """
                        INSERT INTO inventory_price_recod (
                            id, inventory_price_link, inventory_price_selling, inventory_price_purcharsing, created_date
                        ) VALUES (0, %s, %s, %s, %s)
                    """
                    cursor.execute(query_price, (item_id, selling_price, cost_price, today_date))

                flash('Inventory Item created successfully!', 'success')

            except Exception as e:
                flash(f'Database Error: {str(e)}', 'danger')

        except Exception as e:
            flash(f'System Error: {str(e)}', 'danger')

        return redirect(url_for('add_inventory_item'))

    # GET Request
    main_cats = db.execute_query("SELECT main_catogory FROM inventory_carogory WHERE main_catogory IS NOT NULL AND main_catogory != '' AND dis_continue_main = 0")
    sub_cats = db.execute_query("SELECT sub_catogory FROM inventory_carogory WHERE sub_catogory IS NOT NULL AND sub_catogory != '' AND dis_continue_sub = 0")

    return render_template('add_inventory_item.html', main_categories=main_cats, sub_categories=sub_cats)

# --- GRN (Goods Received Note) Management ---
@app.route('/grn', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Inventory')
def grn():
    if request.method == 'POST':
        try:
            # 1. Extract Data
            supplier_name = request.form.get('supplier')
            items_json = request.form.get('items_json')
            invoice_no = request.form.get('invoice_no')
            invoice_date = request.form.get('invoice_date')
            due_date = request.form.get('due_date')
            narration = request.form.get('narration')
            job_no = request.form.get('job_no')
            location = request.form.get('location')

            total_value = parse_float(request.form.get('total_value', 0))
            vat_rate = parse_float(request.form.get('vat_rate', 0))
            vat_amount = parse_float(request.form.get('vat_amount', 0))
            grand_total = parse_float(request.form.get('grand_total', 0))

            items = json.loads(items_json) if items_json else []

            if not items:
                flash('No items in GRN', 'warning')
                return redirect(url_for('grn'))

            # 2. Get Supplier Details
            sup_res = db.execute_query("SELECT supplier_code, sup_id FROM suppliers WHERE supplier_name = %s", (supplier_name,))
            if not sup_res:
                flash('Invalid Supplier', 'danger')
                return redirect(url_for('grn'))
            supplier_code = sup_res[0]['supplier_code']
            supplier_id = sup_res[0]['sup_id']

            # 3. Create Transaction using Service Layer
            try:
                current_user = get_current_user_id()
                supplier_info = {'code': supplier_code, 'id': supplier_id}
                invoice_info = {
                    'no': invoice_no,
                    'date': invoice_date,
                    'due_date': due_date,
                    'narration': narration,
                    'job_no': job_no,
                    'location': location,
                    'total_value': total_value,
                    'vat_rate': vat_rate,
                    'vat_amount': vat_amount,
                    'grand_total': grand_total
                }

                jv_no = services.create_grn(db, current_user, supplier_info, invoice_info, items)

                current_user_pk = get_current_user_pk()
                flash(f'GRN created successfully. JV No: {jv_no}', 'success')
                return render_template('grn_print.html', grn_no=jv_no, supplier=supplier_name, date=invoice_date, invoice_no=invoice_no, location=location, items=items, total_value=total_value, vat_amount=vat_amount, grand_total=grand_total)

            except Exception as e:
                flash(f'Transaction failed: {str(e)}', 'danger')
                return redirect(url_for('grn'))

        except Exception as e:
            flash(f'Error processing GRN: {str(e)}', 'danger')
            return redirect(url_for('grn'))

    # GET Request: Load Form Data
    suppliers = db.execute_query("SELECT supplier_name FROM suppliers")
    items = db.execute_query("SELECT inventoy_name, inventoy_code, inventoy_items_messurment_unit FROM inventoy_items")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit")
    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")

    return render_template('grn.html',
                           suppliers=suppliers,
                           items=items,
                           jobs=jobs,
                           locations=locations,
                           today_date=date.today().strftime('%Y-%m-%d'))

# --- Inventory Locations ---
@app.route('/inventory_locations', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Inventory')
def inventory_locations():
    if request.method == 'POST':
        name = request.form.get('house_name')
        desc = request.form.get('description')
        if name:
            db.execute_query("INSERT INTO inventory_locations (id, inventory_locations_name, inventory_locations_descriptions) VALUES (0, %s, %s)", (name, desc), commit=True)
            flash('Inventory location added', 'success')
        return redirect(url_for('inventory_locations'))

    locations = db.execute_query("SELECT * FROM inventory_locations")
    return render_template('inventory_locations.html', locations=locations)

# --- Cash Flow Categories ---
@app.route('/cash_flow_categories', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def cash_flow_categories():
    if request.method == 'POST':
        category_id = int(request.form.get('category_id', 0))
        name = request.form.get('category_name')
        level = request.form.get('hold_level')

        if not name:
            flash('Category Name is required', 'danger')
            return redirect(url_for('cash_flow_categories'))

        try:
            if category_id == 0:
                # Insert
                db.execute_query("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", (name, level), commit=True)
                clear_category_cache()
                flash('Category added successfully', 'success')
            else:
                # Update
                db.execute_query("UPDATE cf_catogory SET catogory_name = %s, hold_level = %s WHERE id = %s", (name, level, category_id), commit=True)
                clear_category_cache()
                flash('Category updated successfully', 'success')
        except Exception as e:
            flash(f'Error saving category: {str(e)}', 'danger')

        return redirect(url_for('cash_flow_categories'))

    cats = db.execute_query("SELECT * FROM cf_catogory ORDER BY hold_level, catogory_name")
    return render_template('cash_flow_categories.html', categories=cats)

@app.route('/cash_flow_categories/delete', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def delete_cash_flow_category():
    # Support both single deletion (from old form) and bulk (from new form)
    selected_ids = request.form.getlist('selected_ids')
    single_id = request.form.get('id')

    try:
        if selected_ids:
            placeholders = ', '.join(['%s'] * len(selected_ids))
            query = f"DELETE FROM cf_catogory WHERE id IN ({placeholders})"
            db.execute_query(query, tuple(selected_ids), commit=True)
            clear_category_cache()
            flash(f'{len(selected_ids)} categories deleted', 'success')
        elif single_id:
            db.execute_query("DELETE FROM cf_catogory WHERE id = %s", (single_id,), commit=True)
            clear_category_cache()
            flash('Category deleted', 'success')
        else:
            flash('No items selected', 'info')
    except Exception as e:
        flash(f'Error deleting categories: {str(e)}', 'danger')

    return redirect(url_for('cash_flow_categories'))

# --- Chart of Accounts ---
@app.route('/chart_of_accounts')
@login_required
@has_permission('Access_Accounting')
def chart_of_accounts():
    accounts = db.execute_query("SELECT * FROM new_account_table WHERE account_active = 1")
    pl_count = 0
    bs_count = 0
    for a in accounts:
        if a['account_name_of_catogory_PL']:
            pl_count += 1
        if a['account_name_of_catogory_Balace_sheet']:
            bs_count += 1
    return render_template('chart_of_accounts.html', accounts=accounts, total_accounts=len(accounts), pl_count=pl_count, bs_count=bs_count)

# --- Add New Account ---
@app.route('/add_new_account', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def add_new_account():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_account':
            account_name = request.form.get('account_name')
            currency_code = request.form.get('currency_code', 'LKR') # Default LKR

            if not account_name:
                flash('Please enter an account name', 'danger')
                return redirect(url_for('add_new_account'))

            # Process categories
            bs_cat_val = request.form.get('bs_category')
            pl_cat_val = request.form.get('income_category')
            cf_cat = request.form.get('cf_category')

            if (not bs_cat_val or bs_cat_val == "") and (not pl_cat_val or pl_cat_val == ""):
                flash('Please select a category', 'danger')
                return redirect(url_for('add_new_account'))

            if not cf_cat:
                flash('Please select a cash flow category', 'danger')
                return redirect(url_for('add_new_account'))

            bs_name = None
            bs_pos = None
            if bs_cat_val:
                bs_name, bs_pos = bs_cat_val.split(',')

            pl_name = None
            pl_pos = None
            if pl_cat_val:
                pl_name, pl_pos = pl_cat_val.split(',')

            # Account Types
            is_income = 1 if 'income' in request.form.getlist('account_type') else 0
            is_expense = 1 if 'expense' in request.form.getlist('account_type') else 0
            is_liability = 1 if 'liability' in request.form.getlist('account_type') else 0
            is_equity = 1 if 'equity' in request.form.getlist('account_type') else 0
            is_asset = 1 if 'asset' in request.form.getlist('account_type') else 0

            current_user = get_current_user_id()

            query = """
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_PL, account_hold_possion_Balace_Sheet,
                    account_name_of_catogory_PL, account_name_of_catogory_Balace_sheet,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    cf_catogory, accont_create_date, account_create_user, account_active, account_basment,
                    currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, '', %s)
            """
            params = (
                account_name, pl_pos, bs_pos, pl_name, bs_name,
                is_income, is_expense, is_asset, is_liability, is_equity,
                cf_cat, date.today(), current_user, currency_code
            )

            try:
                db.execute_query(query, params, commit=True)
                flash('New account created successfully', 'success')
            except Exception as e:
                flash(f'Error creating account: {str(e)}', 'danger')

        elif action == 'add_sub_account':
            sub_name = request.form.get('sub_account_name')
            main_account = request.form.get('main_account_select')

            if not sub_name or not main_account:
                flash('Sub account name and main account are required', 'danger')
                return redirect(url_for('add_new_account'))

            current_user = get_current_user_id()

            query = """
                INSERT INTO sub_accont_for_new_account (
                    sub_sub_accaount_name, sub_new_account, creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, 1, 0)
            """
            try:
                db.execute_query(query, (sub_name, main_account, current_user, date.today()), commit=True)
                flash('Sub account created successfully', 'success')
            except Exception as e:
                flash(f'Error creating sub account: {str(e)}', 'danger')

        return redirect(url_for('add_new_account'))

    # Load Data for Dropdowns
    bs_cats, pl_cats, cf_cats = get_cached_categories(db)
    existing_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_active = 1")
    currencies = db.execute_query("SELECT currency_code, currency_name FROM currency_table")
    if not currencies: # Fallback if table empty
        currencies = [{'currency_code': 'LKR', 'currency_name': 'Sri Lankan Rupee'}]

    return render_template('add_new_account.html',
                           bs_categories=bs_cats,
                           pl_categories=pl_cats,
                           cf_categories=cf_cats,
                           existing_accounts=existing_accounts,
                           currencies=currencies)

# --- Balance Sheet Category Management ---
@app.route('/balance_sheet_category', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def balance_sheet_category():
    if request.method == 'POST':
        category_id = int(request.form.get('category_id', 0))
        name = request.form.get('category_name')
        level = request.form.get('holding_level')

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()
        current_date = date.today()

        if not name or not level:
            flash('Name and Level are required', 'danger')
            return redirect(url_for('balance_sheet_category'))

        try:
            if category_id == 0:
                # Insert
                query = """
                    INSERT INTO balance_sheet_category
                    (id, name_of_category, holding_position, create_date_time, create_user_code)
                    VALUES (0, %s, %s, %s, %s)
                """
                db.execute_query(query, (name, level, current_date, current_user_pk), commit=True)
                clear_category_cache()
                flash('Category created successfully', 'success')
            else:
                # Update
                query = """
                    UPDATE balance_sheet_category
                    SET name_of_category = %s, holding_position = %s,
                        create_date_time = %s, create_user_code = %s
                    WHERE id = %s
                """
                db.execute_query(query, (name, level, current_date, current_user_pk, category_id), commit=True)
                clear_category_cache()
                flash('Category updated successfully', 'success')

        except Exception as e:
            flash(f'Error saving category: {str(e)}', 'danger')

        return redirect(url_for('balance_sheet_category'))

    # GET
    categories = db.execute_query("SELECT * FROM balance_sheet_category ORDER BY holding_position")
    return render_template('balance_sheet_category.html', categories=categories)

@app.route('/balance_sheet_category/delete', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def delete_balance_sheet_category():
    selected_ids = request.form.getlist('selected_ids')
    if selected_ids:
        try:
            placeholders = ', '.join(['%s'] * len(selected_ids))
            query = f"DELETE FROM balance_sheet_category WHERE id IN ({placeholders})"
            db.execute_query(query, tuple(selected_ids), commit=True)
            clear_category_cache()
            flash(f'{len(selected_ids)} categories deleted', 'success')
        except Exception as e:
            flash(f'Error deleting categories: {str(e)}', 'danger')
    else:
        flash('No items selected', 'info')

    return redirect(url_for('balance_sheet_category'))

# --- Create Bank Account ---
@app.route('/pl_category', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def pl_category():
    if request.method == 'POST':
        category_id = int(request.form.get('category_id', 0))
        name = request.form.get('category_name')
        level = request.form.get('holding_level')

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()
        current_date = date.today()

        if not name or not level:
            flash('Name and Level are required', 'danger')
            return redirect(url_for('pl_category'))

        try:
            if category_id == 0:
                # Insert
                query = """
                    INSERT INTO `p&l_category`
                    (id, name_of_category, holding_position, create_date_time, create_user_code)
                    VALUES (0, %s, %s, %s, %s)
                """
                db.execute_query(query, (name, level, current_date, current_user_pk), commit=True)
                clear_category_cache()
                flash('P&L Category created successfully', 'success')
            else:
                # Update
                query = """
                    UPDATE `p&l_category`
                    SET name_of_category = %s, holding_position = %s,
                        create_date_time = %s, create_user_code = %s
                    WHERE id = %s
                """
                db.execute_query(query, (name, level, current_date, current_user_pk, category_id), commit=True)
                clear_category_cache()
                flash('P&L Category updated successfully', 'success')

        except Exception as e:
            flash(f'Error saving category: {str(e)}', 'danger')

        return redirect(url_for('pl_category'))

    # GET
    categories = db.execute_query("SELECT * FROM `p&l_category` ORDER BY holding_position")
    return render_template('pl_category.html', categories=categories)

@app.route('/pl_category/delete', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def delete_pl_category():
    selected_ids = request.form.getlist('selected_ids')
    if selected_ids:
        try:
            placeholders = ', '.join(['%s'] * len(selected_ids))
            query = f"DELETE FROM `p&l_category` WHERE id IN ({placeholders})"
            db.execute_query(query, tuple(selected_ids), commit=True)
            clear_category_cache()
            flash(f'{len(selected_ids)} categories deleted', 'success')
        except Exception as e:
            flash(f'Error deleting categories: {str(e)}', 'danger')
    else:
        flash('No items selected', 'info')

    return redirect(url_for('pl_category'))

@app.route('/pl_category_correction', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def pl_category_correction():
    if request.method == 'POST':
        account_ids = request.form.getlist('account_id[]')
        selections = request.form.getlist('category_selection[]')

        updates = []
        for i in range(len(account_ids)):
            if i < len(selections) and selections[i]:
                cat_name, hold_pos = selections[i].split(',')
                updates.append((cat_name, hold_pos, account_ids[i]))

        if updates:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                conn.start_transaction()

                query = "UPDATE new_account_table SET account_name_of_catogory_PL = %s, account_hold_possion_PL = %s WHERE id = %s"
                cursor.executemany(query, updates)

                conn.commit()
                flash(f'Updated {len(updates)} accounts successfully', 'success')
            except Exception as e:
                flash(f'Error updating accounts: {str(e)}', 'danger')

        return redirect(url_for('pl_category_correction'))

    # GET: Fetch unassigned P&L accounts (Logic from wpf_catigiry_corections)
    # The C# code fetches accounts where (Income=1 OR Expense=1) AND Category IS NULL
    query_acc = """
        SELECT id, account_name, account_name_of_catogory_PL
        FROM new_account_table
        WHERE (account_income = 1 OR account_expenses = 1)
        AND (account_name_of_catogory_PL IS NULL OR account_name_of_catogory_PL = '')
    """
    accounts = db.execute_query(query_acc)

    # Fetch Categories
    query_cat = "SELECT name_of_category, holding_position FROM `p&l_category` ORDER BY holding_position"
    categories = db.execute_query(query_cat)

    return render_template('pl_category_correction.html', accounts=accounts, categories=categories)

@app.route('/bs_category_correction', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def bs_category_correction():
    if request.method == 'POST':
        account_ids = request.form.getlist('account_id[]')
        selections = request.form.getlist('category_selection[]')

        updates = []
        for i in range(len(account_ids)):
            if i < len(selections) and selections[i]:
                cat_name, hold_pos = selections[i].split(',')
                updates.append((cat_name, hold_pos, account_ids[i]))

        if updates:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                conn.start_transaction()

                query = "UPDATE new_account_table SET account_name_of_catogory_Balace_sheet = %s, account_hold_possion_Balace_Sheet = %s WHERE id = %s"
                cursor.executemany(query, updates)

                conn.commit()
                flash(f'Updated {len(updates)} accounts successfully', 'success')
            except Exception as e:
                flash(f'Error updating accounts: {str(e)}', 'danger')

        return redirect(url_for('bs_category_correction'))

    # GET: Fetch unassigned BS accounts (Logic from wpf_bs_catogory_corections)
    query_acc = """
        SELECT id, account_name, account_name_of_catogory_Balace_sheet
        FROM new_account_table
        WHERE (account_assets = 1 OR account_liabilities = 1 OR account_equity = 1)
        AND (account_name_of_catogory_Balace_sheet IS NULL OR account_name_of_catogory_Balace_sheet = '')
    """
    accounts = db.execute_query(query_acc)

    # Fetch Categories
    query_cat = "SELECT name_of_category, holding_position FROM balance_sheet_category ORDER BY holding_position"
    categories = db.execute_query(query_cat)

    return render_template('bs_category_correction.html', accounts=accounts, categories=categories)

@app.route('/create_bank_account', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def create_bank_account():
    if request.method == 'POST':
        acc_no = request.form.get('account_number')
        bank_name = request.form.get('bank_name')

        if not acc_no or not bank_name:
            flash('Account number and Bank Name are required', 'danger')
            return redirect(url_for('create_bank_account'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()
        today_date = date.today()

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            conn.start_transaction()

            # 1. Check/Create GL Account (Using Account Number as Name)
            cursor.execute("SELECT id FROM new_account_table WHERE account_name = %s", (acc_no,))
            if not cursor.fetchone():
                # Find 'Current assets' or 'Cash & Bank'
                cursor.execute("SELECT holding_position, name_of_category FROM balance_sheet_category WHERE name_of_category LIKE '%Bank%' OR name_of_category LIKE '%Cash%' LIMIT 1")
                res = cursor.fetchone()

                if res:
                    bs_pos = res[0]
                    bs_cat_name = res[1]
                else:
                    # Fallback to the first available category if no match
                    cursor.execute("SELECT holding_position, name_of_category FROM balance_sheet_category LIMIT 1")
                    fallback_res = cursor.fetchone()
                    if fallback_res:
                        bs_pos = fallback_res[0]
                        bs_cat_name = fallback_res[1]
                    else:
                        # Extreme fallback: Create 'Current assets' if table is empty
                        bs_pos = 3
                        bs_cat_name = 'Current assets'
                        cursor.execute("INSERT IGNORE INTO balance_sheet_category (name_of_category, holding_position) VALUES (%s, %s)", (bs_cat_name, bs_pos))

                cursor.execute("""
                    INSERT INTO new_account_table (
                        account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                        account_assets, account_basment, accont_create_date, account_create_user, account_active,
                        currency_code
                    ) VALUES (%s, %s, %s, 1, 'DR', %s, %s, 1, 'LKR')
                """, (acc_no, bs_pos, bs_cat_name, today_date, current_user))

            # 2. Insert into Bank Book
            cursor.execute("""
                INSERT INTO bank_book (bank_bookcol_account_number, bank_book_bank_name, bank_book_create_date, bank_book_create_user)
                VALUES (%s, %s, %s, %s)
            """, (acc_no, bank_name, today_date, current_user_pk))

            conn.commit()
            flash('New bank account created', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error creating bank account: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('create_bank_account'))

    return render_template('create_bank_account.html')

# --- Create Cash Account ---
@app.route('/create_cash_account', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def create_cash_account():
    if request.method == 'POST':
        acc_name = request.form.get('account_name')

        if not acc_name:
            flash('Account name is required', 'danger')
            return redirect(url_for('create_cash_account'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()
        today_date = date.today()

        conn = db.get_connection()
        cursor = conn.cursor()

        try:
            conn.start_transaction()

            # 1. Check if GL Account exists
            cursor.execute("SELECT id FROM new_account_table WHERE account_name = %s", (acc_name,))
            if not cursor.fetchone():
                # Create GL Account (Current Asset)
                # Need to find 'Current assets' category position
                cursor.execute("SELECT holding_position, name_of_category FROM balance_sheet_category WHERE name_of_category LIKE '%Current asset%' LIMIT 1")
                res = cursor.fetchone()

                if res:
                    bs_pos = res[0]
                    bs_cat_name = res[1]
                else:
                    # Fallback to the first available category if no match
                    cursor.execute("SELECT holding_position, name_of_category FROM balance_sheet_category LIMIT 1")
                    fallback_res = cursor.fetchone()
                    if fallback_res:
                        bs_pos = fallback_res[0]
                        bs_cat_name = fallback_res[1]
                    else:
                        # Extreme fallback: Create 'Current assets' if table is empty
                        bs_pos = 3
                        bs_cat_name = 'Current assets'
                        cursor.execute("INSERT IGNORE INTO balance_sheet_category (name_of_category, holding_position) VALUES (%s, %s)", (bs_cat_name, bs_pos))

                cursor.execute("""
                    INSERT INTO new_account_table (
                        account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                        account_assets, account_basment, accont_create_date, account_create_user, account_active,
                        currency_code
                    ) VALUES (%s, %s, %s, 1, 'DR', %s, %s, 1, 'LKR')
                """, (acc_name, bs_pos, bs_cat_name, today_date, current_user))

            # 2. Insert into Cash Book
            # cash_book schema: cash_id, cash_book_account_name, cash_creat_date, cash_created_user, Select_As
            cursor.execute("""
                INSERT INTO cash_book (cash_book_account_name, cash_creat_date, cash_created_user, Select_As)
                VALUES (%s, %s, %s, 0)
            """, (acc_name, today_date, current_user_pk))

            conn.commit()
            flash('New cash account created', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error creating cash account: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('create_cash_account'))

    return render_template('create_cash_account.html')

# --- Control Panel (P&L Correction + Settings) ---
@app.route('/control_panel', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def control_panel():
    # 1. Handle Settings (Warranty & Approval)
    if request.method == 'POST':
        # Warranty & Settings
        if 'warranty_enabled' in request.form or 'approval_enabled' in request.form or 'system_theme' in request.form:
            # Warranty Logic
            warranty_enabled = 1 if request.form.get('warranty_enabled') else 0
            count_res = db.execute_query("SELECT COUNT(*) as cnt FROM adding_new")
            if count_res and count_res[0]['cnt'] == 0:
                db.execute_query("INSERT INTO adding_new (id, yes) VALUES (0, %s)", (warranty_enabled,), commit=True)
            else:
                db.execute_query("UPDATE adding_new SET yes = %s", (warranty_enabled,), commit=True)

            # Approval Workflow Logic
            approval_enabled = 1 if request.form.get('approval_enabled') else 0
            # Check if setting exists
            check = db.execute_query("SELECT id FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
            if not check:
                db.execute_query("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('enable_approval_workflow', %s, 'Enable Park & Post Workflow')", (str(approval_enabled),), commit=True)
            else:
                db.execute_query("UPDATE system_settings SET setting_value = %s WHERE setting_key = 'enable_approval_workflow'", (str(approval_enabled),), commit=True)

            # Theme Logic
            new_theme = request.form.get('system_theme')
            if new_theme and new_theme in THEMES:
                check_theme = db.execute_query("SELECT id FROM system_settings WHERE setting_key = 'system_theme'")
                if not check_theme:
                    db.execute_query("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('system_theme', %s, 'Active System Theme')", (new_theme,), commit=True)
                else:
                    db.execute_query("UPDATE system_settings SET setting_value = %s WHERE setting_key = 'system_theme'", (new_theme,), commit=True)

            flash('Settings updated', 'success')
            return redirect(url_for('control_panel'))

    # 2. Fetch Status
    res = db.execute_query("SELECT yes FROM adding_new")
    warranty_enabled = False
    if res and res[0]['yes'] == 1:
        warranty_enabled = True

    res_app = db.execute_query("SELECT setting_value FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
    approval_enabled = False
    if res_app and res_app[0]['setting_value'] == '1':
        approval_enabled = True

    res_theme = db.execute_query("SELECT setting_value FROM system_settings WHERE setting_key = 'system_theme'")
    current_theme_key = res_theme[0]['setting_value'] if res_theme else 'default'

    # 3. Fetch Unassigned P&L Accounts (Income or Expense but no P&L Category)
    unassigned_pl = db.execute_query("""
        SELECT id, account_name
        FROM new_account_table
        WHERE (account_income = 1 OR account_expenses = 1)
        AND (account_name_of_catogory_PL IS NULL OR account_name_of_catogory_PL = '')
    """)

    # 4. Fetch Unassigned Balance Sheet Accounts
    unassigned_bs = db.execute_query("""
        SELECT id, account_name
        FROM new_account_table
        WHERE (account_assets = 1 OR account_liabilities = 1 OR account_equity = 1)
        AND (account_name_of_catogory_Balace_sheet IS NULL OR account_name_of_catogory_Balace_sheet = '')
    """)

    # 5. Fetch Categories for Dropdown
    bs_cats, pl_cats, _ = get_cached_categories(db)

    return render_template('control_panel.html',
                           warranty_enabled=warranty_enabled,
                           approval_enabled=approval_enabled,
                           current_theme_key=current_theme_key,
                           themes=THEMES,
                           unassigned_pl=unassigned_pl,
                           unassigned_bs=unassigned_bs,
                           pl_categories=pl_cats,
                           bs_categories=bs_cats)

@app.route('/control_panel/update', methods=['POST'])
@login_required
def control_panel_update():
    update_type = request.form.get('update_type')
    updates = []

    # Identify fields based on update type
    if update_type == 'pl':
        prefix = 'category_'
        sql = "UPDATE new_account_table SET account_name_of_catogory_PL = %s, account_hold_possion_PL = %s WHERE id = %s"
    elif update_type == 'bs':
        prefix = 'bscategory_'
        sql = "UPDATE new_account_table SET account_name_of_catogory_Balace_sheet = %s, account_hold_possion_Balace_Sheet = %s WHERE id = %s"
    else:
        flash('Invalid update type', 'danger')
        return redirect(url_for('control_panel'))

    for key, value in request.form.items():
        if key.startswith(prefix) and value:
            acc_id = key.split('_')[1]
            cat_name, hold_pos = value.split(',')
            updates.append((cat_name, hold_pos, acc_id))

    if updates:
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            cursor.executemany(sql, updates)

            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Updated {len(updates)} accounts.', 'success')
        except Exception as e:
            flash(f'Error updating accounts: {str(e)}', 'danger')
    else:
        flash('No changes selected.', 'info')

    return redirect(url_for('control_panel'))

# --- Approvals Dashboard ---
@app.route('/approvals', methods=['GET'])
@login_required
@has_permission('OP_Approved') # Assuming this permission covers all approvals for now
def approvals():
    # 1. Pending Purchase Orders (Status = 0)
    pending_pos = db.execute_query("""
        SELECT id, OP_NO_Other as ref_no, Create_Date as date, Sup_Name as party,
               'Purchase Order' as type,
               (SELECT SUM(QTY*Unit_price) FROM PO_Recode_Details WHERE Link_OP_NO_Table=OP_NO_Table.id) as amount
        FROM OP_NO_Table
        WHERE status = 0 AND Delete_PO = 0
    """)

    # 2. Pending JVs (Manual, Payments, Receipts) (Status = 0)
    pending_jvs = db.execute_query("""
        SELECT j.jv_id as id, j.jv_user_code as ref_no, e.entry_effective_date as date,
               'Journal Voucher' as type, j.jv_naration as narration,
               SUM(e.enty_values_DR) as amount
        FROM jv_numbers j
        LEFT JOIN entry_details e ON j.jv_id = e.entry_jv
        WHERE j.status = 0
        GROUP BY j.jv_id, j.jv_user_code, e.entry_effective_date, j.jv_naration
    """)

    # Combine lists
    items = []
    for po in pending_pos:
        items.append({
            'id': po['id'],
            'ref_no': po['ref_no'],
            'date': str(po['date']),
            'party': po['party'],
            'type': 'Purchase Order',
            'amount': float(po['amount'] or 0),
            'source': 'po'
        })

    for jv in pending_jvs:
        items.append({
            'id': jv['id'],
            'ref_no': f"JV-{jv['id']}", # JV User Code might be user ID, using ID for ref
            'date': str(jv['date']),
            'party': jv['narration'], # Use narration as description/party
            'type': 'Journal/Payment',
            'amount': float(jv['amount'] or 0),
            'source': 'jv'
        })

    return render_template('approvals.html', items=items)

@app.route('/approvals/action', methods=['POST'])
@login_required
@has_permission('OP_Approved')
def approval_action():
    item_id = request.form.get('id')
    source = request.form.get('source')
    action = request.form.get('action') # 'approve' or 'reject'

    current_user = get_current_user_id()
    current_user_pk = get_current_user_pk()
    new_status = 1 if action == 'approve' else 2

    try:
        if source == 'po':
            db.execute_query("UPDATE OP_NO_Table SET status = %s, Aprove_By = %s, Aproed_Date = %s WHERE id = %s",
                             (new_status, current_user_pk, date.today(), item_id), commit=True)

        elif source == 'jv':
            db.execute_query("UPDATE jv_numbers SET status = %s WHERE jv_id = %s",
                             (new_status, item_id), commit=True)

        flash(f'Item {action}d successfully', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('approvals'))

# --- Bulk Upload Helpers ---
def read_csv_content(file_storage):
    """
    Reads a FileStorage object (CSV), attempts various encodings,
    and returns the decoded string content.
    """
    if not file_storage or file_storage.filename == '':
        raise ValueError("No file provided")

    try:
        file_bytes = file_storage.stream.read()
        decoded_str = None

        # prioritized list of encodings
        encodings = ['utf-8-sig', 'utf-16', 'utf-8', 'cp1252', 'latin1']

        for encoding in encodings:
            try:
                decoded_str = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded_str is None:
            raise ValueError(f"Unable to determine file encoding (tried {', '.join(encodings)})")

        return decoded_str

    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def parse_gl_upload_data(file_storage):
    """
    Parses the GL Upload CSV file and returns a list of dictionaries representing the rows.
    """
    try:
        csv_content = read_csv_content(file_storage)
        stream = io.StringIO(csv_content, newline=None)
        csv_input = csv.DictReader(stream)

        rows = []
        for row in csv_input:
            # Clean keys/values
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            if not clean_row.get('Account Name'): continue
            rows.append(clean_row)

        return rows
    except Exception as e:
        raise ValueError(f"Error parsing CSV data: {str(e)}")

def _parse_gl_category(cat_val):
    cat_name = None
    cat_pos = None
    is_bs = False
    is_pl = False

    if cat_val:
        parts = cat_val.split('|')
        if len(parts) == 2:
            cat_data, cat_type = parts
            cat_name, cat_pos = cat_data.split(',')
            if cat_type == 'BS': is_bs = True
            elif cat_type == 'PL': is_pl = True

    return cat_name, cat_pos, is_bs, is_pl

def _process_bulk_gl_subledgers(cursor, potential_banks, potential_cash, today, current_user):
    # Batch Sub-Ledger (Bank)
    if potential_banks:
        format_strings = ','.join(['%s'] * len(potential_banks))
        cursor.execute(f"SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number IN ({format_strings})", tuple(potential_banks))
        existing_banks = {row[0] for row in cursor.fetchall()}

        banks_to_insert = []
        for b_name in potential_banks:
            if b_name not in existing_banks:
                banks_to_insert.append((b_name, b_name, today, current_user))

        if banks_to_insert:
            cursor.executemany("""
                INSERT INTO bank_book (bank_bookcol_account_number, bank_book_bank_name, bank_book_create_date, bank_book_create_user)
                VALUES (%s, %s, %s, %s)
            """, banks_to_insert)

    # Batch Sub-Ledger (Cash)
    if potential_cash:
        format_strings = ','.join(['%s'] * len(potential_cash))
        cursor.execute(f"SELECT cash_book_account_name FROM cash_book WHERE cash_book_account_name IN ({format_strings})", tuple(potential_cash))
        existing_cash = {row[0] for row in cursor.fetchall()}

        cash_to_insert = []
        for c_name in potential_cash:
            if c_name not in existing_cash:
                cash_to_insert.append((c_name, today, current_user))

        if cash_to_insert:
            cursor.executemany("""
                INSERT INTO cash_book (cash_book_account_name, cash_creat_date, cash_created_user, Select_As)
                VALUES (%s, %s, %s, 0)
            """, cash_to_insert)

def save_bulk_gl_accounts(form_data, current_user):
    """
    Handles the database insertion logic for bulk GL account upload.
    Returns the count of successfully processed accounts.
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    conn.start_transaction()

    try:
        today = date.today()

        names = form_data.getlist('account_name[]')
        types = form_data.getlist('account_type[]')
        cats = form_data.getlist('category[]')
        cfs = form_data.getlist('cf_category[]')
        actions = form_data.getlist('action[]')

        # Filter valid names to check
        valid_names = [n for i, n in enumerate(names) if actions[i] != 'skip' and n]

        # Batch Fetch Existing Accounts
        existing_map = {}
        if valid_names:
            format_strings = ','.join(['%s'] * len(valid_names))
            cursor.execute(f"SELECT id, account_name FROM new_account_table WHERE account_name IN ({format_strings})", tuple(valid_names))
            existing_rows = cursor.fetchall()
            for row in existing_rows:
                existing_map[row[1]] = row[0] # Name -> ID

        to_update = []
        to_insert = []

        # For Sub-Ledgers
        potential_banks = []
        potential_cash = []

        count = 0
        for i in range(len(names)):
            if actions[i] == 'skip': continue

            name = names[i]
            acc_type = types[i]
            cat_val = cats[i]
            cf = cfs[i]

            # Parse Category
            cat_name, cat_pos, is_bs, is_pl = _parse_gl_category(cat_val)

            is_inc = 1 if acc_type == 'Income' else 0
            is_exp = 1 if acc_type == 'Expense' else 0
            is_ast = 1 if acc_type == 'Asset' else 0
            is_lia = 1 if acc_type == 'Liability' else 0
            is_equ = 1 if acc_type == 'Equity' else 0

            basement = 'DR' if is_ast or is_exp else 'CR'

            if name in existing_map:
                # Prepare Update
                to_update.append((
                    cat_pos if is_pl else None, cat_pos if is_bs else None,
                    cat_name if is_pl else None, cat_name if is_bs else None,
                    is_inc, is_exp, is_ast, is_lia, is_equ,
                    cf, basement, existing_map[name]
                ))
            else:
                # Prepare Insert
                to_insert.append((
                    name, cat_pos if is_pl else None, cat_pos if is_bs else None,
                    cat_name if is_pl else None, cat_name if is_bs else None,
                    is_inc, is_exp, is_ast, is_lia, is_equ,
                    cf, today, current_user, basement
                ))

                # Collect for Sub-Ledger check
                if is_ast:
                    acc_name_lower = name.lower()
                    if 'bank' in acc_name_lower:
                        potential_banks.append(name)
                    elif 'cash' in acc_name_lower:
                        potential_cash.append(name)

            count += 1

        # Batch Update
        if to_update:
            cursor.executemany("""
                UPDATE new_account_table SET
                    account_hold_possion_PL=%s, account_hold_possion_Balace_Sheet=%s,
                    account_name_of_catogory_PL=%s, account_name_of_catogory_Balace_sheet=%s,
                    account_income=%s, account_expenses=%s, account_assets=%s, account_liabilities=%s, account_equity=%s,
                    cf_catogory=%s, account_basment=%s
                WHERE id=%s
            """, to_update)

        # Batch Insert
        if to_insert:
            cursor.executemany("""
                INSERT INTO new_account_table (
                    account_name, account_hold_possion_PL, account_hold_possion_Balace_Sheet,
                    account_name_of_catogory_PL, account_name_of_catogory_Balace_sheet,
                    account_income, account_expenses, account_assets, account_liabilities, account_equity,
                    cf_catogory, accont_create_date, account_create_user, account_active, account_basment, currency_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, 'LKR')
            """, to_insert)

        _process_bulk_gl_subledgers(cursor, potential_banks, potential_cash, today, current_user)

        conn.commit()
        return count

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# --- Bulk Upload Module ---
@app.route('/bulk_upload_gl', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def bulk_upload_gl():
    if request.method == 'POST':
        # Step 2: Process Uploaded File
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(url_for('bulk_upload_gl'))

            try:
                rows = parse_gl_upload_data(file)
                # Use helper to parse and validate
                raw_rows = parse_csv_file(file, required_columns=['Account Name'])

                rows = []
                for row in raw_rows:
                    if not row.get('Account Name'): continue
                    rows.append(row)

                # Fetch Existing Data for Validation/Dropdowns
                existing_accounts = {a['account_name']: a for a in db.execute_query("SELECT account_name, account_basment FROM new_account_table")}
                bs_cats, pl_cats, cf_cats = get_cached_categories(db)

                return render_template('bulk_upload_review.html',
                                       rows=rows,
                                       existing=existing_accounts,
                                       bs_cats=bs_cats,
                                       pl_cats=pl_cats,
                                       cf_cats=cf_cats)

            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'danger')
                return redirect(url_for('bulk_upload_gl'))

        # Step 3: Save Data
        elif 'save_data' in request.form:
            try:
                current_user = get_current_user_id()
                count = save_bulk_gl_accounts(request.form, current_user)
                flash(f'Successfully processed {count} accounts.', 'success')
                return redirect(url_for('chart_of_accounts'))

            except Exception as e:
                flash(f'Transaction failed: {str(e)}', 'danger')
                return redirect(url_for('bulk_upload_gl'))

    return render_template('bulk_upload_gl.html')

@app.route('/bulk_upload_tb', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def bulk_upload_tb():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(url_for('bulk_upload_tb'))

            try:
                # Need to reset stream cursor since read_csv_content consumes it
                # Wait, our first parse_csv_file definition parses directly.
                # Just call parse_csv_file directly and use its output.
                parsed_rows = parse_csv_file(file, required_columns=['Account Name', 'Debit', 'Credit'])

                rows = []
                missing_accounts = []

                # Fetch existing accounts
                existing = {a['account_name'] for a in db.execute_query("SELECT account_name FROM new_account_table")}

                for row in parsed_rows:
                    name = row.get('Account Name', '').strip()
                    dr = parse_float(row.get('Debit', 0) or 0)
                    cr = parse_float(row.get('Credit', 0) or 0)

                    if not name: continue

                    status = 'OK'
                    if name not in existing:
                        status = 'Missing'
                        missing_accounts.append(name)

                    rows.append({'name': name, 'dr': dr, 'cr': cr, 'status': status})

                # Calculate Totals
                total_dr = sum(r['dr'] for r in rows)
                total_cr = sum(r['cr'] for r in rows)

                if missing_accounts:
                    flash(f'Found {len(missing_accounts)} missing accounts. Please create them first.', 'warning')

                    # Fetch categories again for quick create modal
                    bs_cats, pl_cats, cf_cats = get_cached_categories(db)

                    return render_template('bulk_upload_tb_review.html',
                                           rows=rows, total_dr=total_dr, total_cr=total_cr,
                                           bs_cats=bs_cats, pl_cats=pl_cats, cf_cats=cf_cats,
                                           today_date=date.today().strftime('%Y-%m-%d'))

                return render_template('bulk_upload_tb_review.html', rows=rows, total_dr=total_dr, total_cr=total_cr, today_date=date.today().strftime('%Y-%m-%d'))

            except Exception as e:
                flash(f'Error: {str(e)}', 'danger')

        elif 'save_tb' in request.form:
            # Post TB as Opening Balance JV
            names = request.form.getlist('account_name[]')
            drs = request.form.getlist('dr[]')
            crs = request.form.getlist('cr[]')
            opening_date = request.form.get('opening_date')

            if not opening_date:
                flash('Opening Balance Date is required', 'danger')
                return redirect(url_for('bulk_upload_tb'))

            # Verify Totals
            total_dr = sum(parse_float(d) for d in drs)
            total_cr = sum(parse_float(c) for c in crs)

            if abs(total_dr - total_cr) > 0.01:
                flash(f'Totals do not match! Debit: {total_dr}, Credit: {total_cr}. Difference: {total_dr - total_cr}', 'danger')
                return redirect(url_for('bulk_upload_tb'))

            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                conn.start_transaction()

                current_user = get_current_user_id()
                current_user_pk = get_current_user_pk()
                today = date.today()

                # Create JV
                cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, 1)",
                               ('OB-UPLOAD', 'Opening Balance Upload'))
                jv_no = cursor.lastrowid

                entries_to_insert = []
                count = 0
                for i in range(len(names)):
                    dr = parse_float(drs[i] or 0)
                    cr = parse_float(crs[i] or 0)
                    if dr == 0 and cr == 0: continue

                    entries_to_insert.append((names[i], dr, cr, opening_date, today, current_user, jv_no))
                    count += 1

                if entries_to_insert:
                    cursor.executemany("""
                        INSERT INTO entry_details (
                            account_name, enty_values_DR, enty_values_CR,
                            entry_effective_date, entry_create_date, entry_naration,
                            entry_create_user, entry_jv
                        ) VALUES (%s, %s, %s, %s, %s, 'Opening Balance', %s, %s)
                    """, entries_to_insert)

                conn.commit()
                flash(f'TB Uploaded successfully. {count} entries posted to JV {jv_no}', 'success')
                return redirect(url_for('trial_balance'))

            except Exception as e:
                conn.rollback()
                flash(f'Error posting TB: {str(e)}', 'danger')
                return redirect(url_for('bulk_upload_tb'))

    return render_template('bulk_upload_tb.html')

# --- Cheque Print Setup ---
@app.route('/cheque_print_setup', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def cheque_print_setup():
    if request.method == 'POST':
        bank_account = request.form.get('bank_account')
        width = request.form.get('paper_width')
        height = request.form.get('paper_height')

        # Coordinates
        date_x = request.form.get('date_x')
        date_y = request.form.get('date_y')
        payee_x = request.form.get('payee_x')
        payee_y = request.form.get('payee_y')
        words_x = request.form.get('words_x')
        words_y = request.form.get('words_y')
        digits_x = request.form.get('digits_x')
        digits_y = request.form.get('digits_y')

        # Font Sizes
        date_fs = request.form.get('date_fs')
        payee_fs = request.form.get('payee_fs')
        words_fs = request.form.get('words_fs')
        digits_fs = request.form.get('digits_fs')

        is_cross = 1 if request.form.get('is_cross') else 0

        try:
            # Check if settings exist for bank account (or global if NULL)
            # Simplification: One setting per bank account, or one global if bank_account is None
            # Here we assume we are saving for a specific bank account or default

            # Delete existing for this bank to overwrite (or update)
            if bank_account:
                db.execute_query("DELETE FROM cheque_print_settings WHERE bank_account = %s", (bank_account,), commit=True)
            else:
                db.execute_query("DELETE FROM cheque_print_settings WHERE bank_account IS NULL", commit=True)

            query = """
                INSERT INTO cheque_print_settings (
                    bank_account, paper_width_mm, paper_height_mm,
                    date_x, date_y, date_font_size,
                    payee_x, payee_y, payee_font_size,
                    amount_words_x, amount_words_y, amount_words_font_size,
                    amount_digits_x, amount_digits_y, amount_digits_font_size,
                    is_cross_cheque
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                bank_account if bank_account else None, width, height,
                date_x, date_y, date_fs,
                payee_x, payee_y, payee_fs,
                words_x, words_y, words_fs,
                digits_x, digits_y, digits_fs,
                is_cross
            )
            db.execute_query(query, params, commit=True)
            flash('Cheque settings saved successfully', 'success')

        except Exception as e:
            flash(f'Error saving settings: {str(e)}', 'danger')

        return redirect(url_for('cheque_print_setup', bank_account=bank_account))

    # GET
    selected_bank = request.args.get('bank_account')
    bank_accounts = db.execute_query("SELECT bank_bookcol_account_number FROM bank_book")

    settings = None
    if selected_bank:
        res = db.execute_query("SELECT * FROM cheque_print_settings WHERE bank_account = %s", (selected_bank,))
        if res: settings = res[0]

    # Fallback to global/default if not found for specific bank
    if not settings:
        res = db.execute_query("SELECT * FROM cheque_print_settings WHERE bank_account IS NULL")
        if res: settings = res[0]

    return render_template('cheque_print_setup.html',
                           bank_accounts=bank_accounts,
                           settings=settings,
                           selected_bank=selected_bank)

@app.route('/cheque/print/<int:jv_no>')
@login_required
def print_cheque(jv_no):
    # Fetch Payment Details
    # We need Payee, Date, Amount, Bank Account
    query = """
        SELECT
            b.Bank_Payment_Date as date,
            b.bank_book__suplier_name as payee,
            SUM(b.bank_book_book_recode_dr) as amount,
            b.bank_book__accont_name as bank_account
        FROM bank_book_recod b
        WHERE b.jv_numbers_jv_id = %s
        GROUP BY b.Bank_Payment_Date, b.bank_book__suplier_name, b.bank_book__accont_name
    """
    res = db.execute_query(query, (jv_no,))
    if not res:
        return "Payment Not Found", 404
    payment = res[0]

    # Fetch Settings for this bank
    settings_res = db.execute_query("SELECT * FROM cheque_print_settings WHERE bank_account = %s", (payment['bank_account'],))
    settings = settings_res[0] if settings_res else None

    if not settings:
        # Fallback to default
        settings_res = db.execute_query("SELECT * FROM cheque_print_settings WHERE bank_account IS NULL")
        settings = settings_res[0] if settings_res else {}

    # Convert amount to words (Placeholder logic or simple implementation)
    # Ideally use `num2words` library. Since I can't install packages easily, simple fallback or dummy.
    # Actually I can `pip install num2words` in bash session if needed, or write a simple function.
    # For now, let's assume numeric.

    return render_template('cheque_print.html', payment=payment, settings=settings)

# --- Tax Settings ---
@app.route('/tax_settings', methods=['GET', 'POST'])
@login_required
@has_permission('Add_New_User') # Assuming admin/setup permission
def tax_settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('tax_name')
            rate = request.form.get('tax_rate')
            desc = request.form.get('description')

            if name and rate:
                try:
                    db.execute_query("INSERT INTO tax_rates (tax_name, rate, description, active) VALUES (%s, %s, %s, 1)",
                                     (name, rate, desc), commit=True)
                    flash('Tax rate added successfully', 'success')
                except Exception as e:
                    flash(f'Error adding tax rate: {e}', 'danger')

        elif action == 'delete':
            tid = request.form.get('id')
            if tid:
                db.execute_query("DELETE FROM tax_rates WHERE id = %s", (tid,), commit=True)
                flash('Tax rate deleted', 'success')

        return redirect(url_for('tax_settings'))

    rates = db.execute_query("SELECT * FROM tax_rates")
    return render_template('tax_settings.html', rates=rates)

# --- Company Profile ---
@app.route('/company_profile', methods=['GET', 'POST'])
@login_required
@has_permission('Add_New_User')
def company_profile():
    if request.method == 'POST':
        import base64

        name = request.form.get('company_name')
        addr1 = request.form.get('address_no')
        addr2 = request.form.get('city')
        addr3 = request.form.get('province')
        addr4 = request.form.get('country')
        addr5 = request.form.get('postal_code')
        land = request.form.get('land_no')
        fax = request.form.get('fax_no')
        vat = request.form.get('vat_no')
        curr = request.form.get('currency')
        vat_registered = 1 if request.form.get('vat_registered') else 0

        # Handle Logo Upload
        logo_data = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file.filename != '':
                logo_data = base64.b64encode(file.read()).decode('utf-8')

        # Check if record exists (ID is usually 0 or 1, assuming single row config)
        exists = db.execute_query("SELECT id FROM company")

        try:
            if exists:
                # Update
                query = """
                    UPDATE company SET
                    company_name=%s, company_addras_1=%s, company_addras_2=%s,
                    company_addras_3=%s, company_addras_4=%s, company_addras_5=%s,
                    company_land_line=%s, company_fax_line=%s, company_vate_code=%s,
                    company_curency=%s, vat_registered=%s
                """
                params = [name, addr1, addr2, addr3, addr4, addr5, land, fax, vat, curr, vat_registered]

                if logo_data:
                    query += ", company_log=%s"
                    params.append(logo_data)

                db.execute_query(query, tuple(params), commit=True)
            else:
                # Insert
                query = """
                    INSERT INTO company (
                        id, company_name, company_addras_1, company_addras_2, company_addras_3,
                        company_addras_4, company_addras_5, company_land_line, company_fax_line,
                        company_vate_code, company_curency, company_log, vat_registered
                    ) VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                db.execute_query(query, (name, addr1, addr2, addr3, addr4, addr5, land, fax, vat, curr, logo_data, vat_registered), commit=True)

            flash('Company profile updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')

        return redirect(url_for('company_profile'))

    # Load Data
    res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = res[0] if res else {}

    # If logo exists as bytes, we might need to handle it for display (template expects base64 string)
    # Note: MySQL connector returns bytes for blobs.
    # If it was saved as base64 string (as above), it comes out as string or bytes depending on driver.
    # The template expects a base64 string.
    if company.get('company_log') and isinstance(company['company_log'], bytes):
        try:
            # If it's already base64 bytes
            company['company_log'] = company['company_log'].decode('utf-8')
        except UnicodeDecodeError:
            # If it's raw image bytes, encode it
            import base64
            company['company_log'] = base64.b64encode(company['company_log']).decode('utf-8')

    currencies = db.execute_query("SELECT currency_code, currency_name FROM currency_table")
    if not currencies: # Fallback if table empty
        currencies = [{'currency_code': 'LKR', 'currency_name': 'Sri Lankan Rupee'}]

    return render_template('company_profile.html', company=company, currencies=currencies)

# --- Bank Payment Module ---
@app.route('/bank_payment', methods=['GET'])
@login_required
@has_permission('Access_Accounting')
def bank_payment():
    suppliers = db.execute_query("SELECT supplier_name FROM suppliers WHERE Is_Suplier = 1 AND supplier_name != 'Direct Payment'")
    bank_accounts = db.execute_query("SELECT bank_bookcol_account_number FROM bank_book")
    return render_template('bank_payment.html', suppliers=suppliers, bank_accounts=bank_accounts, today_date=date.today().strftime('%Y-%m-%d'))

# --- Cash Payment Module ---
@app.route('/cash_payment', methods=['GET'])
@login_required
@has_permission('Access_Accounting')
def cash_payment():
    suppliers = db.execute_query("SELECT supplier_name FROM suppliers WHERE Is_Suplier = 1 AND supplier_name != 'Direct Payment'")
    cash_accounts = db.execute_query("SELECT cash_book_account_name FROM cash_book")
    return render_template('cash_payment.html', suppliers=suppliers, cash_accounts=cash_accounts, today_date=date.today().strftime('%Y-%m-%d'))

def _get_supplier_history_data(sup_name, payment_type):
    """Helper to fetch common supplier details, outstanding invoices, and payment history."""
    details, inv_list, sup_id = _get_supplier_base_data(sup_name)
    if not details:
        return {'error': 'Supplier not found'}, 404

    if payment_type == 'cash':
        history = db.execute_query("""
            SELECT cash_book_recod_voucher_no as voucher, Payment_Date as date,
                   cash_book_recode_accont_name as account, cash_book_recode_cr as amount,
                   User_Enter as extra, jv_numbers_jv_id as extra2
            FROM cash_book_recode
            WHERE cash_book_recode_suplier_name = %s
            ORDER BY chash_book_recod_id DESC
        """, (sup_name,))
    else:
        history = db.execute_query("""
            SELECT bank_book_recod_voucher_no as voucher, Bank_Payment_Date as date,
                   bank_book__accont_name as account, bank_book__recode_cr as amount,
                   bank_book__naration as extra, NULL as extra2
            FROM bank_book_recod
            WHERE bank_book__suplier_name = %s
            ORDER BY id DESC
        """, (sup_name,))

    hist_list = []
    for h in history:
        item = {
            'voucher': h['voucher'],
            'date': str(h['date']),
            'account': h['account'],
            'amount': float(h['amount'] or 0)
        }
        if payment_type == 'cash':
            item['user_id'] = h['extra']
            item['jv_no'] = h['extra2']
        else:
            item['narration'] = h['extra']
        hist_list.append(item)

    return {'details': details, 'invoices': inv_list, 'history': hist_list}

def _get_supplier_base_data(sup_name):
    """Helper to fetch common supplier details and outstanding invoices."""
    sup_data = db.execute_query("SELECT * FROM suppliers WHERE supplier_name = %s", (sup_name,))
    if not sup_data:
        return None, None, None

    s = sup_data[0]
    details = {
        'code': s['supplier_code'],
        'address': f"{s['supplier_address_1']}, {s['supplier_address_2']}",
        'mobile': s['suppliers_teli_1'],
        'email': s['suppliers_e_mail'],
        'vat': s['suppliers_vat_regidter_no']
    }
    sup_id = s['sup_id']

    invoices = db.execute_query("""
        SELECT s_i_id, suppliers_invoice_number, suppliers_invoice_date, suppliers_invoice_final_date,
               suppliers_invoice_total_oustanding, suppliers_invoice_total_payment, suppliers_invoice_oustanding
        FROM suppliers_invoice_data
        WHERE suppliers_invoice_buinding_supplier = %s AND suppliers_invoice_oustanding > 0 AND suppliers_oustanding_delete = 0
    """, (sup_id,))

    inv_list = []
    for inv in invoices:
        inv_list.append({
            'id': inv['s_i_id'],
            'invoice_no': inv['suppliers_invoice_number'],
            'date': str(inv['suppliers_invoice_date']),
            'due_date': str(inv['suppliers_invoice_final_date']),
            'total': float(inv['suppliers_invoice_total_oustanding']),
            'paid': float(inv['suppliers_invoice_total_payment']),
            'balance': float(inv['suppliers_invoice_oustanding'])
        })

    return details, inv_list, sup_id


@app.route('/cash_payment/get_data')
@login_required
def get_cash_supplier_data():
    sup_name = request.args.get('name')
    if not sup_name:
        return {'error': 'No supplier name'}, 400

    return _get_supplier_history_data(sup_name, 'cash')

@app.route('/cash_payment/submit', methods=['POST'])
@login_required
def cash_payment_submit():
    supplier_name = request.form.get('supplier')
    cash_account = request.form.get('cash_account')
    payment_date = request.form.get('payment_date')
    narration = request.form.get('narration')
    wht_amount = parse_float(request.form.get('wht_amount', 0))

    if not supplier_name or not cash_account:
        flash('Missing supplier or cash account', 'danger')
        return redirect(url_for('cash_payment'))

    # Collect payments (Total Gross Payment to Supplier)
    payments = []
    total_payment = 0

    # Iterate form to find payment items
    for key in request.form:
        if key.startswith('payment_'):
            inv_id = key.split('_')[1]
            try:
                amount = parse_float(request.form[key])
                if amount > 0:
                    payments.append({'id': inv_id, 'amount': amount})
                    total_payment += amount
            except:
                continue

    if not payments:
        flash('No payment amounts entered', 'warning')
        return redirect(url_for('cash_payment'))

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        # 1. Generate Voucher Number
        cursor.execute("SELECT MAX(cash_voucher_number) FROM cash_voucher_no WHERE cash_voucher_link = %s", (cash_account,))
        res = cursor.fetchone()
        max_voucher = res[0] if res and res[0] else 0
        new_voucher = max_voucher + 1

        cursor.execute("INSERT INTO cash_voucher_no (id, cash_voucher_link, cash_voucher_number) VALUES (0, %s, %s)",
                       (cash_account, new_voucher))

        # 2. Create Journal Voucher (JV)
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM PAYMENT', narration))
        jv_no = cursor.lastrowid

        # Get Sub Account Code
        cursor.execute("SELECT sub_account_code FROM sub_accont_for_new_account WHERE sub_sub_accaount_name = %s", (supplier_name,))
        res = cursor.fetchone()
        sub_ac_code = res[0] if res else 0

        # 3. Create GL Entries

        # A. Debit AP (Full Invoice Amount settled)
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_sub_account_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Account Payable', total_payment, payment_date, date.today(), narration, current_user_pk, jv_no, sub_ac_code))

        # B. Credit Cash (Net Amount = Total - WHT)
        net_payment = total_payment - wht_amount
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (cash_account, net_payment, payment_date, date.today(), narration, current_user_pk, jv_no))

        # C. Credit WHT Payable (If any)
        if wht_amount > 0:
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_CR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('WHT Payable', wht_amount, payment_date, date.today(), f"WHT on {narration}", current_user_pk, jv_no))

        # 4. Process Individual Payments (Update Outstanding)
        if payments:
            inv_ids = [p['id'] for p in payments]
            format_strings = ','.join(['%s'] * len(inv_ids))
            cursor.execute(f"SELECT s_i_id, suppliers_invoice_oustanding FROM suppliers_invoice_data WHERE s_i_id IN ({format_strings})", tuple(inv_ids))

            outstanding_map = {}
            for row in cursor.fetchall():
                outstanding_map[str(row[0])] = parse_float(row[1] or 0)

            call_params = []
            insert_params = []

            for p in payments:
                current_outstanding = outstanding_map.get(str(p['id']), 0.0)
                call_params.append((current_outstanding, p['amount'], p['id']))

                net_item_amount = p['amount']
                if total_payment > 0:
                    net_item_amount = p['amount'] * (net_payment / total_payment)

                insert_params.append((
                    net_item_amount, cash_account, narration,
                    p['id'], supplier_name, jv_no,
                    p['id'], new_voucher, current_user_pk, payment_date
                ))

            # Batch execute Stored Procedure calls
            cursor.executemany("CALL vender_settele(%s, %s, %s)", call_params)

            # Batch insert Cash Book Records
            cursor.executemany("""
                INSERT INTO cash_book_recode (
                    cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                    cash_book_recode_naration, cash_book_recode_suplier_oustanding_id,
                    cash_book_recode_suplier_name, jv_numbers_jv_id,
                    cash_book_po_no, cash_book_suplier_oustanding_id,
                    cash_book_recod_voucher_no, User_Enter, Payment_Date
                ) VALUES (0, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
            """, insert_params)

        conn.commit()
        flash(f'Cash Payment processed successfully. Voucher No: {new_voucher}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Transaction failed: {str(e)}', 'danger')
        logging.error(f"Cash Payment Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('cash_payment'))

@app.route('/cash_payment/delete_invoice', methods=['POST'])
@login_required
@has_permission('Access_Reversals')
def delete_cash_payment_invoice():
    jv_no = request.form.get('jv_no')
    if not jv_no:
        return {'error': 'No JV Number provided'}, 400

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Delete Supplier Invoice (Mark as deleted)
        cursor.execute("CALL Sup_Delete_Invoice(%s)", (jv_no,))

        # 2. Delete Inventory Records (Mark as deleted)
        cursor.execute("CALL Inventory_Delete(%s)", (jv_no,))

        conn.commit()
        cursor.close()
        conn.close()

        return {'success': True}

    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/voucher/print/<string:voucher_type>/<int:jv_no>')
@login_required
def print_voucher(voucher_type, jv_no):
    voucher_configs = {
        'cash': {
            'title': "CASH PAYMENT VOUCHER",
            'table': 'cash_book_recode c',
            'columns': {
                'voucher_no': 'c.cash_book_recod_voucher_no',
                'date': 'c.Payment_Date',
                'paid_to': 'c.cash_book_recode_suplier_name',
                'paid_from': 'c.cash_book_recode_accont_name',
                'narration': 'c.cash_book_recode_naration',
                'amount': 'SUM(c.cash_book_recode_dr)',
                'user_id': 'c.User_Enter'
            },
            'where': 'c.jv_numbers_jv_id = %s',
            'group_by': ['c.cash_book_recod_voucher_no', 'c.Payment_Date', 'c.cash_book_recode_suplier_name',
                         'c.cash_book_recode_accont_name', 'c.cash_book_recode_naration', 'c.User_Enter']
        },
        'bank': {
            'title': "BANK PAYMENT VOUCHER",
            'table': 'bank_book_recod b',
            'columns': {
                'voucher_no': 'b.bank_book_recod_voucher_no',
                'date': 'b.Bank_Payment_Date',
                'paid_to': 'b.bank_book__suplier_name',
                'paid_from': 'b.bank_book__accont_name',
                'narration': 'b.bank_book__naration',
                'amount': 'SUM(b.bank_book_book_recode_dr)',
                'user_id': 'b.Bank_User_Id',
                'cheque_no': 'b.bank_book_chque_no'
            },
            'where': 'b.jv_numbers_jv_id = %s',
            'group_by': ['b.bank_book_recod_voucher_no', 'b.Bank_Payment_Date', 'b.bank_book__suplier_name',
                         'b.bank_book__accont_name', 'b.bank_book__naration', 'b.Bank_User_Id', 'b.bank_book_chque_no']
        },
        'direct': {
            'title': "DIRECT PAYMENT VOUCHER",
            'table': 'cash_book_recode c',
            'columns': {
                'voucher_no': 'c.cash_book_recod_voucher_no',
                'date': 'c.Payment_Date',
                'paid_to': "'Direct Purchase'",
                'paid_from': 'c.cash_book_recode_accont_name',
                'narration': 'c.cash_book_recode_naration',
                'amount': 'SUM(c.cash_book_recode_dr)',
                'user_id': 'c.User_Enter'
            },
            'where': 'c.jv_numbers_jv_id = %s',
            'group_by': ['c.cash_book_recod_voucher_no', 'c.Payment_Date',
                         'c.cash_book_recode_accont_name', 'c.cash_book_recode_naration', 'c.User_Enter']
        }
    }

    config = voucher_configs.get(voucher_type)
    if not config:
        return "Invalid Voucher Type", 404

    columns_str = ", ".join([f"{v} as {k}" for k, v in config['columns'].items()])
    group_by_str = ", ".join(config['group_by'])
    query = f"SELECT {columns_str} FROM {config['table']} WHERE {config['where']} GROUP BY {group_by_str}"

    res = db.execute_query(query, (jv_no,))
    if not res:
        return "Voucher Not Found", 404
    voucher = res[0]

    # Fetch Company Info
    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    return render_template('payment_voucher_print.html',
                           voucher=voucher,
                           company=company,
                           title=config['title'])

@app.route('/service_entry/print/<int:jv_no>')
@login_required
def print_service_entry(jv_no):
    # Fetch Header
    header_query = """
        SELECT j.jv_user_code, j.jv_naration, MIN(e.entry_effective_date) as entry_date,
               (SELECT suppliers_invoice_number FROM suppliers_invoice_data WHERE suppliers_invoice_JV = j.jv_id LIMIT 1) as inv_no
        FROM jv_numbers j
        LEFT JOIN entry_details e ON j.jv_id = e.entry_jv
        WHERE j.jv_id = %s
        GROUP BY j.jv_id
    """
    header_res = db.execute_query(header_query, (jv_no,))
    if not header_res:
        return "Entry Not Found", 404
    header = header_res[0]

    # Fetch Details (Debit entries are the services/expenses)
    details_query = """
        SELECT account_name, entry_naration, enty_values_DR, entry_job_number
        FROM entry_details
        WHERE entry_jv = %s AND enty_values_DR > 0
    """
    details = db.execute_query(details_query, (jv_no,))

    # Calculate Total
    total = sum(d['enty_values_DR'] for d in details)

    # Fetch Supplier (Credit entry)
    sup_query = """
        SELECT account_name, enty_values_CR
        FROM entry_details
        WHERE entry_jv = %s AND enty_values_CR > 0 AND account_name = 'Account Payable'
    """
    sup_res = db.execute_query(sup_query, (jv_no,))

    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    return render_template('service_entry_print.html',
                           header=header,
                           details=details,
                           total=total,
                           company=company,
                           jv_id=jv_no)

# --- Purchase Orders ---
@app.route('/purchase_orders', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def purchase_orders():
    suppliers = db.execute_query("SELECT supplier_name FROM suppliers WHERE Is_Suplier = 1")
    items = db.execute_query("""
        SELECT i.inventoy_name, i.inventoy_items_messurment_unit, p.inventory_price_purcharsing
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
    """)
    return render_template('purchase_orders.html', suppliers=suppliers, items=items)

@app.route('/purchase_orders/save', methods=['POST'])
@login_required
def save_purchase_order():
    try:
        supplier = request.form.get('supplier')
        po_number = request.form.get('po_number')
        delivery_date = request.form.get('delivery_date')
        if not delivery_date:
            delivery_date = None
        location = request.form.get('location')
        comments = request.form.get('comments')
        vat_rate = parse_float(request.form.get('vat_rate', 0))
        items_json = request.form.get('items_json')
        items = json.loads(items_json) if items_json else []

        if not items:
            flash('No items in Purchase Order', 'danger')
            return redirect(url_for('purchase_orders'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # Get Supplier ID
            cursor.execute("SELECT sup_id FROM suppliers WHERE supplier_name = %s", (supplier,))
            res = cursor.fetchone()
            sup_id = res[0] if res else 0

            # Insert Header
            # Use auto-increment ID, but if PO number is manually provided, store it in OP_NO_Other
            # If no manual PO number, generate one? C# logic seems to allow manual.
            if not po_number:
                # Simple generation if empty
                po_number = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            query_header = """
                INSERT INTO OP_NO_Table (
                    OP_NO_Other, Creator_Id, Create_Date, Sup_ID, Sup_Name,
                    Special_Instractions, Expecting_Date, Deliver_Location, VAT_Rate,
                    Save_Post, Delete_PO, Aprove_By, Edit_By
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 0)
            """
            cursor.execute(query_header, (
                po_number, current_user_pk, date.today(), sup_id, supplier,
                comments, delivery_date, location, vat_rate
            ))
            po_id = cursor.lastrowid

            # Insert Details
            query_detail = """
                INSERT INTO PO_Recode_Details (
                    Link_OP_NO_Table, Item, Discription, QTY, Unit_price, Mesurment
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            batch_data = [(
                po_id, item['item'], item['description'],
                parse_float(item.get('qty', 0)), parse_float(item.get('price', 0)), item['unit']
            ) for item in items]

            if batch_data:
                cursor.executemany(query_detail, batch_data)

            conn.commit()
            flash(f'Purchase Order {po_number} created successfully.', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error saving PO: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'System Error: {str(e)}', 'danger')

    return redirect(url_for('purchase_orders'))

@app.route('/purchase_orders/get/<int:po_id>')
@login_required
def get_purchase_order_details(po_id):
    header_res = db.execute_query("SELECT Sup_Name as supplier FROM OP_NO_Table WHERE id = %s", (po_id,))
    if not header_res:
        return {'error': 'Not Found'}, 404

    items = db.execute_query("""
        SELECT Item as item, QTY as qty, Unit_price as price, Mesurment as unit
        FROM PO_Recode_Details WHERE Link_OP_NO_Table = %s
    """, (po_id,))

    return json.dumps({
        'header': header_res[0],
        'items': [{
            'item': i['item'],
            'qty': float(i['qty'] or 0),
            'price': float(i['price'] or 0),
            'unit': i['unit']
        } for i in items]
    })

@app.route('/purchase_orders/list')
@login_required
def list_purchase_orders():
    query = """
        SELECT
            h.id, h.OP_NO_Other as po_number, h.Create_Date as date,
            h.Sup_Name as supplier, h.Save_Post as approved,
            (SELECT SUM(d.QTY * d.Unit_price) FROM PO_Recode_Details d WHERE d.Link_OP_NO_Table = h.id) as subtotal,
            h.VAT_Rate
        FROM OP_NO_Table h
        WHERE h.Delete_PO = 0
        ORDER BY h.id DESC
    """
    rows = db.execute_query(query)

    data = []
    for r in rows:
        subtotal = float(r['subtotal'] or 0)
        vat = float(r['VAT_Rate'] or 0)
        total = subtotal + (subtotal * vat / 100)

        data.append({
            'id': r['id'],
            'po_number': r['po_number'],
            'date': str(r['date']),
            'supplier': r['supplier'],
            'approved': r['approved'] == 1,
            'total': total
        })
    return json.dumps(data)

@app.route('/purchase_orders/approve', methods=['POST'])
@login_required
@has_permission('OP_Approved')
def approve_purchase_order():
    po_id = request.form.get('id')
    current_user = get_current_user_id()
    current_user_pk = get_current_user_pk()

    if po_id:
        db.execute_query("""
            UPDATE OP_NO_Table
            SET Save_Post = 1, Aprove_By = %s, Aproed_Date = %s
            WHERE id = %s
        """, (current_user_pk, date.today(), po_id), commit=True)
        return {'success': True}
    return {'error': 'No ID provided'}, 400

@app.route('/purchase_orders/print/<int:po_id>')
@login_required
def print_purchase_order(po_id):
    # Fetch Header
    header_res = db.execute_query("SELECT * FROM OP_NO_Table WHERE id = %s", (po_id,))
    if not header_res:
        return "PO Not Found", 404
    header = header_res[0]

    # Fetch Items
    items = db.execute_query("SELECT * FROM PO_Recode_Details WHERE Link_OP_NO_Table = %s", (po_id,))

    # Fetch Company Info
    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    # Fetch Supplier Address
    supplier_res = db.execute_query("SELECT * FROM suppliers WHERE sup_id = %s", (header['Sup_ID'],))
    supplier = supplier_res[0] if supplier_res else {}

    # Calculate Totals
    subtotal = sum(float(i['QTY'] or 0) * float(i['Unit_price'] or 0) for i in items)
    vat_rate = float(header['VAT_Rate'] or 0)
    vat_amount = subtotal * vat_rate / 100
    grand_total = subtotal + vat_amount

    return render_template('po_print.html',
                           po=header,
                           items=items,
                           company=company,
                           supplier=supplier,
                           subtotal=subtotal,
                           vat_amount=vat_amount,
                           grand_total=grand_total)

# --- Admin Panel & User Management ---
@app.route('/admin/users', methods=['GET'])
@login_required
@has_permission('Add_New_User')
def admin_users():
    users = db.execute_query("SELECT * FROM Login_Table")
    return render_template('admin_panel.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
@has_permission('Add_New_User')
def add_new_user():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    mobile = request.form.get('mobile')
    email = request.form.get('email')

    if not username or not password:
        flash('Username and Password are required', 'danger')
        return redirect(url_for('admin_users'))

    if password != confirm_password:
        flash('Passwords do not match', 'danger')
        return redirect(url_for('admin_users'))

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # Hash Password
        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash(password)

        # Insert User
        cursor.execute("""
            INSERT INTO Login_Table (User_Name, Password, Mobile_No, Email, User_Active)
            VALUES (%s, %s, %s, %s, 1)
        """, (username, pw_hash, mobile, email))
        user_id = cursor.lastrowid

        # Generate User Code (ID + 50000)
        user_code = user_id + 50000
        cursor.execute("UPDATE Login_Table SET User_Code = %s WHERE id = %s", (user_code, user_id))

        # Insert Default Rights
        # Check if extended columns exist, if not, schema migration handles it or we default
        # We assume columns exist or triggers handle it. But per plan, we insert manually.
        # Note: We need to handle potential missing columns safely or migrate schema.
        # For now, inserting basic rights rows. Extended rights updated via update route.
        cursor.execute("""
            INSERT INTO User_Rights (Link_To_Loging_Tabke, Add_New_User, OP_Approved)
            VALUES (%s, 0, 0)
        """, (user_id,))

        conn.commit()

        # Sync to Master DB for multi-tenant login routing
        try:
            current_db_name = get_session_db_name()
            # Find tenant ID
            tenant_res = master_db.execute_query("SELECT id FROM tenants WHERE db_name = %s", (current_db_name,))
            if tenant_res:
                tenant_id = tenant_res[0]['id']
                master_db.execute_query("""
                    INSERT INTO users (username, password, email, tenant_id)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE password=VALUES(password), email=VALUES(email)
                """, (username, pw_hash, email, tenant_id), commit=True)
        except Exception as master_e:
            logging.error("Error syncing new user to master DB")

        flash(f'User {username} created successfully.', 'success')
    except Exception as e:
        conn.rollback()
        logging.error("Database error while creating user.")
        flash('Error creating user. Please try again.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin/users/details/<int:user_id>', methods=['GET'])
@login_required
@has_permission('Add_New_User')
def get_user_details(user_id):
    users = db.execute_query("SELECT id, User_Name, Password, Mobile_No, Email, User_Active FROM Login_Table WHERE id = %s", (user_id,))
    if users:
        return json.dumps(users[0])
    return json.dumps({'error': 'User not found'})

@app.route('/admin/users/update_details', methods=['POST'])
@login_required
@has_permission('Add_New_User')
def update_user_details():
    user_id = request.form.get('user_id')
    username = request.form.get('username')
    password = request.form.get('password')
    mobile = request.form.get('mobile')
    email = request.form.get('email')
    active = 1 if request.form.get('active') else 0

    if not user_id or not username:
        flash('Username is required', 'danger')
        return redirect(url_for('admin_users'))

    try:
        # If password provided, hash it. Else keep existing.
        if password:
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash(password)
            query = """
                UPDATE Login_Table
                SET User_Name = %s, Password = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            """
            params = (username, pw_hash, mobile, email, active, user_id)
        else:
            query = """
                UPDATE Login_Table
                SET User_Name = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            """
            params = (username, mobile, email, active, user_id)

        db.execute_query(query, params, commit=True)
        # Check if password needs update (if provided)
        # Note: Frontend currently sends password field. If it's intended to be updated only when changed, logic should be handled.
        # However, the provided form logic in `admin_panel.html` (not visible here but implied) likely sends value.
        # If the password field is populated, we assume it's a new password.
        # If we want to support "leave blank to keep existing", we need to check if password is empty.
        # Assuming typical admin panel behavior: empty = no change.

        if password:
            pw_hash = generate_password_hash(password)
            db.execute_query("""
                UPDATE Login_Table
                SET User_Name = %s, Password = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            """, (username, pw_hash, mobile, email, active, user_id), commit=True)
        else:
            db.execute_query("""
                UPDATE Login_Table
                SET User_Name = %s, Mobile_No = %s, Email = %s, User_Active = %s
                WHERE id = %s
            """, (username, mobile, email, active, user_id), commit=True)

        # Sync update to Master DB
        try:
            current_db_name = get_session_db_name()
            tenant_res = master_db.execute_query("SELECT id FROM tenants WHERE db_name = %s", (current_db_name,))
            if tenant_res:
                tenant_id = tenant_res[0]['id']
                if password:
                    master_db.execute_query("""
                        UPDATE users SET username = %s, password = %s, email = %s
                        WHERE username = (SELECT User_Name FROM (SELECT User_Name FROM Login_Table WHERE id = %s) as t) AND tenant_id = %s
                    """, (username, pw_hash, email, user_id, tenant_id), commit=True)
                else:
                    master_db.execute_query("""
                        UPDATE users SET username = %s, email = %s
                        WHERE username = (SELECT User_Name FROM (SELECT User_Name FROM Login_Table WHERE id = %s) as t) AND tenant_id = %s
                    """, (username, email, user_id, tenant_id), commit=True)
        except Exception as master_e:
            logging.error("Error syncing user update to master DB")

        flash('User details updated successfully', 'success')
    except Exception as e:
        logging.error("Database error while updating user.")
        flash('Error updating user. Please try again.', 'danger')

    return redirect(url_for('admin_users'))

@app.route('/admin/users/rights/<int:user_id>', methods=['GET'])
@login_required
@has_permission('Add_New_User')
def get_user_rights(user_id):
    rights = db.execute_query("SELECT * FROM User_Rights WHERE Link_To_Loging_Tabke = %s", (user_id,))
    if rights:
        return json.dumps(rights[0])
    return json.dumps({})

@app.route('/admin/users/rights/update', methods=['POST'])
@login_required
@has_permission('Add_New_User')
def update_user_rights():
    user_id = request.form.get('user_id')
    if not user_id: return {'error': 'No User ID'}, 400

    # Map form fields to columns
    # We use .get() which returns None if not present (unchecked)
    # Checkbox sends 'on' if checked, nothing if unchecked.
    perms = {
        'Add_New_User': 1 if request.form.get('Add_New_User') else 0,
        'OP_Approved': 1 if request.form.get('OP_Approved') else 0,
        'Access_Inventory': 1 if request.form.get('Access_Inventory') else 0,
        'Access_POS': 1 if request.form.get('Access_POS') else 0,
        'Access_Accounting': 1 if request.form.get('Access_Accounting') else 0,
        'Access_Reports': 1 if request.form.get('Access_Reports') else 0,
        'Access_Reversals': 1 if request.form.get('Access_Reversals') else 0
    }

    try:
        # We construct update query dynamically to ignore missing columns if schema isn't fully migrated yet
        # But for robustness, we should run migration at startup (next step).
        query = """
            UPDATE User_Rights SET
            Add_New_User=%s, OP_Approved=%s,
            Access_Inventory=%s, Access_POS=%s,
            Access_Accounting=%s, Access_Reports=%s,
            Access_Reversals=%s
            WHERE Link_To_Loging_Tabke=%s
        """
        db.execute_query(query, (
            perms['Add_New_User'], perms['OP_Approved'],
            perms['Access_Inventory'], perms['Access_POS'],
            perms['Access_Accounting'], perms['Access_Reports'],
            perms['Access_Reversals'],
            user_id
        ), commit=True)
        return {'success': True}
    except Exception as e:
        logging.error(f"Rights Update Error: {e}")
        return {'error': str(e)}, 500

# --- Job Management ---
@app.route('/job_management', methods=['GET'])
@login_required
def job_management():
    # Fetch all jobs with status
    jobs = db.execute_query("SELECT * FROM jobs_unit ORDER BY job_number DESC")
    return render_template('job_management.html', jobs=jobs)

@app.route('/jobs/create', methods=['POST'])
@login_required
def create_job():
    job_no = request.form.get('job_no')
    description = request.form.get('job_description')

    if not job_no or not description:
        flash('Job No and Description are required', 'danger')
        return redirect(url_for('job_management'))

    current_user = get_current_user_id()

    try:
        db.execute_query("""
            INSERT INTO jobs_unit (id, job_number, job_description, job_create_date, job_create_user, job_finsh, job_cancell)
            VALUES (0, %s, %s, %s, %s, 0, 0)
        """, (job_no, description, date.today(), current_user), commit=True)
        flash('New job created successfully', 'success')
    except Exception as e:
        flash(f'Error creating job: {str(e)}', 'danger')

    return redirect(url_for('job_management'))

@app.route('/jobs/toggle_status', methods=['POST'])
@login_required
def toggle_job_status():
    job_id = request.form.get('job_id')
    status = request.form.get('status') # 1 = Finish, 0 = Active

    try:
        db.execute_query("UPDATE jobs_unit SET job_finsh = %s WHERE id = %s", (status, job_id), commit=True)
        msg = "Job finished" if str(status) == "1" else "Job re-activated"
        flash(f'{msg} successfully', 'success')
    except Exception as e:
        flash(f'Error updating job: {str(e)}', 'danger')

    return redirect(url_for('job_management'))

# --- Job Profit Analysis ---
@app.route('/job_profit_analysis', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def job_profit_analysis():
    jobs = db.execute_query("SELECT job_number, job_description FROM jobs_unit ORDER BY job_number DESC")
    default_from = date.today().replace(day=1).strftime('%Y-%m-%d')
    default_to = date.today().strftime('%Y-%m-%d')
    return render_template('job_profit_analysis.html', jobs=jobs, default_from=default_from, default_to=default_to)

@app.route('/job_profit_analysis/data', methods=['POST'])
@login_required
@has_permission('Access_Reports')
def job_profit_analysis_data():
    data = request.json
    scope = data.get('scope', 'single')
    job_ids = data.get('job_ids', [])
    from_date = data.get('from_date')
    to_date = data.get('to_date')

    # Handle single select coming as string vs list
    if isinstance(job_ids, str): job_ids = [job_ids]
    if not job_ids and scope in ['single', 'compare']:
        return {'error': 'Please select job(s)'}, 400

    # Build Filters
    params = []
    where_clause = "WHERE (na.account_income = 1 OR na.account_expenses = 1) AND ed.entry_deleted = 0"

    # Job Filter
    if scope == 'single' or scope == 'compare':
        placeholders = ','.join(['%s'] * len(job_ids))
        where_clause += f" AND ed.entry_job_number IN ({placeholders})"
        params.extend(job_ids)
    elif scope == 'open':
        where_clause += " AND ed.entry_job_number IN (SELECT job_number FROM jobs_unit WHERE job_finsh = 0)"
    elif scope == 'closed':
        where_clause += " AND ed.entry_job_number IN (SELECT job_number FROM jobs_unit WHERE job_finsh = 1)"

    # Date Filter
    if from_date and to_date:
        where_clause += " AND ed.entry_effective_date BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    # Fetch Data
    # Group by Job if Comparison, else Aggregate
    group_cols = "na.account_name, na.account_name_of_catogory_PL, na.account_hold_possion_PL, na.account_income, na.account_expenses"
    select_cols = group_cols

    if scope == 'compare':
        # If comparing, we need pivot-like data.
        # Easier to fetch flat list (Account, Job, Amount) and process in Python
        query = f"""
            SELECT
                ed.entry_job_number,
                na.account_name,
                na.account_name_of_catogory_PL as category,
                na.account_hold_possion_PL as sort_order,
                na.account_income,
                SUM(COALESCE(ed.enty_values_CR, 0) - COALESCE(ed.enty_values_DR, 0)) as income_amount,
                SUM(COALESCE(ed.enty_values_DR, 0) - COALESCE(ed.enty_values_CR, 0)) as expense_amount
            FROM entry_details ed
            JOIN new_account_table na ON ed.account_name = na.account_name
            {where_clause}
            GROUP BY ed.entry_job_number, {group_cols}
            ORDER BY na.account_hold_possion_PL, na.account_name
        """
    else:
        # Standard View (Aggregated)
        query = f"""
            SELECT
                na.account_name,
                na.account_name_of_catogory_PL as category,
                na.account_hold_possion_PL as sort_order,
                na.account_income,
                SUM(COALESCE(ed.enty_values_CR, 0) - COALESCE(ed.enty_values_DR, 0)) as income_amount,
                SUM(COALESCE(ed.enty_values_DR, 0) - COALESCE(ed.enty_values_CR, 0)) as expense_amount
            FROM entry_details ed
            JOIN new_account_table na ON ed.account_name = na.account_name
            {where_clause}
            GROUP BY {group_cols}
            ORDER BY na.account_hold_possion_PL, na.account_name
        """

    rows = db.execute_query(query, tuple(params))

    # Process Logic
    summary = {'income': 0, 'expense': 0, 'profit': 0, 'margin': 0}
    result_rows = []

    if scope == 'compare':
        # Organize by Account -> Job columns
        acc_map = {}
        unique_jobs = set()

        for r in rows:
            key = (r['category'], r['account_name'])
            job = str(r['entry_job_number'])
            unique_jobs.add(job)

            val = float(r['income_amount']) if r['account_income'] == 1 else float(r['expense_amount'])

            # Global Summary
            if r['account_income'] == 1: summary['income'] += val
            else: summary['expense'] += val

            if key not in acc_map:
                acc_map[key] = {'amounts': {}}

            acc_map[key]['amounts'][job] = val

        summary['profit'] = summary['income'] - summary['expense']
        summary['margin'] = round((summary['profit'] / summary['income'] * 100) if summary['income'] else 0, 2)

        for (cat, acc), data in acc_map.items():
            total = sum(data['amounts'].values())
            result_rows.append({
                'category': cat or 'Uncategorized',
                'account': acc,
                'amounts': data['amounts'],
                'total': total
            })

        return {'mode': 'compare', 'jobs': sorted(list(unique_jobs)), 'rows': result_rows, 'summary': summary}

    else:
        # Standard Aggregated View (with Categories)
        grouped = {}

        for r in rows:
            cat = r['category'] or 'Uncategorized'
            if cat not in grouped: grouped[cat] = {'total': 0, 'accounts': []}

            val = float(r['income_amount']) if r['account_income'] == 1 else float(r['expense_amount'])

            # Summary
            if r['account_income'] == 1: summary['income'] += val
            else: summary['expense'] += val

            if val != 0:
                grouped[cat]['accounts'].append({
                    'name': r['account_name'],
                    'val': val
                })
                grouped[cat]['total'] += val

        summary['profit'] = summary['income'] - summary['expense']
        summary['margin'] = round((summary['profit'] / summary['income'] * 100) if summary['income'] else 0, 2)

        # Flatten for table
        base_amt = summary['income'] # For % calculation (usually % of Sales)

        for cat, data in grouped.items():
            # Header Row
            result_rows.append({
                'is_header': True,
                'category': cat,
                'account': '',
                'amount': data['total'],
                'percent': round((data['total'] / base_amt * 100) if base_amt else 0, 1)
            })
            # Detail Rows
            for acc in data['accounts']:
                result_rows.append({
                    'is_header': False,
                    'category': '',
                    'account': acc['name'],
                    'amount': acc['val'],
                    'percent': round((acc['val'] / base_amt * 100) if base_amt else 0, 1)
                })

        return {'mode': 'standard', 'rows': result_rows, 'summary': summary}

# --- Warranty Period Management ---
@app.route('/warranty_period', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def warranty_period():
    item_name = request.args.get('item_name')

    items = db.execute_query("SELECT inventoy_name FROM inventoy_items WHERE active = 1 ORDER BY inventoy_name")

    query = """
        SELECT wp.id, wp.yeas_, wp.month, wp.date_, ii.inventoy_name as name
        FROM inventory_vorenty_period wp
        LEFT JOIN inventoy_items ii ON wp.name = ii.inventoy_name
    """
    params = None
    if item_name:
        query += " WHERE ii.inventoy_name = %s"
        params = (item_name,)

    query += " ORDER BY ii.inventoy_name"

    warranty_items = db.execute_query(query, params)

    return render_template('warranty_period.html', items=items, warranty_items=warranty_items, selected_item=item_name)

@app.route('/warranty_save', methods=['POST'])
@login_required
def warranty_save():
    ids = request.form.getlist('id[]')
    names = request.form.getlist('name[]')
    years = request.form.getlist('year[]')
    months = request.form.getlist('month[]')
    days = request.form.getlist('day[]')

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        for i in range(len(ids)):
            wid = int(ids[i])
            if wid == 0: # Insert
                cursor.execute("""
                    INSERT INTO inventory_vorenty_period (yeas_, month, date_, name)
                    VALUES (%s, %s, %s, %s)
                """, (years[i], months[i], days[i], names[i]))
            else: # Update
                cursor.execute("""
                    UPDATE inventory_vorenty_period
                    SET yeas_ = %s, month = %s, date_ = %s, name = %s
                    WHERE id = %s
                """, (years[i], months[i], days[i], names[i], wid))

        conn.commit()
        cursor.close()
        conn.close()
        flash('Warranty data saved successfully', 'success')
    except Exception as e:
        flash(f'Error saving data: {str(e)}', 'danger')

    return redirect(url_for('warranty_period'))

# --- Inventory Trend Analysis ---
@app.route('/inventory_trend_analysis', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def inventory_trend_analysis():
    item_name = request.args.get('item_name')
    months_back = int(request.args.get('months', 6))

    items = db.execute_query("SELECT DISTINCT inventoy_name FROM inventoy_items WHERE inventoy_name IS NOT NULL AND inventoy_name != '' ORDER BY inventoy_name")

    trend_data = []
    trend_direction = "Stable"
    slope_val = 0
    forecast = 0

    if item_name:
        # Fetch Data
        raw_data = db.execute_query("""
            SELECT
                YEAR(inventory_recod_action_date) as Year,
                MONTH(inventory_recod_action_date) as Month,
                SUM(inventory_recod_movment_out) as MonthlySales
            FROM inventory_recod
            WHERE inventoy_name = %s
            AND inventory_recod_action_date >= DATE_SUB(NOW(), INTERVAL %s MONTH)
            AND inventory_recod_movment_out > 0
            GROUP BY YEAR(inventory_recod_action_date), MONTH(inventory_recod_action_date)
            ORDER BY Year, Month
        """, (item_name, months_back))

        if raw_data:
            # Prepare Lists
            sales = [float(r.get('MonthlySales', 0)) for r in raw_data]
            n = len(sales)

            # Moving Average (3 months)
            moving_avgs = []
            for i in range(n):
                if i < 2:
                    val = sum(sales[:i+1]) / (i+1)
                else:
                    val = sum(sales[i-2:i+1]) / 3
                moving_avgs.append(val)

            # Trend Analysis (Linear Regression)
            sumX = sum(range(n))
            sumY = sum(sales)
            sumXY = sum(i * sales[i] for i in range(n))
            sumX2 = sum(i * i for i in range(n))

            if n > 1 and (n * sumX2 - sumX * sumX) != 0:
                slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
                intercept = (sumY - slope * sumX) / n
            else:
                slope = 0
                intercept = sales[0] if n > 0 else 0

            slope_val = round(slope, 2)
            trend_direction = "Increasing" if slope > 0 else "Decreasing" if slope < 0 else "Stable"
            forecast = round(intercept + slope * n, 1)

            # Combine for Template
            for i, r in enumerate(raw_data):
                trend_val = intercept + slope * i
                trend_data.append({
                    'Period': f"{r['Year']}-{r['Month']:02d}",
                    'Year': r['Year'],
                    'Month': r['Month'],
                    'SalesQuantity': r['MonthlySales'],
                    'MovingAverage': round(moving_avgs[i], 2),
                    'TrendValue': round(trend_val, 2)
                })

    return render_template('inventory_trend_analysis.html',
                           items=items,
                           trend_data=trend_data,
                           selected_item=item_name,
                           months=months_back,
                           trend_direction=trend_direction,
                           slope=slope_val,
                           next_month_forecast=forecast)

@app.route('/api/predict_account_type')
@login_required
def predict_account_type():
    account_name = request.args.get('name', '')
    if not account_name:
        return {'error': 'No name provided'}

    # Get matches
    matches = difflib.get_close_matches(account_name, knowledge_base.account_types.keys(), n=1, cutoff=0.6)

    if matches:
        match = matches[0]
        # Calculate a simple similarity ratio
        ratio = difflib.SequenceMatcher(None, account_name.lower(), match.lower()).ratio()

        # User requested > 75% probability logic (here mapped to ratio > 0.75)
        # Note: get_close_matches uses cutoff, but we check ratio manually for specific threshold if needed
        # The prompt said "if probability less than 75% connect the internet".
        # Since we don't have internet, we only return if confidence is high enough or return low confidence.

        predicted_type = knowledge_base.account_types[match]

        # Map knowledge base types to checkbox values
        # Knowledge Base: "Assets Account", "Cost Account", "Equity Accont", "Income Account", "Liabilities Account"
        # Checkbox values: "asset", "expense", "equity", "income", "liability"

        type_map = {
            "Assets Account": "asset",
            "Fixed Asset": "asset",
            "Intangible Assets": "asset",
            "Cost Account": "expense",
            "Equity Accont": "equity",
            "Equity Account": "equity",
            "Income Account": "income",
            "Liabilities Account": "liability",
            "Liabilities Accounts": "liability"
        }

        mapped_type = type_map.get(predicted_type, "")

        return {
            'match': match,
            'original_type': predicted_type,
            'mapped_type': mapped_type,
            'confidence': ratio
        }

    return {'confidence': 0}

@app.route('/api/get_customers')
@login_required
def api_get_customers():
    query = "SELECT id, customer_name as name FROM customer ORDER BY customer_name"
    rows = db.execute_query(query)
    return json.dumps(rows)

@app.route('/api/get_sub_accounts')
@login_required
def api_get_sub_accounts():
    account_name = request.args.get('account_name')
    if not account_name:
        return json.dumps([])

    query = """
        SELECT sub_account_code as code, sub_sub_accaount_name as name
        FROM sub_accont_for_new_account
        WHERE sub_new_account = %s AND active = 1
        ORDER BY sub_sub_accaount_name
    """
    rows = db.execute_query(query, (account_name,))
    return json.dumps(rows)

@app.route('/get_supplier_data')
@login_required
def get_supplier_data():
    sup_name = request.args.get('name')
    if not sup_name:
        return {'error': 'No supplier name'}, 400

    return _get_supplier_history_data(sup_name, 'bank')

@app.route('/bank_payment_submit', methods=['POST'])
@login_required
def bank_payment_submit():
    supplier_name = request.form.get('supplier')
    bank_account = request.form.get('bank_account')
    payment_date = request.form.get('payment_date')
    narration = request.form.get('narration')
    cheque_no = request.form.get('cheque_no')
    wht_amount = float(request.form.get('wht_amount', 0))

    if not supplier_name or not bank_account:
        flash('Missing supplier or bank account', 'danger')
        return redirect(url_for('bank_payment'))

    # Collect payments
    payments = []
    total_payment = 0
    inv_ids = request.form.getlist('inv_id[]')

    for inv_id in inv_ids:
        amount_str = request.form.get(f'payment_{inv_id}')
        if amount_str and float(amount_str) > 0:
            amount = float(amount_str)
            payments.append({'id': inv_id, 'amount': amount})
            total_payment += amount

    if not payments:
        flash('No payment amounts entered', 'warning')
        return redirect(url_for('bank_payment'))

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        current_user = get_current_user_id()

        # 1. Update Invoices (Vender Settle Logic)
        if payments:
            inv_ids = tuple(p['id'] for p in payments)
            format_strings = ','.join(['%s'] * len(inv_ids))
            cursor.execute(f"SELECT s_i_id, suppliers_invoice_oustanding, suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE s_i_id IN ({format_strings})", inv_ids)
            res = cursor.fetchall()

            # Using list for invoice_data to allow updates to current_paid
            invoice_data = {str(r[0]): [float(r[1] or 0), float(r[2] or 0)] for r in res}

            update_args = []
            for p in payments:
                inv_d = invoice_data.get(str(p['id']))
                if not inv_d: continue

                current_outstanding = inv_d[0]
                current_paid = inv_d[1]

                if p['amount'] > current_outstanding:
                    raise Exception(f"Payment amount {p['amount']} exceeds outstanding {current_outstanding} for invoice ID {p['id']}")

                new_total_paid = current_paid + p['amount']

                # Update the cached data so subsequent duplicate payments use the new total
                inv_d[0] = current_outstanding - p['amount'] # Reduce outstanding conceptually, although not checked directly here it is safer
                inv_d[1] = new_total_paid

                update_args.append((new_total_paid, p['id']))

            if update_args:
                # If there are duplicates, executemany might execute them sequentially or fail depending on the db driver and isolation.
                # It's better to aggregate updates per invoice ID.
                # Since update_args contains all sequential updates, the last one per ID is the one that matters.
                # Let's aggregate to ensure executemany works correctly if the driver batches them.
                final_updates = {}
                for paid, inv_id in update_args:
                    final_updates[inv_id] = paid

                final_update_args = [(paid, inv_id) for inv_id, paid in final_updates.items()]
                cursor.executemany("UPDATE suppliers_invoice_data SET suppliers_invoice_total_payment = %s WHERE s_i_id = %s", final_update_args)

        # Check Workflow
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
        res_set = cursor.fetchone()
        workflow_enabled = res_set and res_set[0] == '1'
        status = 0 if workflow_enabled else 1

        # 2. Generate Voucher Number
        cursor.execute("SELECT MAX(bank_book_voucher_no) FROM bank_book_voucher_no WHERE bank_book_voucher_link = %s", (bank_account,))
        res = cursor.fetchone()
        max_voucher = res[0] if res and res[0] else 0
        new_voucher = max_voucher + 1

        cursor.execute("INSERT INTO bank_book_voucher_no (bank_book_voucher_link, bank_book_voucher_no, bank_book_chq_no) VALUES (%s, %s, %s)",
                       (bank_account, new_voucher, cheque_no))

        # 2a. Generate Master Voucher Number (Global Sequence)
        cursor.execute("INSERT INTO master_payment_voucher_no (voucher_no, create_date) VALUES (0, %s)", (date.today(),))
        master_voucher_no = cursor.lastrowid

        # 3. Create Journal Voucher (JV)
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, %s)",
                       ('JV FROM PAYMENT', narration, status))
        jv_no = cursor.lastrowid

        # Get Sub Account Code for Supplier
        cursor.execute("SELECT sub_account_code FROM sub_accont_for_new_account WHERE sub_sub_accaount_name = %s", (supplier_name,))
        res = cursor.fetchone()
        sub_ac_code = res[0] if res else 0

        # Debit AP (Full amount settled)
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_sub_account_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Account Payable', total_payment, payment_date, date.today(), narration, current_user, jv_no, sub_ac_code))

        # Credit Bank (Net amount = Total - WHT)
        net_payment = total_payment - wht_amount
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (bank_account, net_payment, payment_date, date.today(), narration, current_user, jv_no))

        # Credit WHT Payable (If any)
        if wht_amount > 0:
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_CR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('WHT Payable', wht_amount, payment_date, date.today(), f"WHT on {narration}", current_user, jv_no))

        # 4. Record Bank Transactions (Split proportionately if needed, or record full/net?)
        # Bank Book typically matches bank statement, so record NET payment.

        sup_id_res = db.execute_query("SELECT sup_id FROM suppliers WHERE supplier_name = %s", (supplier_name,))
        sup_id = sup_id_res[0]['sup_id'] if sup_id_res else 0

        for p in payments:
            net_item_amount = p['amount']
            if total_payment > 0:
                net_item_amount = p['amount'] * (net_payment / total_payment)

            cursor.execute("""
                INSERT INTO bank_book_recod (
                    bank_book__accont_name, bank_book__recode_cr, bank_book__naration,
                    bank_book__suplier_oustanding_id, bank_book__suplier_name, jv_numbers_jv_id,
                    bank_book_recod_voucher_no, bank_book_chque_no, Bank_Sup_Code, Bank_User_Id, Bank_Payment_Date,
                    master_voucher_no
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (bank_account, net_item_amount, narration, p['id'], supplier_name, jv_no, new_voucher, cheque_no, sup_id, current_user, payment_date, master_voucher_no))

        conn.commit()
        flash(f'Payment processed successfully. Voucher No: {new_voucher}, Master Voucher: {master_voucher_no}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Transaction failed: {str(e)}', 'danger')
        logging.error(f"Cash Payment Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('bank_payment'))

# --- Customer Loyalty ---
@app.route('/customer_loyalty', methods=['GET', 'POST'])
@login_required
def customer_loyalty():
    if request.method == 'POST':
        name = request.form.get('customer_name')
        billing = request.form.get('billing_address')
        delivery = request.form.get('delivery_address')
        email = request.form.get('email')
        mobile = request.form.get('mobile_no')
        paid = request.form.get('amount_paid')

        if not mobile:
            flash('Please enter the mobile number', 'danger')
            return redirect(url_for('customer_loyalty'))

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            # Determine next ID
            cursor.execute("SELECT MAX(id) FROM customer")
            res = cursor.fetchone()
            max_id = res[0] if res and res[0] else 0
            customer_code = max_id + 60001

            current_date = datetime.utcnow()

            query = """
                INSERT INTO customer (
                    id, customer_name, customer_code,
                    customer_Billing_Address, costomer_Delivery_Address,
                    e_mail, coustomer_credit_limit, Mobile_nimber,
                    Is_Loyality_Customer, Compay_Or_Not, Create_Date,
                    Paid_Amountl, Create_Cashiyer
                ) VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                name, customer_code, billing, delivery, email,
                1, mobile, 1, 0, current_date, paid if paid else 0, 0
            )

            cursor.execute(query, params)
            conn.commit()
            flash('Updated ..', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('customer_loyalty'))

    return render_template('customer_loyalty.html')

# --- Direct Purchasing ---
@app.route('/direct_purchasing', methods=['GET'])
@login_required
@has_permission('Access_Accounting')
def direct_purchasing():
    cash_accounts = db.execute_query("SELECT cash_book_account_name FROM cash_book")
    cost_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_expenses = 1 OR account_assets = 1")
    items = db.execute_query("SELECT inventoy_name FROM inventoy_items")

    return render_template('direct_purchasing.html',
                           cash_accounts=cash_accounts,
                           cost_accounts=cost_accounts,
                           inventory_items=items,
                           today_date=datetime.now().strftime('%Y-%m-%d'),
                           session_payment_items=session.get('payment_items', []),
                           total_value=session.get('payment_total', 0))

@app.route('/direct_purchasing/add_item', methods=['POST'])
@login_required
def direct_purchasing_add_item():
    qty_str = request.form.get('qty')
    price_str = request.form.get('price')

    try:
        qty = float(qty_str) if qty_str and qty_str.strip() else 0.0
    except ValueError:
        qty = 0.0

    try:
        price = float(price_str) if price_str and price_str.strip() else 0.0
    except ValueError:
        price = 0.0

    item = {
        'account': request.form.get('cost_account'),
        'item_name': request.form.get('inventory_item'),
        'job_no': request.form.get('job_no'),
        'qty': qty,
        'price': price,
        'narration': request.form.get('narration')
    }
    item['total'] = item['qty'] * item['price']

    if 'payment_items' not in session:
        session['payment_items'] = []

    session['payment_items'].append(item)
    session.modified = True

    # Recalculate total
    total = sum(i['total'] for i in session['payment_items'])
    session['payment_total'] = total

    return redirect(url_for('direct_purchasing'))

@app.route('/direct_purchasing/submit', methods=['POST'])
@login_required
def direct_purchasing_submit():
    if 'payment_items' not in session or not session['payment_items']:
        flash('No items to submit', 'warning')
        return redirect(url_for('direct_purchasing'))

    cash_account = request.form.get('cash_account')
    if not cash_account:
        flash('Please select a cash account', 'danger')
        return redirect(url_for('direct_purchasing'))

    items = session['payment_items']
    total_amount = session.get('payment_total', 0)
    current_user = get_current_user_id()
    today_date = date.today()
    narration = "Direct Purchase / Cash Payment"

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Generate Voucher Number for Cash Book
        # Check max voucher for this account
        cursor.execute("SELECT MAX(cash_voucher_number) FROM cash_voucher_no WHERE cash_voucher_link = %s", (cash_account,))
        res = cursor.fetchone()
        max_voucher = res[0] if res and res[0] else 0
        new_voucher = max_voucher + 1

        cursor.execute("INSERT INTO cash_voucher_no (cash_voucher_link, cash_voucher_number) VALUES (%s, %s)", (cash_account, new_voucher))

        # 2. Create Journal Voucher (JV)
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM DIRECT CASH', narration))
        jv_no = cursor.lastrowid

        # 3. GL Entries
        # Credit Cash Account (Total)
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (cash_account, total_amount, today_date, today_date, narration, current_user, jv_no))

        # Debit Expense/Asset Accounts (Per Item)
        for item in items:
            # Handle Job No
            job_no = item.get('job_no')
            if job_no and job_no.strip() == "": job_no = None

            # Debit Entry
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (item['account'], item['total'], today_date, today_date, item['narration'], current_user, jv_no, job_no))

            # 4. Cash Book Record
            cursor.execute("""
                INSERT INTO cash_book_recode (
                    cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                    cash_book_recode_naration, jv_numbers_jv_id, cash_book_recod_voucher_no,
                    User_Enter, Payment_Date
                ) VALUES (0, %s, %s, %s, %s, %s, %s, %s)
            """, (item['total'], cash_account, item['narration'], jv_no, new_voucher, current_user, today_date))

            # 5. Inventory Record (if Item Name is present)
            if item.get('item_name'):
                # Get item code
                cursor.execute("SELECT inventoy_code, inventoy_items_messurment_unit FROM inventoy_items WHERE inventoy_name = %s", (item['item_name'],))
                inv_res = cursor.fetchone()

                if inv_res:
                    inv_code = inv_res[0]
                    inv_unit = inv_res[1]

                    cursor.execute("""
                        INSERT INTO inventory_recod (
                            inventoy_name, inventoy_code, inventory_recod_action_date,
                            inventory_recod_moument_in, inventory_recod_movment_out,
                            inventory_recod_mesrmet, inventory_recod_unit_price,
                            inventory_recod_account, inventory_recod_user_id,
                            inventory_recod_user_recod_date, JV_No
                        ) VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s)
                    """, (item['item_name'], inv_code, today_date, item['qty'], inv_unit, item['price'], item['account'], current_user, today_date, jv_no))

        conn.commit()

        session.pop('payment_items', None)
        session.pop('payment_total', None)
        flash(f'Payment submitted successfully. JV No: {jv_no}, Voucher: {new_voucher}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error submitting payment: {str(e)}', 'danger')
        logging.error(f"Direct Payment Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('direct_purchasing'))

# --- Inventory Price Editing ---
@app.route('/inventory_price_editing', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def inventory_price_editing():
    search = request.args.get('search', '')
    query = """
        SELECT
            ii.id, ii.inventoy_name, ii.inventoy_code,
            ipr.inventory_price_selling, ipr.inventory_price_profit_marging_comen,
            ipr.inventory_price_purcharsing, ipr.inventory_price_for_Loyality_customer
        FROM inventoy_items ii
        LEFT JOIN inventory_price_recod ipr ON ii.id = ipr.inventory_price_link
    """
    params = None
    if search:
        query += " WHERE ii.inventoy_name LIKE %s OR ii.inventoy_code LIKE %s"
        search_pattern = f"%{search}%"
        params = (search_pattern, search_pattern)

    items = db.execute_query(query, params)
    return render_template('inventory_price_editing.html', items=items, search_query=search)

@app.route('/inventory_price_editing/update', methods=['POST'])
@login_required
def update_inventory_prices():
    item_ids = request.form.getlist('item_ids[]')
    market_prices = request.form.getlist('market_prices[]')
    spm_prices = request.form.getlist('spm_prices[]')
    loyalty_prices = request.form.getlist('loyalty_prices[]')

    if not item_ids:
        flash('No items to update', 'warning')
        return redirect(url_for('inventory_price_editing'))

    # Check existence in bulk
    placeholders = ', '.join(['%s'] * len(item_ids))
    query = f"SELECT inventory_price_link FROM inventory_price_recod WHERE inventory_price_link IN ({placeholders})"
    existing_records = db.execute_query(query, tuple(item_ids))

    existing_links = set()
    if existing_records:
        # execute_query with DictionaryCursor returns list of dicts
        if isinstance(existing_records[0], dict):
            existing_links = {str(r['inventory_price_link']) for r in existing_records}
        else:
            existing_links = {str(r[0]) for r in existing_records}

    for i in range(len(item_ids)):
        link_id = str(item_ids[i])

        if link_id in existing_links:
            db.execute_query("""
                UPDATE inventory_price_recod SET
                inventory_price_selling = %s,
                inventory_price_profit_marging_comen = %s,
                inventory_price_for_Loyality_customer = %s
                WHERE inventory_price_link = %s
            """, (market_prices[i], spm_prices[i], loyalty_prices[i], link_id), commit=True)
        else:
            db.execute_query("""
                INSERT INTO inventory_price_recod
                (inventory_price_link, inventory_price_selling, inventory_price_profit_marging_comen, inventory_price_for_Loyality_customer)
                VALUES (%s, %s, %s, %s)
            """, (link_id, market_prices[i], spm_prices[i], loyalty_prices[i]), commit=True)

    flash('Prices updated successfully', 'success')
    return redirect(url_for('inventory_price_editing'))

# --- Balance Sheet ---
@app.route('/balance_sheet')
@login_required
@has_permission('Access_Reports')
def balance_sheet():
    as_at_date = request.args.get('as_at_date', datetime.now().strftime('%Y-%m-%d'))

    # Using existing stored procedures if possible, or reproducing logic
    # Reproducing logic from Balance_sheet.xaml.cs using queries for portablity

    assets = db.execute_query("""
        SELECT
            na.account_name_of_catogory_Balace_sheet as category,
            na.account_name as name,
            COALESCE(SUM(ed.enty_values_DR), 0) - COALESCE(SUM(ed.enty_values_CR), 0) as balance
        FROM new_account_table na
        LEFT JOIN entry_details ed ON na.account_name = ed.account_name
            AND ed.entry_effective_date <= %s AND ed.entry_deleted = 0
        WHERE na.account_assets = 1
        GROUP BY na.account_name, na.account_name_of_catogory_Balace_sheet
    """, (as_at_date,))

    liabilities = db.execute_query("""
        SELECT
            na.account_name_of_catogory_Balace_sheet as category,
            na.account_name as name,
            COALESCE(SUM(ed.enty_values_CR), 0) - COALESCE(SUM(ed.enty_values_DR), 0) as balance
        FROM new_account_table na
        LEFT JOIN entry_details ed ON na.account_name = ed.account_name
            AND ed.entry_effective_date <= %s AND ed.entry_deleted = 0
        WHERE na.account_liabilities = 1
        GROUP BY na.account_name, na.account_name_of_catogory_Balace_sheet
    """, (as_at_date,))

    equity = db.execute_query("""
        SELECT
            na.account_name_of_catogory_Balace_sheet as category,
            na.account_name as name,
            COALESCE(SUM(ed.enty_values_CR), 0) - COALESCE(SUM(ed.enty_values_DR), 0) as balance
        FROM new_account_table na
        LEFT JOIN entry_details ed ON na.account_name = ed.account_name
            AND ed.entry_effective_date <= %s AND ed.entry_deleted = 0
        WHERE na.account_equity = 1
        GROUP BY na.account_name, na.account_name_of_catogory_Balace_sheet
    """, (as_at_date,))

    # Calculate Retained Earnings (Income - Expense - COGS) matching legacy C# logic
    retained_earnings_query = """
        SELECT
            na.account_name,
            na.account_income,
            na.account_expenses,
            na.account_basment,
            COALESCE(SUM(ed.enty_values_DR), 0) as total_dr,
            COALESCE(SUM(ed.enty_values_CR), 0) as total_cr
        FROM
            new_account_table na
        LEFT JOIN
            entry_details ed ON na.account_name = ed.account_name
            AND ed.entry_effective_date <= %s
            AND ed.entry_deleted = 0
        WHERE
            (na.account_income = 1 OR na.account_expenses = 1)
            AND na.account_active = 1
        GROUP BY
            na.account_name,
            na.account_income,
            na.account_expenses,
            na.account_basment
    """
    retained_earnings_rows = db.execute_query(retained_earnings_query, (as_at_date,))

    total_income = 0.0
    total_expenses = 0.0

    for row in retained_earnings_rows:
        is_income = bool(row['account_income'])
        is_expense = bool(row['account_expenses'])
        basement = row['account_basment']
        debit_total = float(row['total_dr'] or 0)
        credit_total = float(row['total_cr'] or 0)

        balance = 0.0
        if basement == "DR":
            balance = debit_total - credit_total
        else:
            balance = credit_total - debit_total

        if is_income:
            total_income += balance
        elif is_expense:
            total_expenses += balance

    retained_earnings = total_income - total_expenses

    # Grouping
    grouped_assets = {}
    total_assets = 0
    for a in assets:
        cat = a['category'] or 'Uncategorized'
        if cat not in grouped_assets: grouped_assets[cat] = []
        val = float(a['balance'])
        if val != 0:
            a['balance'] = val
            grouped_assets[cat].append(a)
            total_assets += val

    grouped_liabilities = {}
    total_liabilities = 0
    for l in liabilities:
        cat = l['category'] or 'Uncategorized'
        if cat not in grouped_liabilities: grouped_liabilities[cat] = []
        val = float(l['balance'])
        if val != 0:
            l['balance'] = val
            grouped_liabilities[cat].append(l)
            total_liabilities += val

    # Clean equity
    cleaned_equity = []
    total_equity = 0
    for e in equity:
        val = float(e['balance'])
        if val != 0:
            e['balance'] = val
            cleaned_equity.append(e)
            total_equity += val

    report_data = {
        'assets': grouped_assets,
        'liabilities': grouped_liabilities,
        'equity': cleaned_equity
    }

    totals = {
        'assets': total_assets,
        'liabilities': total_liabilities,
        'equity': total_equity,
        'retained_earnings': retained_earnings
    }

    return render_template('balance_sheet.html', as_at_date=as_at_date, report_data=report_data, totals=totals)

# --- Cash Flow ---
@app.route('/cash_flow')
@login_required
@has_permission('Access_Reports')
def cash_flow():
    from_date = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))

    if request.args.get('from_date'):
        # 1. Net Profit
        net_profit_res = db.execute_query("""
            SELECT
            (SELECT COALESCE(SUM(enty_values_CR - enty_values_DR), 0)
             FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
             WHERE na.account_income = 1 AND entry_effective_date BETWEEN %s AND %s) -
            (SELECT COALESCE(SUM(enty_values_DR - enty_values_CR), 0)
             FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
             WHERE na.account_expenses = 1 AND entry_effective_date BETWEEN %s AND %s) as val
        """, (from_date, to_date, from_date, to_date))
        net_profit = net_profit_res[0]['val'] if net_profit_res else 0

        # 2. Adjustments
        adjustments = db.execute_query("""
            SELECT na.account_name as description, SUM(CASE WHEN na.account_basment='CR' THEN (ed.enty_values_CR - ed.enty_values_DR) ELSE (ed.enty_values_DR - ed.enty_values_CR) END) as amount
            FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
            JOIN cf_catogory cf ON na.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Adjustments' AND entry_effective_date BETWEEN %s AND %s
            GROUP BY na.account_name
        """, (from_date, to_date))

        # 3. Working Capital
        working_capital = db.execute_query("""
            SELECT na.account_name as description, SUM(CASE WHEN na.account_basment='DR' THEN (ed.enty_values_CR - ed.enty_values_DR) ELSE (ed.enty_values_CR - ed.enty_values_DR) END) as amount
            FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
            JOIN cf_catogory cf ON na.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Changes In Working Capital' AND entry_effective_date BETWEEN %s AND %s
            GROUP BY na.account_name
        """, (from_date, to_date))

        # 4. Investing
        investing = db.execute_query("""
            SELECT na.account_name as description, SUM((ed.enty_values_DR - ed.enty_values_CR) * -1) as amount
            FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
            JOIN cf_catogory cf ON na.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Investing Activities' AND entry_effective_date BETWEEN %s AND %s
            GROUP BY na.account_name
        """, (from_date, to_date))

        # 5. Financing
        financing = db.execute_query("""
            SELECT na.account_name as description, SUM((ed.enty_values_DR - ed.enty_values_CR) * -1) as amount
            FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
            JOIN cf_catogory cf ON na.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Financing Activities' AND entry_effective_date BETWEEN %s AND %s
            GROUP BY na.account_name
        """, (from_date, to_date))

        net_prof_val = float(net_profit or 0)
        op_total = net_prof_val + sum(float(x['amount']) for x in adjustments) + sum(float(x['amount']) for x in working_capital)
        inv_total = sum(float(x['amount']) for x in investing)
        fin_total = sum(float(x['amount']) for x in financing)

        report_data = {
            'net_profit': net_prof_val,
            'adjustments': adjustments,
            'working_capital': working_capital,
            'investing': investing,
            'financing': financing,
            'totals': {
                'operating': op_total,
                'investing': inv_total,
                'financing': fin_total,
                'net_change': op_total + inv_total + fin_total
            }
        }
        return render_template('cash_flow.html', from_date=from_date, to_date=to_date, report_data=report_data)

    return render_template('cash_flow.html', from_date=from_date, to_date=to_date)


# --- Inventory Balance ---
@app.route('/inventory_balance')
@login_required
@has_permission('Access_Inventory')
def inventory_balance():
    view = request.args.get('view', 'all')
    report_data = []

    if view == 'all':
        report_data = db.execute_query("CALL inventory_balance_01()")
    elif view == 'low':
        report_data = db.execute_query("CALL inventory_balance_02()")
    elif view == 'out':
        report_data = db.execute_query("CALL inventory_balance_03()")

    return render_template('inventory_balance.html', view=view, report_data=report_data)

# --- Inventory Reports ---
@app.route('/inventory_reports')
@login_required
@has_permission('Access_Reports')
def inventory_reports():
    report_type = request.args.get('report_type', 'balance')
    item_name = request.args.get('item_name')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    items = db.execute_query("SELECT inventoy_name FROM inventoy_items")
    report_data = []
    opening_balance = 0

    if report_type == 'balance':
        # Inventory Balance
        rows = db.execute_query("""
            SELECT
                ii.inventoy_name as item_name, ii.inventoy_code as code, ii.inventoy_items_messurment_unit as unit,
                SUM(ir.inventory_recod_moument_in - ir.inventory_recod_movment_out) as qty,
                SUM((ir.inventory_recod_moument_in - ir.inventory_recod_movment_out) * ir.inventory_recod_unit_price) as value
            FROM inventoy_items ii
            LEFT JOIN inventory_recod ir ON ii.inventoy_name = ir.inventoy_name
            GROUP BY ii.id
        """)
        report_data = rows

    elif report_type == 'card' and item_name and from_date:
        # Opening Balance
        ob_res = db.execute_query("""
            SELECT SUM(inventory_recod_moument_in - inventory_recod_movment_out) as bal
            FROM inventory_recod
            WHERE inventoy_name = %s AND inventory_recod_action_date < %s
        """, (item_name, from_date))
        opening_balance = float(ob_res[0]['bal'] or 0) if ob_res else 0

        # Movements
        mvs = db.execute_query("""
            SELECT
                inventory_recod_action_date as date,
                inventory_recodcol_memo as description,
                inventory_recod_moument_in as in_qty,
                inventory_recod_movment_out as out_qty,
                inventory_recod_suplier_iv_no as iv_no,
                inventory_recod_unit_price as purchasing_price,
                inventory_recod_selling_price as selling_price
            FROM inventory_recod
            WHERE inventoy_name = %s AND inventory_recod_action_date BETWEEN %s AND %s
            ORDER BY inventory_recod_action_date
        """, (item_name, from_date, to_date))

        curr = opening_balance
        for m in mvs:
            curr += float(m['in_qty']) - float(m['out_qty'])
            m['balance'] = curr
            m['balance_value'] = curr * float(m['purchasing_price'] or 0)
            report_data.append(m)

    return render_template('inventory_reports.html', report_type=report_type, items=items, report_data=report_data, item_name=item_name, from_date=from_date, to_date=to_date, opening_balance=opening_balance)

# --- Bank Reconciliation ---
@app.route('/bank_reconciliation', methods=['GET'])
@login_required
def bank_reconciliation():
    bank_account = request.args.get('bank_account')
    rec_date = request.args.get('rec_date', date.today().strftime('%Y-%m-%d'))
    statement_balance = request.args.get('statement_balance', 0)

    bank_accounts = db.execute_query("SELECT bank_bookcol_account_number FROM bank_book")

    deposits = []
    payments = []
    book_balance = 0
    opening_balance = 0

    if bank_account:
        # Deposits (DR > 0, Not Reconciled)
        deposits = db.execute_query("""
            SELECT id, entry_effective_date, entry_naration, enty_values_DR
            FROM entry_details
            WHERE account_name = %s AND enty_values_DR > 0 AND (entry_Rec = 0 OR entry_Rec IS NULL) AND entry_deleted = 0
            ORDER BY entry_effective_date
        """, (bank_account,))

        # Payments (CR > 0, Not Reconciled)
        payments = db.execute_query("""
            SELECT id, entry_effective_date, entry_naration, enty_values_CR
            FROM entry_details
            WHERE account_name = %s AND enty_values_CR > 0 AND (entry_Rec = 0 OR entry_Rec IS NULL) AND entry_deleted = 0
            ORDER BY entry_effective_date
        """, (bank_account,))

        # Book Balance logic (simplified version of procedure)
        bb_res = db.execute_query("""
            SELECT SUM(enty_values_DR) - SUM(enty_values_CR) as bal
            FROM entry_details
            WHERE account_name = %s AND entry_effective_date <= %s
        """, (bank_account, rec_date))
        book_balance = float(bb_res[0]['bal'] or 0) if bb_res else 0

        # Opening Balance logic (simplified: sum of Reconciled items)
        op_res = db.execute_query("""
            SELECT SUM(enty_values_DR) - SUM(enty_values_CR) as bal
            FROM entry_details
            WHERE account_name = %s AND entry_Rec = 1
        """, (bank_account,))
        opening_balance = float(op_res[0]['bal'] or 0) if op_res else 0

    return render_template('bank_reconciliation.html',
                           bank_accounts=bank_accounts,
                           selected_account=bank_account,
                           rec_date=rec_date,
                           deposits=deposits,
                           payments=payments,
                           book_balance=book_balance,
                           opening_balance=opening_balance,
                           statement_balance=statement_balance)

@app.route('/bank_reconciliation/process', methods=['POST'])
@login_required
def process_reconciliation():
    bank_account = request.form.get('bank_account')
    rec_date = request.form.get('rec_date')
    cleared_ids = request.form.getlist('cleared_ids[]')

    if not bank_account or not rec_date:
        flash('Missing required data', 'danger')
        return redirect(url_for('bank_reconciliation'))

    if cleared_ids:
        # Mark selected items as reconciled
        placeholders = ', '.join(['%s'] * len(cleared_ids))
        query = f"UPDATE entry_details SET entry_Rec = 1, entry_effective_date = %s WHERE id IN ({placeholders})"
        params = [rec_date] + cleared_ids
        db.execute_query(query, tuple(params), commit=True)

        flash(f'Reconciliation processed. {len(cleared_ids)} transactions cleared.', 'success')
    else:
        flash('No transactions selected to clear.', 'info')

    return redirect(url_for('bank_reconciliation', bank_account=bank_account, rec_date=rec_date))

# --- Ledger View ---
@app.route('/ledger_view')
@login_required
@has_permission('Access_Reports')
def ledger_view():
    # Fetch accounts grouped/labeled like C# (P&L vs BS)
    # C# Logic:
    # 1. P&L: account_income=1 OR account_expenses=1
    # 2. BS: account_assets=1 OR account_liabilities=1 OR account_equity=1

    pl_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_income = 1 OR account_expenses = 1 ORDER BY account_name")
    bs_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_assets = 1 OR account_liabilities = 1 OR account_equity = 1 ORDER BY account_name")

    # Structure for Select2 optgroups
    # However, HTML select structure is easier:
    return render_template('ledger_view.html',
                           pl_accounts=pl_accounts,
                           bs_accounts=bs_accounts,
                           default_from=date.today().replace(day=1).strftime('%Y-%m-%d'),
                           default_to=date.today().strftime('%Y-%m-%d'))

@app.route('/api/ledger_data', methods=['POST'])
@login_required
def get_ledger_data():
    account_name = request.json.get('account_name')
    from_date = request.json.get('from_date')
    to_date = request.json.get('to_date')

    if not account_name or not from_date or not to_date:
        return {'error': 'Missing parameters'}, 400

    # 1. Get Account Basement (DR/CR)
    acc_res = db.execute_query("SELECT account_basment FROM new_account_table WHERE account_name = %s", (account_name,))
    if not acc_res:
        return {'error': 'Account not found'}, 404
    basement = acc_res[0]['account_basment'] # 'DR' or 'CR'

    # 2. Calculate Opening Balance
    # Logic: Sum previous entries based on basement

    op_dr = 0
    op_cr = 0

    # Calculate Sums before from_date
    op_res = db.execute_query("""
        SELECT SUM(enty_values_DR), SUM(enty_values_CR)
        FROM entry_details
        WHERE account_name = %s AND entry_effective_date < %s AND entry_deleted = 0
    """, (account_name, from_date))

    if op_res:
        op_dr = float(op_res[0]['SUM(enty_values_DR)'] or 0)
        op_cr = float(op_res[0]['SUM(enty_values_CR)'] or 0)

    opening_balance = 0
    if basement == 'DR':
        opening_balance = op_dr - op_cr
    else: # CR
        opening_balance = op_cr - op_dr

    # 3. Fetch Transactions
    rows = db.execute_query("""
        SELECT
            entry_effective_date as date,
            entry_naration as narration,
            enty_values_DR as dr,
            enty_values_CR as cr,
            entry_jv as jv_no
        FROM entry_details
        WHERE account_name = %s AND entry_effective_date BETWEEN %s AND %s AND entry_deleted = 0
        ORDER BY entry_effective_date, id
    """, (account_name, from_date, to_date))

    # 4. Process Running Balance
    data = []

    # Add Opening Balance Row
    data.append({
        'date': from_date,
        'narration': 'Opening Balance',
        'dr': 0,
        'cr': 0,
        'balance': opening_balance,
        'is_opening': True
    })

    current_bal = opening_balance

    for r in rows:
        dr = float(r['dr'] or 0)
        cr = float(r['cr'] or 0)

        if basement == 'DR':
            current_bal = current_bal + dr - cr
        else: # CR
            current_bal = current_bal + cr - dr

        data.append({
            'date': str(r['date']),
            'narration': r['narration'],
            'dr': dr,
            'cr': cr,
            'balance': current_bal,
            'jv_no': r['jv_no'],
            'is_opening': False
        })

    return {'data': data, 'basement': basement}


# --- Trial Balance ---
@app.route('/trial_balance')
@login_required
@has_permission('Access_Reports')
def trial_balance():
    as_at_date = request.args.get('as_at_date', datetime.now().strftime('%Y-%m-%d'))
    download = request.args.get('download')

    query = """
        SELECT
            a.account_name AS AccountName,
            a.account_basment AS Basement,
            SUM(COALESCE(e.enty_values_DR, 0)) AS Debit,
            SUM(COALESCE(e.enty_values_CR, 0)) AS Credit
        FROM new_account_table a
        LEFT JOIN entry_details e ON a.account_name = e.account_name
            AND e.entry_effective_date <= %s
            AND e.entry_deleted = 0
        GROUP BY a.account_name, a.account_basment
        HAVING Debit != 0 OR Credit != 0
        ORDER BY a.account_name ASC
    """

    rows = db.execute_query(query, (as_at_date,))

    # Calculate Totals
    total_dr = sum(float(r['Debit']) for r in rows)
    total_cr = sum(float(r['Credit']) for r in rows)
    diff = abs(total_dr - total_cr)
    status = "Balanced" if diff < 0.01 else f"Out of Balance: {diff:,.2f}"
    is_balanced = diff < 0.01

    if download == 'csv':
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Account Name', 'Type', 'Debit', 'Credit'])

        for r in rows:
            cw.writerow([
                r['AccountName'],
                r['Basement'],
                f"{float(r['Debit']):.2f}",
                f"{float(r['Credit']):.2f}"
            ])

        cw.writerow([])
        cw.writerow(['', 'TOTAL', f"{total_dr:.2f}", f"{total_cr:.2f}"])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=Trial_Balance_{as_at_date}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('trial_balance.html',
                           as_at_date=as_at_date,
                           rows=rows,
                           total_dr=total_dr,
                           total_cr=total_cr,
                           status=status,
                           is_balanced=is_balanced)

# --- Supplier Aging Report ---
@app.route('/supplier_aging')
@login_required
@has_permission('Access_Reports')
def supplier_aging():
    selected_supplier = request.args.get('supplier_id')
    download = request.args.get('download')

    # Load Suppliers for Dropdown
    suppliers = db.execute_query("SELECT sup_id, supplier_name FROM suppliers WHERE Is_Suplier = 1 ORDER BY supplier_name")

    # Aging Query
    query = """
        SELECT
            s.sup_id as SupplierId,
            s.supplier_name as SupplierName,
            sid.suppliers_invoice_number as InvoiceNumber,
            sid.suppliers_invoice_date as InvoiceDate,
            sid.suppliers_invoice_final_date as FinalDate,
            sid.suppliers_invoice_total_oustanding as InvoiceTotal,
            COALESCE(sid.suppliers_invoice_total_payment, 0) as PaidAmount,
            (sid.suppliers_invoice_total_oustanding - COALESCE(sid.suppliers_invoice_total_payment, 0)) as Outstanding
        FROM suppliers_invoice_data sid
        INNER JOIN suppliers s ON sid.suppliers_invoice_buinding_supplier = s.sup_id
        WHERE s.Is_Suplier = 1
        AND sid.suppliers_oustanding_delete = 0
        AND (sid.suppliers_invoice_total_oustanding - COALESCE(sid.suppliers_invoice_total_payment, 0)) > 0
    """

    params = []
    if selected_supplier:
        query += " AND s.sup_id = %s"
        params.append(selected_supplier)

    query += " ORDER BY s.supplier_name, sid.suppliers_invoice_final_date"

    rows = db.execute_query(query, tuple(params))

    # Process Aging
    aging_data = []
    today = date.today()

    buckets = {
        'Current': 0.0,
        '1-30 Days': 0.0,
        '31-60 Days': 0.0,
        '61-90 Days': 0.0,
        'Over 90 Days': 0.0
    }

    for r in rows:
        due_date = r['FinalDate']
        # Calculate days overdue (Today - Due Date)
        # Note: If due_date is None, treat as Current or handle error. Assuming valid date.
        if isinstance(due_date, datetime):
            due_date = due_date.date()

        age_days = (today - due_date).days

        bucket = "Current"
        if age_days > 90: bucket = "Over 90 Days"
        elif age_days > 60: bucket = "61-90 Days"
        elif age_days > 30: bucket = "31-60 Days"
        elif age_days > 0: bucket = "1-30 Days"
        else: bucket = "Current"

        # In C# code:
        # if (ageDays <= 0) return "Current";
        # if (ageDays <= 30) return "1-30 Days";
        # ...
        # This means positive ageDays are overdue.

        r['AgeDays'] = age_days
        r['AgingBucket'] = bucket
        r['Outstanding'] = float(r['Outstanding'])

        buckets[bucket] += r['Outstanding']
        aging_data.append(r)

    total_outstanding = sum(r['Outstanding'] for r in aging_data)
    total_invoices = len(aging_data)
    total_suppliers = len(set(r['SupplierId'] for r in aging_data))

    # Export to CSV
    if download == 'csv':
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Supplier ID', 'Supplier Name', 'Invoice No', 'Invoice Date', 'Due Date', 'Invoice Amount', 'Paid Amount', 'Outstanding', 'Age (Days)', 'Aging Bucket'])

        for r in aging_data:
            cw.writerow([
                r['SupplierId'],
                r['SupplierName'],
                r['InvoiceNumber'],
                r['InvoiceDate'],
                r['FinalDate'],
                f"{float(r['InvoiceTotal']):.2f}",
                f"{float(r['PaidAmount']):.2f}",
                f"{r['Outstanding']:.2f}",
                r['AgeDays'],
                r['AgingBucket']
            ])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=Supplier_Aging_Report_{today}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('supplier_aging.html',
                           suppliers=suppliers,
                           selected_supplier=int(selected_supplier) if selected_supplier else None,
                           rows=aging_data,
                           buckets=buckets,
                           summary={
                               'total_outstanding': total_outstanding,
                               'total_invoices': total_invoices,
                               'total_suppliers': total_suppliers,
                               'report_date': today
                           })

# --- Supplier Aging Report ---
@app.route('/sales_summary_cashier', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def sales_summary_cashier():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    filter_type = request.args.get('filter', 'current')
    download = request.args.get('download')

    current_cashier_id = get_current_user_id()

    # 1. Fetch Current User PK (Session stores user_pk as 'id' from Login_Table)
    current_user_pk = session.get('user_pk')

    # Fetch cashier name from pose_setting_table if possible, or Login_Table
    # The C# error suggests RecodeUserId in pos_sales_invoice_01 is INT (likely Login_Table.id or pose_setting_table.Id)
    # But C# uses `control_variable.POS_User_ID` which implies it might be different from Login User.
    # However, given `current_cashier_id = get_current_user_id()` returns `session['user_id']` (User_Code e.g., 'ADM001'),
    # and the error says "Truncated incorrect DOUBLE value: 'ADM001'", it means `RecodeUserId` column is numeric.
    # We should use `session['user_pk']` (the auto-inc ID) for filtering if RecodeUserId stores the ID.

    res = db.execute_query("SELECT User_Name FROM pose_setting_table WHERE Id = %s", (current_user_pk,))
    cashier_name = res[0]['User_Name'] if res else session.get('username', 'Unknown')

    # 2. Build Query
    query = """
        SELECT
            s.Invoice_No,
            s.ItemCoude,
            s.ItemName,
            s.PaymentMethord,
            s.QuntirySale,
            s.SllingPrice,
            s.ItemPriceComen,
            s.ItemLoyalityPrice,
            s.Total_Value,
            s.AcctionDate,
            s.Revers,
            s.jv,
            s.Sales_with_market_price_Active,
            s.Sales_with_Special_price_Active,
            s.Loyalty_Price_Active,
            s.Loyalty_No,
            s.RecodeUserId,
            lt.User_Name as CashierName
        FROM pos_sales_invoice_01 s
        LEFT JOIN pose_setting_table lt ON s.RecodeUserId = lt.Id
        WHERE DATE(s.AcctionDate) = %s
        AND s.Revers = 0
    """
    params = [selected_date]

    if filter_type == 'current':
        # Use user_pk (INT) instead of User_Code (VARCHAR)
        query += " AND s.RecodeUserId = %s"
        params.append(current_user_pk)

    query += " ORDER BY s.AcctionDate DESC, s.jv DESC"

    rows = db.execute_query(query, tuple(params))

    # 3. Process Data
    sales_data = []
    total_cash = 0
    total_card = 0
    total_sales = 0

    for r in rows:
        # Calculate Actual Unit Price Logic from C#
        unit_price = r['SllingPrice']
        loyalty_no = r['Loyalty_No']

        if r['Loyalty_Price_Active'] == 1 and loyalty_no != "-1" and loyalty_no:
            unit_price = r['ItemLoyalityPrice']
        elif r['Sales_with_Special_price_Active'] == 1:
            unit_price = r['ItemPriceComen']
        elif r['Sales_with_market_price_Active'] == 1:
            unit_price = r['SllingPrice']

        r['UnitPrice'] = unit_price

        # Payment Method Text
        pm = r['PaymentMethord']
        r['PaymentMethodText'] = "Cash" if pm == 1 else "Card" if pm == 2 else "Other"

        # Aggregates
        val = float(r['Total_Value'] or 0)
        if pm == 1: total_cash += val
        elif pm == 2: total_card += val
        total_sales += val

        sales_data.append(r)

    transaction_count = len(set(r['jv'] for r in sales_data))
    cashier_count = len(set(r['RecodeUserId'] for r in sales_data))

    # 4. Export CSV
    if download == 'csv':
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Invoice No', 'Cashier ID', 'Cashier Name', 'Item Code', 'Item Name', 'Payment Method', 'Quantity', 'Unit Price', 'Total Value', 'Date', 'Time', 'Transaction No'])

        for r in sales_data:
            cw.writerow([
                r['Invoice_No'],
                r['RecodeUserId'],
                r['CashierName'],
                r['ItemCoude'],
                r['ItemName'],
                r['PaymentMethodText'],
                r['QuntirySale'],
                r['UnitPrice'],
                r['Total_Value'],
                r['AcctionDate'].strftime('%Y-%m-%d') if r['AcctionDate'] else '',
                r['AcctionDate'].strftime('%H:%M') if hasattr(r['AcctionDate'], 'strftime') else '00:00',
                r['jv']
            ])

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=Sales_Report_{selected_date}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('sales_summary_cashier.html',
                           sales_data=sales_data,
                           selected_date=selected_date,
                           filter_type=filter_type,
                           cashier_name=cashier_name,
                           summary={
                               'cash': total_cash,
                               'card': total_card,
                               'total': total_sales,
                               'transactions': transaction_count,
                               'cashiers': cashier_count,
                               'record_count': len(sales_data)
                           })

# --- POS Reversal ---
@app.route('/pos_reversal')
@login_required
@has_permission('Access_Reversals')
def pos_reversal():
    # Use PK (INT) for RecodeUserId filtering
    current_cashier_id = session.get('user_pk')
    current_date = date.today().strftime('%Y-%m-%d')

    # 1. Fetch Sales History (Grouped by JV)
    # The C# code fetches grouped by JV for current user and date
    query = """
        SELECT jv, SUM(Total_Value) as Total_payment
        FROM pos_sales_invoice_01
        WHERE RecodeUserId = %s AND AcctionDate = %s AND Revers = 0
        GROUP BY jv
        ORDER BY jv
    """
    rows = db.execute_query(query, (current_cashier_id, current_date))

    jv_list = []
    for i, r in enumerate(rows):
        jv_list.append({
            'No': i + 1,
            'jv': r['jv'],
            'Total_payment': float(r['Total_payment'] or 0)
        })

    return render_template('pos_reversal.html', jv_list=jv_list)

@app.route('/pos_reversal/get_details')
@login_required
def pos_reversal_details():
    jv = request.args.get('jv')
    if not jv: return {'error': 'No JV provided'}, 400

    # Fetch details for the text box (similar to C# logic)
    query = """
        SELECT
            Invoice_No, ItemName, QuntirySale, Total_Value
        FROM pos_sales_invoice_01
        WHERE jv = %s
    """
    rows = db.execute_query(query, (jv,))

    details_text = f"Journal Voucher No: {jv} Reversal Impact\n"
    details_text += "-" * 40 + "\n"

    for r in rows:
        details_text += f"Inv: {r['Invoice_No']} | Item: {r['ItemName']} | Qty: {r['QuntirySale']} | Val: {r['Total_Value']}\n"

    details_text += "-" * 40 + "\n"
    details_text += "Do you want to reverse this entry?"

    return {'details': details_text}

@app.route('/pos_receipt/<int:jv_no>')
@login_required
def pos_receipt(jv_no):
    # Fetch invoice items for this JV
    query = """
        SELECT
            Invoice_No, ItemName, ItemMesurmet,
            SllingPrice, ItemPriceComen, ItemLoyalityPrice,
            Sales_with_market_price_Active, Sales_with_Special_price_Active, Loyalty_Price_Active,
            Loyalty_No, PaymentMethord, QuntirySale, Total_Value,
            RecodeUserId, AcctionDate, CashAccountName
        FROM pos_sales_invoice_01
        WHERE jv = %s
    """
    rows = db.execute_query(query, (jv_no,))

    if not rows:
        return "Receipt not found", 404

    items = []
    total_sales = 0
    total_savings = 0
    original_total = 0

    invoice_no = rows[0]['Invoice_No']
    date_val = rows[0]['AcctionDate']
    cashier = rows[0]['RecodeUserId']
    loyalty_no = rows[0]['Loyalty_No']
    payment_method = rows[0]['PaymentMethord']
    is_loyalty = False

    # Determine Customer Type logic from C#
    # if(Loyality_No > 0) -> Loyality_costomer_Find = 1
    # Check if loyalty number is valid (not 0, not -1, not empty)
    if loyalty_no and str(loyalty_no) != "0" and str(loyalty_no) != "-1":
        is_loyalty = True

    for r in rows:
        qty = float(r['QuntirySale'])
        selling_price = float(r['SllingPrice'] or 0)
        special_price = float(r['ItemPriceComen'] or 0)
        loyalty_price = float(r['ItemLoyalityPrice'] or 0)

        # Calculate Active Price
        active_price = selling_price # Default

        if is_loyalty and r['Loyalty_Price_Active'] == 1:
            active_price = loyalty_price
        elif r['Sales_with_Special_price_Active'] == 1:
            active_price = special_price
        elif r['Sales_with_market_price_Active'] == 1:
            active_price = selling_price

        # Savings Calculation
        # If Special Active: Saving = Selling - Special
        # If Loyalty Active: Saving = Selling - Loyalty
        saving_per_unit = 0
        if r['Sales_with_Special_price_Active'] == 1 and not is_loyalty:
            saving_per_unit = selling_price - special_price
        elif r['Loyalty_Price_Active'] == 1 and is_loyalty:
            saving_per_unit = selling_price - loyalty_price

        # Add to lists
        line_total = active_price * qty
        line_saving = saving_per_unit * qty
        line_original = selling_price * qty

        total_sales += line_total
        total_savings += line_saving
        original_total += line_original

        items.append({
            'name': r['ItemName'],
            'qty': qty,
            'unit': r['ItemMesurmet'],
            'price': active_price,
            'total': line_total,
            'saving': line_saving
        })

    # Payment Method Text
    pm_text = "CASH"
    if payment_method == 2: pm_text = "CARD"

    return render_template('pos_receipt.html',
                           items=items,
                           invoice_no=invoice_no,
                           date=date_val,
                           cashier=cashier,
                           is_loyalty=is_loyalty,
                           loyalty_no=loyalty_no,
                           totals={
                               'subtotal': total_sales,
                               'savings': total_savings,
                               'original': original_total,
                               'final': total_sales
                           },
                           payment_method=pm_text)

@app.route('/pos_reversal/process', methods=['POST'])
@login_required
def pos_reversal_process():
    jv = request.form.get('jv')
    if not jv:
        flash('No transaction selected', 'danger')
        return redirect(url_for('pos_reversal'))

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Reverse JV Entries
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, session.get("user_pk"), datetime.utcnow().strftime("%Y-%m-%d")))

        # 2. Mark POS Customer as Reversed/Deleted
        cursor.execute("CALL POS_Customer_Delete(%s)", (jv,))

        # 3. Reverse Inventory Out (Bring items back)
        cursor.execute("CALL Inventory_Items_Revers_OUT(%s)", (jv,))

        conn.commit()
        flash(f'Transaction {jv} reversed successfully.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error reversing transaction: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('pos_reversal'))

# --- Bank Payment Reversal ---
@app.route('/bank_payment_reversal')
@login_required
@has_permission('Access_Reversals')
def bank_payment_reversal():
    # Fetch recent Bank Payments (limit to 50 for performance)
    # Using `bank_book_recod` joined with `jv_numbers` to get JV
    query = """
        SELECT
            b.id,
            b.bank_book_recod_voucher_no as Voucher,
            b.Bank_Payment_Date as Date,
            b.bank_book__accont_name as Account,
            b.bank_book__suplier_name as Supplier,
            b.bank_book__recode_cr as Amount,
            b.jv_numbers_jv_id as JV
        FROM bank_book_recod b
        WHERE b.bank_book__recode_cr > 0
        AND b.User_Revers IS NULL
        ORDER BY b.Bank_Payment_Date DESC, b.id DESC
        LIMIT 50
    """
    rows = db.execute_query(query)
    return render_template('bank_payment_reversal.html', rows=rows)

@app.route('/bank_payment_reversal/get_details')
@login_required
def bank_payment_reversal_details():
    jv_param = request.args.get('jv')
    if not jv_param: return {'error': 'No JV provided'}, 400

    jvs = [j.strip() for j in jv_param.split(',') if j.strip()]
    if not jvs: return {'error': 'No valid JVs provided'}, 400

    format_strings = ','.join(['%s'] * len(jvs))
    jv_tuple = tuple(jvs)

    # Fetch details text
    query = f"""
        SELECT
            jv_numbers_jv_id,
            suppliers_invoice_number as IV_No,
            suppliers_VAT_rate as VAT_Rate,
            cash_book_recode_cr as Paid_Amount
        FROM suppliers_invoice_data
        LEFT JOIN cash_book_recode ON suppliers_invoice_data.s_i_id = cash_book_recode_suplier_oustanding_id
        WHERE jv_numbers_jv_id IN ({format_strings})
    """
    inv_rows = db.execute_query(query, jv_tuple)

    # Pre-fetch Bank Book Record for bank payments specifically (schema variation handling)
    query_bank = f"""
        SELECT jv_numbers_jv_id, bank_book__naration, bank_book__recode_cr
        FROM bank_book_recod
        WHERE jv_numbers_jv_id IN ({format_strings})
    """
    bank_rows_all = db.execute_query(query_bank, jv_tuple)

    # Fetch GL Entries
    gl_query = f"SELECT entry_jv, account_name, enty_values_DR, enty_values_CR FROM entry_details WHERE entry_jv IN ({format_strings})"
    gl_rows = db.execute_query(gl_query, jv_tuple)

    text = ""
    for current_jv in jvs:
        jv_inv_rows = [r for r in inv_rows if str(r.get('jv_numbers_jv_id')) == current_jv]

        if not jv_inv_rows:
           bank_rows = [r for r in bank_rows_all if str(r.get('jv_numbers_jv_id')) == current_jv]
           if len(jvs) > 1 and text:
               text += f"\n"
           text += f"Bank Payment Reversal (JV: {current_jv})\n" + "-"*30 + "\n"
           for r in bank_rows:
               text += f"Narration: {r['bank_book__naration']} | Amount: {r['bank_book__recode_cr']}\n"
        else:
            if len(jvs) > 1 and text:
               text += f"\n"
            text += f"Journal Voucher {current_jv} Impact\n" + "-"*30 + "\n"
            for r in jv_inv_rows:
                text += f"Inv: {r['IV_No']} | VAT: {r['VAT_Rate']}% | Paid: {r['Paid_Amount']}\n"

        jv_gl_rows = [gl for gl in gl_rows if str(gl.get('entry_jv')) == current_jv]
        if jv_gl_rows:
            if len(jvs) > 1:
                text += f"\nGL Entries (JV: {current_jv}):\n"
            else:
                text += "\nGL Entries:\n"
            for gl in jv_gl_rows:
                text += f"{gl['account_name']}: DR {gl['enty_values_DR']} | CR {gl['enty_values_CR']}\n"

    text += "\nDo you need to reverse this entry?"

    return {'details': text.strip()}

@app.route('/bank_payment_reversal/process', methods=['POST'])
@login_required
def bank_payment_reversal_process():
    jv = request.form.get('jv')
    if not jv:
        flash('No transaction selected', 'danger')
        return redirect(url_for('bank_payment_reversal'))

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Bank Transaction Reversal (Updates Bank Book Record)
        cursor.execute("CALL `Bank_Transaction Revesale`(%s)", (jv,))

        # 2. Reverse GL Entries
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, session.get("user_pk"), datetime.utcnow().strftime("%Y-%m-%d")))

        # 3. Reverse Supplier Outstanding (Bank Version)
        cursor.execute("CALL Suplier_Oustanding_Revers_Bank(%s)", (jv,))

        conn.commit()
        flash(f'Bank Payment (JV: {jv}) reversed successfully.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error reversing bank payment: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('bank_payment_reversal'))

# --- Cash Payment Reversal (Supplier) ---
@app.route('/cash_payment_reversal')
@login_required
@has_permission('Access_Reversals')
def cash_payment_reversal():
    # Fetch recent Cash Payments (from cash_book_recode)
    # Filter where suplier_name is NOT NULL (Supplier Payments)
    query = """
        SELECT
            c.chash_book_recod_id as id,
            c.cash_book_recod_voucher_no as Voucher,
            c.Payment_Date as Date,
            c.cash_book_recode_accont_name as Account,
            c.cash_book_recode_suplier_name as Supplier,
            c.cash_book_recode_cr as Amount,
            c.jv_numbers_jv_id as JV
        FROM cash_book_recode c
        WHERE c.cash_book_recode_cr > 0
        AND c.User_Revers IS NULL
        AND c.cash_book_recode_suplier_name IS NOT NULL
        ORDER BY c.Payment_Date DESC, c.chash_book_recod_id DESC
        LIMIT 50
    """
    rows = db.execute_query(query)
    return render_template('cash_payment_reversal.html', rows=rows)

@app.route('/cash_payment_reversal/process', methods=['POST'])
@login_required
def cash_payment_reversal_process():
    jv = request.form.get('jv')
    if not jv:
        flash('No transaction selected', 'danger')
        return redirect(url_for('cash_payment_reversal'))

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Update Reversal (Cash Book)
        cursor.execute("CALL Pudate_Reversale(%s)", (jv,))

        # 2. Reverse GL Entries
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, session.get("user_pk"), datetime.utcnow().strftime("%Y-%m-%d")))

        # 3. Reverse Supplier Outstanding
        cursor.execute("CALL Suplier_Oustanding_Revers(%s)", (jv,))

        conn.commit()
        flash(f'Cash Payment (JV: {jv}) reversed successfully.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error reversing cash payment: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('cash_payment_reversal'))

# --- Direct Payment Reversal (Inventory) ---
@app.route('/direct_payment_reversal')
@login_required
@has_permission('Access_Reversals')
def direct_payment_reversal():
    # Fetch recent Direct Payments (Inventory related)
    # These usually have inventory records attached or narration implies direct purchase
    # We filter for those that have inventory records linked to this JV
    query = """
        SELECT DISTINCT
            c.chash_book_recod_id as id,
            c.cash_book_recod_voucher_no as Voucher,
            c.Payment_Date as Date,
            c.cash_book_recode_accont_name as Account,
            c.cash_book_recode_naration as Narration,
            c.cash_book_recode_cr as Amount,
            c.jv_numbers_jv_id as JV
        FROM cash_book_recode c
        JOIN inventory_recod i ON c.jv_numbers_jv_id = i.JV_No
        WHERE c.cash_book_recode_cr > 0
        AND c.User_Revers IS NULL
        ORDER BY c.Payment_Date DESC
        LIMIT 50
    """
    rows = db.execute_query(query)
    return render_template('direct_payment_reversal.html', rows=rows)

@app.route('/direct_payment_reversal/process', methods=['POST'])
@login_required
def direct_payment_reversal_process():
    jv = request.form.get('jv')
    if not jv:
        flash('No transaction selected', 'danger')
        return redirect(url_for('direct_payment_reversal'))

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Update Reversal (Cash Book)
        cursor.execute("CALL Pudate_Reversale(%s)", (jv,))

        # 2. Reverse GL Entries
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, session.get("user_pk"), datetime.utcnow().strftime("%Y-%m-%d")))

        # 3. Reverse Inventory In (Bring items out/mark deleted)
        # Note: The C# code called `Inventory_Items_Revers_IN`.
        # Logic in `Inventory_Items_Revers_IN` sets `inventory_recod_movment_out = var_In_Items`.
        # This effectively reverses the IN movement by creating an OUT movement or modifying it.
        cursor.execute("CALL Inventory_Items_Revers_IN(%s)", (jv,))

        conn.commit()
        flash(f'Direct Payment (JV: {jv}) reversed successfully.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error reversing direct payment: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('direct_payment_reversal'))

@app.route('/get_reversal_details')
@login_required
def get_reversal_details():
    jv = request.args.get('jv')
    if not jv: return {'error': 'No JV'}, 400

    query = "SELECT account_name, enty_values_DR, enty_values_CR FROM entry_details WHERE entry_jv = %s"
    rows = db.execute_query(query, (jv,))

    text = f"Journal Voucher {jv} Details:\n" + "-"*30 + "\n"
    for r in rows:
        text += f"{r['account_name']}: DR {r['enty_values_DR']} | CR {r['enty_values_CR']}\n"

    text += "\nInventory Items (if any):\n"
    inv_rows = db.execute_query("SELECT inventoy_name, inventory_recod_moument_in FROM inventory_recod WHERE JV_No = %s", (jv,))
    for r in inv_rows:
        text += f"{r['inventoy_name']}: Qty {r['inventory_recod_moument_in']}\n"

    return {'details': text}

# --- Customer Receipt (Accounts Receivable) ---
@app.route('/customer_receipt')
@login_required
@has_permission('Access_Accounting')
def customer_receipt():
    # Fetch customers with outstanding balances
    # We look at `Invoice_Oustanding` table
    query = """
        SELECT DISTINCT c.id, c.customer_name
        FROM customer c
        JOIN Invoice_Oustanding io ON c.id = io.invoice_buinding_Customer
        WHERE io.Invoice_Oustanding > 0
    """
    customers = db.execute_query(query)
    cash_accounts = db.execute_query("SELECT cash_book_account_name FROM cash_book")
    bank_accounts = db.execute_query("SELECT bank_bookcol_account_number FROM bank_book")

    return render_template('customer_receipt.html',
                           customers=customers,
                           cash_accounts=cash_accounts,
                           bank_accounts=bank_accounts,
                           today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/customer_receipt/get_outstanding')
@login_required
def get_customer_outstanding():
    customer_id = request.args.get('customer_id')
    if not customer_id: return {'error': 'No customer ID'}, 400

    query = """
        SELECT
            Id, invoice_number, invoice_date, invoice_final_date,
            invoice_total_oustanding, invoice_oustanding_Patment, Invoice_Oustanding
        FROM Invoice_Oustanding
        WHERE invoice_buinding_Customer = %s AND Invoice_Oustanding > 0
        ORDER BY invoice_date
    """
    rows = db.execute_query(query, (customer_id,))

    # Format for JSON
    data = []
    for r in rows:
        data.append({
            'id': r['Id'],
            'inv_no': r['invoice_number'],
            'date': str(r['invoice_date']),
            'due_date': str(r['invoice_final_date']),
            'total': float(r['invoice_total_oustanding']),
            'paid': float(r['invoice_oustanding_Patment']),
            'balance': float(r['Invoice_Oustanding'])
        })

    return {'invoices': data}

@app.route('/customer_receipt/get_history')
@login_required
def get_customer_receipt_history():
    customer_id = request.args.get('customer_id')
    if not customer_id: return {'error': 'No customer ID'}, 400

    # Get Customer Name
    cursor = db.get_connection().cursor()
    cursor.execute("SELECT customer_name FROM customer WHERE id = %s", (customer_id,))
    res = cursor.fetchone()
    if not res: return {'error': 'Customer not found'}, 404
    cust_name = res[0]
    cursor.close()

    # Fetch History from Cash Book
    # Grouping by JV to show single line per receipt transaction if multiple invoices paid
    # However, C# grid shows individual lines. But for printing, we need to group by JV/Receipt.
    # We will return list of receipt headers (unique by JV/Voucher)

    query = """
        SELECT
            jv_numbers_jv_id as jv_no,
            cash_book_recod_voucher_no as voucher_no,
            Payment_Date as date,
            SUM(cash_book_recode_dr) as amount,
            cash_book_recode_accont_name as account,
            cash_book_recode_naration as narration
        FROM cash_book_recode
        WHERE cash_book_recode_suplier_name = %s
        GROUP BY jv_numbers_jv_id, cash_book_recod_voucher_no, Payment_Date, cash_book_recode_accont_name, cash_book_recode_naration
        ORDER BY Payment_Date DESC
    """
    cash_rows = db.execute_query(query, (cust_name,))

    # Fetch History from Bank Book
    query_bank = """
        SELECT
            jv_numbers_jv_id as jv_no,
            bank_book_recod_voucher_no as voucher_no,
            Bank_Payment_Date as date,
            SUM(bank_book_book_recode_dr) as amount,
            bank_book__accont_name as account,
            bank_book__naration as narration
        FROM bank_book_recod
        WHERE bank_book__suplier_name = %s
        GROUP BY jv_numbers_jv_id, bank_book_recod_voucher_no, Bank_Payment_Date, bank_book__accont_name, bank_book__naration
        ORDER BY Bank_Payment_Date DESC
    """
    bank_rows = db.execute_query(query_bank, (cust_name,))

    history = []

    for r in cash_rows:
        history.append({
            'type': 'Cash',
            'jv_no': r['jv_no'],
            'voucher_no': r['voucher_no'],
            'date': str(r['date']),
            'amount': float(r['amount'] or 0),
            'account': r['account'],
            'narration': r['narration']
        })

    for r in bank_rows:
        history.append({
            'type': 'Bank',
            'jv_no': r['jv_no'],
            'voucher_no': r['voucher_no'],
            'date': str(r['date']),
            'amount': float(r['amount'] or 0),
            'account': r['account'],
            'narration': r['narration']
        })

    # Sort combined history by date desc
    history.sort(key=lambda x: x['date'], reverse=True)

    return {'history': history}

@app.route('/receipt/print/<int:jv_no>')
@login_required
def print_receipt(jv_no):
    # Determine if Cash or Bank based on JV existence in tables

    # Try Cash Book
    cash_res = db.execute_query("""
        SELECT
            c.cash_book_recod_voucher_no as voucher_no,
            c.Payment_Date as date,
            c.cash_book_recode_suplier_name as received_from,
            c.cash_book_recode_accont_name as account,
            c.cash_book_recode_naration as narration,
            SUM(c.cash_book_recode_dr) as amount,
            c.User_Enter as user_id
        FROM cash_book_recode c
        WHERE c.jv_numbers_jv_id = %s
        GROUP BY c.cash_book_recod_voucher_no, c.Payment_Date, c.cash_book_recode_suplier_name,
                 c.cash_book_recode_accont_name, c.cash_book_recode_naration, c.User_Enter
    """, (jv_no,))

    # Try Bank Book
    bank_res = db.execute_query("""
        SELECT
            b.bank_book_recod_voucher_no as voucher_no,
            b.Bank_Payment_Date as date,
            b.bank_book__suplier_name as received_from,
            b.bank_book__accont_name as account,
            b.bank_book__naration as narration,
            SUM(b.bank_book_book_recode_dr) as amount,
            b.Bank_User_Id as user_id
        FROM bank_book_recod b
        WHERE b.jv_numbers_jv_id = %s
        GROUP BY b.bank_book_recod_voucher_no, b.Bank_Payment_Date, b.bank_book__suplier_name,
                 b.bank_book__accont_name, b.bank_book__naration, b.Bank_User_Id
    """, (jv_no,))

    receipt = None
    if cash_res: receipt = cash_res[0]
    elif bank_res: receipt = bank_res[0]

    if not receipt:
        return "Receipt Not Found", 404

    # Get Invoice Details (Invoices settled by this JV)
    # We join with invoice_oustanding or check `cash_book_suplier_oustanding_id` links
    # Note: `cash_book_recode` has `cash_book_recode_suplier_oustanding_id` which links to `Invoice_Oustanding.Id`

    invoices = []
    if cash_res:
        inv_query = """
            SELECT io.invoice_number, c.cash_book_recode_dr as amount_paid
            FROM cash_book_recode c
            JOIN Invoice_Oustanding io ON c.cash_book_recode_suplier_oustanding_id = io.Id
            WHERE c.jv_numbers_jv_id = %s
        """
        invoices = db.execute_query(inv_query, (jv_no,))
    elif bank_res:
        inv_query = """
            SELECT io.invoice_number, b.bank_book_book_recode_dr as amount_paid
            FROM bank_book_recod b
            JOIN Invoice_Oustanding io ON b.bank_book__suplier_oustanding_id = io.Id
            WHERE b.jv_numbers_jv_id = %s
        """
        invoices = db.execute_query(inv_query, (jv_no,))

    # Company Info
    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    # Amount in words (Basic implementation or placeholder)
    # Ideally use a library like num2words

    return render_template('receipt_print.html',
                           receipt=receipt,
                           invoices=invoices,
                           company=company,
                           jv_no=jv_no)

@app.route('/customer_receipt/submit', methods=['POST'])
@login_required
def submit_customer_receipt():
    customer_id = request.form.get('customer_id')
    account_type = request.form.get('account_type') # 'cash' or 'bank'
    account_name = request.form.get('account_name')
    payment_date = request.form.get('payment_date')
    narration = request.form.get('narration')

    if not customer_id or not account_name:
        flash('Missing required fields', 'danger')
        return redirect(url_for('customer_receipt'))

    # Get payments
    payments = []
    total_receipt = 0

    # Iterate form keys to find 'pay_{id}'
    for key in request.form:
        if key.startswith('pay_') and request.form[key]:
            inv_id = key.split('_')[1]
            try:
                amount = float(request.form[key])
                if amount > 0:
                    payments.append({'id': inv_id, 'amount': amount})
                    total_receipt += amount
            except:
                pass

    if total_receipt <= 0:
        flash('No payment amount entered', 'warning')
        return redirect(url_for('customer_receipt'))

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Update Invoice Outstanding (Settle)
        if payments:
            # Fetch all outstanding balances in a single query
            payment_ids = [p['id'] for p in payments]
            format_strings = ','.join(['%s'] * len(payment_ids))
            cursor.execute(f"SELECT Id, invoice_oustanding_Patment FROM Invoice_Oustanding WHERE Id IN ({format_strings})", tuple(payment_ids))

            # Map fetched balances to IDs
            res = cursor.fetchall()
            current_balances = {str(row[0]): float(row[1]) for row in res}

            # Aggregate amounts per invoice in case of duplicates
            payment_totals = {}
            for p in payments:
                pid = str(p['id'])
                payment_totals[pid] = payment_totals.get(pid, 0.0) + p['amount']

            # Prepare batch update data
            update_data = []
            for pid, total_amount in payment_totals.items():
                current_paid = current_balances.get(pid)
                if current_paid is not None:
                    new_paid = current_paid + total_amount
                    update_data.append((new_paid, pid))

            # Execute batch update
            if update_data:
                cursor.executemany("UPDATE Invoice_Oustanding SET invoice_oustanding_Patment = %s WHERE Id = %s", update_data)

        # 2. Generate Receipt No
        if account_type == 'cash':
            cursor.execute("SELECT MAX(reciept_no) FROM cash_recipt WHERE likn = %s", (account_name,))
            res = cursor.fetchone()
            receipt_no = (res[0] if res and res[0] else 0) + 1
            cursor.execute("INSERT INTO cash_recipt (likn, reciept_no) VALUES (%s, %s)", (account_name, receipt_no))
        else:
            # Bank Receipt logic
            cursor.execute("SELECT MAX(reciept_no) FROM bank_ecipt WHERE link = %s", (account_name,))
            res = cursor.fetchone()
            receipt_no = (res[0] if res and res[0] else 0) + 1
            cursor.execute("INSERT INTO bank_ecipt (link, reciept_no) VALUES (%s, %s)", (account_name, receipt_no))

        # 3. Create JV
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM RECEIPT', narration))
        jv_no = cursor.lastrowid

        # 4. GL Entries
        # Debit Cash/Bank
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (account_name, total_receipt, payment_date, date.today(), narration, current_user, jv_no))

        # Credit Accounts Receivable
        # Need sub account code for customer if possible, usually stored in `sub_accont_for_new_account`
        # But simple version: just credit AR control account
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('Account Receivable', total_receipt, payment_date, date.today(), narration, current_user, jv_no))

        # 5. Record Transaction (Cash/Bank Book)
        # Using `cash_book_recode` for cash receipts or `bank_book_recod` ??
        # The schema has `cash_book_recode` with `cash_book_recode_dr` (receipt)

        # Get customer name
        cursor.execute("SELECT customer_name FROM customer WHERE id = %s", (customer_id,))
        cust_name = cursor.fetchone()[0]

        if account_type == 'cash':
            # Create a record per invoice payment or summary?
            # `Recipt.xaml.cs` does foreach item in Accont_collections
            for p in payments:
                 cursor.execute("""
                    INSERT INTO cash_book_recode (
                        cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                        cash_book_recode_naration, cash_book_recode_suplier_oustanding_id,
                        cash_book_recode_suplier_name, jv_numbers_jv_id,
                        cash_book_recod_voucher_no, User_Enter, Payment_Date
                    ) VALUES (%s, 0, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (p['amount'], account_name, narration, p['id'], cust_name, jv_no, receipt_no, current_user, payment_date))
        else:
            # Bank Recode
            for p in payments:
                cursor.execute("""
                    INSERT INTO bank_book_recod (
                        bank_book_book_recode_dr, bank_book__recode_cr, bank_book__accont_name,
                        bank_book__naration, bank_book__suplier_oustanding_id,
                        bank_book__suplier_name, jv_numbers_jv_id,
                        bank_book_recod_voucher_no, Bank_User_Id, Bank_Payment_Date
                    ) VALUES (%s, 0, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (p['amount'], account_name, narration, p['id'], cust_name, jv_no, receipt_no, current_user, payment_date))

        conn.commit()
        flash(f'Receipt processed successfully. Receipt No: {receipt_no}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error processing receipt: {str(e)}', 'danger')
        logging.error(f"Receipt Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('customer_receipt'))

# --- Profit & Loss Report ---

import ast
import operator
import re

# Safe math evaluator
def safe_eval_math(expr):
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg
    }

    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError("Only numbers are allowed")
        elif getattr(ast, 'Num', None) and isinstance(node, getattr(ast, 'Num')):
            return node.n
        elif isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(f"Unsupported mathematical operation: {node}")

    try:
        parsed = ast.parse(expr, mode='eval')
        return _eval(parsed.body)
    except Exception:
        return 0.0

def _safe_eval_expression(expr, context_vars):
    if not expr: return 0.0
    # Replace variable names (alphabetic strings) with their float values
    vars_in_expr = re.findall(r'[A-Za-z]+', expr)
    eval_str = expr
    for var in vars_in_expr:
        val = context_vars.get(var, 0.0)
        # Regex to safely replace whole words only
        eval_str = re.sub(fr'\b{var}\b', str(val), eval_str)

    # Use ast-based safe eval instead of Python's eval()
    return safe_eval_math(eval_str)

# Custom P&L Feature
@app.route('/profit_loss_custom', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def profit_loss_custom():
    formats = db.execute_query("SELECT id, Description FROM New_PL_Format")
    accounts_rows = db.execute_query("SELECT account_name FROM new_account_table WHERE (account_income = 1 OR account_expenses = 1) AND account_active = 1")
    accounts = [row['account_name'] for row in accounts_rows]
    return render_template('profit_loss_custom.html', formats=formats, accounts=accounts)

@app.route('/api/pl_custom/format', methods=['POST'])
@login_required
def pl_custom_create_format():
    data = request.json
    desc = data.get('description')
    if not desc: return {'success': False, 'error': 'Description missing'}, 400
    db.execute_query("INSERT INTO New_PL_Format (Description) VALUES (%s)", (desc,), commit=True)
    return {'success': True}

@app.route('/api/pl_custom/setup/<int:format_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def pl_custom_setup(format_id):
    if request.method == 'GET':
        rows = db.execute_query("SELECT * FROM PL_Setup WHERE PL_Report_ID = %s ORDER BY LENGTH(PL_LIne_Number), PL_LIne_Number", (str(format_id),))
        return {'success': True, 'rows': rows}

    elif request.method == 'DELETE':
        db.execute_query("DELETE FROM PL_Setup WHERE PL_Report_ID = %s", (str(format_id),), commit=True)
        return {'success': True}

    elif request.method == 'POST':
        data = request.json
        rows = data.get('rows', [])
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            conn.start_transaction()
            cursor.execute("DELETE FROM PL_Setup WHERE PL_Report_ID = %s", (str(format_id),))
            for r in rows:
                cursor.execute('''
                    INSERT INTO PL_Setup (
                        PL_Report_ID, PL_LIne_Number, PL_Text_Description, PL_Text_Colom,
                        PL_Calqulation_instraction, PL_Rasior_instraction, PL_Text_Format,
                        PL_Text_line, PL_Text_Size
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    str(format_id), r.get('PL_LIne_Number'), r.get('PL_Text_Description'), r.get('PL_Text_Colom'),
                    r.get('PL_Calqulation_instraction'), r.get('PL_Rasior_instraction'), r.get('PL_Text_Format'),
                    r.get('PL_Text_line'), r.get('PL_Text_Size')
                ))
            conn.commit()
            return {'success': True}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}, 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/pl_custom/generate', methods=['POST'])
@login_required
def pl_custom_generate():
    data = request.json
    format_id = data.get('format_id')
    prev_from = data.get('prev_from')
    prev_to = data.get('prev_to')
    curr_from = data.get('curr_from')
    curr_to = data.get('curr_to')

    rows = db.execute_query("SELECT * FROM PL_Setup WHERE PL_Report_ID = %s ORDER BY LENGTH(PL_LIne_Number), PL_LIne_Number", (str(format_id),))
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    results = []
    prev_vars = {}
    curr_vars = {}

    try:
        for r in rows:
            line_no = r['PL_LIne_Number']
            desc = r['PL_Text_Description']
            account = r['PL_Text_Colom']
            calc_instr = r['PL_Calqulation_instraction']
            ratio_instr = r['PL_Rasior_instraction']

            prev_val = 0.0
            curr_val = 0.0

            if account:
                def get_balance(start, end):
                    cursor.execute("SELECT account_basment, account_income, account_expenses FROM new_account_table WHERE account_name = %s", (account,))
                    acc_info = cursor.fetchone()
                    if not acc_info: return 0.0
                    cursor.execute('''
                        SELECT COALESCE(SUM(enty_values_DR), 0) as dr, COALESCE(SUM(enty_values_CR), 0) as cr
                        FROM entry_details
                        WHERE account_name = %s AND entry_effective_date BETWEEN %s AND %s AND entry_deleted = 0
                    ''', (account, start, end))
                    b = cursor.fetchone()
                    dr = float(b['dr'] or 0)
                    cr = float(b['cr'] or 0)
                    if acc_info['account_expenses'] == 1: return dr - cr
                    elif acc_info['account_income'] == 1: return cr - dr
                    else:
                        if acc_info['account_basment'] == 'DR': return dr - cr
                        else: return cr - dr

                prev_val = get_balance(prev_from, prev_to)
                curr_val = get_balance(curr_from, curr_to)

            if calc_instr:
                prev_val = _safe_eval_expression(calc_instr, prev_vars)
                curr_val = _safe_eval_expression(calc_instr, curr_vars)

            if line_no:
                prev_vars[line_no] = prev_val
                curr_vars[line_no] = curr_val

            diff_pct = ""
            if curr_val != 0 or prev_val != 0:
                if prev_val == 0:
                    val = ((curr_val - prev_val) / curr_val) * 100 if curr_val != 0 else 0
                else:
                    if curr_val == 0:
                        val = ((curr_val - prev_val) / prev_val) * 100
                    else:
                        val = ((curr_val - prev_val) / curr_val) * 100
                diff_pct = f"{val:.2f}"

            ratio_pct = ""
            if ratio_instr:
                r_val = _safe_eval_expression(ratio_instr, curr_vars)
                ratio_pct = f"{r_val:.2f}"

            results.append({
                'line': line_no,
                'description': desc,
                'account': account,
                'prev_val': f"{prev_val:,.2f}" if prev_val != 0 else "",
                'curr_val': f"{curr_val:,.2f}" if curr_val != 0 else "",
                'diff': diff_pct,
                'ratio': ratio_pct,
                'format': r.get('PL_Text_Format'),
                'line': r.get('PL_Text_line'),
                'size': r.get('PL_Text_Size')
            })
        return {'success': True, 'results': results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()



@app.route('/balance_sheet_custom', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def balance_sheet_custom():
    formats = db.execute_query("SELECT id, Description FROM New_BS_Format")
    accounts_rows = db.execute_query("SELECT account_name FROM new_account_table WHERE (account_assets = 1 OR account_liabilities = 1 OR account_equity = 1) AND account_active = 1")
    accounts = [row['account_name'] for row in accounts_rows]
    accounts.append("Retained earnings")
    return render_template('balance_sheet_custom.html', formats=formats, accounts=accounts)

@app.route('/api/bs_custom/format', methods=['POST'])
@login_required
def bs_custom_create_format():
    data = request.json
    desc = data.get('description')
    if not desc: return {'success': False, 'error': 'Description missing'}, 400
    db.execute_query("INSERT INTO New_BS_Format (Description) VALUES (%s)", (desc,), commit=True)
    return {'success': True}

@app.route('/api/bs_custom/setup/<int:format_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def bs_custom_setup(format_id):
    if request.method == 'GET':
        rows = db.execute_query("SELECT * FROM BS_Setup WHERE BS_Report_ID = %s ORDER BY LENGTH(BS_LIne_Number), BS_LIne_Number", (str(format_id),))
        return {'success': True, 'rows': rows}

    elif request.method == 'DELETE':
        db.execute_query("DELETE FROM BS_Setup WHERE BS_Report_ID = %s", (str(format_id),), commit=True)
        return {'success': True}

    elif request.method == 'POST':
        data = request.json
        rows = data.get('rows', [])
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            conn.start_transaction()
            cursor.execute("DELETE FROM BS_Setup WHERE BS_Report_ID = %s", (str(format_id),))
            for r in rows:
                cursor.execute('''
                    INSERT INTO BS_Setup (
                        BS_Report_ID, BS_LIne_Number, BS_Text_Description, BS_Text_Colom,
                        BS_Calqulation_instraction, BS_Text_Format, BS_Text_line, BS_Text_Size
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    str(format_id), r.get('BS_LIne_Number'), r.get('BS_Text_Description'), r.get('BS_Text_Colom'),
                    r.get('BS_Calqulation_instraction'), r.get('BS_Text_Format'), r.get('BS_Text_line'),
                    r.get('BS_Text_Size')
                ))
            conn.commit()
            return {'success': True}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}, 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/bs_custom/generate', methods=['POST'])
@login_required
def bs_custom_generate():
    data = request.json
    format_id = data.get('format_id')
    as_at_date = data.get('as_at_date')

    rows = db.execute_query("SELECT * FROM BS_Setup WHERE BS_Report_ID = %s ORDER BY LENGTH(BS_LIne_Number), BS_LIne_Number", (str(format_id),))
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    results = []
    vars_dict = {}

    try:
        for r in rows:
            line_no = r['BS_LIne_Number']
            desc = r['BS_Text_Description']
            account = r['BS_Text_Colom']
            calc_instr = r['BS_Calqulation_instraction']

            amount = 0.0

            if account:
                if account == "Retained earnings":
                    # Use existing retained earnings logic
                    amount = calculate_retained_earnings(cursor, as_at_date)
                else:
                    cursor.execute("SELECT account_basment, account_assets, account_liabilities, account_equity FROM new_account_table WHERE account_name = %s", (account,))
                    acc_info = cursor.fetchone()
                    if acc_info:
                        cursor.execute('''
                            SELECT COALESCE(SUM(enty_values_DR), 0) as dr, COALESCE(SUM(enty_values_CR), 0) as cr
                            FROM entry_details
                            WHERE account_name = %s AND entry_effective_date <= %s AND entry_deleted = 0
                        ''', (account, as_at_date))
                        b = cursor.fetchone()
                        if b:
                            dr = float(b['dr'] or 0)
                            cr = float(b['cr'] or 0)

                            if acc_info['account_assets'] == 1:
                                amount = dr - cr
                            elif acc_info['account_liabilities'] == 1 or acc_info['account_equity'] == 1:
                                amount = cr - dr
                            else:
                                if acc_info['account_basment'] == 'DR':
                                    amount = dr - cr
                                else:
                                    amount = cr - dr

            if calc_instr:
                amount = _safe_eval_expression(calc_instr, vars_dict)

            if line_no:
                vars_dict[line_no] = amount

            results.append({
                'line': line_no,
                'description': desc,
                'account': account,
                'amount': f"{amount:,.2f}" if amount != 0 else "",
                'format': r.get('BS_Text_Format'),
                'line': r.get('BS_Text_line'),
                'size': r.get('BS_Text_Size')
            })

        return {'success': True, 'results': results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

def calculate_retained_earnings(cursor, as_at_date):
    # Same logic as Balance Sheet endpoint for Retained earnings
    cursor.execute('''
        SELECT
            na.account_basment,
            COALESCE(SUM(ed.enty_values_DR), 0) as dr,
            COALESCE(SUM(ed.enty_values_CR), 0) as cr
        FROM new_account_table na
        JOIN entry_details ed ON na.account_name = ed.account_name
        WHERE (na.account_income = 1 OR na.account_expenses = 1)
          AND ed.entry_effective_date <= %s
          AND na.account_active = 1
          AND ed.entry_deleted = 0
        GROUP BY na.account_basment
    ''', (as_at_date,))

    rows = cursor.fetchall()

    total_retained_earnings = 0.0
    for row in rows:
        dr = float(row['dr'])
        cr = float(row['cr'])
        if row['account_basment'] == 'DR':
            total_retained_earnings -= (dr - cr)
        elif row['account_basment'] == 'CR':
            total_retained_earnings += (cr - dr)

    return total_retained_earnings

@app.route('/profit_loss', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Reports')
def profit_loss():
    from profit_loss_report import ProfitLossReportGenerator

    try:
        generator = ProfitLossReportGenerator(db)
        periods, report_data, default_start, default_end = generator.generate(request)
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('index'))

    return render_template('profit_loss.html',
                           periods=periods,
                           report_data=report_data,
                           default_start=default_start,
                           default_end=default_end)

# --- VAT Report (Sri Lanka Schedule 01 & 02) ---
@app.route('/vat_report', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def vat_report():
    from vat_helper import VATReportGenerator

    from_date = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))

    generator = VATReportGenerator(db, from_date, to_date)

    if not generator.check_vat_registered():
        flash("Company is not VAT Registered. Please enable VAT in Company Profile to view reports.", "warning")
        return render_template('vat_report.html', vat_enabled=False)

    report_data = generator.generate()
    return render_template('vat_report.html', **report_data)

# --- POS Settings ---
@app.route('/pos_settings', methods=['GET', 'POST'])
@login_required
@has_permission('Access_POS')
def pos_settings():
    if request.method == 'POST':
        user_id = request.form.get('user_id')

        # General Settings
        location = request.form.get('location')
        card_ac = request.form.get('card_ac')
        cash_ac = request.form.get('cash_ac')

        # Pricing Settings
        market_price = 1 if request.form.get('market_price') else 0
        special_price = 1 if request.form.get('special_price') else 0
        loyalty_price = 1 if request.form.get('loyalty_price') else 0
        vat_enable = 1 if request.form.get('vat_enable') else 0

        # Messages
        footer = request.form.get('footer_msg')
        top = request.form.get('top_msg')

        # Image Handling
        import base64
        img_data = None
        if 'receipt_logo' in request.files:
            file = request.files['receipt_logo']
            if file.filename != '':
                img_data = file.read() # Store as bytes in BLOB

        try:
            if not user_id:
                flash('User ID missing', 'danger')
                return redirect(url_for('pos_settings'))

            # Update Query
            query = """
                UPDATE pose_setting_table SET
                    Select_Inventry_Location=%s, Card_Control_AC=%s, Cash_Account=%s,
                    Sales_with_market_price=%s, Sales_with_Special_price=%s, Loyalty_Price=%s, VAT_Enable=%s,
                    Footer_Message=%s, Top_Message=%s
            """
            params = [location, card_ac, cash_ac, market_price, special_price, loyalty_price, vat_enable, footer, top]

            if img_data:
                query += ", Image=%s"
                params.append(img_data)

            query += " WHERE Id=%s"
            params.append(user_id)

            db.execute_query(query, tuple(params), commit=True)
            flash('POS Settings updated successfully.', 'success')

        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'danger')

        return redirect(url_for('pos_settings', user_id=user_id))

    # GET
    # 1. Fetch all POS users for dropdown
    pos_users = db.execute_query("SELECT Id, User_Name FROM pose_setting_table")

    # 2. Determine Selected User
    selected_user_id = request.args.get('user_id')
    current_settings = {}

    if pos_users:
        if not selected_user_id:
            # Default to first user found or try to match current session user
            # Try matching session username first
            session_username = session.get('username')
            match = next((u for u in pos_users if u['User_Name'] == session_username), None)
            if match:
                selected_user_id = match['Id']
            else:
                selected_user_id = pos_users[0]['Id']

        # Fetch settings for selected user
        res = db.execute_query("SELECT * FROM pose_setting_table WHERE Id = %s", (selected_user_id,))
        if res:
            current_settings = res[0]
            # Handle Image for Display (Convert bytes to base64)
            if current_settings.get('Image'):
                import base64
                current_settings['ImageBase64'] = base64.b64encode(current_settings['Image']).decode('utf-8')

    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")
    accounts = db.execute_query("SELECT account_name FROM new_account_table") # For Card/Cash selection

    return render_template('pos_settings.html',
                           settings=current_settings,
                           pos_users=pos_users,
                           selected_user_id=int(selected_user_id) if selected_user_id else 0,
                           locations=locations,
                           accounts=accounts)

@app.route('/add_pos_user', methods=['POST'])
@login_required
@has_permission('Access_POS')
def add_pos_user():
    username = request.form.get('username')
    password = request.form.get('password')
    mobile = request.form.get('mobile')

    if not username or not password:
        flash('Username and Password are required', 'danger')
        return redirect(url_for('pos_settings'))

    try:
        # Check duplicate
        exists = db.execute_query("SELECT Id FROM pose_setting_table WHERE User_Name = %s", (username,))
        if exists:
            flash('Username already exists', 'danger')
            return redirect(url_for('pos_settings'))

        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash(password)
        db.execute_query("""
            INSERT INTO pose_setting_table (Id, User_Name, Password, Mobile_Number)
            VALUES (0, %s, %s, %s)
        """, (username, pw_hash, mobile), commit=True)

        flash(f'New Cashier {username} registered successfully', 'success')

    except Exception as e:
        flash(f'Error adding cashier: {str(e)}', 'danger')

    return redirect(url_for('pos_settings'))

# --- Point of Sale (POS) ---
@app.route('/pos', methods=['GET'])
@login_required
@has_permission('Access_POS')
def pos():
    return render_template('pos.html')

@app.route('/api/pos/login', methods=['POST'])
def pos_api_login():
    data = request.json or {}
    company_name = data.get('company_name')
    username = data.get('username')
    password = data.get('password')

    if not company_name or not username or not password:
        return {'success': False, 'error': 'Company Name, Username, and Password are required'}, 400

    try:
        master_user_res = master_db.execute_query('''
            SELECT t.db_name
            FROM tenants t
            WHERE t.company_name = %s
        ''', (company_name,))

        if master_user_res:
            tenant_db_name = master_user_res[0]['db_name']
        else:
            return {'success': False, 'error': 'Company not found'}, 404
    except Exception as e:
        tenant_db_name = db.db_name

    conn = None
    cursor = None

    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        from database import is_safe_db_name
        if tenant_db_name and is_safe_db_name(tenant_db_name):
            cursor.execute(f"USE `{tenant_db_name}`")

        cursor.execute("SELECT * FROM pose_setting_table WHERE User_Name = %s", (username,))
        users = cursor.fetchall()

        if not users:
            return {'success': False, 'error': 'Invalid username or password'}, 401

        user = users[0]

        if user.get('is_locked'):
            return {'success': False, 'error': 'Account locked due to too many failed attempts. Contact admin.'}, 403

        stored_password = user['Password']

        verified = False
        from werkzeug.security import check_password_hash, generate_password_hash
        try:
            if stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:'):
                if check_password_hash(stored_password, password):
                    verified = True
            elif stored_password == password:
                verified = True
                new_hash = generate_password_hash(password)
                cursor.execute("UPDATE pose_setting_table SET Password = %s WHERE Id = %s", (new_hash, user['Id']))
                conn.commit()
        except Exception:
            if stored_password == password:
                verified = True

        if not verified:
            fails = user.get('failed_attempts', 0) + 1
            if fails >= 3:
                cursor.execute("UPDATE pose_setting_table SET failed_attempts = %s, is_locked = 1 WHERE Id = %s", (fails, user['Id']))
                conn.commit()
                return {'success': False, 'error': 'Account locked due to too many failed attempts. Contact admin.'}, 403
            else:
                cursor.execute("UPDATE pose_setting_table SET failed_attempts = %s WHERE Id = %s", (fails, user['Id']))
                conn.commit()
                return {'success': False, 'error': 'Invalid username or password'}, 401

        # Successful login, reset attempts
        cursor.execute("UPDATE pose_setting_table SET failed_attempts = 0 WHERE Id = %s", (user['Id'],))
        conn.commit()

        session['db_name'] = tenant_db_name
        session['username'] = username
        session['user_id'] = user['User_Name']
        session['user_pk'] = user['Id']

        cursor.execute('''
            SELECT
                i.id, i.inventoy_name, i.inventoy_code, i.inventoy_bach_code, i.inventoy_items_messurment_unit,
                p.inventory_price_selling, p.inventory_price_profit_marging_comen,
                p.inventory_price_for_Loyality_customer, p.inventory_price_purcharsing, i.expiry_date
            FROM inventoy_items i
            LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        ''')
        items = cursor.fetchall()

        response_items = []
        for r in items:
            response_items.append({
                'id': r['id'],
                'name': r['inventoy_name'],
                'code': r['inventoy_code'],
                'barcode': r['inventoy_bach_code'],
                'unit': r['inventoy_items_messurment_unit'],
                'price_market': r['inventory_price_selling'],
                'price_special': r['inventory_price_profit_marging_comen'],
                'price_loyalty': r['inventory_price_for_Loyality_customer'],
                'price_cost': r['inventory_price_purcharsing'],
                'expiry_date': str(r.get('expiry_date')) if r.get('expiry_date') else None
            })

        return {
            'success': True,
            'settings': {
                'location': user['Select_Inventry_Location'],
                'card_ac': user['Card_Control_AC'],
                'cash_ac': user['Cash_Account'],
                'market_price': user['Sales_with_market_price'],
                'special_price': user['Sales_with_Special_price'],
                'loyalty_price': user['Loyalty_Price'],
                'vat_enable': user['VAT_Enable'],
                'footer': user['Footer_Message'],
                'top': user['Top_Message']
            },
            'items': response_items,
            'db_name': tenant_db_name
        }

    except Exception as e:
        import logging
        logging.error(f"POS Login Error: {e}")
        return {'success': False, 'error': 'Database error occurred'}, 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()




# --- POS Web Login with Device Fingerprinting & 2FA ---
def send_sms_otp(mobile, code):
    url = "https://app.notify.lk/api/v1/send"
    params = {
        'user_id': os.getenv('NOTIFY_USER_ID', '13120'),
        'api_key': os.getenv('NOTIFY_API_KEY'),
        'sender_id': os.getenv('NOTIFY_SENDER_ID', 'The Bunker'),
        'to': mobile,
        'message': f"Your POS login verification code is: {code}"
    }

    if not params['api_key']:
        logging.error("NOTIFY_API_KEY is not set. Skipping SMS delivery.")
        return

    try:
        requests.get(url, params=params, timeout=5)
    except Exception as e:
        logging.error(f"Failed to send SMS: {e}")

@app.route('/pos_login', methods=['GET', 'POST'])
def pos_web_login():
    if request.method == 'GET':
        return render_template('pos_login.html')

    company_name = request.form.get('company_name')
    username = request.form.get('username')
    password = request.form.get('password')

    if not company_name or not username or not password:
        flash('Company Name, Username, and Password are required', 'danger')
        return redirect(url_for('pos_web_login'))

    # Locate DB from company name in master DB
    try:
        master_user_res = master_db.execute_query('''
            SELECT t.db_name
            FROM tenants t
            WHERE t.company_name = %s
        ''', (company_name,))
        if master_user_res:
            tenant_db_name = master_user_res[0]['db_name']
        else:
            flash('Company not found', 'danger')
            return redirect(url_for('pos_web_login'))
    except Exception as e:
        tenant_db_name = db.db_name

    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        from database import is_safe_db_name
        if tenant_db_name and is_safe_db_name(tenant_db_name):
            cursor.execute(f"USE `{tenant_db_name}`")

        cursor.execute("SELECT * FROM pose_setting_table WHERE User_Name = %s", (username,))
        users = cursor.fetchall()

        if not users:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('pos_web_login'))

        user = users[0]

        if user.get('is_locked'):
            flash('Account locked due to too many failed attempts. Contact admin.', 'danger')
            return redirect(url_for('pos_web_login'))

        stored_password = user['Password']
        verified = False
        try:
            if stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:'):
                if check_password_hash(stored_password, password):
                    verified = True
            elif stored_password == password:
                verified = True
                new_hash = generate_password_hash(password)
                cursor.execute("UPDATE pose_setting_table SET Password = %s WHERE Id = %s", (new_hash, user['Id']))
                conn.commit()
        except Exception:
            if stored_password == password:
                verified = True

        if not verified:
            fails = user.get('failed_attempts', 0) + 1
            if fails >= 3:
                cursor.execute("UPDATE pose_setting_table SET failed_attempts = %s, is_locked = 1 WHERE Id = %s", (fails, user['Id']))
                conn.commit()
                flash('Account locked due to too many failed attempts. Contact admin.', 'danger')
            else:
                cursor.execute("UPDATE pose_setting_table SET failed_attempts = %s WHERE Id = %s", (fails, user['Id']))
                conn.commit()
                flash('Invalid username or password', 'danger')
            return redirect(url_for('pos_web_login'))

        # Successful auth -> Reset failed attempts
        cursor.execute("UPDATE pose_setting_table SET failed_attempts = 0 WHERE Id = %s", (user['Id'],))
        conn.commit()

        # Check Device Fingerprint
        ip_address = request.remote_addr
        user_agent = request.user_agent.string

        cursor.execute("SELECT * FROM pos_user_devices WHERE user_id = %s", (user['Id'],))
        all_devices = cursor.fetchall()

        device = next((d for d in all_devices if d['ip_address'] == ip_address and d['user_agent'] == user_agent), None)

        if not all_devices:
            # Very first login - register device seamlessly
            cursor.execute("INSERT INTO pos_user_devices (user_id, ip_address, user_agent, last_login) VALUES (%s, %s, %s, %s)",
                           (user['Id'], ip_address, user_agent, datetime.now()))
            conn.commit()
        elif not device:
            # New device but user has previous devices - Require 2FA
            otp = ''.join(random.choices(string.digits, k=6))
            expires = datetime.now() + timedelta(minutes=10)
            cursor.execute("INSERT INTO pos_2fa_codes (user_id, code, expires_at) VALUES (%s, %s, %s)", (user['Id'], otp, expires))
            conn.commit()

            # Send SMS
            mobile = user.get('Mobile_Number')
            if mobile:
                send_sms_otp(mobile, otp)
            else:
                logging.error(f"Cannot send 2FA SMS for User {user['Id']} because Mobile_Number is NULL.")

            session['pending_pos_user_id'] = user['Id']
            session['pending_pos_company'] = company_name
            return render_template('pos_2fa.html')
        else:
            # Existing verified device
            cursor.execute("UPDATE pos_user_devices SET last_login = %s WHERE id = %s", (datetime.now(), device['id']))
            conn.commit()

        if user.get('must_change_password'):
            session['pending_pos_user_id'] = user['Id']
            session['pending_pos_company'] = company_name
            return render_template('pos_reset_password.html')

        # Final Login Success
        session['db_name'] = tenant_db_name
        session['username'] = username
        session['user_id'] = user['User_Name']
        session['user_pk'] = user['Id']

        return redirect(url_for('pos'))

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/pos_verify_2fa', methods=['POST'])
def pos_verify_2fa():
    user_id = session.get('pending_pos_user_id')
    company_name = session.get('pending_pos_company')
    otp = request.form.get('otp')

    if not user_id or not company_name:
        flash('Session expired or invalid.', 'danger')
        return redirect(url_for('pos_web_login'))

    # Needs Tenant DB connection again to verify
    try:
        master_user_res = master_db.execute_query('SELECT db_name FROM tenants WHERE company_name = %s', (company_name,))
        tenant_db_name = master_user_res[0]['db_name'] if master_user_res else db.db_name
    except:
        tenant_db_name = db.db_name

    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from database import is_safe_db_name
        if tenant_db_name and is_safe_db_name(tenant_db_name):
            cursor.execute(f"USE `{tenant_db_name}`")

        cursor.execute("SELECT * FROM pos_2fa_codes WHERE user_id = %s AND code = %s AND is_used = 0 AND expires_at > %s", (user_id, otp, datetime.now()))
        valid_code = cursor.fetchone()

        if valid_code:
            # Mark used
            cursor.execute("UPDATE pos_2fa_codes SET is_used = 1 WHERE id = %s", (valid_code['id'],))

            # Register device
            ip_address = request.remote_addr
            user_agent = request.user_agent.string
            cursor.execute("INSERT INTO pos_user_devices (user_id, ip_address, user_agent, last_login) VALUES (%s, %s, %s, %s)", (user_id, ip_address, user_agent, datetime.now()))

            # Fetch User to setup session
            cursor.execute("SELECT * FROM pose_setting_table WHERE Id = %s", (user_id,))
            user = cursor.fetchone()
            conn.commit()

            # Since this is a new device, force password change immediately
            cursor.execute("UPDATE pose_setting_table SET must_change_password = 1 WHERE Id = %s", (user_id,))
            conn.commit()

            return render_template('pos_reset_password.html')
        else:
            flash('Invalid or expired code.', 'danger')
            return render_template('pos_2fa.html')
    finally:
        cursor.close()
        conn.close()

@app.route('/pos_reset_password', methods=['POST'])
def pos_reset_password():
    from werkzeug.security import generate_password_hash
    user_id = session.get('pending_pos_user_id')
    company_name = session.get('pending_pos_company')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not user_id or not company_name:
        flash('Session expired or invalid.', 'danger')
        return redirect(url_for('pos_web_login'))

    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('pos_reset_password.html')

    try:
        master_user_res = master_db.execute_query('SELECT db_name FROM tenants WHERE company_name = %s', (company_name,))
        tenant_db_name = master_user_res[0]['db_name'] if master_user_res else db.db_name
    except:
        tenant_db_name = db.db_name

    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        from database import is_safe_db_name
        if tenant_db_name and is_safe_db_name(tenant_db_name):
            cursor.execute(f"USE `{tenant_db_name}`")

        new_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE pose_setting_table SET Password = %s, must_change_password = 0 WHERE Id = %s", (new_hash, user_id))

        cursor.execute("SELECT * FROM pose_setting_table WHERE Id = %s", (user_id,))
        user = cursor.fetchone()
        conn.commit()

        session['db_name'] = tenant_db_name
        session['username'] = user['User_Name']
        session['user_id'] = user['User_Name']
        session['user_pk'] = user['Id']

        session.pop('pending_pos_user_id', None)
        session.pop('pending_pos_company', None)

        flash('Password updated successfully.', 'success')
        return redirect(url_for('pos'))
    finally:
        cursor.close()
        conn.close()


@app.route('/api/pos/settings', methods=['GET'])
@login_required
def pos_api_settings():
    username = session.get('username')

    # Verify against pose_setting_table
    users = db.execute_query("SELECT * FROM pose_setting_table WHERE User_Name = %s", (username,))

    if users:
        settings = users[0]
        return {
            'success': True,
            'settings': {
                'location': settings['Select_Inventry_Location'],
                'card_ac': settings['Card_Control_AC'],
                'cash_ac': settings['Cash_Account'],
                'market_price': settings['Sales_with_market_price'],
                'special_price': settings['Sales_with_Special_price'],
                'loyalty_price': settings['Loyalty_Price'],
                'vat_enable': settings['VAT_Enable'],
                'footer': settings['Footer_Message'],
                'top': settings['Top_Message']
            }
        }

    return {'success': False, 'error': 'POS settings not found for current user'}

@app.route('/api/pos/items', methods=['GET'])
@pos_login_required
def pos_api_items():
    # Fetch all active items with prices for caching
    query = """
        SELECT
            i.id, i.inventoy_name, i.inventoy_code, i.inventoy_bach_code, i.inventoy_items_messurment_unit,
            p.inventory_price_selling, p.inventory_price_profit_marging_comen,
            p.inventory_price_for_Loyality_customer, p.inventory_price_purcharsing, i.expiry_date
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        WHERE i.active = 1
    """
    rows = db.execute_query(query)

    items = []
    for r in rows:
        items.append({
            'id': r['id'],
            'name': r['inventoy_name'],
            'code': r['inventoy_code'],
            'batch_code': r['inventoy_bach_code'],
            'unit': r['inventoy_items_messurment_unit'],
            'price_market': float(r['inventory_price_selling'] or 0),
            'price_special': float(r['inventory_price_profit_marging_comen'] or 0),
            'price_loyalty': float(r['inventory_price_for_Loyality_customer'] or 0),
            'cost': float(r['inventory_price_purcharsing'] or 0),
            'expiry_date': str(r.get('expiry_date')) if r.get('expiry_date') else None
        })
    return json.dumps(items)

@app.route('/api/pos/customers', methods=['GET'])
@pos_login_required
def pos_api_customers():
    # Fetch customers for caching
    query = "SELECT id, customer_name, Mobile_nimber FROM customer WHERE Compay_Or_Not = 0 OR Compay_Or_Not IS NULL"
    rows = db.execute_query(query)

    custs = []
    for r in rows:
        custs.append({
            'id': r['id'],
            'name': r['customer_name'],
            'mobile': r['Mobile_nimber']
        })
    return json.dumps(custs)

@app.route('/api/pos/add_loyalty_customer', methods=['POST'])
@login_required
def pos_api_add_loyalty_customer():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    email = data.get('email', '')
    billing_address = data.get('billing_address', '')
    delivery_address = data.get('delivery_address', '')
    amount_paid = data.get('amount_paid', 0)

    if not name or not mobile:
        return {'success': False, 'error': 'Name and Mobile Number are required'}

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Determine max id to generate customer_code
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM customer")
        max_id = cursor.fetchone()[0]
        customer_code = max_id + 60001

        query = """
            INSERT INTO customer (
                customer_name, customer_code, customer_Billing_Address, costomer_Delivery_Address,
                e_mail, coustomer_credit_limit, Mobile_nimber, Is_Loyality_Customer, Compay_Or_Not,
                Create_Date, Paid_Amountl, Create_Cashiyer
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Note: Depending on the schema, Paid_Amountl might be a string or number,
        # and Is_Loyality_Customer might be a boolean/tinyint.
        cursor.execute(query, (
            name, str(customer_code), billing_address, delivery_address,
            email, 1, mobile, 1, 0,
            datetime.utcnow().strftime("%Y-%m-%d"), amount_paid, 0
        ))

        conn.commit()

        # Fetch the new customer details to return
        new_customer_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return {
            'success': True,
            'customer': {
                'id': new_customer_id,
                'name': name,
                'mobile': mobile
            }
        }
    except Exception as e:
        if conn:
            conn.rollback()
        return {'success': False, 'error': str(e)}

def _generate_pos_invoice_number(cursor, today_date):
    """Helper to generate a new POS Invoice Number."""
    cursor.execute("INSERT INTO pos_invoice_no (IV_No) VALUES ('')")
    last_id = cursor.lastrowid
    invoice_no = f"{today_date.year}POS-{last_id}"
    cursor.execute("UPDATE pos_invoice_no SET IV_No = %s WHERE Id = %s", (invoice_no, last_id))
    return invoice_no

def _process_pos_cart_items(cursor, cart, settings, current_user, current_user_pk, payment, customer, invoice_no, jv_no, today_date):
    """Helper to process items, yielding total sales and total costs, and executing batch inserts."""
    total_sale_value = 0
    total_cost_value = 0
    pos_sales_params = []
    inventory_params = []
    action_date_str = today_date.strftime('%Y-%m-%d')

    for item in cart:
        qty = parse_float(item.get('qty', 0))
        cost = parse_float(item.get('cost', 0))
        total = parse_float(item.get('total', 0))

        # If the frontend passes 'cost' as the total cost already, multiplying it by qty squares it.
        # But we assume 'cost' is unit cost based on pos.html. Just to be safe and match legacy C#:
        # Wait, if pos.html sends unit cost, then unit_cost * qty is correct.
        total_item_cost = cost * qty

        total_sale_value += total
        total_cost_value += total_item_cost

        # Prepare pos_sales_invoice_01 params
        pos_sales_params.append((
            item.get('code'), item.get('name'), item.get('unit'),
            item.get('price_market'), item.get('price_special'), item.get('price_loyalty'),
            settings.get('market_active', 0), settings.get('special_active', 0), settings.get('loyalty_active', 0),
            current_user_pk, settings.get('location'), action_date_str, qty, cost,
            payment.get('method'), settings.get('cash_ac'), settings.get('bank_ac'),
            invoice_no, customer.get('loyalty_no', 0), total, jv_no
        ))

        # Prepare Inventory Movement OUT params.
        # Legacy C# app and submit_invoice BOTH expect total cost in inventory_recod_unit_price
        inventory_params.append((
            item.get('name'), item.get('code'), today_date, qty, item.get('unit'), total_item_cost,
            current_user, jv_no, settings.get('location')
        ))

    # Batch Insert into pos_sales_invoice_01
    if pos_sales_params:
        cursor.executemany("""
            INSERT INTO pos_sales_invoice_01 (
                ItemCoude, ItemName, ItemMesurmet, SllingPrice, ItemPriceComen, ItemLoyalityPrice,
                Sales_with_market_price_Active, Sales_with_Special_price_Active, Loyalty_Price_Active,
                RecodeUserId, Location, AcctionDate, QuntirySale, InventoryCost, PaymentMethord,
                CashAccountName, BankAccountName, Invoice_No, Loyalty_No, Total_Value, jv, Revers
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        """, pos_sales_params)

    # Batch Insert into inventory_recod
    if inventory_params:
        cursor.executemany("""
            INSERT INTO inventory_recod (
                inventoy_name, inventoy_code, inventory_recod_action_date,
                inventory_recod_moument_in, inventory_recod_movment_out,
                inventory_recod_mesrmet, inventory_recod_unit_price,
                inventory_recod_account, inventory_recod_user_id, JV_No,
                inventory_recod_location
            ) VALUES (%s, %s, %s, 0, %s, %s, %s, 'Cost Of Goods Sold', %s, %s, %s)
        """, inventory_params)

    return total_sale_value, total_cost_value

def _post_pos_gl_entries(cursor, settings, payment, total_sale_value, total_cost_value, today_date, invoice_no, current_user_pk, jv_no):
    """Helper to post corresponding General Ledger entries for POS sale."""
    # Debit Cash/Bank
    ac_name = settings.get('cash_ac') if payment.get('method') == 1 else settings.get('bank_ac')
    cursor.execute("""
        INSERT INTO entry_details (
            account_name, enty_values_DR, entry_effective_date, entry_create_date,
            entry_naration, entry_create_user, entry_jv
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (ac_name, total_sale_value, today_date, today_date, f"POS Sale {invoice_no}", current_user_pk, jv_no))

    # Calculate VAT if enabled
    vat_enabled = settings.get('vat_enable') == 1
    vat_amount = 0
    net_sales = total_sale_value

    if vat_enabled:
        # Fetch VAT Rate from Tax Settings if exists, else 18%
        cursor.execute("SELECT rate FROM tax_rates WHERE tax_name LIKE '%VAT%' AND active=1 LIMIT 1")
        res_vat = cursor.fetchone()
        vat_rate = res_vat[0] if res_vat else 18.0

        net_sales = total_sale_value / (1 + (vat_rate / 100))
        vat_amount = total_sale_value - net_sales

    # Credit Sales Account (Net)
    cursor.execute("""
        INSERT INTO entry_details (
            account_name, enty_values_CR, entry_effective_date, entry_create_date,
            entry_naration, entry_create_user, entry_jv
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, ('Sales', net_sales, today_date, today_date, f"POS Sale {invoice_no}", current_user_pk, jv_no))

    # Credit VAT Control (If VAT > 0)
    if vat_amount > 0:
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('VAT Control', vat_amount, today_date, today_date, f"VAT on POS Sale {invoice_no}", current_user_pk, jv_no))

    # Cost of Goods Sold (DR COGS, CR Inventory)
    if total_cost_value > 0:
        # Debit Cost Of Goods Sold
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('Cost Of Goods Sold', total_cost_value, today_date, today_date, f"POS Sale {invoice_no} (COGS)", current_user_pk, jv_no))

        # Credit Inventory
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('Inventory', total_cost_value, today_date, today_date, f"POS Sale {invoice_no} (COGS)", current_user_pk, jv_no))


@app.route('/pos/submit_sale', methods=['POST'])
@app.route('/api/pos/submit', methods=['POST'])
@login_required
def submit_pos_sale():
    data = request.json

    # Client is expected to save JSON locally as per requirement before sending

    cart = data.get('cart', [])
    payment = data.get('payment', {})
    customer = data.get('customer', {})
    settings = data.get('settings', {})

    if not cart: return {'error': 'Cart is empty'}, 400

    current_user = get_current_user_id()
    current_user_pk = get_current_user_pk()
    today_date = date.today()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Generate Invoice No
        invoice_no = _generate_pos_invoice_number(cursor, today_date)

        # 2. Create JV
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM POS', f"POS Sale {invoice_no}"))
        jv_no = cursor.lastrowid

        # 3. Process Cart Items
        total_sale_value, total_cost_value = _process_pos_cart_items(
            cursor, cart, settings, current_user, current_user_pk, payment, customer, invoice_no, jv_no, today_date
        )

        # 4. GL Entries
        _post_pos_gl_entries(
            cursor, settings, payment, total_sale_value, total_cost_value, today_date, invoice_no, current_user_pk, jv_no
        )

        conn.commit()
        return {'success': True, 'invoice_no': invoice_no, 'jv': jv_no}

    except Exception as e:
        conn.rollback()
        logging.error(f"POS Error: {e}")
        return {'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

def run_schema_migrations(target_db_conn=None):
    """Checks and updates database schema for new features."""
    conn = target_db_conn if target_db_conn else db.get_connection()
    if not conn: return
    migrations.run_migrations(conn)
    try:
        cursor = conn.cursor()

        # 0. Migration Table
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS migrations (id INT AUTO_INCREMENT PRIMARY KEY, migration_name VARCHAR(255) UNIQUE NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        except Exception as e:
            logging.error(f"Error creating migrations table: {e}")

        # Helper to check/record migration
        def is_migration_applied(name):
            try:
                cursor.execute("SELECT id FROM migrations WHERE migration_name = %s", (name,))
                return cursor.fetchone() is not None
            except:
                return False

        def record_migration(name):
            try:
                cursor.execute("INSERT INTO migrations (migration_name) VALUES (%s)", (name,))
                conn.commit()
            except Exception as e:
                logging.error(f"Error recording migration {name}: {e}")

        # 1. Password Hashing Migration (Modify VARCHAR Length)
        # Login_Table
        cursor.execute("SHOW COLUMNS FROM Login_Table LIKE 'Password'")
        res = cursor.fetchone()
        if res:
            # res structure depends on driver, usually tuple
            # Field, Type, Null, Key, Default, Extra
            # Type is index 1
            col_type = res[1]
            # Check if it is varchar(45) or similar short length
            if b'varchar(45)' in col_type.lower() or 'varchar(45)' in col_type.lower():
                print("Migrating: Extending Login_Table Password column to 255 chars")
                cursor.execute("ALTER TABLE Login_Table MODIFY COLUMN Password VARCHAR(255)")

        # pose_setting_table
        cursor.execute("SHOW TABLES LIKE 'pose_setting_table'")
        if cursor.fetchone():
            cursor.execute("SHOW COLUMNS FROM pose_setting_table LIKE 'Password'")
            res_pos = cursor.fetchone()
            if res_pos:
                col_type_pos = res_pos[1]
                if b'varchar(45)' in col_type_pos.lower() or 'varchar(45)' in col_type_pos.lower():
                    print("Migrating: Extending pose_setting_table Password column to 255 chars")
                    cursor.execute("ALTER TABLE pose_setting_table MODIFY COLUMN Password VARCHAR(255)")

        # 1b. User_Rights Columns
        cursor.execute("SHOW COLUMNS FROM User_Rights")
        columns = [row[0] for row in cursor.fetchall()]

        new_columns = [
            'Access_Inventory', 'Access_POS', 'Access_Accounting', 'Access_Reports', 'Access_Reversals'
        ]

        for col in new_columns:
            if col not in columns:
                logging.info(f"Migrating: Adding {col} to User_Rights")
                cursor.execute(f"ALTER TABLE User_Rights ADD COLUMN {col} TINYINT DEFAULT 0")

        # 1b. Password Column Expansion
        # Login_Table
        cursor.execute("SHOW COLUMNS FROM Login_Table LIKE 'Password'")
        res = cursor.fetchone()
        if res:
            # res format: ('Password', 'varchar(45)', ...)
            col_type = res[1].lower()
            if 'varchar(45)' in col_type:
                print("Migrating: Expanding Password column in Login_Table to VARCHAR(255)")
                cursor.execute("ALTER TABLE Login_Table MODIFY COLUMN Password VARCHAR(255)")

        # Pose_Setting_Table
        cursor.execute("SHOW TABLES LIKE 'pose_setting_table'")
        if cursor.fetchone():
            cursor.execute("SHOW COLUMNS FROM pose_setting_table LIKE 'Password'")
            res = cursor.fetchone()
            if res:
                col_type = res[1].lower()
                if 'varchar(45)' in col_type:
                    print("Migrating: Expanding Password column in pose_setting_table to VARCHAR(255)")
                    cursor.execute("ALTER TABLE pose_setting_table MODIFY COLUMN Password VARCHAR(255)")

        # 2. Currency Table
        cursor.execute("SHOW TABLES LIKE 'currency_table'")
        if not cursor.fetchone():
            logging.info("Migrating: Creating currency_table")
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

        # 3. New Account Table Columns
        if not is_migration_applied('add_currency_code_to_new_account'):
            try:
                # Check column existence just in case, or use ADD COLUMN IF NOT EXISTS (MariaDB 10.2+)
                # Standard MySQL doesn't support IF NOT EXISTS in ALTER TABLE nicely without stored proc.
                # But since we track migration_name, we assume if not applied, we run it.
                # Wrap in try-except to handle "Duplicate column" if manually added.
                cursor.execute("ALTER TABLE new_account_table ADD COLUMN currency_code VARCHAR(10) DEFAULT 'LKR'")
                record_migration('add_currency_code_to_new_account')
                logging.info("Migrated: add_currency_code_to_new_account")
            except Exception as e:
                if "Duplicate column" in str(e) or "1060" in str(e):
                    record_migration('add_currency_code_to_new_account')
                else:
                    logging.error(f"Migration failed: {e}")

        # 4. Inventory Items Columns (UOM)
        cursor.execute("SHOW COLUMNS FROM inventoy_items")
        inv_columns = [row[0] for row in cursor.fetchall()]
        if 'uom_secondary' not in inv_columns:
            logging.info("Migrating: Adding uom_secondary to inventoy_items")
            cursor.execute("ALTER TABLE inventoy_items ADD COLUMN uom_secondary VARCHAR(45) NULL")

        if 'uom_conversion_rate' not in inv_columns:
            logging.info("Migrating: Adding uom_conversion_rate to inventoy_items")
            cursor.execute("ALTER TABLE inventoy_items ADD COLUMN uom_conversion_rate DOUBLE DEFAULT 1")

        # 5. Suppliers Table Columns (TIN, NIC)
        cursor.execute("SHOW COLUMNS FROM suppliers")
        sup_columns = [row[0] for row in cursor.fetchall()]

        if 'suppliers_TIN' not in sup_columns:
            logging.info("Migrating: Adding suppliers_TIN to suppliers")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN suppliers_TIN VARCHAR(50) NULL")

        if 'suppliers_NIC' not in sup_columns:
            logging.info("Migrating: Adding suppliers_NIC to suppliers")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN suppliers_NIC VARCHAR(20) NULL")

        # 5b. Company Table (VAT Registered)
        cursor.execute("SHOW COLUMNS FROM company")
        comp_columns = [row[0] for row in cursor.fetchall()]
        if 'vat_registered' not in comp_columns:
            logging.info("Migrating: Adding vat_registered to company")
            cursor.execute("ALTER TABLE company ADD COLUMN vat_registered TINYINT DEFAULT 0")

        # 6. Tax Rates Table
        cursor.execute("SHOW TABLES LIKE 'tax_rates'")
        if not cursor.fetchone():
            logging.info("Migrating: Creating tax_rates table")
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

        # 7. Cheque Print Settings Table
        cursor.execute("SHOW TABLES LIKE 'cheque_print_settings'")
        if not cursor.fetchone():
            logging.info("Migrating: Creating cheque_print_settings table")
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

        # 8. Proforma Invoice Tables
        cursor.execute("SHOW TABLES LIKE 'proforma_invoice_header'")
        if not cursor.fetchone():
            logging.info("Migrating: Creating proforma_invoice_header table")
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
            logging.info("Migrating: Creating proforma_invoice_details table")
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

        # 9. Approval Workflow Updates
        # Add status columns to transaction tables
        # Status: 0=Parked, 1=Posted/Approved, 2=Rejected

        # OP_NO_Table (Purchase Orders)
        cursor.execute("SHOW COLUMNS FROM OP_NO_Table")
        op_cols = [row[0] for row in cursor.fetchall()]
        if 'status' not in op_cols:
            logging.info("Migrating: Adding status to OP_NO_Table")
            cursor.execute("ALTER TABLE OP_NO_Table ADD COLUMN status TINYINT DEFAULT 1")
            # Default 1 (Posted) for existing data to avoid breaking current flow

        # jv_numbers (Journal Vouchers - covers JV, Payments, Receipts)
        cursor.execute("SHOW COLUMNS FROM jv_numbers")
        jv_cols = [row[0] for row in cursor.fetchall()]
        if 'status' not in jv_cols:
            logging.info("Migrating: Adding status to jv_numbers")
            cursor.execute("ALTER TABLE jv_numbers ADD COLUMN status TINYINT DEFAULT 1")

        # System Settings Table (for toggles)
        cursor.execute("SHOW TABLES LIKE 'system_settings'")
        if not cursor.fetchone():
            logging.info("Migrating: Creating system_settings table")
            cursor.execute("""
                CREATE TABLE system_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    setting_key VARCHAR(100) UNIQUE,
                    setting_value VARCHAR(255),
                    description VARCHAR(255)
                )
            """)
            # Default: Disable workflow initially (value '0') to match user request "if need it need to diasable"
            # User request: "post parking is doing ground workers and post is doing managing level if need it need to diasable"
            # I interpret this as "Enable it, but allow disabling". Let's default to DISABLED ('0') to not disrupt current flow immediately, or ENABLED ('1')?
            # User says "I Need to authentication proses... we cant bilt it like park and post".
            # "we cant bilt it like park and post" might mean "we can build it"? Or "we count bill it"?
            # Context: "parking is doing ground workers and post is doing managing level".
            # "if need it need to diasable" -> feature toggle.
            # I'll default to '0' (Disabled) so they can turn it on when ready.
            cursor.execute("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('enable_approval_workflow', '0', 'Enable Park & Post Workflow (0=Disabled, 1=Enabled)')")

        # 10. Master Payment Voucher Sequence
        cursor.execute("SHOW TABLES LIKE 'master_payment_voucher_no'")
        if not cursor.fetchone():
            print("Migrating: Creating master_payment_voucher_no table")
            cursor.execute("""
                CREATE TABLE master_payment_voucher_no (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    voucher_no BIGINT NOT NULL,
                    create_date DATE
                )
            """)
            cursor.execute("INSERT INTO master_payment_voucher_no (voucher_no, create_date) VALUES (0, %s)", (date.today(),))

        # 11. Add Master Voucher Column to Bank Book Record
        cursor.execute("SHOW COLUMNS FROM bank_book_recod")
        bbr_cols = [row[0] for row in cursor.fetchall()]
        if 'master_voucher_no' not in bbr_cols:
            print("Migrating: Adding master_voucher_no to bank_book_recod")
            cursor.execute("ALTER TABLE bank_book_recod ADD COLUMN master_voucher_no BIGINT DEFAULT 0")
        # Default Theme Setting
        cursor.execute("SELECT id FROM system_settings WHERE setting_key = 'system_theme'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('system_theme', 'default', 'Active System Theme')")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Schema Migration Error: {e}")

def ensure_default_accounts(target_db=None):
    """Ensures essential General Ledger accounts exist."""
    current_db = target_db if target_db else db
    try:
        defaults = [
            # Name, BS Position, BS Category, P&L Position, P&L Category, Type
            ('Account Payable', 6, 'Current liabilities', None, None, 'liabilities'),
            ('Account Receivable', 3, 'Current assets', None, None, 'assets'),
            ('Cost Of Goods Sold', None, None, 2, 'Cost Of Sales', 'expenses'),
            ('Sales', None, None, 1, 'Revenue', 'income'),
            ('Income', None, None, 1, 'Revenue', 'income'),
            ('Inventory', 3, 'Current assets', None, None, 'assets'),
            ('VAT Control', 6, 'Current liabilities', None, None, 'liabilities'),
            ('Cash In Hand', 3, 'Current assets', None, None, 'assets')
        ]

        current_user = 0 # System

        if not defaults:
            return

        # Extract all account names
        account_names = [acc[0] for acc in defaults]

        # Check existing accounts using a single batch query
        format_strings = ','.join(['%s'] * len(account_names))
        query = f"SELECT account_name FROM new_account_table WHERE account_name IN ({format_strings})"

        existing_rows = current_db.execute_query(query, tuple(account_names))

        # Store existing account names in a set for O(1) lookups
        existing_names = {row['account_name'] for row in (existing_rows or [])}

        for acc in defaults:
            name, bs_pos, bs_cat, pl_pos, pl_cat, acc_type = acc

            # Check against the set instead of making a DB query
            if name not in existing_names:
                logging.info(f"Creating default account: {name}")
                # Determine basement
                basement = 'DR' if acc_type in ['expenses', 'assets'] else 'CR'

                query = """
                    INSERT INTO new_account_table (
                        account_name, account_hold_possion_Balace_Sheet, account_name_of_catogory_Balace_sheet,
                        account_hold_possion_PL, account_name_of_catogory_PL,
                        account_income, account_expenses, account_assets, account_liabilities, account_equity,
                        accont_create_date, account_create_user, account_active, account_basment
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                """
                current_db.execute_query(query, (
                    name, bs_pos, bs_cat, pl_pos, pl_cat,
                    1 if acc_type=='income' else 0, 1 if acc_type=='expenses' else 0,
                    1 if acc_type=='assets' else 0, 1 if acc_type=='liabilities' else 0, 0,
                    date.today(), current_user, basement
                ), commit=True)

        # 2. Add POS SALE sub-account under Income
        sub_query = "SELECT id FROM sub_account_table WHERE sub_sub_accaount_name = 'POS SALE' AND sub_new_account = 'Income'"
        if not db.execute_query(sub_query):
            db.execute_query("""
                INSERT INTO sub_account_table (sub_sub_accaount_name, sub_new_account, creat_user, creat_date, active)
                VALUES ('POS SALE', 'Income', %s, %s, 1)
            """, (current_user, date.today()), commit=True)

        # 3. Add Common customer
        cust_query = "SELECT id FROM Customer_table WHERE costomer_code = '60001'"
        if not db.execute_query(cust_query):
            db.execute_query("""
                INSERT INTO Customer_table (
                    costomer_name, costomer_code, costomer_billing_addres,
                    customer_dilivery_addres, coustomer_email, customer_credit_limit
                ) VALUES ('Common customer', '60001', 'non', 'non', 'non', 0)
            """, commit=True)

        # 4. Add Direct Payment supplier
        sup_query = "SELECT sup_id FROM suppliers WHERE supplier_code = '70001'"
        if not db.execute_query(sup_query):
            db.execute_query("""
                INSERT INTO suppliers (sup_name, supplier_code)
                VALUES ('Direct Payment', '70001')
            """, commit=True)

    except Exception as e:
        logging.error(f"Error ensuring default accounts/entities: {e}")

# --- Quotation Evaluation ---
@app.route('/quotation_evaluation', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def quotation_evaluation():
    return render_template('quotation_evaluation.html')

@app.route('/api/evaluate_quotations', methods=['POST'])
@login_required
def evaluate_quotations():
    data = request.json
    constraints = data.get('constraints', {})
    suppliers = data.get('suppliers', [])

    # Constraints
    max_days = float(constraints.get('max_days') or 9999)
    # Weights (Simple priority: Price, Speed, Quality)
    priority = constraints.get('priority', 'price')

    # 1. Filter Step
    filtered = []
    for s in suppliers:
        s_days = float(s.get('days', 0))
        if s_days <= max_days:
            filtered.append(s)

    if not filtered:
        return {'results': [], 'message': 'No suppliers meet the delivery deadline constraint.'}

    # 2. Scoring Step
    # Normalize values for scoring
    # Price: Lower is better
    # Days: Lower is better
    # Quality: Higher is better (1-5)

    # Avoid division by zero
    min_price = min(float(s['price']) for s in filtered) if filtered else 1
    min_days = min(float(s['days']) for s in filtered) if filtered else 1
    max_qual = max(float(s['quality']) for s in filtered) if filtered else 1

    scored = []
    for s in filtered:
        price = float(s['price'])
        days = float(s['days'])
        qual = float(s['quality'])

        # Calculate Scores (0 to 1 scale, 1 is best)
        # Price Score: (Min / Actual)
        s_price = min_price / price if price > 0 else 0
        # Days Score: (Min / Actual)
        s_days = min_days / days if days > 0 else 0
        # Quality Score: (Actual / Max)
        s_qual = qual / max_qual if max_qual > 0 else 0

        # Define Weights and Reasons based on Priority
        # Format: (Price Weight, Days Weight, Quality Weight, Reason)
        # s_price (min/actual), s_days (min/actual), s_qual (actual/max)
        strategies = {
            'speed':   (0.2, 0.6, 0.2, "Fastest delivery within constraints"),
            'quality': (0.2, 0.2, 0.6, "Best quality rating"),
            'price':   (0.6, 0.2, 0.2, "Best price")
        }

        # Get weights or default to 'price'
        w_price, w_days, w_qual, reason = strategies.get(priority, strategies['price'])

        # Calculate Score
        # Note: s_price and s_days logic was: Best/Actual (so higher is better, max 1)
        # s_qual logic was: Actual/Best (so higher is better, max 1)
        # However, the previous logic for s_qual in quality priority used s_qual * 0.6.
        # But for price/speed priority it also used s_qual * 0.2.
        # The key difference was which variable got the 0.6 weight.

        final_score = (s_price * w_price) + (s_days * w_days) + (s_qual * w_qual)

        s['score'] = round(final_score * 100, 1)
        scored.append(s)

    # Sort by Score Descending
    scored.sort(key=lambda x: x['score'], reverse=True)

    # Mark the winner
    if scored:
        scored[0]['is_winner'] = True
        scored[0]['win_reason'] = reason

    return {'results': scored}

# --- Proforma Invoice ---
@app.route('/proforma_invoice', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting') # or Sales
def proforma_invoice():
    if request.method == 'POST':
        cust_name = request.form.get('customer_name')
        pi_date = request.form.get('pi_date')
        exp_date = request.form.get('expiry_date')
        narration = request.form.get('narration')
        items_json = request.form.get('items_json')

        items = json.loads(items_json) if items_json else []
        if not items:
            flash('No items', 'danger')
            return redirect(url_for('proforma_invoice'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            # Generate PI Number
            # Simple timestamp based or sequence
            pi_no = f"PI-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Calc Totals
            subtotal = sum(float(i['total']) for i in items)
            vat_rate = 0 # Can add VAT logic if needed, simple for now
            vat_amount = 0
            grand_total = subtotal + vat_amount

            # Insert Header
            cursor.execute("""
                INSERT INTO proforma_invoice_header (
                    pi_number, customer_name, pi_date, expiry_date,
                    subtotal, vat_amount, grand_total, narration, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (pi_no, cust_name, pi_date, exp_date, subtotal, vat_amount, grand_total, narration, current_user_pk))
            pi_id = cursor.lastrowid

            # Insert Details
            if items:
                cursor.executemany("""
                    INSERT INTO proforma_invoice_details (
                        pi_id, item_name, description, qty, unit_price, total
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, [(pi_id, i['name'], i.get('desc', ''), i['qty'], i['price'], i['total']) for i in items])

            conn.commit()
            flash(f'Proforma Invoice {pi_no} created', 'success')
            return redirect(url_for('print_proforma', pi_id=pi_id))

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('proforma_invoice'))

    customers = db.execute_query("SELECT customer_name FROM customer")
    items = db.execute_query("SELECT inventoy_name, inventoy_items_messurment_unit, inventory_price_selling FROM inventoy_items LEFT JOIN inventory_price_recod ON inventoy_items.id = inventory_price_link")

    return render_template('proforma_invoice.html',
                           customers=customers,
                           items=items,
                           today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/proforma/print/<int:pi_id>')
@login_required
def print_proforma(pi_id):
    header_res = db.execute_query("SELECT * FROM proforma_invoice_header WHERE id = %s", (pi_id,))
    if not header_res: return "Not Found", 404
    header = header_res[0]

    details = db.execute_query("SELECT * FROM proforma_invoice_details WHERE pi_id = %s", (pi_id,))
    company = db.execute_query("SELECT * FROM company LIMIT 1")[0]

    return render_template('proforma_print.html', header=header, details=details, company=company)

# --- Currency Setup ---
@app.route('/currency_setup', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def currency_setup():
    if request.method == 'POST':
        code = request.form.get('code', '').upper()
        name = request.form.get('name')
        is_base = 1 if request.form.get('is_base') else 0

        if not code:
            flash('Code required', 'danger')
            return redirect(url_for('currency_setup'))

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            # If setting base, unset others
            if is_base:
                cursor.execute("UPDATE currency_table SET is_base_currency = 0")

            cursor.execute("INSERT INTO currency_table (currency_code, currency_name, is_base_currency) VALUES (%s, %s, %s)",
                           (code, name, is_base))

            conn.commit()
            cursor.close()
            conn.close()
            flash('Currency added', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('currency_setup'))

    currencies = db.execute_query("SELECT * FROM currency_table")
    return render_template('currency_setup.html', currencies=currencies)

@app.route('/currency_setup/delete', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def delete_currency():
    cid = request.form.get('id')
    try:
        db.execute_query("DELETE FROM currency_table WHERE id=%s", (cid,), commit=True)
        flash('Currency deleted', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('currency_setup'))

# --- Exchange Rate API ---
@app.route('/api/get_exchange_rate')
@login_required
def get_exchange_rate():
    from_curr = request.args.get('from', '').upper()
    to_curr = request.args.get('to', '').upper()

    if not from_curr or not to_curr:
        return {'error': 'Missing currencies'}, 400

    if from_curr == to_curr:
        return {'rate': 1.0}

    # Check cache first
    cache_key = f"{from_curr}_{to_curr}"
    current_time = time.time()

    if cache_key in exchange_rate_cache:
        cached_data = exchange_rate_cache[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_DURATION:
            return {'rate': cached_data['rate']}

    try:
        # Use urllib instead of requests to avoid external dependency if not installed
        url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            rate = data.get('rates', {}).get(to_curr)

            if rate is not None:
                # Update cache
                exchange_rate_cache[cache_key] = {
                    'rate': float(rate),
                    'timestamp': current_time
                }

                # Also cache the reverse if possible (1/rate)
                exchange_rate_cache[f"{to_curr}_{from_curr}"] = {
                    'rate': 1.0 / float(rate),
                    'timestamp': current_time
                }

                return {'rate': float(rate)}

    except Exception as e:
        print(f"Exchange Rate API Error: {e}")
        # Fallback to hardcoded/mock values on error (e.g. no internet)
        pass

    # Fallback / Mocking Logic
    rate = 1.0
    if from_curr == 'USD' and to_curr == 'LKR':
        rate = 300.0 + random.uniform(-5, 5) # Fluctuation
    elif from_curr == 'LKR' and to_curr == 'USD':
        rate = 1 / 300.0
    elif from_curr == 'EUR' and to_curr == 'LKR':
        rate = 330.0

    return {'rate': rate}

# --- Journal Entry Management ---
@app.route('/journal_entry', methods=['GET'])
@login_required
@has_permission('Access_Accounting')
def journal_entry():
    # Fetch accounts with currency info and type classification
    accounts = db.execute_query("""
        SELECT
            account_name,
            currency_code,
            CASE
                WHEN account_income = 1 OR account_expenses = 1 THEN 'P&L Account'
                WHEN account_assets = 1 OR account_liabilities = 1 OR account_equity = 1 THEN 'BS Account'
                ELSE 'Other'
            END as account_type
        FROM new_account_table
        WHERE account_active = 1
    """)

    sub_accounts = db.execute_query("SELECT sub_account_code, sub_sub_accaount_name FROM sub_accont_for_new_account WHERE active = 1")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit")

    # Auto-generate next system JV no if possible (simplified max + 1)
    jv_res = db.execute_query("SELECT MAX(jv_id) as max_id FROM jv_numbers")
    next_sys_jv = (jv_res[0]['max_id'] if jv_res and jv_res[0]['max_id'] else 0) + 1

    # Get Base Currency
    base_curr_res = db.execute_query("SELECT currency_code FROM currency_table WHERE is_base_currency = 1 LIMIT 1")
    base_currency = base_curr_res[0]['currency_code'] if base_curr_res else 'LKR'

    return render_template('journal_entry.html',
                           accounts=accounts,
                           sub_accounts=sub_accounts,
                           jobs=jobs,
                           next_sys_jv=next_sys_jv,
                           base_currency=base_currency,
                           today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/journal_entry/save', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def save_journal_entry():
    try:
        user_code = request.form.get('jv_user_code')
        entry_date = request.form.get('entry_date')
        main_narration = request.form.get('main_narration')
        entries_json = request.form.get('entries_json')

        entries = json.loads(entries_json) if entries_json else []

        if not entries:
            flash('No entries provided', 'danger')
            return redirect(url_for('journal_entry'))

        if not user_code or not main_narration:
            flash('JV Number and Main Narration are required', 'danger')
            return redirect(url_for('journal_entry'))

        # Verify balance again (Base Currency)
        total_dr = sum(parse_float(e['dr']) for e in entries)
        total_cr = sum(parse_float(e['cr']) for e in entries)

        if abs(total_dr - total_cr) > 0.01:
            flash(f'Entries not balanced. Diff: {total_dr - total_cr}', 'danger')
            return redirect(url_for('journal_entry'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # Check Workflow
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'enable_approval_workflow'")
            res_set = cursor.fetchone()
            workflow_enabled = res_set and res_set[0] == '1'
            status = 0 if workflow_enabled else 1

            # 1. Create JV Header
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, %s)",
                           (user_code, main_narration, status))
            jv_no = cursor.lastrowid

            # 2. Insert Entries
            for e in entries:
                # Handle sub account
                sub_code = 0
                if e.get('sub_account'):
                    # Format "Code - Name" -> split
                    parts = e['sub_account'].split(' - ')
                    if parts: sub_code = parts[0]

                # Handle Job No
                job_no = e.get('job_no') if e.get('job_no') else None

                # Currency Info
                curr_code = e.get('currency', 'LKR')
                fc_amt = parse_float(e.get('fc_amount', 0))
                rate = parse_float(e.get('rate', 1))

                cursor.execute("""
                    INSERT INTO entry_details (
                        account_name, enty_values_DR, enty_values_CR,
                        entry_effective_date, entry_create_date, entry_naration,
                        entry_create_user, entry_jv, entry_sub_account_code, entry_job_number,
                        currency_code, fc_amount, exchange_rate
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    e['account'], e['dr'], e['cr'],
                    entry_date, datetime.now().date(), e['narration'],
                    current_user, jv_no, sub_code, job_no,
                    curr_code, fc_amt, rate
                ))

            conn.commit()
            flash(f'Journal Entry created successfully. System JV: {jv_no}', 'success')

        except Exception as ex:
            conn.rollback()
            flash(f'Database Error: {str(ex)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'System Error: {str(e)}', 'danger')

    return redirect(url_for('journal_entry'))

@app.route('/journal_entry/history')
@login_required
def journal_entry_history():
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    if not from_date or not to_date:
        return {'error': 'Dates required'}, 400

    query = """
        SELECT
            ed.entry_jv, ed.entry_effective_date, ed.account_name,
            ed.entry_naration, ed.enty_values_DR, ed.enty_values_CR
        FROM entry_details ed
        JOIN jv_numbers jv ON ed.entry_jv = jv.jv_id
        WHERE ed.entry_effective_date BETWEEN %s AND %s
        AND ed.entry_deleted = 0
        ORDER BY ed.entry_jv DESC, ed.id ASC
    """
    rows = db.execute_query(query, (from_date, to_date))

    data = []
    for r in rows:
        data.append({
            'jv_no': r['entry_jv'],
            'date': str(r['entry_effective_date']),
            'account': r['account_name'],
            'narration': r['entry_naration'],
            'dr': float(r['enty_values_DR'] or 0),
            'cr': float(r['enty_values_CR'] or 0)
        })

    return json.dumps(data)

@app.route('/journal_entry/reverse', methods=['POST'])
@login_required
@has_permission('Access_Accounting') # or Access_Reversals
def reverse_journal_entry():
    jv_no = request.form.get('jv_no')
    if not jv_no: return {'error': 'JV No required'}, 400

    current_user = get_current_user_id()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check if already reversed or linked to bank rec (simplified check)
        # C# logic checks entry_deleted = 1
        cursor.execute("SELECT entry_deleted FROM entry_details WHERE entry_jv = %s LIMIT 1", (jv_no,))
        res = cursor.fetchone()
        if res and res[0] == 1:
            return {'error': 'Already reversed or deleted'}, 400

        # Call Stored Procedure
        # Note: schema.sql defined `JV_Entry_Revers` with params (jv_No, User01, Edit_Date)
        # User01 is TEXT, Edit_Date is DATE
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv_no, session.get("user_pk"), datetime.now().date()))

        conn.commit()
        cursor.close()
        conn.close()
        return {'success': True}

    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/journal_entry/print/<int:jv_no>')
@login_required
def print_journal_voucher(jv_no):
    # Fetch Header
    # Note: jv_numbers has jv_id, jv_user_code, jv_naration
    # Need date from entries or assume logic. entries have entry_effective_date.
    header_query = """
        SELECT j.jv_user_code, j.jv_naration, MIN(e.entry_effective_date) as entry_date,
               SUM(e.enty_values_DR) as total_amount
        FROM jv_numbers j
        LEFT JOIN entry_details e ON j.jv_id = e.entry_jv
        WHERE j.jv_id = %s
        GROUP BY j.jv_id
    """
    header_res = db.execute_query(header_query, (jv_no,))
    if not header_res:
        return "JV Not Found", 404
    header = header_res[0]

    # Fetch Details
    details_query = """
        SELECT account_name, entry_naration, enty_values_DR, enty_values_CR, entry_sub_account_code
        FROM entry_details
        WHERE entry_jv = %s
        ORDER BY id
    """
    details = db.execute_query(details_query, (jv_no,))

    # Fetch Company Info
    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    return render_template('jv_print.html', header=header, details=details, company=company, jv_sys_id=jv_no)

def create_default_user():
    """Creates a default admin user if the Login_Table is empty."""
    try:
        # Check connection first
        conn = db.get_connection()
        if not conn:
            logging.warning("WARNING: Database connection failed. Cannot create default user.")
            return

        # Check for existing users
        result = db.execute_query("SELECT COUNT(*) as count FROM Login_Table")
        if result and result[0]['count'] == 0:
            print("No users found. Creating default admin user...")
            # Hash default password
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash('123')
            logging.info("No users found. Creating default admin user...")
            query = """
                INSERT INTO Login_Table (User_Name, Password, User_Code, User_Active, Mobile_No, Email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # Using 'admin' / '123' (Hashed)
            db.execute_query(query, ('admin', pw_hash, 'ADM001', 1, '0000000000', 'admin@example.com'), commit=True)
            logging.info("Default user created: admin / 123")

            # Create Default Rights for Admin
            last_id_res = db.execute_query("SELECT id FROM Login_Table WHERE User_Name = 'admin'")
            if last_id_res:
                uid = last_id_res[0]['id']
                db.execute_query("""
                    INSERT INTO User_Rights (Link_To_Loging_Tabke, Add_New_User, OP_Approved, Access_Inventory, Access_POS, Access_Accounting, Access_Reports, Access_Reversals)
                    VALUES (%s, 1, 1, 1, 1, 1, 1, 1)
                """, (uid,), commit=True)

        else:
            logging.info("Users exist in database. Skipping default user creation.")
    except Exception as e:
        logging.error("Error creating default user.")

def ensure_default_categories(target_db=None):
    """Ensures default Balance Sheet and P&L categories exist."""
    current_db = target_db if target_db else db
    try:
        conn = current_db.get_connection()
        if not conn: return
        cursor = conn.cursor()

        # Balance Sheet Categories
        bs_cats = [
            ('ASSETS', 1),
            ('Non-current assets', 2),
            ('Current assets', 3),
            ('EQUITY AND LIABILITIES', 4),
            ('Capital and reserves', 5),
            ('Current liabilities', 6)
        ]
        try:
            cursor.execute("SELECT holding_position FROM balance_sheet_category")
            existing_bs_positions = {row['holding_position'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()}
        except Exception as e:
            logging.error(f"Error fetching BS categories: {e}")
            existing_bs_positions = set()

        bs_inserts = [(name, pos, date.today()) for name, pos in bs_cats if pos not in existing_bs_positions]
        if bs_inserts:
            try:
                cursor.executemany("INSERT INTO balance_sheet_category (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", bs_inserts)
            except Exception as e:
                logging.error(f"Error bulk inserting BS categories: {e}")

        # P&L Categories
        pl_cats = [
            ('Revenue', 1),
            ('Cost of sales', 2),
            ('Gross profit', 3),
            ('Distribution costs', 4),
            ('Administrative expenses', 5),
            ('Other operating expenses', 6),
            ('Finance cost', 7),
            ('Income from associates', 8),
            ('Income tax expenses', 9),
            ('Minority interest', 10),
            ('Extraordinary items', 11)
        ]
        try:
            cursor.execute("SELECT holding_position FROM `p&l_category`")
            existing_pl_positions = {row['holding_position'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()}
        except Exception as e:
            logging.error(f"Error fetching PL categories: {e}")
            existing_pl_positions = set()

        pl_inserts = [(name, pos, date.today()) for name, pos in pl_cats if pos not in existing_pl_positions]
        if pl_inserts:
            try:
                cursor.executemany("INSERT INTO `p&l_category` (name_of_category, holding_position, create_date_time) VALUES (%s, %s, %s)", pl_inserts)
            except Exception as e:
                logging.error(f"Error bulk inserting PL categories: {e}")

        # CF Categories
        cf_cats = [
            ('Operating Activities', 1), ('Investing Activities', 2), ('Financing Activities', 3),
            ('Adjustments', 0), ('Changes In Working Capital', 0)
        ]
        try:
            cursor.execute("SELECT catogory_name FROM cf_catogory")
            existing_cf_names = {row['catogory_name'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()}
        except Exception as e:
            logging.error(f"Error fetching CF categories: {e}")
            existing_cf_names = set()

        cf_inserts = [(name, pos) for name, pos in cf_cats if name not in existing_cf_names]
        if cf_inserts:
            try:
                cursor.executemany("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", cf_inserts)
            except Exception as e:
                logging.error(f"Error bulk inserting CF categories: {e}")

        conn.commit()
        cursor.close()
        conn.close()
        clear_category_cache()
        logging.info("Default categories checked/created.")

    except Exception as e:
        logging.error(f"Error ensuring default categories: {e}")

def validate_db_config(config):
    """
    Validates database configuration to prevent command injection.
    Only allows alphanumeric characters, underscores, and hyphens in sensitive fields.
    Does not allow arguments starting with dash to prevent argument injection.
    """
    # Alphanumeric, underscore, hyphen.
    # Host might contain dots (IP/domain) and colons (IPv6/port although mysql cli uses -P for port).
    # MySQL CLI host (-h) expects hostname or IP.
    # Database and User usually don't have dots but to be safe we can stick to strict for them.

    strict_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    host_pattern = re.compile(r'^[a-zA-Z0-9_.-]+$') # Allow dots for host

    # Fields to validate (user, host, database)
    # Password is treated differently (passed via env)

    for field in ['user', 'database']:
        value = config.get(field, '')
        if not value: continue
        if not isinstance(value, str) or value.startswith('-') or not strict_pattern.match(value):
            return False

    # Validate Host specifically
    host = config.get('host', '')
    if host:
        if not isinstance(host, str) or host.startswith('-') or not host_pattern.match(host):
            return False

    return True

# --- System Backup ---
@app.route('/system_backup')
@login_required
def system_backup():
    # Only allow admin or specific users? For now, login_required is minimal.
    # Ideally should be restricted.

    # Validate Config
    if not validate_db_config(db_config):
        flash('Invalid database configuration', 'danger')
        return redirect(url_for('index'))

    # Check for mysqldump
    if not shutil.which('mysqldump'):
        flash('mysqldump not found', 'danger')
        return redirect(url_for('index'))

    try:
        filename = f"backup_{date.today().strftime('%Y%m%d')}.sql"

        # Create temporary defaults file to store credentials securely
        # Using tempfile with strict permissions
        defaults_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        try:
            # Set permissions to 600 (owner read/write only) BEFORE writing data
            os.chmod(defaults_file.name, 0o600)

            # Write credentials
            defaults_file.write('[client]\n')
            defaults_file.write(f"user={db_config['user']}\n")
            if db_config['password']:
                defaults_file.write(f"password={db_config['password']}\n")
            defaults_file.write(f"host={db_config['host']}\n")
            defaults_file.flush()
            defaults_file.close()

            # Command construction
            # mysqldump --defaults-extra-file=... -- database > filename
            # Since we are in python, we can pipe output to string or file.

            cmd = [
                'mysqldump',
                f'--defaults-extra-file={defaults_file.name}',
                '--', # End of options
                db_config['database']
            ]

            # Run command
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()

            if process.returncode != 0:
                flash(f'Backup failed: {error.decode("utf-8")}', 'danger')
                return redirect(url_for('index'))

            # Return as file download
            response = make_response(output)
            response.headers['Content-Type'] = 'application/sql'
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        finally:
            # Secure cleanup
            if os.path.exists(defaults_file.name):
                os.remove(defaults_file.name)

    except Exception as e:
        flash(f'Backup error: {str(e)}', 'danger')
        return redirect(url_for('index'))

# --- Fixed Assets Module ---
@app.route('/fixed_assets')
@login_required
@has_permission('Access_Accounting')
def fixed_assets():
    # Fetch accounts for dropdowns
    accounts = db.execute_query("SELECT id, account_name FROM new_account_table WHERE account_active = 1 ORDER BY account_name")

    # Fetch existing Classes and Locations for suggestions
    classes = db.execute_query("SELECT DISTINCT asset_class FROM fixed_assets_register WHERE asset_class IS NOT NULL AND asset_class != ''")
    locations = db.execute_query("SELECT DISTINCT location FROM fixed_assets_register WHERE location IS NOT NULL AND location != ''")

    return render_template('fixed_assets.html', accounts=accounts, classes=classes, locations=locations)

@app.route('/fixed_assets/add', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def add_fixed_asset():
    try:
        class_name = request.form.get('asset_class')
        desc = request.form.get('description')
        brand = request.form.get('brand_name')
        qty = int(request.form.get('quantity', 1))
        serial = request.form.get('serial_no')
        location = request.form.get('location')
        cost = float(request.form.get('cost_value', 0))
        p_date = request.form.get('purchasing_date')
        life = int(request.form.get('depreciable_life_months', 0))

        asset_acc = request.form.get('asset_account_id')
        exp_acc = request.form.get('expense_account_id')
        acc_dep_acc = request.form.get('accumulated_dep_account_id')

        if not asset_acc or not exp_acc or not acc_dep_acc:
             flash('Please select all GL accounts', 'warning')
             return redirect(url_for('fixed_assets'))

        query = """
            INSERT INTO fixed_assets_register
            (asset_class, description, brand_name, quantity, serial_no, location, cost_value, purchasing_date, depreciable_life_months, asset_account_id, expense_account_id, accumulated_dep_account_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (class_name, desc, brand, qty, serial, location, cost, p_date, life, asset_acc, exp_acc, acc_dep_acc), commit=True)
        flash('Asset added successfully', 'success')
    except Exception as e:
        flash(f'Error adding asset: {str(e)}', 'danger')
    return redirect(url_for('fixed_assets'))

@app.route('/fixed_assets/calculate_depreciation', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def calculate_depreciation():
    month_str = request.form.get('month') # "YYYY-MM"
    if not month_str:
        return {'error': 'Month required'}, 400

    try:
        year, month = map(int, month_str.split('-'))
        # Last day of month
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        dep_date = date(year, month, last_day)

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()

        try:
            # 1. Fetch Active Assets
            cursor.execute("SELECT * FROM fixed_assets_register WHERE status = 'Active'")
            assets = cursor.fetchall()

            processed_count = 0

            # Create a shared JV for this month's depreciation run
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                           (f"DEP-{month_str}", f"Depreciation Run for {month_str}"))
            jv_id = cursor.lastrowid

            total_dr = 0
            total_cr = 0
            entries = []

            # Pre-fetch existing depreciations for this month
            cursor.execute("""
                SELECT asset_id FROM asset_depreciation_history
                WHERE YEAR(depreciation_date) = %s AND MONTH(depreciation_date) = %s
            """, (year, month))
            depreciated_assets = {row['asset_id'] for row in cursor.fetchall()}

            for asset in assets:
                # Check if already depreciated for this month
                if asset['id'] in depreciated_assets:
                    continue # Skip if already done

                # Check purchase date
                p_date = asset['purchasing_date']
                if not p_date: continue
                if isinstance(p_date, datetime): p_date = p_date.date()

                # If purchased this month or after, maybe skip or pro-rata?
                # Simple rule: Depreciate if purchased before end of month
                if p_date > dep_date:
                    continue

                # Calculate Amount (Straight Line Monthly)
                # Cost / Life Months
                life = asset['depreciable_life_months']
                if life <= 0: continue

                monthly_amount = asset['cost_value'] / life

                # Check if fully depreciated
                cursor.execute("SELECT SUM(amount) as total FROM asset_depreciation_history WHERE asset_id = %s", (asset['id'],))
                res = cursor.fetchone()
                acc_dep = res['total'] if res and res['total'] else 0

                remaining = asset['cost_value'] - acc_dep
                if remaining <= 0:
                    continue # Fully depreciated

                # Cap amount at remaining
                amount = min(monthly_amount, remaining)
                if amount <= 0: continue

                # Record History
                cursor.execute("""
                    INSERT INTO asset_depreciation_history (asset_id, depreciation_date, amount, jv_id)
                    VALUES (%s, %s, %s, %s)
                """, (asset['id'], dep_date, amount, jv_id))

                # Prepare GL Entries
                # Need account names for entry_details (it uses name, not ID, sadly)
                # Fetch account names
                cursor.execute("SELECT account_name FROM new_account_table WHERE id = %s", (asset['expense_account_id'],))
                exp_name = cursor.fetchone()['account_name']

                cursor.execute("SELECT account_name FROM new_account_table WHERE id = %s", (asset['accumulated_dep_account_id'],))
                acc_dep_name = cursor.fetchone()['account_name']

                entries.append({
                    'dr_acc': exp_name,
                    'cr_acc': acc_dep_name,
                    'amount': amount,
                    'narration': f"Depreciation {month_str} - {asset['asset_class']} - {asset['serial_no']}"
                })

                processed_count += 1

            # Aggregate Entries by Account to reduce lines?
            # Or insert per asset? Per asset is better for audit trail in narration

            insert_tuples = []
            for e in entries:
                # DR Tuple
                insert_tuples.append((e['dr_acc'], e['amount'], 0, dep_date, date.today(), e['narration'], current_user_pk, jv_id))
                # CR Tuple
                insert_tuples.append((e['cr_acc'], 0, e['amount'], dep_date, date.today(), e['narration'], current_user_pk, jv_id))

            if insert_tuples:
                cursor.executemany("""
                    INSERT INTO entry_details (
                        account_name, enty_values_DR, enty_values_CR, entry_effective_date, entry_create_date,
                        entry_naration, entry_create_user, entry_jv
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, insert_tuples)

            conn.commit()
            return {'success': True, 'processed': processed_count, 'jv_id': jv_id}

        except Exception as e:
            conn.rollback()
            logging.error(f"Depreciation Error: {e}")
            return {'error': str(e)}, 500
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/fixed_assets/data')
@login_required
def fixed_assets_data():
    # Fetch all assets
    assets = db.execute_query("SELECT * FROM fixed_assets_register ORDER BY id")

    # Fetch all depreciation history
    history = db.execute_query("SELECT * FROM asset_depreciation_history ORDER BY depreciation_date")

    # Process history into a dict: asset_id -> { 'YYYY-MM': amount, 'total': sum }
    hist_map = {}
    months = set()

    for h in history:
        aid = h['asset_id']
        if aid not in hist_map: hist_map[aid] = {'total': 0, 'months': {}}

        d_date = h['depreciation_date']
        if isinstance(d_date, datetime): d_date = d_date.date()
        month_key = d_date.strftime('%Y-%b') # e.g., 2023-Jan

        hist_map[aid]['months'][month_key] = float(h['amount'])
        hist_map[aid]['total'] += float(h['amount'])
        months.add(month_key)

    # Sort months chronologically
    sorted_months = sorted(list(months), key=lambda x: datetime.strptime(x, '%Y-%b'))

    # Prepare Result
    result = {
        'columns': ['Class', 'Description', 'Brand', 'Qty', 'Serial', 'Location', 'Cost', 'Purchase Date', 'Life (M)'] + sorted_months + ['Total Dep', 'Net Book Value'],
        'data': []
    }

    for a in assets:
        row = {
            'id': a['id'],
            'class': a['asset_class'],
            'desc': a['description'],
            'brand': a['brand_name'],
            'qty': a['quantity'],
            'serial': a['serial_no'],
            'location': a['location'],
            'cost': float(a['cost_value']),
            'date': str(a['purchasing_date']),
            'life': a['depreciable_life_months']
        }

        h_data = hist_map.get(a['id'], {'total': 0, 'months': {}})

        # Add monthly columns
        for m in sorted_months:
            row[m] = h_data['months'].get(m, 0)

        row['total_dep'] = h_data['total']
        row['nbv'] = float(a['cost_value']) - h_data['total']

        result['data'].append(row)

    result['month_headers'] = sorted_months
    return json.dumps(result)

# --- Inventory Transfer ---
@app.route('/inventory_transfer', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def inventory_transfer():
    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit")
    # Fetch active items with cost for reference (though cost isn't changed in transfer)
    items = db.execute_query("""
        SELECT i.inventoy_name, i.inventoy_code, i.inventoy_items_messurment_unit, p.inventory_price_purcharsing
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        WHERE i.active = 1
    """)
    return render_template('inventory_transfer.html', locations=locations, jobs=jobs, items=items, today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/inventory_transfer/submit', methods=['POST'])
@login_required
@has_permission('Access_Inventory')
def submit_inventory_transfer():
    try:
        transfer_date = request.form.get('transfer_date')
        job_no = request.form.get('job_no')
        from_loc = request.form.get('from_location')
        to_loc = request.form.get('to_location')
        narration = request.form.get('narration')

        item_names = request.form.getlist('item_name[]')
        item_codes = request.form.getlist('item_code[]')
        item_units = request.form.getlist('item_unit[]')
        item_costs = request.form.getlist('item_cost[]')
        qtys = request.form.getlist('qty[]')

        if not item_names:
            flash('No items to transfer', 'danger')
            return redirect(url_for('inventory_transfer'))

        if from_loc == to_loc:
            flash('Source and Destination locations must be different', 'danger')
            return redirect(url_for('inventory_transfer'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # 1. Create JV for tracking (Transfer Note)
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                           (str(current_user), f"Inventory Transfer: {narration}"))
            jv_no = cursor.lastrowid

            tf_note = f"TF-Note{jv_no}"

            batch_data = []
            today_date = datetime.now().date()

            for i in range(len(item_names)):
                qty = float(qtys[i])
                cost = float(item_costs[i] or 0)

                if qty <= 0: continue

                # 2. Record OUT from Source (moument_in = 0, movment_out = qty)
                batch_data.append((
                    item_names[i], item_codes[i], item_units[i], cost,
                    0, qty, # in, out
                    tf_note, current_user, today_date, from_loc,
                    transfer_date, narration, jv_no
                ))

                # 3. Record IN to Destination (moument_in = qty, movment_out = 0)
                batch_data.append((
                    item_names[i], item_codes[i], item_units[i], cost,
                    qty, 0, # in, out
                    tf_note, current_user, today_date, to_loc,
                    transfer_date, narration, jv_no
                ))

            if batch_data:
                query = """
                    INSERT INTO inventory_recod (
                        inventoy_name, inventoy_code, inventory_recod_mesrmet,
                        inventory_recod_unit_price, inventory_recod_moument_in, inventory_recod_movment_out,
                        inventory_recod_suplier_iv_no, inventory_recod_user_id,
                        inventory_recod_user_recod_date, inventory_recod_location,
                        inventory_recod_action_date, inventory_recodcol_memo, JV_No
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(query, batch_data)

            conn.commit()
            flash(f'Transfer successful. Tracking Ref: {tf_note}', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error processing transfer: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'System Error: {str(e)}', 'danger')

    return redirect(url_for('inventory_transfer'))

# --- Invoice Creation ---
@app.route('/invoice_creating', methods=['GET'])
@login_required
@has_permission('Access_Accounting') # or Access_Sales if defined
def invoice_creating():
    customers = db.execute_query("SELECT supplier_name as customer_name FROM suppliers WHERE Is_Customer = 1")
    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit")

    # Active items with cost (purcharsing price)
    items = db.execute_query("""
        SELECT i.id, i.inventoy_name, i.inventoy_code, i.inventoy_items_messurment_unit as unit, p.inventory_price_purcharsing as cost
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        WHERE i.active = 1
    """)

    today_date = date.today().strftime('%Y-%m-%d')
    return render_template('invoice_creating.html',
                           customers=customers,
                           locations=locations,
                           jobs=jobs,
                           inventory_items=items,
                           today_date=today_date)

@app.route('/api/get_item_prices/<int:item_id>')
@login_required
def api_get_item_prices(item_id):
    # Fetch all prices (selling, special, etc) for selection logic if multiple
    # Simplified: Returning selling price. If multiple pricing structure exists in `inventory_price_recod`, adjust here.
    # The WPF code checks `inventory_price_selling` and `inventory_price_purcharsing`.
    # It seems to check count. If multiple rows for same link?
    # Schema suggests `inventory_price_link` is FK to item.
    # WPF code: SELECT ... FROM inventory_price_recod WHERE inventory_price_link = ...
    # If count > 1, show selection.

    prices = db.execute_query("SELECT inventory_price_selling FROM inventory_price_recod WHERE inventory_price_link = %s", (item_id,))
    price_list = [p['inventory_price_selling'] for p in prices]
    return json.dumps(price_list)

def calculate_invoice_totals(inv_items, non_inv_items, vat_rate, apply_vat):
    total_sales = 0
    total_cost = 0

    # Inventory Items
    for item in inv_items:
        qty = parse_float(item.get('qty', 0))
        price = parse_float(item.get('price', 0))
        cost = parse_float(item.get('cost', 0))
        total_sales += qty * price
        total_cost += qty * cost

    # Non-Inventory Items
    for item in non_inv_items:
        qty = parse_float(item.get('qty', 0))
        price = parse_float(item.get('price', 0))
        total_sales += qty * price

    vat_amount = 0
    grand_total = total_sales
    if apply_vat:
        vat_amount = (total_sales * vat_rate) / 100
        grand_total += vat_amount

    return {
        'total_sales': total_sales,
        'total_cost': total_cost,
        'vat_amount': vat_amount,
        'grand_total': grand_total
    }

def generate_invoice_number(cursor):
    cursor.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_no, 5) AS UNSIGNED)), 0) FROM customer_outstanding")
    max_inv = cursor.fetchone()[0]
    return f"INV-{max_inv + 1:05d}"

def create_invoice_jv(cursor, current_user, narration):
    cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                   (str(current_user), narration))
    return cursor.lastrowid

@dataclass
class OutstandingRecordContext:
    cursor: typing.Any
    invoice_no: str
    inv_date: str
    grand_total: float
    due_date: str
    cust_name: str
    jv_no: str
    vat_rate: float

def create_outstanding_record(ctx: OutstandingRecordContext):
    ctx.cursor.execute("SELECT sup_id FROM suppliers WHERE supplier_name = %s LIMIT 1", (ctx.cust_name,))
    res = ctx.cursor.fetchone()
    cust_id = res[0] if res else 0

    ctx.cursor.execute("""
        INSERT INTO Invoice_Oustanding (
            invoice_number, invoice_date, invoice_total_oustanding,
            invoice_oustanding_Patment, invoice_final_date,
            invoice_buinding_Customer, invoice_JV, VAT_rate, oustanding_delete
        ) VALUES (%s, %s, %s, 0, %s, %s, %s, %s, 0)
    """, (ctx.invoice_no, ctx.inv_date, ctx.grand_total, ctx.due_date, cust_id, ctx.jv_no, ctx.vat_rate))
    return ctx.cursor.lastrowid


@dataclass
class InvoiceBatchContext:
    cursor: typing.Any
    inv_items: list
    non_inv_items: list
    jv_no: str
    current_user: int
    customer_name: str
    outstanding_id: int
    location: str
    inv_date: str
    invoice_no: str

def process_invoice_items_batch(ctx: InvoiceBatchContext):
    # Prepare batch data
    invoice_recode_batch = []
    inventory_recode_batch = []

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Inventory Items
    for item in ctx.inv_items:
        # Add to invoice_recode (Note: WPF code uses table `invoice_recode` - wait, schema says `Invoice_Recode`)
        # Check schema capitalization. Given previous tables, sticking to lowercase match if possible or schema name.
        # Schema: Invoice_Recode

        # Warranty Logic (Preserved but optimized to only run query)
        # Fetch warranty period for item
        w_end_date = None
        ctx.cursor.execute("""
            SELECT yeas_, month, date_ FROM inventory_vorenty_period
            WHERE name = %s LIMIT 1
        """, (item['name'],))
        w_res = ctx.cursor.fetchone()
        if w_res:
            try:
                years, months, days = w_res
                # Logic retained from original code (pass)
                pass
            except Exception as e:
                logging.error(f"Error parsing warranty for item '{item.get('name')}': {e}")
                pass

        # Add to batch for Invoice_Recode
        invoice_recode_batch.append((
            item['name'], parse_float(item.get('qty', 0)), parse_float(item.get('price', 0)), 1, 'Being account of customer sales', ctx.jv_no, ctx.current_user,
            ctx.customer_name, 1, ctx.outstanding_id, item['unit'], current_date
        ))

        # Add to batch for Inventory_Recod
        inventory_recode_batch.append((
            item['name'], item['code'], item['unit'], item['cost'] * parse_float(item['qty']), parse_float(item['qty']),
            ctx.current_user, current_date, ctx.location, ctx.inv_date, ctx.jv_no, ctx.outstanding_id, ctx.invoice_no
        ))

    # Non-Inventory Items
    for item in ctx.non_inv_items:
        # Add to batch for Invoice_Recode
        invoice_recode_batch.append((
            item['name'], parse_float(item.get('qty', 0)), parse_float(item.get('price', 0)), 0, 'Being account of customer sales', ctx.jv_no, ctx.current_user,
            ctx.customer_name, 1, ctx.outstanding_id, item['unit'], current_date
        ))

    # Execute Batch Inserts
    if invoice_recode_batch:
        ctx.cursor.executemany("""
            INSERT INTO Invoice_Recode (
                Item_Name, Qty, Pricing, Inventory_Items_Or_Not, Natation, JV_No,
                User, Customer_Name, Save_Or_Not, Buinding_To_Oustanding, mesurment,
                recode_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, invoice_recode_batch)

    if inventory_recode_batch:
        ctx.cursor.executemany("""
            INSERT INTO inventory_recod (
                inventoy_name, inventoy_code, inventory_recod_mesrmet,
                inventory_recod_unit_price, inventory_recod_movment_out,
                inventory_recod_account, inventory_recod_user_id,
                inventory_recod_user_recod_date, inventory_recod_location,
                inventory_recod_action_date, inventory_recodcol_memo, JV_No,
                inventory_recod_link_invoice, inventory_recod_suplier_iv_no
            ) VALUES (%s, %s, %s, %s, %s, 'Inventoy', %s, %s, %s, %s, 'Credit Sales', %s, %s, %s)
        """, inventory_recode_batch)

@dataclass
class InvoiceGLContext:
    cursor: object
    current_user: int
    jv_no: str
    invoice_date: str
    job_no: str
    totals: dict

def post_invoice_gl_entries(ctx: InvoiceGLContext):
    job_no_val = ctx.job_no if ctx.job_no else None

    # DR Account Receivable (Total + VAT)
    ctx.cursor.execute("""
        INSERT INTO entry_details (
            account_name, enty_values_DR, entry_effective_date, entry_create_date,
            entry_naration, entry_create_user, entry_jv, entry_job_number
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ('Account Receivable', ctx.totals['grand_total'], ctx.invoice_date, datetime.now().date(), "Credit Sale", ctx.current_user, ctx.jv_no, job_no_val))

    # CR Income (Sales)
    ctx.cursor.execute("""
        INSERT INTO entry_details (
            account_name, enty_values_CR, entry_effective_date, entry_create_date,
            entry_naration, entry_create_user, entry_jv, entry_job_number
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ('Sales', ctx.totals['total_sales'], ctx.invoice_date, datetime.now().date(), "Credit Sale", ctx.current_user, ctx.jv_no, job_no_val))

    # CR VAT (If any)
    if ctx.totals['vat_amount'] > 0:
        ctx.cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_job_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('VAT Control', ctx.totals['vat_amount'], ctx.invoice_date, datetime.now().date(), "Credit Sale", ctx.current_user, ctx.jv_no, job_no_val))

    # Cost of Goods Sold (If inventory items exist)
    if ctx.totals['total_cost'] > 0:
            # DR COGS
        ctx.cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_job_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Cost Of Goods Sold', ctx.totals['total_cost'], ctx.invoice_date, datetime.now().date(), "Credit Sale", ctx.current_user, ctx.jv_no, job_no_val))

        # CR Inventory
        ctx.cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_job_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Inventory', ctx.totals['total_cost'], ctx.invoice_date, datetime.now().date(), "Credit Sale", ctx.current_user, ctx.jv_no, job_no_val))

def parse_invoice_form_data(form):
    customer_name = form.get('customer')
    inv_date = form.get('invoice_date')

    if not customer_name or not inv_date:
        return None, 'Customer and Invoice Date are required.'

    location = form.get('location')
    due_date = form.get('due_date')
    job_no = form.get('job_no')
    vat_rate = parse_float(form.get('vat_rate', 0))
    apply_vat = 1 if form.get('apply_vat') else 0

    inv_items_json = form.get('inventory_items_json')
    non_inv_items_json = form.get('non_inventory_items_json')

    try:
        inv_items = json.loads(inv_items_json) if inv_items_json else []
        non_inv_items = json.loads(non_inv_items_json) if non_inv_items_json else []
    except json.JSONDecodeError as e:
        return None, f'Error processing item list: {str(e)}'

    if not inv_items and not non_inv_items:
        return None, 'No items in invoice'

    return {
        'customer_name': customer_name,
        'inv_date': inv_date,
        'location': location,
        'due_date': due_date,
        'job_no': job_no,
        'vat_rate': vat_rate,
        'apply_vat': apply_vat,
        'inv_items': inv_items,
        'non_inv_items': non_inv_items
    }, None

@app.route('/invoice_creating/submit', methods=['POST'])
@login_required
def submit_invoice():
    # 1. Validation & Input Parsing
    parsed_data, error_msg = parse_invoice_form_data(request.form) if hasattr(request, 'form') else parse_invoice_form_data(request)

    if error_msg:
        flash(error_msg, 'danger')
        return redirect(url_for('invoice_creating'))

    customer_name = parsed_data['customer_name']
    inv_date = parsed_data['inv_date']
    location = parsed_data['location']
    due_date = parsed_data['due_date']
    job_no = parsed_data['job_no']
    vat_rate = parsed_data['vat_rate']
    apply_vat = parsed_data['apply_vat']
    inv_items = parsed_data['inv_items']
    non_inv_items = parsed_data['non_inv_items']

    current_user = get_current_user_id()
    # current_user_pk is unused in the transaction below

    # 2. Database Transaction
    conn = db.get_connection()
    if not conn:
        flash('Database connection failed.', 'danger')
        return redirect(url_for('invoice_creating'))

    cursor = conn.cursor()
    conn.start_transaction()

    try:
        # 3. Generate Invoice No (Credit_Invoice_No table)
        cursor.execute("INSERT INTO Credit_Invoice_No (id) VALUES (0)")
        inv_id_seq = cursor.lastrowid
        invoice_no = f"IV-{datetime.now().year}{datetime.now().month}-{inv_id_seq}"

        # 4. Create JV Header
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                       (str(current_user), "Credit Sales"))
        jv_no = cursor.lastrowid

        # 5. Calculate Totals
        totals = calculate_invoice_totals(inv_items, non_inv_items, vat_rate, apply_vat)
        total_sales = totals['total_sales']
        total_cost = totals['total_cost']
        vat_amount = totals['vat_amount']
        grand_total = totals['grand_total']

        # 6. Insert Outstanding Record
        ctx = OutstandingRecordContext(
            cursor=cursor,
            invoice_no=invoice_no,
            inv_date=inv_date,
            grand_total=grand_total,
            due_date=due_date,
            cust_name=customer_name,
            jv_no=jv_no,
            vat_rate=vat_rate
        )
        outstanding_id = create_outstanding_record(ctx)

        # 7. Insert Invoice Records (Details) & Update Inventory
        batch_ctx = InvoiceBatchContext(
            cursor=cursor,
            inv_items=inv_items,
            non_inv_items=non_inv_items,
            jv_no=jv_no,
            current_user=current_user,
            customer_name=customer_name,
            outstanding_id=outstanding_id,
            location=location,
            inv_date=inv_date,
            invoice_no=invoice_no
        )
        process_invoice_items_batch(batch_ctx)

        # 8. GL Entries
        gl_ctx = InvoiceGLContext(
            cursor=cursor,
            current_user=current_user,
            jv_no=jv_no,
            invoice_date=inv_date,
            job_no=job_no,
            totals={
                'grand_total': grand_total,
                'total_sales': total_sales,
                'vat_amount': vat_amount,
                'total_cost': total_cost
            }
        )
        post_invoice_gl_entries(gl_ctx)
        conn.commit()
        flash(f'Invoice {invoice_no} created successfully.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Transaction failed: {str(e)}', 'danger')
        print(f"Invoice Error: {e}")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('invoice_creating'))

# --- Inventory Production ---
@app.route('/inventory_production', methods=['GET'])
@login_required
@has_permission('Access_Inventory')
def inventory_production():
    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit")

    # Accounts for Cost/Expense selection (PL accounts)
    expense_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_expenses = 1 OR account_assets = 1")

    items = db.execute_query("""
        SELECT i.inventoy_name, i.inventoy_code, i.inventoy_items_messurment_unit, p.inventory_price_purcharsing
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        WHERE i.active = 1
    """)

    return render_template('inventory_production.html',
                           locations=locations, jobs=jobs, items=items,
                           expense_accounts=expense_accounts,
                           today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/inventory_production/issue', methods=['POST'])
@login_required
@has_permission('Access_Inventory')
def submit_production_issue():
    # Logic: Stock OUT, Dr Expense, Cr Inventory
    try:
        date_val = request.form.get('issue_date')
        job_no = request.form.get('job_no')
        source_loc = request.form.get('source_location')
        dr_account = request.form.get('cost_account') # User selected Expense Account
        narration = request.form.get('narration')

        item_names = request.form.getlist('item_name[]')
        item_codes = request.form.getlist('item_code[]')
        item_units = request.form.getlist('item_unit[]')
        item_costs = request.form.getlist('unit_cost[]') # or fetched from DB if readonly
        qtys = request.form.getlist('qty[]')

        if not item_names:
            flash('No items to issue', 'danger')
            return redirect(url_for('inventory_production'))

        current_user = get_current_user_id()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # 1. Create JV
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                           (str(current_user), f"Production Issue: {narration}"))
            jv_no = cursor.lastrowid

            total_value = 0

            # 2. Process Items (Stock OUT)
            for i in range(len(item_names)):
                qty = float(qtys[i])
                # Note: WPF code allows user to select price/cost or takes it from grid.
                # Here we take from form (which defaults to DB cost but is editable or hidden)
                cost = float(item_costs[i] or 0)

                if qty <= 0: continue

                line_val = qty * cost
                total_value += line_val

                # Stock OUT
                cursor.execute("""
                    INSERT INTO inventory_recod (
                        inventoy_name, inventoy_code, inventory_recod_mesrmet,
                        inventory_recod_unit_price, inventory_recod_movment_out,
                        inventory_recod_suplier_iv_no, inventory_recod_user_id,
                        inventory_recod_user_recod_date, inventory_recod_location,
                        inventory_recod_action_date, inventory_recodcol_memo, JV_No
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item_names[i], item_codes[i], item_units[i], cost, qty,
                    f"TF-Prod-{jv_no}", current_user_pk, datetime.now().date(), source_loc,
                    date_val, narration, jv_no
                ))

            # 3. GL Entries
            # Dr User Selected Account (Expense/WIP)
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (dr_account, total_value, date_val, datetime.now().date(), narration, current_user_pk, jv_no, job_no if job_no else None))

            # Cr Inventory Control Account
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_CR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('Inventory', total_value, date_val, datetime.now().date(), narration, current_user_pk, jv_no, job_no if job_no else None))

            conn.commit()
            flash(f'Production Issue recorded successfully. JV: {jv_no}', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error processing issue: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'System Error: {str(e)}', 'danger')

    return redirect(url_for('inventory_production'))

@app.route('/inventory_production/receive', methods=['POST'])
@login_required
@has_permission('Access_Inventory')
def submit_production_receive():
    # Logic: Stock IN, Dr Inventory, Cr Expense/WIP
    try:
        date_val = request.form.get('receive_date')
        job_no = request.form.get('job_no')
        target_loc = request.form.get('target_location')
        cr_account = request.form.get('credit_account') # User selected Cost Source
        narration = request.form.get('narration')

        item_names = request.form.getlist('item_name[]')
        item_codes = request.form.getlist('item_code[]')
        item_units = request.form.getlist('item_unit[]')
        item_costs = request.form.getlist('unit_cost[]')
        qtys = request.form.getlist('qty[]')

        if not item_names:
            flash('No items to receive', 'danger')
            return redirect(url_for('inventory_production'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # 1. Create JV
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)",
                           (str(current_user), f"Production Receipt: {narration}"))
            jv_no = cursor.lastrowid

            total_value = 0

            # 2. Process Items (Stock IN)
            for i in range(len(item_names)):
                qty = float(qtys[i])
                cost = float(item_costs[i] or 0)

                if qty <= 0: continue

                line_val = qty * cost
                total_value += line_val

                # Stock IN
                cursor.execute("""
                    INSERT INTO inventory_recod (
                        inventoy_name, inventoy_code, inventory_recod_mesrmet,
                        inventory_recod_unit_price, inventory_recod_moument_in,
                        inventory_recod_suplier_iv_no, inventory_recod_user_id,
                        inventory_recod_user_recod_date, inventory_recod_location,
                        inventory_recod_action_date, inventory_recodcol_memo, JV_No
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item_names[i], item_codes[i], item_units[i], cost, qty,
                    f"TF-Prod-{jv_no}", current_user_pk, datetime.now().date(), target_loc,
                    date_val, narration, jv_no
                ))

            # 3. GL Entries
            # Dr Inventory Control Account
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('Inventory', total_value, date_val, datetime.now().date(), narration, current_user_pk, jv_no, job_no if job_no else None))

            # Cr User Selected Account (Expense/WIP)
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_CR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv, entry_job_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cr_account, total_value, date_val, datetime.now().date(), narration, current_user_pk, jv_no, job_no if job_no else None))

            # 4. Log to inventory_productions (from WPF Manufacturing_Inventory logic)
            cursor.execute("""
                INSERT INTO inventory_productions (ID, JV_No, Delete_Or_Note, Effective_Date)
                VALUES (0, %s, 0, %s)
            """, (jv_no, date_val))

            conn.commit()
            flash(f'Production Receipt recorded successfully. JV: {jv_no}', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error processing receipt: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'System Error: {str(e)}', 'danger')

    return redirect(url_for('inventory_production'))

def create_db_if_missing():
    """Attempts to create the database if it does not exist."""
    try:
        # Check connection
        try:
            conn = mysql.connector.connect(**db_config)
            conn.close()
            return # Connected successfully
        except mysql.connector.Error:
            pass # Failed, proceed to create

        # Connect without DB name
        temp_config = db_config.copy()
        if 'database' in temp_config:
            del temp_config['database']

        try:
            conn_root = mysql.connector.connect(**temp_config)
            cursor = conn_root.cursor()

            db_name = db_config.get('database', 'Book_keeping')
            logging.warning(f"Database '{db_name}' not found or connection failed. Attempting to create...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            conn_root.commit()
            cursor.close()
            conn_root.close()
            logging.info(f"Database '{db_name}' checked/created.")
        except mysql.connector.Error as e:
            if e.errno in (1007, 1044):
                logging.warning(f"Ignored DB creation error {e.errno} in create_db_if_missing: {e.msg}")
            else:
                raise e
    except Exception as e:
        logging.warning(f"Warning: Could not check/create database: {e}")

def execute_sql_file(cursor, filepath, db_name=None):
    """Parses and executes a MySQL dump file with DELIMITER support."""
    import re
    logging.info(f"Executing SQL file: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        # Read lines to handle DELIMITER command which is line-based
        content = f.read()
        if db_name:
            content = re.sub(r'(?i)Book_keeping', db_name, content)
        lines = content.split('\n')

    delimiter = ';'
    statement = ""

    for line in lines:
        stripped = line.strip()

        # Handle DELIMITER command
        # Syntax: DELIMITER $$
        if stripped.upper().startswith('DELIMITER '):
            delimiter = stripped.split()[1]
            continue

        # Skip comments (simple check)
        if stripped.startswith('--') or stripped.startswith('#'):
            continue

        # Skip empty lines if statement is empty
        if not statement and not stripped:
            continue

        statement += line + "\n"

        # Check if statement ends with delimiter
        if statement.strip().endswith(delimiter):
            # Clean up statement
            sql_to_run = statement.strip()
            # Remove the delimiter from the end
            if sql_to_run.endswith(delimiter):
                 sql_to_run = sql_to_run[:-len(delimiter)]

            if sql_to_run.strip():
                try:
                    cursor.execute(sql_to_run)
                    # consume results if any
                    while cursor.nextset(): pass
                except mysql.connector.Error as e:
                    # Ignore "Table already exists" or similar non-critical if robust
                    # But for initial schema, we usually want to know.
                    # Warning: USE command might fail if user doesn't have perm, but we are inside DB context usually
                    logging.warning(f"SQL Execution Warning: {e}\nStatement partial: {sql_to_run[:100]}...")

            statement = ""

def import_initial_schema():
    """Imports database_schema.sql if Login_Table is missing, using Python parser."""
    try:
        conn = db.get_connection()
        if not conn: return
        cursor = conn.cursor()

        cursor.execute("SHOW TABLES LIKE 'Login_Table'")
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return # Schema likely exists

        logging.info("Login_Table missing. Attempting to import initial schema...")

        default_db_name = db_config.get('database')

        if os.path.exists('database_schema.sql'):
            try:
                execute_sql_file(cursor, 'database_schema.sql', db_name=default_db_name)
                logging.info("Schema imported successfully.")

                if os.path.exists('fixed_assets.sql'):
                    execute_sql_file(cursor, 'fixed_assets.sql', db_name=default_db_name)
                    logging.info("Fixed Assets schema imported.")

                conn.commit()
            except Exception as ex:
                logging.error(f"Failed to execute SQL file: {ex}")
                conn.rollback()
        else:
            logging.warning("database_schema.sql not found.")

        cursor.close()
        conn.close()

    except Exception as e:
        logging.error(f"Error importing initial schema: {e}")

@app.route('/sales_summary_customer', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def sales_summary_customer():
    from_date = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))

    query = """
        SELECT
            c.customer_code,
            c.customer_name,
            COUNT(io.Id) as invoice_count,
            SUM(io.invoice_total_oustanding) as total_sales,
            SUM(io.invoice_oustanding_Patment) as total_paid,
            SUM(io.invoice_total_oustanding - io.invoice_oustanding_Patment) as balance_due
        FROM Invoice_Oustanding io
        JOIN customer c ON io.invoice_buinding_Customer = c.id
        WHERE io.invoice_date BETWEEN %s AND %s
        AND io.oustanding_delete = 0
        GROUP BY c.id, c.customer_code, c.customer_name
        ORDER BY total_sales DESC
    """

    rows = db.execute_query(query, (from_date, to_date))

    # Calculate Grand Totals
    totals = {
        'sales': sum(float(r['total_sales'] or 0) for r in rows),
        'paid': sum(float(r['total_paid'] or 0) for r in rows),
        'balance': sum(float(r['balance_due'] or 0) for r in rows),
        'count': sum(int(r['invoice_count'] or 0) for r in rows)
    }

    return render_template('sales_summary_customer.html',
                           rows=rows,
                           totals=totals,
                           from_date=from_date,
                           to_date=to_date)

# Ensure initialization runs once regardless of startup method
app_initialized = False

@app.before_request
def initialize_app():
    global app_initialized
    if not app_initialized:
        create_db_if_missing()
        setup_master_db()
        import_initial_schema()
        run_schema_migrations()
        ensure_default_categories()
        create_default_user()
        ensure_default_accounts()
        app_initialized = True

if __name__ == '__main__':
    app.run(debug=True, port=5000)
