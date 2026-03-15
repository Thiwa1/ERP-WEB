import tests.mock_env
import unittest
from unittest.mock import MagicMock
import sys

# Mock Flask and Database dependencies correctly
import app as app_module

class TestBalanceSheet(unittest.TestCase):
    def setUp(self):
        app_module.session = {'user_id': 'ADM001', 'user_pk': 1}
        self.original_execute_query = app_module.db.execute_query
        app_module.db.execute_query = MagicMock()

    def tearDown(self):
        app_module.db.execute_query = self.original_execute_query

    def test_balance_sheet_logic(self):
        assets_data = [{'category': 'A', 'name': 'Cash', 'balance': 100}]
        liabilities_data = [{'category': 'L', 'name': 'Payable', 'balance': 50}]
        equity_data = [{'category': 'E', 'name': 'Equity', 'balance': 10}]

        def side_effect(query, params=None):
            q = " ".join(query.split())
            if "account_assets = 1" in q: return assets_data
            if "account_liabilities = 1" in q: return liabilities_data
            if "account_equity = 1" in q: return equity_data
            if "(na.account_income = 1 OR na.account_expenses = 1)" in q:
                return [
                    {'account_income': 1, 'account_expenses': 0, 'account_basment': 'CR', 'total_cr': 500, 'total_dr': 0},
                    {'account_income': 0, 'account_expenses': 1, 'account_basment': 'DR', 'total_cr': 0, 'total_dr': 200}
                ]
            return []

        app_module.db.execute_query.side_effect = side_effect
        app_module.request = MagicMock()
        app_module.request.args.get.return_value = '2023-12-31'

        # In a mock environment, we can't reliably catch render_template globally because
        # it was already resolved inside app_module at import time. We must mock it directly
        # on the module.
        original_render = app_module.render_template
        app_module.render_template = MagicMock()

        try:
            func = app_module.balance_sheet
            while hasattr(func, '__wrapped__'):
                func = func.__wrapped__

            func()

            self.assertTrue(app_module.render_template.called)
            args, kwargs = app_module.render_template.call_args
            self.assertEqual(kwargs['totals']['retained_earnings'], 300.0)

        finally:
            app_module.render_template = original_render

if __name__ == '__main__':
    unittest.main()
