import sys
import os
from unittest.mock import MagicMock, patch

# Add current directory to path so app can be imported
sys.path.append(os.getcwd())

# Mock Flask and MySQL Connector BEFORE importing app/database
# This is necessary because these modules are not available in the test environment
sys.modules['flask'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Setup Flask Mock to behave correctly for decorators
mock_flask_app = MagicMock()
# Configure route decorator to return the function unchanged
mock_flask_app.route.return_value = lambda f: f
# Configure context_processor and template_filter decorators too
mock_flask_app.context_processor.return_value = lambda f: f
mock_flask_app.template_filter.return_value = lambda f: f

sys.modules['flask'].Flask.return_value = mock_flask_app

import unittest
import app as app_module

class TestChartOfAccounts(unittest.TestCase):
    def setUp(self):
        # We need to ensure app.db is mocked
        self.mock_db = MagicMock()
        app_module.db = self.mock_db
        # Ensure initialization doesn't run again or crash
        app_module.app_initialized = True

        # Mock session proxy
        self.mock_session = MagicMock()
        app_module.session = self.mock_session
        self.mock_session.get.return_value = 1 # user_id

        self.mock_session.__contains__.return_value = True

        # Setup db for check_permission
        def side_effect(query, params=None, commit=False):
            if "SELECT Access_Accounting FROM User_Rights" in query:
                return [{'Access_Accounting': 1}]
            return []

        self.mock_db.execute_query.side_effect = side_effect

    @patch('app.render_template')
    def test_chart_of_accounts_counts(self, mock_render):
        # Setup mock data
        accounts = [
            {'id': 1, 'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_name_of_catogory_Balace_sheet': None, 'account_active': 1},
            {'id': 2, 'account_name': 'Cost of Sales', 'account_name_of_catogory_PL': 'Cost of sales', 'account_name_of_catogory_Balace_sheet': None, 'account_active': 1},
            {'id': 3, 'account_name': 'Cash', 'account_name_of_catogory_PL': None, 'account_name_of_catogory_Balace_sheet': 'Current Assets', 'account_active': 1},
            {'id': 4, 'account_name': 'Bank', 'account_name_of_catogory_PL': None, 'account_name_of_catogory_Balace_sheet': 'Current Assets', 'account_active': 1},
            {'id': 5, 'account_name': 'Capital', 'account_name_of_catogory_PL': None, 'account_name_of_catogory_Balace_sheet': 'Equity', 'account_active': 1},
            {'id': 6, 'account_name': 'Hybrid', 'account_name_of_catogory_PL': 'Other Income', 'account_name_of_catogory_Balace_sheet': 'Other Assets', 'account_active': 1},
            {'id': 7, 'account_name': 'Uncategorized', 'account_name_of_catogory_PL': None, 'account_name_of_catogory_Balace_sheet': None, 'account_active': 1},
        ]

        def db_query(query, params=None, commit=False):
            if "SELECT Access_Accounting FROM User_Rights" in query:
                return [{'Access_Accounting': 1}]
            if "SELECT * FROM new_account_table WHERE account_active = 1" in query:
                return accounts
            return []

        self.mock_db.execute_query.side_effect = db_query

        mock_render.return_value = "Rendered"

        # IMPORTANT: Manually unwrap the decorators to test the core logic!
        original_func = app_module.chart_of_accounts

        while hasattr(original_func, '__wrapped__'):
            original_func = original_func.__wrapped__

        # Call the unwrapped function
        original_func()

        # Verify
        self.assertTrue(mock_render.called, "render_template was not called")
        args, kwargs = mock_render.call_args
        self.assertEqual(args[0], 'chart_of_accounts.html')
        self.assertEqual(kwargs['total_accounts'], 7)
        self.assertEqual(kwargs['pl_count'], 3)
        self.assertEqual(kwargs['bs_count'], 4)

if __name__ == '__main__':
    unittest.main()
