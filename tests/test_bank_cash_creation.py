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

if __name__ == '__main__':
    unittest.main()
