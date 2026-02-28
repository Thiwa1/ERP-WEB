import unittest
from unittest.mock import MagicMock, call
from datetime import date

# Mock implementation of the logic found in app.py
def process_bulk_upload_original(db_mock, form_data, current_user):
    conn = db_mock.get_connection()
    cursor = conn.cursor()
    # conn.start_transaction() # Mocked

    today = date.today()

    names = form_data.get('account_name[]')
    types = form_data.get('account_type[]')
    cats = form_data.get('category[]')
    cfs = form_data.get('cf_category[]')
    actions = form_data.get('action[]')

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

        # Check existence
        cursor.execute("SELECT id FROM new_account_table WHERE account_name = %s", (name,))
        exists = cursor.fetchone()

        if exists:
            # Update
            cursor.execute("UPDATE new_account_table SET ... WHERE id=%s", (exists[0],))
        else:
            # Insert
            cursor.execute("INSERT INTO new_account_table (...) VALUES (%s, ...)", (name,))

            # Auto-create Bank/Cash Book entries
            if is_ast:
                acc_name_lower = name.lower()
                if 'bank' in acc_name_lower:
                    cursor.execute("SELECT bank_id FROM bank_book WHERE bank_bookcol_account_number = %s", (name,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO bank_book ...")
                elif 'cash' in acc_name_lower:
                    cursor.execute("SELECT cash_id FROM cash_book WHERE cash_book_account_name = %s", (name,))
                    if not cursor.fetchone():
                        cursor.execute("INSERT INTO cash_book ...")

        count += 1

    # conn.commit()
    cursor.close()
    conn.close()

class TestBulkUploadPerformance(unittest.TestCase):
    def test_query_count(self):
        # Setup Mock DB
        db_mock = MagicMock()
        conn_mock = MagicMock()
        cursor_mock = MagicMock()
        db_mock.get_connection.return_value = conn_mock
        conn_mock.cursor.return_value = cursor_mock

        # Mock fetchone to simulate mix of existing and new
        # Let's say every even index exists, odd does not
        # side_effect needs to handle multiple calls.
        # 1. SELECT id FROM new_account -> exists/None
        # 2. If new and asset -> SELECT bank/cash -> exists/None

        # Scenario: 10 items.
        # 0: Exists -> Update
        # 1: New (Bank) -> Insert -> Check Bank -> Insert Bank
        # 2: Exists -> Update
        # 3: New (Cash) -> Insert -> Check Cash -> Insert Cash
        # ...

        num_items = 100
        data = {
            'account_name[]': [f'Account {i} Bank' for i in range(num_items)],
            'account_type[]': ['Asset'] * num_items,
            'category[]': ['Cat,1|BS'] * num_items,
            'cf_category[]': ['Op'] * num_items,
            'action[]': ['save'] * num_items
        }

        # Logic for side_effect is complex because calls depend on flow.
        # Easier to just count total calls roughly or just mock return values to always follow longest path
        # If we return None for existence, it does Insert path.
        cursor_mock.fetchone.return_value = None

        process_bulk_upload_original(db_mock, data, 1)

        # Analyze call count
        # For each item (since all are New Asset Bank):
        # 1. SELECT account (1)
        # 2. INSERT account (1)
        # 3. SELECT bank (1)
        # 4. INSERT bank (1)
        # Total = 4 per item = 400 calls.

        print(f"Total execute calls for {num_items} items: {cursor_mock.execute.call_count}")
        self.assertEqual(cursor_mock.execute.call_count, num_items * 4)

if __name__ == '__main__':
    unittest.main()
