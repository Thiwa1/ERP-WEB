from datetime import date

class ProfitLossReportGenerator:
    def __init__(self, db):
        self.db = db

    def generate(self, request):
        periods = self._get_profit_loss_periods(request)

        conn = self.db.get_connection()
        if not conn:
            raise Exception('Database connection failed')

        cursor = conn.cursor(dictionary=True)

        try:
            acc_map = self._fetch_profit_loss_accounts(cursor, periods)
            if not periods:
                return periods, {}, '', ''
            acc_map = self._fetch_profit_loss_data(cursor, periods, acc_map)
        finally:
            cursor.close()
            conn.close()

        report_data = self._process_profit_loss_categories(acc_map, periods)

        default_start = date.today().replace(day=1).strftime('%Y-%m-%d')
        default_end = date.today().strftime('%Y-%m-%d')

        return periods, report_data, default_start, default_end

    def _get_profit_loss_periods(self, req):
        periods = []
        if req.method == 'POST':
            starts = req.form.getlist('start_date[]')
            ends = req.form.getlist('end_date[]')
            for s, e in zip(starts, ends):
                if s and e:
                    periods.append({'start': s, 'end': e})

        if not periods:
            today = date.today()
            start = today.replace(day=1).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            periods.append({'start': start, 'end': end})

        return periods

    def _fetch_profit_loss_accounts(self, cursor, periods):
        acc_map = {}
        cursor.execute("""
            SELECT account_name, account_name_of_catogory_PL, account_hold_possion_PL, account_income, account_expenses
            FROM new_account_table
            WHERE (account_income = 1 OR account_expenses = 1) AND account_active = 1
            ORDER BY account_hold_possion_PL, account_name
        """)
        all_accounts = cursor.fetchall()

        for acc in all_accounts:
            acc_map[acc['account_name']] = {
                'meta': acc,
                'values': [0.0] * len(periods)
            }
        return acc_map

    def _fetch_profit_loss_data(self, cursor, periods, acc_map):
        if not periods:
            return acc_map

        select_clause = ["account_name"]
        params = []

        overall_start = min(p['start'] for p in periods)
        overall_end = max(p['end'] for p in periods)

        for i, p in enumerate(periods):
            select_clause.append(f"SUM(CASE WHEN entry_effective_date BETWEEN %s AND %s THEN enty_values_DR ELSE 0 END) as dr_{i}")
            select_clause.append(f"SUM(CASE WHEN entry_effective_date BETWEEN %s AND %s THEN enty_values_CR ELSE 0 END) as cr_{i}")
            params.extend([p['start'], p['end'], p['start'], p['end']])

        params.extend([overall_start, overall_end])

        query = f"""
            SELECT {', '.join(select_clause)}
            FROM entry_details
            WHERE entry_effective_date BETWEEN %s AND %s
            AND entry_deleted = 0
            GROUP BY account_name
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        for r in rows:
            name = r['account_name']
            if name in acc_map:
                is_income = acc_map[name]['meta']['account_income'] == 1
                for i in range(len(periods)):
                    dr = float(r.get(f'dr_{i}', 0) or 0)
                    cr = float(r.get(f'cr_{i}', 0) or 0)
                    val = (cr - dr) if is_income else (dr - cr)
                    acc_map[name]['values'][i] = val

        return acc_map

    def _process_profit_loss_categories(self, acc_map, periods):
        income_cats_dict = {}
        expense_cats_dict = {}

        for name, data in acc_map.items():
            if all(abs(v) < 0.01 for v in data['values']):
                continue

            cat_name = data['meta']['account_name_of_catogory_PL'] or 'Uncategorized'
            is_income = data['meta']['account_income'] == 1
            sort_order = data['meta']['account_hold_possion_PL'] or 999

            target_dict = income_cats_dict if is_income else expense_cats_dict

            if cat_name not in target_dict:
                target_dict[cat_name] = {'name': cat_name, 'order': sort_order, 'accounts': []}

            target_dict[cat_name]['accounts'].append({
                'name': name,
                'amounts': data['values']
            })

        income_categories = sorted(income_cats_dict.values(), key=lambda x: x['order'])
        expense_categories = sorted(expense_cats_dict.values(), key=lambda x: x['order'])

        for cat in income_categories:
            cat['accounts'].sort(key=lambda x: x['name'])
        for cat in expense_categories:
            cat['accounts'].sort(key=lambda x: x['name'])

        total_income = [0.0] * len(periods)
        total_expense = [0.0] * len(periods)

        for cat in income_categories:
            for acc in cat['accounts']:
                for i, v in enumerate(acc['amounts']):
                    total_income[i] += v

        for cat in expense_categories:
            for acc in cat['accounts']:
                for i, v in enumerate(acc['amounts']):
                    total_expense[i] += v

        net_profit = [i - e for i, e in zip(total_income, total_expense)]

        return {
            'income_categories': income_categories,
            'expense_categories': expense_categories,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_profit': net_profit
        }
