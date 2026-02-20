import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from datetime import date

class TestBankCashCreation(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_ensure_default_categories(self):
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate missing categories (always return None for SELECT id)
        mock_cursor.fetchone.return_value = None

        app_module.ensure_default_categories()

        # Verify 'Current assets' insertion
        found = False
        for call in mock_cursor.execute.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO balance_sheet_category" in query:
                params = args[1]
                if params[0] == "Current assets" and params[1] == 3:
                    found = True
                    break

        self.assertTrue(found, "Should insert 'Current assets' at position 3")

    def test_ensure_default_accounts_ids(self):
        # Verify ensuring accounts uses correct IDs (e.g. 6 for Current Liabilities)

        # Simulate account not existing (db.execute_query returns empty list)
        self.mock_db.execute_query.return_value = []

        app_module.ensure_default_accounts()

        # Check Account Payable insertion
        found_ap = False
        for call in app_module.db.execute_query.call_args_list: # Wait, ensure_default_accounts uses db.execute_query directly
             # app.py: db.execute_query(query, (...), commit=True)
             pass

        # Wait, ensure_default_accounts calls `db.execute_query`.
        # I mocked `app_module.db`. So `db.execute_query` is a mock.

        for call in self.mock_db.execute_query.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO new_account_table" in query:
                params = args[1]
                # params: name, bs_pos, bs_cat, ...
                if params[0] == "Account Payable":
                    # Check bs_pos (index 1)
                    if params[1] == 6:
                        found_ap = True

        self.assertTrue(found_ap, "Account Payable should use BS Position 6")

    def test_create_bank_account_route(self):
        # Test that posting to /create_bank_account updates both tables
        app_module.app.config['TESTING'] = True
        client = app_module.app.test_client()

        with client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        with patch('app.check_permission', return_value=True):
            # Mock DB connection
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Setup fetchone for existence checks (return None so it creates)
            mock_cursor.fetchone.return_value = None

            # Setup balance sheet category search to return something valid (id=3)
            # Actually code calls fetchone() for checking account existence first (None)
            # Then calls fetchone() for category position (needs to return [3])
            # We can use side_effect for fetchone
            mock_cursor.fetchone.side_effect = [None, [3], None] # 1. Acc exists? No. 2. Cat Pos? 3. 3. Bank Book insert? (No return needed)

            data = {
                'account_number': 'HNB-1001',
                'bank_name': 'Hatton National Bank'
            }

            response = client.post('/create_bank_account', data=data, follow_redirects=True)

            self.assertIn(b'New bank account created', response.data)

            # Verify Inserts
            gl_insert = False
            bank_insert = False

            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                query = args[0]

                if "INSERT INTO new_account_table" in query:
                    params = args[1]
                    if params[0] == 'HNB-1001': gl_insert = True

                if "INSERT INTO bank_book" in query:
                    params = args[1]
                    # params: acc_no, bank_name, date, user
                    if params[0] == 'HNB-1001' and params[1] == 'Hatton National Bank':
                        bank_insert = True

            self.assertTrue(gl_insert, "Should insert into GL")
            self.assertTrue(bank_insert, "Should insert into Bank Book")

    def test_create_cash_account_route(self):
        # Test that posting to /create_cash_account updates both tables
        app_module.app.config['TESTING'] = True
        client = app_module.app.test_client()

        with client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        with patch('app.check_permission', return_value=True):
            # Mock DB connection
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # 1. Acc Exists? -> None
            # 2. Cat Pos? -> [3]
            mock_cursor.fetchone.side_effect = [None, [3], None]

            data = {
                'account_name': 'Petty Cash 2'
            }

            response = client.post('/create_cash_account', data=data, follow_redirects=True)

            self.assertIn(b'New cash account created', response.data)

            # Verify Inserts
            gl_insert = False
            cash_insert = False

            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                query = args[0]

                if "INSERT INTO new_account_table" in query:
                    params = args[1]
                    if params[0] == 'Petty Cash 2': gl_insert = True

                if "INSERT INTO cash_book" in query:
                    params = args[1]
                    if params[0] == 'Petty Cash 2':
                        cash_insert = True

            self.assertTrue(gl_insert, "Should insert into GL")
            self.assertTrue(cash_insert, "Should insert into Cash Book")

if __name__ == '__main__':
    unittest.main()
