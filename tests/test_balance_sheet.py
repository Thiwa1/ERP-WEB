import unittest
from unittest.mock import MagicMock, patch
import sys

# 1. Mock mysql
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# 2. Mock Flask
flask_mock = MagicMock()
sys.modules['flask'] = flask_mock
sys.modules['flask.Flask'] = MagicMock()

# 3. Import app
import app as app_module

class TestBalanceSheet(unittest.TestCase):
    def setUp(self):
        app_module.session = {'user_id': 'ADM001', 'user_pk': 1}
        # The app imports Database and creates an instance 'db'.
        # We need to mock the 'execute_query' method on that instance.
        # Since we can't easily replace the instance variable inside the closure/module reliably in this hacked env,
        # we will mock the method on the existing object.
        self.original_execute_query = app_module.db.execute_query
        app_module.db.execute_query = MagicMock()
        self.mock_db_execute = app_module.db.execute_query

    def tearDown(self):
        app_module.db.execute_query = self.original_execute_query

    def test_balance_sheet_logic(self):
        # Sample Data
        assets_data = [{'category': 'A', 'name': 'Cash', 'balance': 100}]
        liabilities_data = [{'category': 'L', 'name': 'Payable', 'balance': 50}]
        equity_data = [{'category': 'E', 'name': 'Equity', 'balance': 10}]
        income_data = [{'val': 500}]
        expense_data = [{'val': 200}]

        def side_effect(query, params=None):
            q = " ".join(query.split())
            if "account_assets = 1" in q: return assets_data
            if "account_liabilities = 1" in q: return liabilities_data
            if "account_equity = 1" in q: return equity_data
            if "account_income = 1" in q: return income_data
            if "account_expenses = 1" in q: return expense_data
            return []

        self.mock_db_execute.side_effect = side_effect

        # Mock request
        flask_mock.request = MagicMock()
        flask_mock.request.args.get.return_value = '2023-12-31'
        app_module.request = flask_mock.request

        # Mock render_template
        flask_mock.render_template = MagicMock()
        app_module.render_template = flask_mock.render_template

        # Unwrap function
        func = app_module.balance_sheet
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__

        # Call
        func()

        # Assertions
        self.assertTrue(flask_mock.render_template.called, "flask.render_template was not called")

        args, kwargs = flask_mock.render_template.call_args
        self.assertEqual(args[0], 'balance_sheet.html')
        self.assertEqual(kwargs['as_at_date'], '2023-12-31')

        totals = kwargs['totals']
        self.assertEqual(totals['assets'], 100)
        self.assertEqual(totals['liabilities'], 50)
        self.assertEqual(totals['equity'], 10)
        self.assertEqual(totals['retained_earnings'], 300)

if __name__ == '__main__':
    unittest.main()
