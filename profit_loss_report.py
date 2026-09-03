from datetime import date

class ProfitLossReportGenerator:
    def __init__(self, db):
        self.db = db

    def generate(self, request, fallback_periods=None):
        periods = self._get_profit_loss_periods(request, fallback_periods)

        conn = self.db.get_connection()
        if not conn:
            raise Exception('Database connection failed')

        cursor = conn.cursor(dictionary=True)

        try:
            acc_map = self._fetch_profit_loss_accounts(cursor, periods)
            cat_levels = self._fetch_pl_category_levels(cursor)
            subtotal_defs = self._fetch_subtotal_defs(cursor)
            if not periods:
                return periods, {}, '', ''
            acc_map = self._fetch_profit_loss_data(cursor, periods, acc_map)
            acc_map = self._fetch_sub_account_data(cursor, periods, acc_map)
        finally:
            cursor.close()
            conn.close()

        report_data = self._process_profit_loss_categories(acc_map, periods, cat_levels, subtotal_defs)

        default_start = date.today().replace(day=1).strftime('%Y-%m-%d')
        default_end = date.today().strftime('%Y-%m-%d')

        return periods, report_data, default_start, default_end

    def _get_profit_loss_periods(self, req, fallback_periods=None):
        periods = []
        # Accept periods from the form (Generate button, POST) or from query
        # parameters (CSV export link, GET) so the export matches the screen.
        source = req.form if req.method == 'POST' else req.args
        starts = source.getlist('start_date[]')
        ends = source.getlist('end_date[]')
        for s, e in zip(starts, ends):
            if s and e:
                periods.append({'start': s, 'end': e})

        # Legacy single-range GET params
        if not periods and req.args.get('from_date') and req.args.get('to_date'):
            periods.append({'start': req.args.get('from_date'), 'end': req.args.get('to_date')})

        # Nothing submitted at all (a fresh page load) — fall back to this
        # user's last-saved period set, if any, before defaulting to "this month".
        if not periods and fallback_periods:
            periods = [{'start': p['start'], 'end': p['end']} for p in fallback_periods if p.get('start') and p.get('end')]

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

    def _fetch_sub_account_data(self, cursor, periods, acc_map):
        """Attach every DEFINED sub-account (from sub_accont_for_new_account,
        linked by sub_new_account) to its main account, with the value from any
        sub-coded postings. Showing defined subs (even at 0) makes the + expander
        appear whenever a main account has sub-accounts, which is what's wanted."""
        if not periods:
            return acc_map
        n = len(periods)

        # 1. Defined active sub-accounts grouped by their main account
        defined = {}   # main_account_name -> [{code, name}]
        try:
            cursor.execute("""
                SELECT sub_new_account, sub_account_code, sub_sub_accaount_name
                FROM sub_accont_for_new_account WHERE active = 1
            """)
            for r in cursor.fetchall():
                defined.setdefault((r['sub_new_account'] or '').strip(), []).append(
                    {'code': str(r['sub_account_code']), 'name': r['sub_sub_accaount_name']})
        except Exception:
            defined = {}

        if not defined:
            return acc_map

        # 2. Values per (account, sub-code) from sub-coded entries
        select_clause = ["account_name", "entry_sub_account_code"]
        params = []
        overall_start = min(p['start'] for p in periods)
        overall_end = max(p['end'] for p in periods)
        for i, p in enumerate(periods):
            select_clause.append(f"SUM(CASE WHEN entry_effective_date BETWEEN %s AND %s THEN enty_values_DR ELSE 0 END) as dr_{i}")
            select_clause.append(f"SUM(CASE WHEN entry_effective_date BETWEEN %s AND %s THEN enty_values_CR ELSE 0 END) as cr_{i}")
            params.extend([p['start'], p['end'], p['start'], p['end']])
        params.extend([overall_start, overall_end])

        values_by = {}   # (account_name, code) -> [vals]
        try:
            cursor.execute(f"""
                SELECT {', '.join(select_clause)}
                FROM entry_details
                WHERE entry_effective_date BETWEEN %s AND %s AND entry_deleted = 0
                  AND entry_sub_account_code IS NOT NULL AND entry_sub_account_code != 0
                GROUP BY account_name, entry_sub_account_code
            """, tuple(params))
            for r in cursor.fetchall():
                name = r['account_name']
                is_income = acc_map.get(name, {}).get('meta', {}).get('account_income') == 1
                vals = []
                for i in range(n):
                    dr = float(r.get(f'dr_{i}', 0) or 0)
                    cr = float(r.get(f'cr_{i}', 0) or 0)
                    vals.append((cr - dr) if is_income else (dr - cr))
                values_by[((name or '').strip(), str(r['entry_sub_account_code']))] = vals
        except Exception:
            pass

        # 3. Attach the defined subs (with values, 0 if no coded postings)
        for name in acc_map:
            subs_def = defined.get((name or '').strip())
            if not subs_def:
                continue
            subs = [{'name': s['name'], 'code': s['code'],
                     'values': values_by.get(((name or '').strip(), s['code']), [0.0] * n)}
                    for s in subs_def]
            subs.sort(key=lambda s: str(s['name']).lower())
            acc_map[name]['sub_accounts'] = subs
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

    def _fetch_subtotal_defs(self, cursor):
        """Custom subtotal rows: {after_category: [labels]} for the P&L."""
        try:
            cursor.execute(
                "SELECT after_category, label FROM report_subtotals WHERE report_type = 'PL' ORDER BY id")
            out = {}
            for r in cursor.fetchall():
                out.setdefault(r['after_category'], []).append(r['label'])
            return out
        except Exception:
            return {}

    def _process_profit_loss_categories(self, acc_map, periods, cat_levels=None, subtotal_defs=None):
        # ONE block per category, exactly as defined on the P&L Categories page.
        # A category may contain both income and expense accounts (e.g. Revenue
        # holding Sales plus Opening Stock - Finished Goods as a deduction).
        cats_dict = {}
        cat_levels = cat_levels or {}
        subtotal_defs = subtotal_defs or {}

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
                'sub_accounts': [{'name': s['name'], 'code': s.get('code'), 'amounts': list(s['values'])}
                                 for s in data.get('sub_accounts', [])],
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
        running = [0.0] * len(periods)  # cumulative income - expense down the statement

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
                    for s in acc.get('sub_accounts', []):
                        s['amounts'] = [-v for v in s['amounts']]
                # "(Unallocated)" sub-row = the part of the account not tagged to
                # any sub-account, so the sub rows reconcile to the account total.
                if acc.get('sub_accounts'):
                    unalloc = [acc['amounts'][i] - sum(s['amounts'][i] for s in acc['sub_accounts'])
                               for i in range(len(periods))]
                    if any(abs(v) >= 0.01 for v in unalloc):
                        acc['sub_accounts'].append({'name': '(Unallocated)', 'code': None, 'amounts': unalloc})
                for i, v in enumerate(acc['amounts']):
                    cat['total'][i] += v

            # Custom subtotal rows: the running result from the top of the statement
            # down to (and including) this category — e.g. "Gross Profit"
            for i in range(len(periods)):
                running[i] += cat['total'][i] if cat['is_income'] else -cat['total'][i]
            cat['subtotal_rows'] = [{'label': lbl, 'amounts': list(running)}
                                    for lbl in subtotal_defs.get(cat['name'], [])]

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

    def _fetch_sub_account_data(self, cursor, periods, acc_map):
        # This report is already filtered to one customer's sub-account, so a
        # further sub-account breakdown does not apply here.
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
