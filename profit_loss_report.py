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
            cat_levels = self._fetch_pl_category_levels(cursor)
            if not periods:
                return periods, {}, '', ''
            acc_map = self._fetch_profit_loss_data(cursor, periods, acc_map)
        finally:
            cursor.close()
            conn.close()

        report_data = self._process_profit_loss_categories(acc_map, periods, cat_levels)

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
        try:
            cursor.execute("""
                SELECT account_name, account_name_of_catogory_PL, account_hold_possion_PL,
                       account_income, account_expenses, account_pl_sort
                FROM new_account_table
                WHERE (account_income = 1 OR account_expenses = 1) AND account_active = 1
                ORDER BY account_hold_possion_PL, COALESCE(account_pl_sort, 9999), account_name
            """)
        except Exception:
            # account_pl_sort column not migrated yet — fall back to the old ordering
            cursor.execute("""
                SELECT account_name, account_name_of_catogory_PL, account_hold_possion_PL,
                       account_income, account_expenses, NULL AS account_pl_sort
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

    def _fetch_pl_category_levels(self, cursor):
        """Authoritative {category: holding_level} from the P&L Categories table.
        The per-account copies in new_account_table go stale when a category's
        level is edited later."""
        try:
            cursor.execute("SELECT name_of_category, holding_position FROM `p&l_category`")
            out = {}
            for r in cursor.fetchall():
                try:
                    out[r['name_of_category']] = int(r['holding_position'])
                except (TypeError, ValueError):
                    out[r['name_of_category']] = 9999
            return out
        except Exception:
            return {}

    def _process_profit_loss_categories(self, acc_map, periods, cat_levels=None):
        # ONE block per category, exactly as defined on the P&L Categories page.
        # A category may contain both income and expense accounts (e.g. Revenue
        # holding Sales plus Opening Stock - Finished Goods as a deduction).
        cats_dict = {}
        cat_levels = cat_levels or {}

        for name, data in acc_map.items():
            if all(abs(v) < 0.01 for v in data['values']):
                continue

            cat_name = data['meta']['account_name_of_catogory_PL'] or 'Uncategorized'
            is_income = data['meta']['account_income'] == 1
            sort_order = cat_levels.get(cat_name)
            if sort_order is None:
                try:
                    sort_order = int(data['meta']['account_hold_possion_PL'])
                except (TypeError, ValueError):
                    sort_order = 999
            acc_sort = data['meta'].get('account_pl_sort')

            if cat_name not in cats_dict:
                cats_dict[cat_name] = {'name': cat_name, 'order': sort_order,
                                       'has_income': False, 'has_expense': False,
                                       'accounts': []}
            cat = cats_dict[cat_name]
            cat['has_income'] = cat['has_income'] or is_income
            cat['has_expense'] = cat['has_expense'] or (not is_income)
            cat['accounts'].append({
                'name': name,
                'amounts': data['values'],
                'sort': acc_sort,
                'is_income': is_income
            })

        for cat in cats_dict.values():
            cat['accounts'].sort(key=lambda a: (a['sort'] if a['sort'] is not None else 9999, a['name']))
            # A block that contains any income account renders income-style; expense
            # accounts inside it are shown as deductions (negative), so the category
            # total is the NET of the block. Pure-expense blocks stay positive/red.
            cat['is_income'] = cat['has_income']
            cat['mixed'] = cat['has_income'] and cat['has_expense']

        # The category holding level drives the WHOLE statement layout
        all_categories = sorted(cats_dict.values(), key=lambda x: (x['order'], x['name']))

        total_income = [0.0] * len(periods)
        total_expense = [0.0] * len(periods)

        for cat in all_categories:
            cat['total'] = [0.0] * len(periods)
            for acc in cat['accounts']:
                # Global totals always split by the ACCOUNT's own type
                for i, v in enumerate(acc['amounts']):
                    if acc['is_income']:
                        total_income[i] += v
                    else:
                        total_expense[i] += v
                # Display: inside an income-style block, expense accounts are deductions
                if cat['is_income'] and not acc['is_income']:
                    acc['amounts'] = [-v for v in acc['amounts']]
                for i, v in enumerate(acc['amounts']):
                    cat['total'][i] += v

        net_profit = [i - e for i, e in zip(total_income, total_expense)]

        income_categories = [c for c in all_categories if c['is_income']]
        expense_categories = [c for c in all_categories if not c['is_income']]

        return {
            'income_categories': income_categories,
            'expense_categories': expense_categories,
            'all_categories': all_categories,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_profit': net_profit
        }

class Customer_ProfitLossReportGenerator(ProfitLossReportGenerator):
    def __init__(self, db, customer_sub_account_code):
        super().__init__(db)
        self.customer_sub_account_code = customer_sub_account_code

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

        params.extend([overall_start, overall_end, self.customer_sub_account_code])

        query = f"""
            SELECT {', '.join(select_clause)}
            FROM entry_details
            WHERE entry_effective_date BETWEEN %s AND %s
            AND entry_deleted = 0
            AND entry_sub_account_code = %s
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
