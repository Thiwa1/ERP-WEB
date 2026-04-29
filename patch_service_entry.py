import re

with open('app.py', 'r') as f:
    content = f.read()

route_code = """
@app.route('/service_entry', methods=['GET'])
@login_required
@has_permission('Access_Accounting')
def service_entry():
    suppliers = db.execute_query("SELECT sup_id, supplier_name, supplier_code FROM suppliers WHERE Is_Suplier = 1")
    accounts = db.execute_query(\"\"\"
        SELECT account_name
        FROM new_account_table
        WHERE account_active = 1 AND (account_income = 1 OR account_expenses = 1)
    \"\"\")
    sub_accounts = db.execute_query("SELECT sub_account_code, sub_sub_accaount_name FROM sub_accont_for_new_account WHERE active = 1")
    jobs = db.execute_query("SELECT job_number FROM jobs_unit WHERE job_finsh = 0 AND job_cancell = 0")

    return render_template('service_entry.html',
                           suppliers=suppliers,
                           accounts=accounts,
                           sub_accounts=sub_accounts,
                           jobs=jobs,
                           today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/service_entry/save', methods=['POST'])
@login_required
@has_permission('Access_Accounting')
def save_service_entry():
    try:
        supplier_id = request.form.get('supplier_id')
        effective_date = request.form.get('effective_date')
        invoice_number = request.form.get('invoice_number')
        invoice_date = request.form.get('invoice_date')
        due_date = request.form.get('due_date')
        main_narration = request.form.get('main_narration')
        header_job = request.form.get('header_job_number')
        include_vat = request.form.get('include_vat') == '1'
        vat_rate = parse_float(request.form.get('vat_rate')) if include_vat else 0.0
        entries_json = request.form.get('entries_json')
        total_amount = parse_float(request.form.get('total_amount'))

        entries = json.loads(entries_json) if entries_json else []

        if not entries:
            flash('No entries provided', 'danger')
            return redirect(url_for('service_entry'))

        if not supplier_id or not invoice_number:
            flash('Supplier and Invoice Number are required', 'danger')
            return redirect(url_for('service_entry'))

        current_user = get_current_user_id()
        current_user_pk = get_current_user_pk()

        conn = db.get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        try:
            # 1. Generate JV Number
            cursor.execute("INSERT INTO jv_numbers (jv_user_code, jv_naration, status) VALUES (%s, %s, %s)",
                           ("JV FORM SEN INVOICE", main_narration, 1))
            jv_no = cursor.lastrowid

            # Get Supplier Details
            cursor.execute("SELECT supplier_code FROM suppliers WHERE sup_id = %s", (supplier_id,))
            sup_res = cursor.fetchone()
            supplier_code = sup_res[0] if sup_res else ""

            # 2. Insert into suppliers_invoice_data
            cursor.execute(\"\"\"
                INSERT INTO suppliers_invoice_data (
                    suppliers_code, suppliers_invoice_number, suppliers_invoice_date,
                    suppliers_invoice_total_oustanding, suppliers_invoice_total_payment,
                    suppliers_invoice_final_date, suppliers_invoice_buinding_supplier,
                    suppliers_invoice_JV, suppliers_VAT_rate
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            \"\"\", (
                supplier_code, invoice_number, invoice_date,
                total_amount, 0,
                due_date, supplier_id,
                jv_no, vat_rate
            ))

            # 3. Journal Entries
            # Credit Account Payable
            cursor.execute(\"\"\"
                INSERT INTO entry_details (
                    entry_account_namae, entry_account_code, entry_value_dr, enty_values_CR,
                    entry_effected_date, entry_create_date, entry_naration, entry_created_user,
                    entry_job_number, entry_sub_account_code, entry_jv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            \"\"\", (
                'Account Payable', 0, 0, total_amount,
                effective_date, date.today(), main_narration, current_user_pk,
                header_job if header_job else None, 0, jv_no
            ))

            # Debit VAT Control if applicable
            total_dr_base = sum(parse_float(e['dr']) for e in entries)
            if include_vat and vat_rate > 0:
                vat_amount = total_dr_base * (vat_rate / 100.0)
                cursor.execute(\"\"\"
                    INSERT INTO entry_details (
                        entry_account_namae, entry_account_code, entry_value_dr, enty_values_CR,
                        entry_effected_date, entry_create_date, entry_naration, entry_created_user,
                        entry_job_number, entry_sub_account_code, entry_jv, entry_VAT
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                \"\"\", (
                    'VAT Control', 0, vat_amount, 0,
                    effective_date, date.today(), main_narration, current_user_pk,
                    header_job if header_job else None, 0, jv_no, vat_rate
                ))

            # Debit Expense/P&L Accounts
            for e in entries:
                sub_code = 0
                if e.get('sub_account'):
                    parts = e['sub_account'].split(' - ')
                    if parts: sub_code = parts[0]

                job_no = e.get('job_no') if e.get('job_no') else None

                cursor.execute(\"\"\"
                    INSERT INTO entry_details (
                        entry_account_namae, entry_account_code, entry_value_dr, enty_values_CR,
                        entry_effected_date, entry_create_date, entry_naration, entry_created_user,
                        entry_job_number, entry_sub_account_code, entry_jv
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                \"\"\", (
                    e['account'], 0, e['dr'], 0,
                    effective_date, date.today(), e['memo'], current_user_pk,
                    job_no, sub_code, jv_no
                ))

            conn.commit()
            flash(f'Service Entry / Supplier Liability saved successfully. JV: {jv_no}', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Database error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        flash(f'Error saving Service Entry: {str(e)}', 'danger')

    return redirect(url_for('service_entry'))
"""

if "def service_entry():" not in content:
    with open('app.py', 'a') as f:
        f.write("\n")
        f.write(route_code)
        f.write("\n")
