import sys
import unittest
from unittest.mock import MagicMock, patch

# --- Mocking Libraries BEFORE import ---
# We must mock flask and mysql.connector because they are not installed in this environment.
# This global patching is necessary for app.py to import successfully.
mock_flask = MagicMock()
mock_mysql = MagicMock()
mock_mysql_connector = MagicMock()

# Mock Flask class and instance
mock_app = MagicMock()
mock_flask.Flask.return_value = mock_app

# Handle @app.route decorator (Pass-through)
def route_decorator(*args, **kwargs):
    def wrapper(f):
        return f
    return wrapper
mock_app.route.side_effect = route_decorator

# Mock other Flask objects
mock_request = MagicMock()
mock_session = {}
mock_flask.request = mock_request
mock_flask.session = mock_session
mock_flask.render_template = MagicMock()
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()
mock_flask.flash = MagicMock()

# Apply mocks to sys.modules
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql_connector

# --- Import App ---
import app

# Helper class to mock request.form behavior (dict-like + getlist)
class MockForm(dict):
    def getlist(self, key):
        # In Flask, getlist returns a list of values for the key
        # We store the list directly in the dict for simplicity in tests
        val = self.get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]

class TestProfitLoss(unittest.TestCase):
    def setUp(self):
        # Reset app state
        app.app_initialized = True

        # Reset Mocks
        app.db = MagicMock() # Mock the Database instance in app
        mock_flask.render_template.reset_mock()
        mock_flask.request.reset_mock()

        # Setup Session
        app.session.clear()
        app.session['user_id'] = 'admin'
        app.session['user_pk'] = 1

        # Patch check_permission to always allow
        self.permission_patcher = patch('app.check_permission', return_value=True)
        self.mock_check_permission = self.permission_patcher.start()

    def tearDown(self):
        self.permission_patcher.stop()

    def test_profit_loss_default_get(self):
        """Test GET request defaults to current month and calculates correctly."""
        # Setup Request
        mock_flask.request.method = 'GET'
        mock_flask.request.form = MockForm() # Empty form

        # Mock DB Cursor
        mock_conn = MagicMock()
        app.db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # 1. First fetchall call: Return Accounts
        accounts_data = [
            {'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_hold_possion_PL': 1, 'account_income': 1, 'account_expenses': 0},
            {'account_name': 'COGS', 'account_name_of_catogory_PL': 'Cost of Sales', 'account_hold_possion_PL': 2, 'account_income': 0, 'account_expenses': 1},
            {'account_name': 'Rent', 'account_name_of_catogory_PL': 'Admin Exp', 'account_hold_possion_PL': 3, 'account_income': 0, 'account_expenses': 1}
        ]

        # 2. Second fetchall call: Return Entries for the period
        entries_data = [
            {'account_name': 'Sales', 'dr_0': 0, 'cr_0': 1000},  # Income = 1000
            {'account_name': 'COGS', 'dr_0': 600, 'cr_0': 0},    # Expense = 600
            {'account_name': 'Rent', 'dr_0': 100, 'cr_0': 0}     # Expense = 100
        ]

        mock_cursor.fetchall.side_effect = [accounts_data, entries_data]

        # Execute
        app.profit_loss()

        # Assertions
        args, kwargs = mock_flask.render_template.call_args
        self.assertEqual(args[0], 'profit_loss.html')

        context = kwargs
        report_data = context['report_data']

        # Verify Totals
        self.assertEqual(report_data['total_income'][0], 1000.0)
        self.assertEqual(report_data['total_expense'][0], 700.0)
        self.assertEqual(report_data['net_profit'][0], 300.0)

    def test_profit_loss_multi_period_post(self):
        """Test POST with multiple periods."""
        # Setup Request
        mock_flask.request.method = 'POST'
        mock_flask.request.form = MockForm({
            'start_date[]': ['2023-01-01', '2023-02-01'],
            'end_date[]': ['2023-01-31', '2023-02-28']
        })

        # Mock DB
        mock_conn = MagicMock()
        app.db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Data
        accounts_data = [
            {'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_hold_possion_PL': 1, 'account_income': 1, 'account_expenses': 0},
            {'account_name': 'COGS', 'account_name_of_catogory_PL': 'Cost of Sales', 'account_hold_possion_PL': 2, 'account_income': 0, 'account_expenses': 1}
        ]

        # Period 1 Data (Jan)
        p1_data = [
            {'account_name': 'Sales', 'dr_0': 0, 'cr_0': 1000, 'dr_1': 0, 'cr_1': 1500},
            {'account_name': 'COGS', 'dr_0': 400, 'cr_0': 0, 'dr_1': 700, 'cr_1': 0}
        ]

        mock_cursor.fetchall.side_effect = [accounts_data, p1_data]

        # Execute
        app.profit_loss()

        # Verify
        args, kwargs = mock_flask.render_template.call_args
        report_data = kwargs['report_data']

        # Check Period 1
        self.assertEqual(report_data['total_income'][0], 1000.0)
        self.assertEqual(report_data['total_expense'][0], 400.0)

        # Check Period 2
        self.assertEqual(report_data['total_income'][1], 1500.0)
        self.assertEqual(report_data['total_expense'][1], 700.0)

    def test_profit_loss_empty_data(self):
        """Test with accounts but no transactions."""
        mock_flask.request.method = 'GET'
        mock_flask.request.form = MockForm()

        mock_conn = MagicMock()
        app.db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        accounts_data = [
            {'account_name': 'Sales', 'account_name_of_catogory_PL': 'Revenue', 'account_hold_possion_PL': 1, 'account_income': 1, 'account_expenses': 0}
        ]

        # No entries returned for the period
        entries_data = []

        mock_cursor.fetchall.side_effect = [accounts_data, entries_data]

        app.profit_loss()

        args, kwargs = mock_flask.render_template.call_args
        report_data = kwargs['report_data']

        self.assertEqual(report_data['total_income'][0], 0.0)
        self.assertEqual(report_data['net_profit'][0], 0.0)

if __name__ == '__main__':
    unittest.main()
