from flask import Flask, render_template, request, redirect, url_for, flash
from database import Database
from datetime import datetime

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

# Helper function to get current user ID (mocked)
def get_current_user_id():
    return 5000 # Mock user ID based on C# code example

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        try:
            # Extract form data
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

            # Logic for Supplier vs Customer (Derived from C# Is_Customer = true)
            is_supplier = False
            is_customer = True

            # Validation (Basic)
            if not supplier_name or not supplier_code:
                flash('Supplier Name and Code are required.', 'danger')
                return redirect(url_for('add_customer'))

            current_user = get_current_user_id()
            current_date = datetime.now().date()

            # 1. Insert into suppliers table
            query_supplier = """
                INSERT INTO suppliers (
                    sup_id, supplier_name, supplier_code,
                    supplier_address_1, supplier_address_2, supplier_address_3, supplier_address_4,
                    suppliers_credit_fasility, suppliers_teli_1, suppliers_teli_2,
                    supplier_create_date, suppliers_create_user,
                    suppliers_last_edit_user, suppliers_last_edit_date,
                    suppliers_e_mail, suppliers_vat_regidter_no, suppliers_salution,
                    Is_Suplier, Is_Customer
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
            """
            params_supplier = (
                0, supplier_name, supplier_code,
                address_no, address_line_1, address_line_2, address_line_3,
                float(credit_limit) if credit_limit else 0.0, contact_1, contact_2,
                current_date, current_user,
                current_user, current_date,
                email, vat_no, salutation,
                1 if is_supplier else 0, 1 if is_customer else 0
            )

            # 2. Create sub-account (Logic from creat_new_account.cs / Add_New_Suplers_01.xaml.cs)
            # The C# code creates a sub account under "Account Receivable"
            query_sub_account = """
                INSERT INTO sub_accont_for_new_account (
                    id_sub, sub_sub_accaount_name, sub_new_account,
                    creat_user, creat_date, active, sub_account_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            # We need to calculate sub_account_code.
            # C# logic: "SELECT LAST_INSERT_ID()" then "sub_account_code = ast_insert_id + 10001" then UPDATE.
            # In Python, we can't easily get the ID *before* insert in a transaction flow without locking or stored proc.
            # However, `sub_accont_for_new_account` has AUTO_INCREMENT `id_sub`.
            # So we can insert with dummy code, get ID, then update.

            queries = []
            queries.append((query_supplier, params_supplier))

            # We execute the supplier insert first to make sure it works, but ideally we wrap in transaction.
            # Since my `execute_transaction` takes a list of queries, I can't get the ID in the middle easily
            # to use in the UPDATE logic for sub_account_code unless I do it procedurally.

            # Let's do it procedurally with a single connection to simulate transaction
            conn = db.get_connection()
            cursor = conn.cursor()
            try:
                conn.start_transaction()

                # Insert Supplier
                cursor.execute(query_supplier, params_supplier)

                # Insert Sub Account (Initial)
                cursor.execute(query_sub_account, (
                    0, supplier_name, "Account Receivable",
                    current_user, current_date, 1, 0
                ))
                last_sub_id = cursor.lastrowid

                # Update Sub Account Code
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

    # GET request: Load Salutations
    salutations = []
    try:
        salutations_data = db.execute_query("SELECT salutation FROM suplier_suporting_1")
        salutations = [row['salutation'] for row in salutations_data]
    except:
        pass # Handle table missing or empty

    return render_template('add_customer.html', salutations=salutations)

# Route to add new salutation (AJAX or form)
@app.route('/add_salutation', methods=['POST'])
def add_salutation():
    new_salutation = request.form.get('new_salutation')
    if new_salutation:
        try:
            db.execute_query(
                "INSERT INTO suplier_suporting_1 (id, salutation) VALUES (%s, %s)",
                (0, new_salutation),
                commit=True
            )
            flash('Salutation added.', 'success')
        except Exception as e:
            flash(f'Error adding salutation: {e}', 'danger')
    return redirect(url_for('add_customer'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
