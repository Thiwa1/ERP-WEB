import re

with open('app.py', 'r') as f:
    content = f.read()

new_cf_api = """
@app.route('/cash_flow', methods=['GET'])
@login_required
@has_permission('Access_Reports')
def cash_flow_view():
    from_date = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))
    return render_template('cash_flow.html', from_date=from_date, to_date=to_date)

@app.route('/api/cash_flow/generate', methods=['POST'])
@login_required
@has_permission('Access_Reports')
def cash_flow_generate():
    data = request.json
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    rec_only = data.get('rec_only', False)

    rec_filter = " AND ed.entry_Rec = 1 " if rec_only else ""

    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Net Profit
        net_profit_query = f'''
            SELECT
                (SELECT COALESCE(SUM(CASE
                    WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                    WHEN a.account_basment = 'DR' THEN (ed.enty_values_DR - ed.enty_values_CR)
                    ELSE 0 END), 0)
                FROM entry_details ed
                JOIN new_account_table a ON ed.account_name = a.account_name
                WHERE a.account_income = 1
                AND ed.entry_effective_date BETWEEN %s AND %s
                AND ed.entry_deleted = 0 {rec_filter}) -
                (SELECT COALESCE(SUM(CASE
                    WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                    WHEN a.account_basment = 'DR' THEN (ed.enty_values_DR - ed.enty_values_CR)
                    ELSE 0 END), 0)
                FROM entry_details ed
                JOIN new_account_table a ON ed.account_name = a.account_name
                WHERE a.account_expenses = 1
                AND ed.entry_effective_date BETWEEN %s AND %s
                AND ed.entry_deleted = 0 {rec_filter}) as NetProfit
        '''
        cursor.execute(net_profit_query, (from_date, to_date, from_date, to_date))
        net_profit_res = cursor.fetchone()
        net_profit = float(net_profit_res['NetProfit']) if net_profit_res and net_profit_res['NetProfit'] is not None else 0.0

        # 2. Adjustments
        adj_query = f'''
            SELECT a.account_name as Description,
                   cf.hold_level as HoldLevel,
                   SUM(CASE
                        WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                        WHEN a.account_basment = 'DR' THEN (ed.enty_values_DR - ed.enty_values_CR)
                        ELSE 0 END) AS Amount
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            JOIN cf_catogory cf ON a.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Adjustments'
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_deleted = 0 {rec_filter}
            GROUP BY a.account_name, cf.hold_level
            ORDER BY cf.hold_level
        '''
        cursor.execute(adj_query, (from_date, to_date))
        adj_items = [dict(r) for r in cursor.fetchall()]

        # 3. Working Capital
        wc_query = f'''
            SELECT a.account_name,
                   a.account_assets,
                   a.account_liabilities,
                   cf.hold_level as HoldLevel,
                   SUM(CASE
                        WHEN a.account_basment = 'DR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                        WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                        ELSE 0 END) AS Amount
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            JOIN cf_catogory cf ON a.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Changes In Working Capital'
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_deleted = 0 {rec_filter}
            GROUP BY a.account_name, a.account_assets, a.account_liabilities, cf.hold_level
            ORDER BY cf.hold_level
        '''
        cursor.execute(wc_query, (from_date, to_date))
        wc_raw = cursor.fetchall()
        wc_items = []
        for r in wc_raw:
            prefix = ""
            if r['account_assets'] == 1:
                prefix = "(Increase)/Decrease In "
            elif r['account_liabilities'] == 1:
                prefix = "Increase/(Decrease) In "

            wc_items.append({
                'Description': prefix + r['account_name'],
                'Amount': float(r['Amount']),
                'HoldLevel': r['HoldLevel'] or 0
            })

        # 4. Investing
        inv_query = f'''
            SELECT a.account_name as Description,
                   cf.hold_level as HoldLevel,
                   SUM(CASE
                        WHEN a.account_basment = 'DR' THEN (ed.enty_values_DR - ed.enty_values_CR) * -1
                        WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR) * -1
                        ELSE 0 END) AS Amount
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            JOIN cf_catogory cf ON a.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Investing Activities'
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_deleted = 0 {rec_filter}
            GROUP BY a.account_name, cf.hold_level
            ORDER BY cf.hold_level
        '''
        cursor.execute(inv_query, (from_date, to_date))
        inv_items = [dict(r) for r in cursor.fetchall()]

        # 5. Financing
        fin_query = f'''
            SELECT a.account_name as Description,
                   cf.hold_level as HoldLevel,
                   SUM(CASE
                        WHEN a.account_basment = 'DR' THEN (ed.enty_values_DR - ed.enty_values_CR) * -1
                        WHEN a.account_basment = 'CR' THEN (ed.enty_values_CR - ed.enty_values_DR)
                        ELSE 0 END) AS Amount
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            JOIN cf_catogory cf ON a.cf_catogory = cf.catogory_name
            WHERE cf.catogory_name = 'Financing Activities'
            AND ed.entry_effective_date BETWEEN %s AND %s
            AND ed.entry_deleted = 0 {rec_filter}
            GROUP BY a.account_name, cf.hold_level
            ORDER BY cf.hold_level
        '''
        cursor.execute(fin_query, (from_date, to_date))
        fin_items = [dict(r) for r in cursor.fetchall()]

        # 6. Cash Balances
        cash_begin_query = f'''
            SELECT COALESCE(SUM(ed.enty_values_DR - ed.enty_values_CR), 0) as val
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            WHERE (a.account_name IN (SELECT bank_bookcol_account_number FROM bank_book)
                OR a.account_name IN (SELECT cash_book_account_name FROM cash_book))
            AND ed.entry_effective_date < %s
            AND ed.entry_deleted = 0 {rec_filter}
        '''
        cursor.execute(cash_begin_query, (from_date,))
        cash_begin = float(cursor.fetchone()['val'] or 0)

        cash_end_query = f'''
            SELECT COALESCE(SUM(ed.enty_values_DR - ed.enty_values_CR), 0) as val
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            WHERE (a.account_name IN (SELECT bank_bookcol_account_number FROM bank_book)
                OR a.account_name IN (SELECT cash_book_account_name FROM cash_book))
            AND ed.entry_effective_date <= %s
            AND ed.entry_deleted = 0 {rec_filter}
        '''
        cursor.execute(cash_end_query, (to_date,))
        cash_end = float(cursor.fetchone()['val'] or 0)

        # 7. Cash Accounts Breakdown
        cash_acc_query = f'''
            SELECT a.account_name as Description,
                   SUM(ed.enty_values_DR - ed.enty_values_CR) as Amount
            FROM entry_details ed
            JOIN new_account_table a ON ed.account_name = a.account_name
            WHERE (a.account_name IN (SELECT bank_bookcol_account_number FROM bank_book)
                OR a.account_name IN (SELECT cash_book_account_name FROM cash_book))
            AND ed.entry_effective_date <= %s
            AND ed.entry_deleted = 0 {rec_filter}
            GROUP BY a.account_name
        '''
        cursor.execute(cash_acc_query, (to_date,))
        cash_acc_items = [dict(r) for r in cursor.fetchall()]

        data = {
            'NetProfit': net_profit,
            'AdjustmentItems': adj_items,
            'WorkingCapitalItems': wc_items,
            'InvestingItems': inv_items,
            'FinancingItems': fin_items,
            'CashBeginning': cash_begin,
            'CashEnding': cash_end,
            'CashAccounts': cash_acc_items
        }

        return {'success': True, 'data': data}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

    finally:
        cursor.close()
        conn.close()
"""

# Find old cash flow endpoint and replace it
# def cash_flow(): -> find until def inventory_balance
start_idx = content.find('def cash_flow():')
end_idx = content.find('# --- Inventory Balance ---')

if start_idx != -1 and end_idx != -1:
    # Also need to replace the @app.route('/cash_flow')
    route_idx = content.rfind("@app.route('/cash_flow')", 0, start_idx)
    new_content = content[:route_idx] + new_cf_api + '\n\n' + content[end_idx:]
    with open('app.py', 'w') as f:
        f.write(new_content)
    print("Replaced cash_flow endpoint logic successfully.")
else:
    print("Could not find cash_flow function.")
