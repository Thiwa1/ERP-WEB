from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from database import Database
from datetime import datetime, date
from functools import wraps
import csv
import io
import json
import os

app = Flask(__name__)
# Set a secret key for session management.
# In production, this should be set via environment variable.
app.secret_key = os.environ.get('SECRET_KEY', 'hardcoded_secret_key_for_development_only')
app.config['SECRET_KEY'] = app.secret_key

# Database Configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'Book_keeping',
    'raise_on_warnings': True
}

db = Database(db_config)

# Context Processor for Currency
@app.context_processor
def inject_currency():
    # Cache lookup could be implemented here for performance
    # For now, fetching single row is fast enough
    try:
        res = db.execute_query("SELECT company_curency FROM company LIMIT 1")
        currency = res[0]['company_curency'] if res and res[0]['company_curency'] else 'LKR'
    except:
        currency = 'LKR'
    return dict(company_currency=currency)

# Custom Filter for Currency Formatting
@app.template_filter('currency')
def currency_filter(value):
    try:
        if value is None:
            value = 0

        # Format: 1,234.56
        formatted = "{:,.2f}".format(float(value))

        # Get symbol from session or DB?
        # Since filters don't easily access context processors, we can just return the number
        # and let the template use {{ company_currency }} {{ value|currency }}
        # OR we fetch it here (less efficient)
        # OR we rely on the user to put the symbol in the template.

        # Better approach: Just format the number here.
        # The symbol is injected via context processor.
        return formatted
    except (ValueError, TypeError):
        return "0.00"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    return session.get('user_id', 0)

def check_permission(perm_name):
    """Checks if current user has specific permission."""
    user_pk = session.get('user_pk')
    if not user_pk: return False

    try:
        # Check if column exists first to avoid errors during migration or if checking invalid perm
        # But simpler to just try-except.
        # Note: We assume schema is migrated.
        query = f"SELECT {perm_name} FROM User_Rights WHERE Link_To_Loging_Tabke = %s"
        res = db.execute_query(query, (user_pk,))
        if res and res[0].get(perm_name) == 1:
            return True
    except Exception as e:
        print(f"Permission check error: {e}")
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
        # Note: In production, passwords should be hashed.
        # The provided C# code compares plain text, so we replicate that.
        query = "SELECT id, User_Code, Password FROM Login_Table WHERE User_Name = %s"
        users = db.execute_query(query, (username,))

        if users is None:
            flash('Database connection failed. Please check your database configuration.', 'danger')
        elif users:
            user = users[0]
            if user['Password'] == password:
                session['user_id'] = user['User_Code']
                session['user_pk'] = user['id']
                session['username'] = username
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
@login_required
def index():
    return render_template('index.html')

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
                float(credit_limit) if credit_limit else 0.0, contact_1, contact_2,
                current_date, current_user,
                current_user, current_date,
                email, vat_no, salutation,
                0, 1 # Is_Suplier=0, Is_Customer=1
            )

            query_sub_account = """
                INSERT INTO sub_accont_for_new_account (
                    id_sub, sub_sub_accaount_name, sub_new_account,
                    creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            conn = db.get_connection()
            cursor = conn.cursor()
            try:
                conn.start_transaction()
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
                conn.commit()
                flash('Customer added successfully!', 'success')
            except Exception as e:
                conn.rollback()
                print(f"Transaction failed: {e}")
                flash(f'Error adding customer: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()

            return redirect(url_for('add_customer'))

        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return redirect(url_for('add_customer'))

    salutations = []
    try:
        salutations_data = db.execute_query("SELECT salutation FROM suplier_suporting_1")
        salutations = [row['salutation'] for row in salutations_data]
    except:
        pass
    return render_template('add_customer.html', salutations=salutations)

# --- Add Supplier (New) ---
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

            if not supplier_name or not supplier_code:
                flash('Supplier Name and Code are required.', 'danger')
                return redirect(url_for('add_supplier'))

            current_user = get_current_user_id()
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
                float(credit_limit) if credit_limit else 0.0, contact_1, contact_2,
                current_date, current_user,
                current_user, current_date,
                email, vat_no, salutation,
                1, 0 # Is_Suplier=1, Is_Customer=0
            )

            query_sub_account = """
                INSERT INTO sub_accont_for_new_account (
                    id_sub, sub_sub_accaount_name, sub_new_account,
                    creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            conn = db.get_connection()
            cursor = conn.cursor()
            try:
                conn.start_transaction()
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
                conn.commit()
                flash('Supplier added successfully!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Error adding supplier: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()

            return redirect(url_for('add_supplier'))

        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return redirect(url_for('add_supplier'))

    salutations = []
    try:
        salutations_data = db.execute_query("SELECT salutation FROM suplier_suporting_1")
        salutations = [row['salutation'] for row in salutations_data]
    except:
        pass
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
            min_qty = float(request.form.get('min_qty', 0))
            selling_price = float(request.form.get('selling_price', 0))
            cost_price = float(request.form.get('cost_price', 0))

            # 2. Handle Image
            img_data = None
            if 'item_image' in request.files:
                file = request.files['item_image']
                if file.filename != '':
                    # C# code saves as JpegBitmapEncoder buffer (bytes)
                    # We store as LONGBLOB or MEDIUMBLOB.
                    # MySQL Connector handles bytes object directly for BLOBs.
                    img_data = file.read()

            if not name or not code or not unit:
                flash('Name, Code, and Unit are required.', 'danger')
                return redirect(url_for('add_inventory_item'))

            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            try:
                current_user = get_current_user_id()
                today_date = date.today()

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
                    current_user, today_date, unit, main_cat, sub_cat, min_qty
                ))
                item_id = cursor.lastrowid

                # 4. Insert Price
                # C# uses "SELECT LAST_INSERT_ID()" but we have item_id
                # However, schema for `inventory_price_recod` has `inventory_price_link` which is FK to item id?
                # Wait, C# code says: `cmd1.Parameters.AddWithValue("@inventory_price_link", last_insert_jv_no);`
                # Yes, `inventory_price_link` links to `inventoy_items.id`.

                query_price = """
                    INSERT INTO inventory_price_recod (
                        id, inventory_price_link, inventory_price_selling, inventory_price_purcharsing, created_date
                    ) VALUES (0, %s, %s, %s, %s)
                """
                cursor.execute(query_price, (item_id, selling_price, cost_price, today_date))

                conn.commit()
                flash('Inventory Item created successfully!', 'success')

            except Exception as e:
                conn.rollback()
                flash(f'Database Error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()

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

            total_value = float(request.form.get('total_value', 0))
            vat_rate = float(request.form.get('vat_rate', 0))
            vat_amount = float(request.form.get('vat_amount', 0))
            grand_total = float(request.form.get('grand_total', 0))

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

            # 3. Create Transaction
            conn = db.get_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            try:
                current_user = get_current_user_id()

                # A. Generate JV Number
                cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM GRN', narration))
                jv_no = cursor.lastrowid

                # B. Insert Invoice Record
                query_inv = """
                    INSERT INTO suppliers_invoice_data (
                        suppliers_code, suppliers_invoice_number, suppliers_invoice_date,
                        suppliers_invoice_total_oustanding, suppliers_invoice_final_date,
                        suppliers_invoice_buinding_supplier, suppliers_invoice_JV, suppliers_VAT_rate, suppliers_invoice_total_payment
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
                """
                cursor.execute(query_inv, (supplier_code, invoice_no, invoice_date, grand_total, due_date, supplier_id, jv_no, vat_rate))

                # C. Journal Entries
                # C1. Credit Account Payable (Grand Total)
                cursor.execute("""
                    INSERT INTO entry_details (
                        account_name, enty_values_CR, entry_effective_date, entry_create_date,
                        entry_naration, entry_create_user, entry_jv, entry_job_number
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('Account Payable', grand_total, invoice_date, date.today(), narration, current_user, jv_no, job_no if job_no else None))

                # C2. Debit Inventory (Total Value)
                cursor.execute("""
                    INSERT INTO entry_details (
                        account_name, enty_values_DR, entry_effective_date, entry_create_date,
                        entry_naration, entry_create_user, entry_jv, entry_job_number
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ('Inventory', total_value, invoice_date, date.today(), narration, current_user, jv_no, job_no if job_no else None))

                # C3. Debit VAT Control (if applicable)
                if vat_amount > 0:
                    cursor.execute("""
                        INSERT INTO entry_details (
                            account_name, enty_values_DR, entry_effective_date, entry_create_date,
                            entry_naration, entry_create_user, entry_jv, entry_job_number
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, ('VAT Control', vat_amount, invoice_date, date.today(), narration, current_user, jv_no, job_no if job_no else None))

                # D. Inventory Records
                for item in items:
                    query_ir = """
                        INSERT INTO inventory_recod (
                            inventoy_name, inventoy_code, inventory_recod_mesrmet,
                            inventory_recod_unit_price, inventory_recod_moument_in, inventory_recod_movment_out,
                            inventory_recod_suplier_iv_no, inventory_recod_user_id, inventory_recod_user_recod_date,
                            inventory_recod_location, inventory_recod_link_invoice, inventory_recod_action_date, JV_No
                        ) VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query_ir, (
                        item['name'], item['code'], item['unit'], item['cost'], item['qty'],
                        invoice_no, current_user, date.today(), location, jv_no, invoice_date, jv_no
                    ))

                conn.commit()
                flash(f'GRN created successfully. JV No: {jv_no}', 'success')
                return render_template('grn_print.html', grn_no=jv_no, supplier=supplier_name, date=invoice_date, invoice_no=invoice_no, location=location, items=items, total_value=total_value, vat_amount=vat_amount, grand_total=grand_total)

            except Exception as e:
                conn.rollback()
                flash(f'Transaction failed: {str(e)}', 'danger')
                return redirect(url_for('grn'))
            finally:
                cursor.close()
                conn.close()

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
        name = request.form.get('category_name')
        level = request.form.get('hold_level')
        if name:
            db.execute_query("INSERT INTO cf_catogory (catogory_name, hold_level) VALUES (%s, %s)", (name, level), commit=True)
            flash('Category added', 'success')
        return redirect(url_for('cash_flow_categories'))

    cats = db.execute_query("SELECT * FROM cf_catogory ORDER BY hold_level, catogory_name")
    return render_template('cash_flow_categories.html', categories=cats)

@app.route('/cash_flow_categories/delete', methods=['POST'])
@login_required
def delete_cash_flow_category():
    cat_id = request.form.get('id')
    db.execute_query("DELETE FROM cf_catogory WHERE id = %s", (cat_id,), commit=True)
    flash('Category deleted', 'success')
    return redirect(url_for('cash_flow_categories'))

# --- Chart of Accounts ---
@app.route('/chart_of_accounts')
@login_required
@has_permission('Access_Accounting')
def chart_of_accounts():
    accounts = db.execute_query("SELECT * FROM new_account_table WHERE account_active = 1")
    pl_count = len([a for a in accounts if a['account_name_of_catogory_PL']])
    bs_count = len([a for a in accounts if a['account_name_of_catogory_Balace_sheet']])
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
                    cf_catogory, accont_create_date, account_create_user, account_active, account_basment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, '')
            """
            params = (
                account_name, pl_pos, bs_pos, pl_name, bs_name,
                is_income, is_expense, is_asset, is_liability, is_equity,
                cf_cat, date.today(), current_user
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
    bs_cats = db.execute_query("SELECT name_of_category, holding_position FROM balance_sheet_category")
    pl_cats = db.execute_query("SELECT name_of_category, holding_position FROM `p&l_category`")
    cf_cats = db.execute_query("SELECT catogory_name FROM cf_catogory ORDER BY hold_level, catogory_name")
    existing_accounts = db.execute_query("SELECT account_name FROM new_account_table WHERE account_active = 1")

    return render_template('add_new_account.html',
                           bs_categories=bs_cats,
                           pl_categories=pl_cats,
                           cf_categories=cf_cats,
                           existing_accounts=existing_accounts)

# --- Create Bank Account ---
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

        try:
            db.execute_query("""
                INSERT INTO bank_book (bank_bookcol_account_number, bank_book_bank_name, bank_book_create_date, bank_book_create_user)
                VALUES (%s, %s, %s, %s)
            """, (acc_no, bank_name, date.today(), current_user), commit=True)
            flash('New bank account created', 'success')
        except Exception as e:
            flash(f'Error creating bank account: {str(e)}', 'danger')

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

        try:
            # cash_book schema: cash_id, cash_book_account_name, cash_creat_date, cash_created_user, Select_As
            db.execute_query("""
                INSERT INTO cash_book (cash_book_account_name, cash_creat_date, cash_created_user, Select_As)
                VALUES (%s, %s, %s, 0)
            """, (acc_name, date.today(), current_user), commit=True)
            flash('New cash account created', 'success')
        except Exception as e:
            flash(f'Error creating cash account: {str(e)}', 'danger')

        return redirect(url_for('create_cash_account'))

    return render_template('create_cash_account.html')

# --- Control Panel (P&L Correction + Settings) ---
@app.route('/control_panel', methods=['GET', 'POST'])
@login_required
@has_permission('Access_Accounting')
def control_panel():
    # 1. Handle Warranty Settings
    if request.method == 'POST':
        enabled = 1 if request.form.get('warranty_enabled') else 0
        count_res = db.execute_query("SELECT COUNT(*) as cnt FROM adding_new")
        count = count_res[0]['cnt'] if count_res else 0
        if count == 0:
            db.execute_query("INSERT INTO adding_new (id, yes) VALUES (0, %s)", (enabled,), commit=True)
        else:
            db.execute_query("UPDATE adding_new SET yes = %s", (enabled,), commit=True)

        flash('Settings updated', 'success')
        return redirect(url_for('control_panel'))

    # 2. Fetch Warranty Status
    res = db.execute_query("SELECT yes FROM adding_new")
    warranty_enabled = False
    if res and res[0]['yes'] == 1:
        warranty_enabled = True

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
    pl_cats = db.execute_query("SELECT name_of_category, holding_position FROM `p&l_category`")
    bs_cats = db.execute_query("SELECT name_of_category, holding_position FROM balance_sheet_category")

    return render_template('control_panel.html',
                           warranty_enabled=warranty_enabled,
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

            for name, pos, aid in updates:
                cursor.execute(sql, (name, pos, aid))

            conn.commit()
            cursor.close()
            conn.close()
            flash(f'Updated {len(updates)} accounts.', 'success')
        except Exception as e:
            flash(f'Error updating accounts: {str(e)}', 'danger')
    else:
        flash('No changes selected.', 'info')

    return redirect(url_for('control_panel'))

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
                    company_curency=%s
                """
                params = [name, addr1, addr2, addr3, addr4, addr5, land, fax, vat, curr]

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
                        company_vate_code, company_curency, company_log
                    ) VALUES (0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                db.execute_query(query, (name, addr1, addr2, addr3, addr4, addr5, land, fax, vat, curr, logo_data), commit=True)

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
        except:
            # If it's raw image bytes, encode it
            import base64
            company['company_log'] = base64.b64encode(company['company_log']).decode('utf-8')

    return render_template('company_profile.html', company=company)

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

@app.route('/cash_payment/get_data')
@login_required
def get_cash_supplier_data():
    sup_name = request.args.get('name')
    if not sup_name:
        return {'error': 'No supplier name'}, 400

    # 1. Supplier Details
    sup_data = db.execute_query("SELECT * FROM suppliers WHERE supplier_name = %s", (sup_name,))
    details = {}
    if sup_data:
        s = sup_data[0]
        details = {
            'code': s['supplier_code'],
            'address': f"{s['supplier_address_1']}, {s['supplier_address_2']}",
            'mobile': s['suppliers_teli_1'],
            'email': s['suppliers_e_mail'],
            'vat': s['suppliers_vat_regidter_no']
        }
        sup_id = s['sup_id']
    else:
        return {'error': 'Supplier not found'}, 404

    # 2. Outstanding Invoices
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

    # 3. Cash Payment History
    history = db.execute_query("""
        SELECT cash_book_recod_voucher_no, Payment_Date, cash_book_recode_accont_name, cash_book_recode_cr, User_Enter, jv_numbers_jv_id
        FROM cash_book_recode
        WHERE cash_book_recode_suplier_name = %s
        ORDER BY chash_book_recod_id DESC
    """, (sup_name,))

    hist_list = []
    for h in history:
        hist_list.append({
            'voucher': h['cash_book_recod_voucher_no'],
            'date': str(h['Payment_Date']),
            'account': h['cash_book_recode_accont_name'],
            'amount': float(h['cash_book_recode_cr'] or 0),
            'user_id': h['User_Enter'],
            'jv_no': h['jv_numbers_jv_id']
        })

    return {'details': details, 'invoices': inv_list, 'history': hist_list}

@app.route('/cash_payment/submit', methods=['POST'])
@login_required
def cash_payment_submit():
    supplier_name = request.form.get('supplier')
    cash_account = request.form.get('cash_account')
    payment_date = request.form.get('payment_date')
    narration = request.form.get('narration')

    if not supplier_name or not cash_account:
        flash('Missing supplier or cash account', 'danger')
        return redirect(url_for('cash_payment'))

    # Collect payments
    payments = []
    total_payment = 0

    # Iterate form to find payment items
    for key in request.form:
        if key.startswith('payment_'):
            inv_id = key.split('_')[1]
            try:
                amount = float(request.form[key])
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

        # 1. Generate Voucher Number
        cursor.execute("SELECT MAX(cash_voucher_number) FROM cash_voucher_no WHERE cash_voucher_link = %s", (cash_account,))
        res = cursor.fetchone()
        max_voucher = res[0] if res and res[0] else 0
        new_voucher = max_voucher + 1

        cursor.execute("INSERT INTO cash_voucher_no (id, cash_voucher_link, cash_voucher_number) VALUES (0, %s, %s)",
                       (cash_account, new_voucher))

        # 2. Create Journal Voucher (JV)
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FORM PAYMENT', narration))
        jv_no = cursor.lastrowid

        # Get Sub Account Code
        cursor.execute("SELECT sub_account_code FROM sub_accont_for_new_account WHERE sub_sub_accaount_name = %s", (supplier_name,))
        res = cursor.fetchone()
        sub_ac_code = res[0] if res else 0

        # 3. Create GL Entries
        # Debit AP
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_sub_account_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Account Payable', total_payment, payment_date, date.today(), narration, current_user, jv_no, sub_ac_code))

        # Credit Cash
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (cash_account, total_payment, payment_date, date.today(), narration, current_user, jv_no))

        # 4. Process Individual Payments
        for p in payments:
            # Update Invoice Outstanding (Logic of vender_settele)
            cursor.execute("SELECT suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE s_i_id = %s", (p['id'],))
            res = cursor.fetchone()
            current_paid = float(res[0] or 0)
            new_total_paid = current_paid + p['amount']

            cursor.execute("UPDATE suppliers_invoice_data SET suppliers_invoice_total_payment = %s WHERE s_i_id = %s", (new_total_paid, p['id']))

            # Insert Cash Book Record
            cursor.execute("""
                INSERT INTO cash_book_recode (
                    cash_book_recode_dr, cash_book_recode_cr, cash_book_recode_accont_name,
                    cash_book_recode_naration, cash_book_recode_suplier_oustanding_id,
                    cash_book_recode_suplier_name, jv_numbers_jv_id,
                    cash_book_po_no, cash_book_suplier_oustanding_id,
                    cash_book_recod_voucher_no, User_Enter, Payment_Date
                ) VALUES (0, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
            """, (
                p['amount'], cash_account, narration,
                p['id'], supplier_name, jv_no,
                p['id'], new_voucher, current_user, payment_date
            ))

        conn.commit()
        flash(f'Cash Payment processed successfully. Voucher No: {new_voucher}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Transaction failed: {str(e)}', 'danger')
        print(e)
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('cash_payment'))

@app.route('/cash_payment/print/<int:jv_no>')
@login_required
def print_cash_voucher(jv_no):
    # Fetch Voucher Details
    voucher_res = db.execute_query("""
        SELECT
            c.cash_book_recod_voucher_no as voucher_no,
            c.Payment_Date as date,
            c.cash_book_recode_suplier_name as paid_to,
            c.cash_book_recode_accont_name as paid_from,
            c.cash_book_recode_naration as narration,
            SUM(c.cash_book_recode_cr) as amount,
            c.User_Enter as user_id
        FROM cash_book_recode c
        WHERE c.jv_numbers_jv_id = %s
        GROUP BY c.cash_book_recod_voucher_no, c.Payment_Date, c.cash_book_recode_suplier_name,
                 c.cash_book_recode_accont_name, c.cash_book_recode_naration, c.User_Enter
    """, (jv_no,))

    if not voucher_res:
        return "Voucher Not Found", 404
    voucher = voucher_res[0]

    # Fetch Company Info
    company_res = db.execute_query("SELECT * FROM company LIMIT 1")
    company = company_res[0] if company_res else {}

    # Fetch Amount in Words (Simplified)
    # In a real app, use a num2words library

    return render_template('payment_voucher_print.html',
                           voucher=voucher,
                           company=company)

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
        location = request.form.get('location')
        comments = request.form.get('comments')
        vat_rate = float(request.form.get('vat_rate', 0))
        items_json = request.form.get('items_json')
        items = json.loads(items_json) if items_json else []

        if not items:
            flash('No items in Purchase Order', 'danger')
            return redirect(url_for('purchase_orders'))

        current_user = get_current_user_id()

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
                po_number, current_user, date.today(), sup_id, supplier,
                comments, delivery_date, location, vat_rate
            ))
            po_id = cursor.lastrowid

            # Insert Details
            query_detail = """
                INSERT INTO PO_Recode_Details (
                    Link_OP_NO_Table, Item, Discription, QTY, Unit_price, Mesurment
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            for item in items:
                cursor.execute(query_detail, (
                    po_id, item['item'], item['description'],
                    item['qty'], item['price'], item['unit']
                ))

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

    if po_id:
        db.execute_query("""
            UPDATE OP_NO_Table
            SET Save_Post = 1, Aprove_By = %s, Aproed_Date = %s
            WHERE id = %s
        """, (current_user, date.today(), po_id), commit=True)
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

        # Insert User
        cursor.execute("""
            INSERT INTO Login_Table (User_Name, Password, Mobile_No, Email, User_Active)
            VALUES (%s, %s, %s, %s, 1)
        """, (username, password, mobile, email))
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
        flash(f'User {username} created successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error creating user: {str(e)}', 'danger')
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
        db.execute_query("""
            UPDATE Login_Table
            SET User_Name = %s, Password = %s, Mobile_No = %s, Email = %s, User_Active = %s
            WHERE id = %s
        """, (username, password, mobile, email, active, user_id), commit=True)
        flash('User details updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating user: {str(e)}', 'danger')

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
        print(f"Rights Update Error: {e}")
        return {'error': str(e)}, 500

# --- Add New Job ---
@app.route('/add_new_job', methods=['GET', 'POST'])
@login_required
def add_new_job():
    if request.method == 'POST':
        job_no = request.form.get('job_no')
        description = request.form.get('job_description')

        if not job_no or not description:
            flash('Job No and Description are required', 'danger')
            return redirect(url_for('add_new_job'))

        current_user = get_current_user_id()

        try:
            db.execute_query("""
                INSERT INTO jobs_unit (id, job_number, job_description, job_create_date, job_create_user, job_finsh, job_cancell)
                VALUES (0, %s, %s, %s, %s, 0, 0)
            """, (job_no, description, date.today(), current_user), commit=True)
            flash('New job created successfully', 'success')
        except Exception as e:
            flash(f'Error creating job: {str(e)}', 'danger')

        return redirect(url_for('add_new_job'))

    return render_template('add_new_job.html')

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
            sales = [float(r['MonthlySales']) for r in raw_data]
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

@app.route('/api/get_customers')
@login_required
def api_get_customers():
    query = "SELECT id, customer_name as name FROM customer ORDER BY customer_name"
    rows = db.execute_query(query)
    return json.dumps(rows)

@app.route('/get_supplier_data')
@login_required
def get_supplier_data():
    sup_name = request.args.get('name')
    if not sup_name:
        return {'error': 'No supplier name'}, 400

    # 1. Supplier Details
    sup_data = db.execute_query("SELECT * FROM suppliers WHERE supplier_name = %s", (sup_name,))
    details = {}
    if sup_data:
        s = sup_data[0]
        details = {
            'code': s['supplier_code'],
            'address': f"{s['supplier_address_1']}, {s['supplier_address_2']}",
            'mobile': s['suppliers_teli_1'],
            'email': s['suppliers_e_mail'],
            'vat': s['suppliers_vat_regidter_no']
        }
        sup_id = s['sup_id']
    else:
        return {'error': 'Supplier not found'}, 404

    # 2. Outstanding Invoices
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

    # 3. Payment History
    history = db.execute_query("""
        SELECT bank_book_recod_voucher_no, Bank_Payment_Date, bank_book__accont_name, bank_book__recode_cr, bank_book__naration
        FROM bank_book_recod
        WHERE bank_book__suplier_name = %s
        ORDER BY id DESC
    """, (sup_name,))

    hist_list = []
    for h in history:
        hist_list.append({
            'voucher': h['bank_book_recod_voucher_no'],
            'date': str(h['Bank_Payment_Date']),
            'account': h['bank_book__accont_name'],
            'amount': float(h['bank_book__recode_cr'] or 0),
            'narration': h['bank_book__naration']
        })

    return {'details': details, 'invoices': inv_list, 'history': hist_list}

@app.route('/bank_payment_submit', methods=['POST'])
@login_required
def bank_payment_submit():
    supplier_name = request.form.get('supplier')
    bank_account = request.form.get('bank_account')
    payment_date = request.form.get('payment_date')
    narration = request.form.get('narration')
    cheque_no = request.form.get('cheque_no')

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
        for p in payments:
            # Check balance again to be safe
            cursor.execute("SELECT suppliers_invoice_oustanding, suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE s_i_id = %s", (p['id'],))
            res = cursor.fetchone() # returns tuple (outstanding, total_payment)
            if not res: continue

            # Note: The C# code fetches outstanding from DB. My execute_query returns dictionary,
            # but raw cursor returns tuple. Let's assume tuple for raw cursor.
            # Actually, let's use the helper to keep it consistent if possible, but we are inside transaction.
            # Raw cursor fetchone returns tuple.

            current_outstanding = float(res[0])
            current_paid = float(res[1])

            if p['amount'] > current_outstanding:
                raise Exception(f"Payment amount {p['amount']} exceeds outstanding {current_outstanding} for invoice ID {p['id']}")

            new_total_paid = current_paid + p['amount']
            cursor.execute("UPDATE suppliers_invoice_data SET suppliers_invoice_total_payment = %s WHERE s_i_id = %s", (new_total_paid, p['id']))

        # 2. Generate Voucher Number
        cursor.execute("SELECT MAX(bank_book_voucher_no) FROM bank_book_voucher_no WHERE bank_book_voucher_link = %s", (bank_account,))
        res = cursor.fetchone()
        max_voucher = res[0] if res and res[0] else 0
        new_voucher = max_voucher + 1

        cursor.execute("INSERT INTO bank_book_voucher_no (bank_book_voucher_link, bank_book_voucher_no, bank_book_chq_no) VALUES (%s, %s, %s)",
                       (bank_account, new_voucher, cheque_no))

        # 3. Create Journal Voucher (JV)
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM PAYMENT', narration))
        jv_no = cursor.lastrowid

        # Get Sub Account Code for Supplier
        cursor.execute("SELECT sub_account_code FROM sub_accont_for_new_account WHERE sub_sub_accaount_name = %s", (supplier_name,))
        res = cursor.fetchone()
        sub_ac_code = res[0] if res else 0

        # Debit AP
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv, entry_sub_account_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, ('Account Payable', total_payment, payment_date, date.today(), narration, current_user, jv_no, sub_ac_code))

        # Credit Bank
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (bank_account, total_payment, payment_date, date.today(), narration, current_user, jv_no))

        # 4. Record Bank Transactions
        sup_id_res = db.execute_query("SELECT sup_id FROM suppliers WHERE supplier_name = %s", (supplier_name,))
        sup_id = sup_id_res[0]['sup_id'] if sup_id_res else 0

        for p in payments:
            cursor.execute("""
                INSERT INTO bank_book_recod (
                    bank_book__accont_name, bank_book__recode_cr, bank_book__naration,
                    bank_book__suplier_oustanding_id, bank_book__suplier_name, jv_numbers_jv_id,
                    bank_book_recod_voucher_no, bank_book_chque_no, Bank_Sup_Code, Bank_User_Id, Bank_Payment_Date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (bank_account, p['amount'], narration, p['id'], supplier_name, jv_no, new_voucher, cheque_no, sup_id, current_user, payment_date))

        conn.commit()
        flash(f'Payment processed successfully. Voucher No: {new_voucher}', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Transaction failed: {str(e)}', 'danger')
        print(e)
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
        paid = request.form.get('amount_paid', 0)

        if not mobile:
            flash('Mobile number is required', 'danger')
            return redirect(url_for('customer_loyalty'))

        current_date = datetime.now().date()

        # Determine next ID (simplified vs MAX+60001)
        # Using auto-increment for ID but custom logic for code
        max_id_res = db.execute_query("SELECT MAX(id) as max_id FROM customer")
        max_id = max_id_res[0]['max_id'] if max_id_res else 0
        if not max_id: max_id = 0
        customer_code = max_id + 60001

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
            1, mobile, 1, 0, current_date, paid, 0
        )

        db.execute_query(query, params, commit=True)
        flash('Loyalty customer registered', 'success')
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
            # Debit Entry
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (item['account'], item['total'], today_date, today_date, item['narration'], current_user, jv_no))

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
        print(f"Direct Payment Error: {e}")
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

    for i in range(len(item_ids)):
        # Check if price record exists
        link_id = item_ids[i]
        exists = db.execute_query("SELECT id FROM inventory_price_recod WHERE inventory_price_link = %s", (link_id,))

        if exists:
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

    # Calculate Retained Earnings (Income - Expense - COGS)
    income_res = db.execute_query("""
        SELECT COALESCE(SUM(enty_values_CR - enty_values_DR), 0) as val
        FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
        WHERE na.account_income = 1 AND ed.entry_effective_date <= %s
    """, (as_at_date,))
    income_val = income_res[0]['val'] if income_res else 0

    expense_res = db.execute_query("""
        SELECT COALESCE(SUM(enty_values_DR - enty_values_CR), 0) as val
        FROM entry_details ed JOIN new_account_table na ON ed.account_name = na.account_name
        WHERE na.account_expenses = 1 AND ed.entry_effective_date <= %s
    """, (as_at_date,))
    expense_val = expense_res[0]['val'] if expense_res else 0

    retained_earnings = float(income_val) - float(expense_val)

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
                inventory_recod_movment_out as out_qty
            FROM inventory_recod
            WHERE inventoy_name = %s AND inventory_recod_action_date BETWEEN %s AND %s
            ORDER BY inventory_recod_action_date
        """, (item_name, from_date, to_date))

        curr = opening_balance
        for m in mvs:
            curr += float(m['in_qty']) - float(m['out_qty'])
            m['balance'] = curr
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

# --- Sales Summary Report (Cashier Wise) ---
@app.route('/sales_summary_cashier')
@login_required
@has_permission('Access_Reports')
def sales_summary_cashier():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    filter_type = request.args.get('filter', 'current')
    download = request.args.get('download')

    current_cashier_id = get_current_user_id()

    # 1. Fetch Current User Name (Cashier)
    # The C# code fetches from `pose_setting_table` or `Login_Table`.
    # Based on session user_id (User_Code), let's get the name.
    # Actually C# fetches from `pose_setting_table` where ID = POS_User_ID.
    # We will assume session['username'] is the cashier name or fetch from login.
    cashier_name = session.get('username', 'Unknown')

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
        LEFT JOIN Login_Table lt ON s.RecodeUserId = lt.User_Code
        WHERE DATE(s.AcctionDate) = %s
        AND s.Revers = 0
    """
    params = [selected_date]

    if filter_type == 'current':
        query += " AND s.RecodeUserId = %s"
        params.append(current_cashier_id)

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
                r['AcctionDate'], # Formatted automatically or need strftime
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
    current_cashier_id = get_current_user_id()
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
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, current_user, datetime.utcnow()))

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
    jv = request.args.get('jv')
    if not jv: return {'error': 'No JV provided'}, 400

    # Fetch details text
    query = """
        SELECT
            suppliers_invoice_number as IV_No,
            suppliers_VAT_rate as VAT_Rate,
            cash_book_recode_cr as Paid_Amount
        FROM suppliers_invoice_data
        LEFT JOIN cash_book_recode ON suppliers_invoice_data.s_i_id = cash_book_recode_suplier_oustanding_id
        WHERE jv_numbers_jv_id = %s
    """
    inv_rows = db.execute_query(query, (jv,))

    # Also check Bank Book Record for bank payments specifically (schema variation handling)
    if not inv_rows:
       query_bank = """
           SELECT bank_book__naration, bank_book__recode_cr
           FROM bank_book_recod
           WHERE jv_numbers_jv_id = %s
       """
       bank_rows = db.execute_query(query_bank, (jv,))
       text = f"Bank Payment Reversal (JV: {jv})\n" + "-"*30 + "\n"
       for r in bank_rows:
           text += f"Narration: {r['bank_book__naration']} | Amount: {r['bank_book__recode_cr']}\n"
    else:
        text = f"Journal Voucher {jv} Impact\n" + "-"*30 + "\n"
        for r in inv_rows:
            text += f"Inv: {r['IV_No']} | VAT: {r['VAT_Rate']}% | Paid: {r['Paid_Amount']}\n"

    # Fetch GL Entries
    gl_query = "SELECT account_name, enty_values_DR, enty_values_CR FROM entry_details WHERE entry_jv = %s"
    gl_rows = db.execute_query(gl_query, (jv,))

    text += "\nGL Entries:\n"
    for gl in gl_rows:
        text += f"{gl['account_name']}: DR {gl['enty_values_DR']} | CR {gl['enty_values_CR']}\n"

    text += "\nDo you need to reverse this entry?"

    return {'details': text}

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
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, current_user, datetime.utcnow()))

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
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, current_user, datetime.utcnow()))

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
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, current_user, datetime.utcnow()))

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
    # We look at `invoice_oustanding` table
    query = """
        SELECT DISTINCT c.id, c.customer_name
        FROM customer c
        JOIN invoice_oustanding io ON c.id = io.invoice_buinding_Customer
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
        FROM invoice_oustanding
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
        for p in payments:
            # Get current payment to update
            cursor.execute("SELECT invoice_oustanding_Patment FROM invoice_oustanding WHERE Id = %s", (p['id'],))
            res = cursor.fetchone()
            if res:
                current_paid = float(res[0])
                new_paid = current_paid + p['amount']
                cursor.execute("UPDATE invoice_oustanding SET invoice_oustanding_Patment = %s WHERE Id = %s", (new_paid, p['id']))

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
        print(e)
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('customer_receipt'))

# --- Profit & Loss Report ---
@app.route('/profit_loss')
@login_required
@has_permission('Access_Reports')
def profit_loss():
    from_date = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))

    # Using `new_account_table` structure where P&L Category is stored in `account_name_of_catogory_PL`
    # Fetch all Income and Expense accounts with their balances in the period
    query = """
        SELECT
            na.account_name,
            na.account_name_of_catogory_PL as category,
            na.account_income,
            na.account_expenses,
            COALESCE(SUM(ed.enty_values_DR), 0) as total_dr,
            COALESCE(SUM(ed.enty_values_CR), 0) as total_cr
        FROM new_account_table na
        LEFT JOIN entry_details ed ON na.account_name = ed.account_name
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_deleted = 0
        WHERE (na.account_income = 1 OR na.account_expenses = 1)
        GROUP BY na.account_name, na.account_name_of_catogory_PL, na.account_income, na.account_expenses, na.account_hold_possion_PL
        ORDER BY na.account_hold_possion_PL, na.account_name
    """
    rows = db.execute_query(query, (from_date, to_date))

    # Process Data
    income_data = {}
    expense_data = {}
    total_income = 0
    total_expense = 0

    for r in rows:
        balance = 0
        # Calculate balance based on type (Income = CR - DR, Expense = DR - CR)
        if r['account_income'] == 1:
            balance = float(r['total_cr']) - float(r['total_dr'])
            if balance != 0:
                cat = r['category'] or "Other Income"
                if cat not in income_data: income_data[cat] = []
                income_data[cat].append({'name': r['account_name'], 'amount': balance})
                total_income += balance
        elif r['account_expenses'] == 1:
            balance = float(r['total_dr']) - float(r['total_cr'])
            if balance != 0:
                cat = r['category'] or "Operating Expenses"
                if cat not in expense_data: expense_data[cat] = []
                expense_data[cat].append({'name': r['account_name'], 'amount': balance})
                total_expense += balance

    net_profit = total_income - total_expense

    return render_template('profit_loss.html',
                           from_date=from_date,
                           to_date=to_date,
                           income_data=income_data,
                           expense_data=expense_data,
                           total_income=total_income,
                           total_expense=total_expense,
                           net_profit=net_profit)

# --- POS Settings ---
@app.route('/pos_settings', methods=['GET', 'POST'])
@login_required
@has_permission('Access_POS')
def pos_settings():
    if request.method == 'POST':
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

        # Image Handling (Optional - simplified)
        # Assuming we just keep existing if not provided or handle separately
        # For simplicity, we update text fields first.

        # Update Query
        # Assuming single row or specific ID. C# uses `id` variable.
        # We'll update the first row or specific user's row if multiple.
        # Ideally, fetch ID first.

        try:
            # Check if settings exist, else insert (though setup usually assumes existing)
            # We'll assume ID=1 for global settings or user specific.
            # C# logic seemed to fetch based on Username then update by ID.
            # Let's update all for now or specific user.

            username = session.get('username')
            db.execute_query("""
                UPDATE pose_setting_table SET
                    Select_Inventry_Location=%s, Card_Control_AC=%s, Cash_Account=%s,
                    Sales_with_market_price=%s, Sales_with_Special_price=%s, Loyalty_Price=%s, VAT_Enable=%s,
                    Footer_Message=%s, Top_Message=%s
                WHERE User_Name=%s
            """, (location, card_ac, cash_ac, market_price, special_price, loyalty_price, vat_enable, footer, top, username), commit=True)

            flash('POS Settings updated successfully.', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'danger')

        return redirect(url_for('pos_settings'))

    # GET
    username = session.get('username')
    settings = db.execute_query("SELECT * FROM pose_setting_table WHERE User_Name = %s", (username,))
    current_settings = settings[0] if settings else {}

    locations = db.execute_query("SELECT inventory_locations_name FROM inventory_locations")
    accounts = db.execute_query("SELECT account_name FROM new_account_table") # For Card/Cash selection

    return render_template('pos_settings.html',
                           settings=current_settings,
                           locations=locations,
                           accounts=accounts)

# --- Point of Sale (POS) ---
@app.route('/pos', methods=['GET', 'POST'])
@login_required
@has_permission('Access_POS')
def pos():
    if request.method == 'GET':
        # Fetch data for POS UI
        username = session.get('username')

        # Settings
        settings_res = db.execute_query("SELECT * FROM pose_setting_table WHERE User_Name = %s", (username,))
        settings = settings_res[0] if settings_res else {}

        # Items
        items = db.execute_query("SELECT inventoy_name, inventoy_code, inventoy_items_messurment_unit FROM inventoy_items WHERE active = 1")

        # Customers
        customers = db.execute_query("SELECT customer_name, Mobile_nimber FROM customer WHERE Compay_Or_Not = 0 OR Compay_Or_Not IS NULL")

        return render_template('pos.html', items=items, customers=customers, settings=settings)

@app.route('/pos/get_item_details')
@login_required
def get_pos_item_details():
    code = request.args.get('code')

    # Get Item Details + Price
    # Joined with price record
    query = """
        SELECT
            i.id, i.inventoy_name, i.inventoy_code, i.inventoy_items_messurment_unit,
            p.inventory_price_selling, p.inventory_price_profit_marging_comen,
            p.inventory_price_for_Loyality_customer, p.inventory_price_purcharsing
        FROM inventoy_items i
        LEFT JOIN inventory_price_recod p ON i.id = p.inventory_price_link
        WHERE i.inventoy_code = %s
    """
    rows = db.execute_query(query, (code,))

    if rows:
        r = rows[0]
        return {
            'id': r['id'],
            'name': r['inventoy_name'],
            'unit': r['inventoy_items_messurment_unit'],
            'price_market': float(r['inventory_price_selling'] or 0),
            'price_special': float(r['inventory_price_profit_marging_comen'] or 0),
            'price_loyalty': float(r['inventory_price_for_Loyality_customer'] or 0),
            'cost': float(r['inventory_price_purcharsing'] or 0)
        }
    return {'error': 'Item not found'}, 404

@app.route('/pos/submit_sale', methods=['POST'])
@login_required
def submit_pos_sale():
    data = request.json
    cart = data.get('cart', [])
    payment = data.get('payment', {})
    customer = data.get('customer', {})
    settings = data.get('settings', {})

    if not cart: return {'error': 'Cart is empty'}, 400

    current_user = get_current_user_id()
    today_date = date.today()

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Generate Invoice No
        cursor.execute("INSERT INTO pos_invoice_no (IV_No) VALUES ('')")
        last_id = cursor.lastrowid
        invoice_no = f"{today_date.year}POS-{last_id}"
        cursor.execute("UPDATE pos_invoice_no SET IV_No = %s WHERE Id = %s", (invoice_no, last_id))

        # 2. Create JV
        cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration) VALUES (%s, %s)", ('JV FROM POS', f"POS Sale {invoice_no}"))
        jv_no = cursor.lastrowid

        total_sale_value = 0
        total_cost_value = 0

        # 3. Process Cart Items
        for item in cart:
            total_sale_value += item['total']
            total_cost_value += (item['cost'] * item['qty'])

            # Insert into pos_sales_invoice_01
            cursor.execute("""
                INSERT INTO pos_sales_invoice_01 (
                    ItemCoude, ItemName, ItemMesurmet, SllingPrice, ItemPriceComen, ItemLoyalityPrice,
                    Sales_with_market_price_Active, Sales_with_Special_price_Active, Loyalty_Price_Active,
                    RecodeUserId, Location, AcctionDate, QuntirySale, InventoryCost, PaymentMethord,
                    CashAccountName, BankAccountName, Invoice_No, Loyalty_No, Total_Value, jv, Revers
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """, (
                item['code'], item['name'], item['unit'],
                item['price_market'], item['price_special'], item['price_loyalty'],
                settings.get('market_active', 0), settings.get('special_active', 0), settings.get('loyalty_active', 0),
                current_user, settings.get('location'), datetime.now(), item['qty'], item['cost'],
                payment.get('method'), settings.get('cash_ac'), settings.get('bank_ac'),
                invoice_no, customer.get('loyalty_no', 0), item['total'], jv_no
            ))

            # Inventory Movement OUT
            cursor.execute("""
                INSERT INTO inventory_recod (
                    inventoy_name, inventoy_code, inventory_recod_action_date,
                    inventory_recod_moument_in, inventory_recod_movment_out,
                    inventory_recod_mesrmet, inventory_recod_unit_price,
                    inventory_recod_account, inventory_recod_user_id, JV_No,
                    inventory_recod_location
                ) VALUES (%s, %s, %s, 0, %s, %s, %s, 'Cost Of Goods Sold', %s, %s, %s)
            """, (
                item['name'], item['code'], today_date, item['qty'], item['unit'], item['cost'],
                current_user, jv_no, settings.get('location')
            ))

        # 4. GL Entries
        # Debit Cash/Bank
        ac_name = settings.get('cash_ac') if payment.get('method') == 1 else settings.get('bank_ac')
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_DR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (ac_name, total_sale_value, today_date, today_date, f"POS Sale {invoice_no}", current_user, jv_no))

        # Credit Sales Account
        cursor.execute("""
            INSERT INTO entry_details (
                account_name, enty_values_CR, entry_effective_date, entry_create_date,
                entry_naration, entry_create_user, entry_jv
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('Sales', total_sale_value, today_date, today_date, f"POS Sale {invoice_no}", current_user, jv_no))

        # Cost of Goods Sold (DR COGS, CR Inventory)
        if total_cost_value > 0:
            # Debit Cost Of Goods Sold
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_DR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('Cost Of Goods Sold', total_cost_value, today_date, today_date, f"POS Sale {invoice_no} (COGS)", current_user, jv_no))

            # Credit Inventory
            cursor.execute("""
                INSERT INTO entry_details (
                    account_name, enty_values_CR, entry_effective_date, entry_create_date,
                    entry_naration, entry_create_user, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, ('Inventory', total_cost_value, today_date, today_date, f"POS Sale {invoice_no} (COGS)", current_user, jv_no))

        conn.commit()
        return {'success': True, 'invoice_no': invoice_no, 'jv': jv_no}

    except Exception as e:
        conn.rollback()
        print(e)
        return {'error': str(e)}, 500
    finally:
        cursor.close()
        conn.close()

def run_schema_migrations():
    """Checks and updates database schema for new features."""
    try:
        conn = db.get_connection()
        if not conn: return
        cursor = conn.cursor()

        # Check User_Rights columns
        cursor.execute("SHOW COLUMNS FROM User_Rights")
        columns = [row[0] for row in cursor.fetchall()]

        new_columns = [
            'Access_Inventory', 'Access_POS', 'Access_Accounting', 'Access_Reports', 'Access_Reversals'
        ]

        for col in new_columns:
            if col not in columns:
                print(f"Migrating: Adding {col} to User_Rights")
                cursor.execute(f"ALTER TABLE User_Rights ADD COLUMN {col} TINYINT DEFAULT 0")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Schema Migration Error: {e}")

def ensure_default_accounts():
    """Ensures essential General Ledger accounts exist."""
    try:
        defaults = [
            # Name, BS Position, BS Category, P&L Position, P&L Category, Type
            ('Account Payable', 4, 'Current liabilities', None, None, 'liabilities'),
            ('Account Receivable', 3, 'Current assets', None, None, 'assets'),
            ('Cost Of Goods Sold', None, None, 2, 'Cost Of Sales', 'expenses'),
            ('Sales', None, None, 1, 'Revenue', 'income'),
            ('Inventory', 3, 'Current assets', None, None, 'assets'),
            ('VAT Control', 4, 'Current liabilities', None, None, 'liabilities'),
            ('Cash In Hand', 3, 'Current assets', None, None, 'assets')
        ]

        current_user = 0 # System

        for acc in defaults:
            name, bs_pos, bs_cat, pl_pos, pl_cat, acc_type = acc
            res = db.execute_query("SELECT id FROM new_account_table WHERE account_name = %s", (name,))

            if not res:
                print(f"Creating default account: {name}")
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
                db.execute_query(query, (
                    name, bs_pos, bs_cat, pl_pos, pl_cat,
                    1 if acc_type=='income' else 0, 1 if acc_type=='expenses' else 0,
                    1 if acc_type=='assets' else 0, 1 if acc_type=='liabilities' else 0, 0,
                    date.today(), current_user, basement
                ), commit=True)
    except Exception as e:
        print(f"Error ensuring default accounts: {e}")

def create_default_user():
    """Creates a default admin user if the Login_Table is empty."""
    try:
        # Check connection first
        conn = db.get_connection()
        if not conn:
            print("WARNING: Database connection failed. Cannot create default user.")
            return

        # Check for existing users
        result = db.execute_query("SELECT COUNT(*) as count FROM Login_Table")
        if result and result[0]['count'] == 0:
            print("No users found. Creating default admin user...")
            query = """
                INSERT INTO Login_Table (User_Name, Password, User_Code, User_Active, Mobile_No, Email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # Using 'admin' / '123'
            db.execute_query(query, ('admin', '123', 'ADM001', 1, '0000000000', 'admin@example.com'), commit=True)
            print("Default user created: admin / 123")

            # Create Default Rights for Admin
            last_id_res = db.execute_query("SELECT id FROM Login_Table WHERE User_Name = 'admin'")
            if last_id_res:
                uid = last_id_res[0]['id']
                db.execute_query("""
                    INSERT INTO User_Rights (Link_To_Loging_Tabke, Add_New_User, OP_Approved, Access_Inventory, Access_POS, Access_Accounting, Access_Reports, Access_Reversals)
                    VALUES (%s, 1, 1, 1, 1, 1, 1, 1)
                """, (uid,), commit=True)

        else:
            print("Users exist in database. Skipping default user creation.")
    except Exception as e:
        print(f"Error creating default user: {e}")

if __name__ == '__main__':
    run_schema_migrations()
    create_default_user()
    ensure_default_accounts()
    app.run(debug=True, port=5000)
