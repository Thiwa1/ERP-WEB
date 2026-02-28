import unittest
from unittest.mock import MagicMock, call
from datetime import date

# Import the NEW logic (simulation of what is now in app.py)
# This mimics the changes I just applied to app.py
def process_bulk_upload_optimized(db_mock, form_data, current_user):
    conn = db_mock.get_connection()
    cursor = conn.cursor()
    # conn.start_transaction() # Mocked

    today = date.today()

    names = form_data.get('account_name[]')
    types = form_data.get('account_type[]')
    cats = form_data.get('category[]')
    cfs = form_data.get('cf_category[]')
    actions = form_data.get('action[]')

    # Filter valid names to check
    valid_names = [n for i, n in enumerate(names) if actions[i] != 'skip' and n]

    # Batch Fetch Existing Accounts
    existing_map = {}
    if valid_names:
        # Mock logic: For simulation, we assume existing_rows comes from DB
        # Format strings logic
        format_strings = ','.join(['%s'] * len(valid_names))
        cursor.execute(f"SELECT id, account_name FROM new_account_table WHERE account_name IN ({format_strings})", tuple(valid_names))
        # fetchall() is mocked in the test setup
        existing_rows = cursor.fetchall() or []
        for row in existing_rows:
            existing_map[row[1]] = row[0]

    to_update = []
    to_insert = []

    # For Sub-Ledgers
    potential_banks = []
    potential_cash = []

    count = 0
    for i in range(len(names)):
        if actions[i] == 'skip': continue

        name = names[i]
        acc_type = types[i]
        cat_val = cats[i]
        cf = cfs[i]

        cat_name = None
        cat_pos = None
        is_bs = False
        is_pl = False

        if cat_val:
            parts = cat_val.split('|')
            if len(parts) == 2:
                cat_data, cat_type = parts
                cat_name, cat_pos = cat_data.split(',')
                if cat_type == 'BS': is_bs = True
                elif cat_type == 'PL': is_pl = True

        is_inc = 1 if acc_type == 'Income' else 0
        is_exp = 1 if acc_type == 'Expense' else 0
        is_ast = 1 if acc_type == 'Asset' else 0
        is_lia = 1 if acc_type == 'Liability' else 0
        is_equ = 1 if acc_type == 'Equity' else 0

        basement = 'DR' if is_ast or is_exp else 'CR'

        if name in existing_map:
            to_update.append((
                cat_pos if is_pl else None, cat_pos if is_bs else None,
                cat_name if is_pl else None, cat_name if is_bs else None,
                is_inc, is_exp, is_ast, is_lia, is_equ,
                cf, basement, existing_map[name]
            ))
        else:
            to_insert.append((
                name, cat_pos if is_pl else None, cat_pos if is_bs else None,
                cat_name if is_pl else None, cat_name if is_bs else None,
                is_inc, is_exp, is_ast, is_lia, is_equ,
                cf, today, current_user, basement
            ))

            if is_ast:
                acc_name_lower = name.lower()
                if 'bank' in acc_name_lower:
                    potential_banks.append(name)
                elif 'cash' in acc_name_lower:
                    potential_cash.append(name)

        count += 1

    # Batch Update
    if to_update:
        cursor.executemany("UPDATE ...", to_update)

    # Batch Insert
    if to_insert:
        cursor.executemany("INSERT ...", to_insert)

    # Batch Sub-Ledger (Bank)
    if potential_banks:
        format_strings = ','.join(['%s'] * len(potential_banks))
        cursor.execute(f"SELECT bank_bookcol_account_number FROM bank_book WHERE bank_bookcol_account_number IN ({format_strings})", tuple(potential_banks))
        existing_banks_rows = cursor.fetchall() or []
        existing_banks = {row[0] for row in existing_banks_rows}

        banks_to_insert = []
        for b_name in potential_banks:
            if b_name not in existing_banks:
                banks_to_insert.append((b_name, b_name, today, current_user))

        if banks_to_insert:
            cursor.executemany("INSERT INTO bank_book ...", banks_to_insert)

    # Batch Sub-Ledger (Cash)
    if potential_cash:
        format_strings = ','.join(['%s'] * len(potential_cash))
        cursor.execute(f"SELECT cash_book_account_name FROM cash_book WHERE cash_book_account_name IN ({format_strings})", tuple(potential_cash))
        existing_cash_rows = cursor.fetchall() or []
        existing_cash = {row[0] for row in existing_cash_rows}

        cash_to_insert = []
        for c_name in potential_cash:
            if c_name not in existing_cash:
                cash_to_insert.append((c_name, today, current_user))

        if cash_to_insert:
            cursor.executemany("INSERT INTO cash_book ...", cash_to_insert)

    cursor.close()
    conn.close()

class BenchmarkBulkUploadOptimized(unittest.TestCase):
    def setUp(self):
        # Setup Mock DB
        self.db_mock = MagicMock()
        self.conn_mock = MagicMock()
        self.cursor_mock = MagicMock()
        self.db_mock.get_connection.return_value = self.conn_mock
        self.conn_mock.cursor.return_value = self.cursor_mock

    def test_benchmark_optimized_implementation(self):
        num_items = 100
        data = {
            'account_name[]': [f'Account {i} Bank' for i in range(num_items)],
            'account_type[]': ['Asset'] * num_items,
            'category[]': ['Cat,1|BS'] * num_items,
            'cf_category[]': ['Op'] * num_items,
            'action[]': ['save'] * num_items
        }

        # Mock fetchall returns
        # 1. Existing accounts: None (all new)
        # 2. Existing banks: None (all new)
        self.cursor_mock.fetchall.side_effect = [[], [], []]

        process_bulk_upload_optimized(self.db_mock, data, 1)

        # Expected calls:
        # 1. Select existing accounts (1 execute)
        # 2. Executemany Insert accounts (1 executemany)
        # 3. Select existing banks (1 execute)
        # 4. Executemany Insert banks (1 executemany)
        # Total db interactions = 4 (mix of execute and executemany)

        executes = self.cursor_mock.execute.call_count
        executemanys = self.cursor_mock.executemany.call_count
        total_calls = executes + executemanys

        print(f"Optimized Implementation: Executed {total_calls} queries (Execute: {executes}, Executemany: {executemanys}) for {num_items} items.")

        # We expect drastically fewer than 400. Ideally around 4-5.
        self.assertLess(total_calls, 10)

if __name__ == '__main__':
    unittest.main()
