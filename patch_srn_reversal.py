import re

with open('app.py', 'r') as f:
    content = f.read()

route_code = """
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

if "def service_entry_reversal():" not in content:
    with open('app.py', 'a') as f:
        f.write("\n")
        f.write(route_code)
        f.write("\n")
