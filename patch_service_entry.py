import json

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



@app.route('/service_entry_reversal')
@login_required
@has_permission('Access_Reversals')
def service_entry_reversal():
    # Fetch recent Service Entries (from suppliers_invoice_data & jv_numbers)
    # We look for outstanding invoices that have not been deleted
    query = \"\"\"
        SELECT
            s.suppliers_invoice_JV as jv,
            j.jv_user_code,
            sup.supplier_name as SupplierName,
            s.suppliers_invoice_number as InvoiceNo,
            s.suppliers_invoice_date as Date,
            s.suppliers_invoice_total_oustanding as Amount
        FROM suppliers_invoice_data s
        JOIN jv_numbers j ON s.suppliers_invoice_JV = j.jv_id
        JOIN suppliers sup ON s.suppliers_invoice_buinding_supplier = sup.sup_id
        WHERE s.suppliers_oustanding_delete = 0
        AND j.jv_user_code LIKE 'JV FORM SEN INVOICE%'
        ORDER BY s.s_i_id DESC
        LIMIT 50
    \"\"\"
    rows = db.execute_query(query)
    return render_template('service_entry_reversal.html', rows=rows)

@app.route('/service_entry_reversal/process', methods=['POST'])
@login_required
def service_entry_reversal_process():
    jv = request.form.get('jv')
    if not jv:
        flash('No transaction selected', 'danger')
        return redirect(url_for('service_entry_reversal'))

    current_user = get_current_user_id()

    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # 1. Security Check: Bank Reconciled?
        cursor.execute("SELECT COUNT(*) FROM entry_details WHERE entry_jv = %s AND entry_Rec = 1", (jv,))
        if cursor.fetchone()[0] > 0:
            flash('Cannot reverse: Transaction has been Bank Reconciled.', 'danger')
            return redirect(url_for('service_entry_reversal'))

        # 2. Security Check: Payments Made?
        cursor.execute("SELECT suppliers_invoice_total_payment FROM suppliers_invoice_data WHERE suppliers_invoice_JV = %s AND suppliers_oustanding_delete = 0", (jv,))
        inv_res = cursor.fetchone()
        if not inv_res:
            flash('Service Entry not found or already deleted.', 'danger')
            return redirect(url_for('service_entry_reversal'))

        if inv_res[0] > 0:
            flash('Cannot reverse: Payments have been made against this invoice. Reverse payments first.', 'danger')
            return redirect(url_for('service_entry_reversal'))

        conn.start_transaction()

        # 3. Reverse GL Entries
        cursor.execute("CALL JV_Entry_Revers(%s, %s, %s)", (jv, session.get("user_pk"), datetime.utcnow().strftime("%Y-%m-%d")))

        # 4. Reverse Supplier Liability (Delete Outstanding)
        cursor.execute("UPDATE suppliers_invoice_data SET suppliers_oustanding_delete = 1 WHERE suppliers_invoice_JV = %s", (jv,))

        conn.commit()
        flash(f'Service Entry (JV: {jv}) reversed successfully.', 'success')

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error reversing Service Entry: {str(e)}', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('service_entry_reversal'))
"""

if "def service_entry():" not in content:
    idx = content.rfind("if __name__ == '__main__':")
    if idx != -1:
        new_content = content[:idx] + route_code + "\n\n" + content[idx:]
        with open('app.py', 'w') as f:
            f.write(new_content)
