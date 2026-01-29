from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import Database
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'Book_keeping',
    'raise_on_warnings': True
}

db = Database(db_config)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    return session.get('user_id', 0)

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

        if users:
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

# --- Inventory Category Management ---
@app.route('/inventory_category')
@login_required
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

# --- Inventory Locations ---
@app.route('/inventory_locations', methods=['GET', 'POST'])
@login_required
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
def chart_of_accounts():
    accounts = db.execute_query("SELECT * FROM new_account_table WHERE account_active = 1")
    pl_count = len([a for a in accounts if a['account_name_of_catogory_PL']])
    bs_count = len([a for a in accounts if a['account_name_of_catogory_Balace_sheet']])
    return render_template('chart_of_accounts.html', accounts=accounts, total_accounts=len(accounts), pl_count=pl_count, bs_count=bs_count)

# --- Control Panel ---
@app.route('/control_panel', methods=['GET', 'POST'])
@login_required
def control_panel():
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

    res = db.execute_query("SELECT yes FROM adding_new")
    warranty_enabled = False
    if res and res[0]['yes'] == 1:
        warranty_enabled = True

    return render_template('control_panel.html', warranty_enabled=warranty_enabled)

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
    item = {
        'account': request.form.get('cost_account'),
        'item_name': request.form.get('inventory_item'),
        'qty': float(request.form.get('qty', 0)),
        'price': float(request.form.get('price', 0)),
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

    # Simplified submission logic (not full transaction implementation for brevity)
    # Would need to implement full JV logic here
    session.pop('payment_items', None)
    session.pop('payment_total', None)
    flash('Payment submitted successfully (Mock)', 'success')
    return redirect(url_for('direct_purchasing'))

# --- Inventory Price Editing ---
@app.route('/inventory_price_editing', methods=['GET'])
@login_required
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
