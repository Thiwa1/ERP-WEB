import re

def apply_patch():
    with open('app.py', 'r') as f:
        content = f.read()

    new_routes = """
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
        WHERE (na.account_income = 1 OR na.account_expenses = 1 OR na.account_cost_of_good_solds = 1)
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
"""

    # Insert it before the @app.route('/profit_loss') which is at the end of the pl_custom block
    content = content.replace("@app.route('/profit_loss', methods=['GET', 'POST'])", new_routes + "\n@app.route('/profit_loss', methods=['GET', 'POST'])")

    with open('app.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    apply_patch()
