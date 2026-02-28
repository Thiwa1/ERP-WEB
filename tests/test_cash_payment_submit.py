
import unittest
from unittest.mock import MagicMock, patch
import sys

# 1. Mock 'flask' and 'mysql.connector' BEFORE importing app
mock_flask = MagicMock()
mock_mysql = MagicMock()
mock_mysql_connector = MagicMock()

# Configure Flask Mock
mock_app = MagicMock()
mock_flask.Flask.return_value = mock_app

# Request Mock (Global Stub)
request_stub = MagicMock()
mock_flask.request = request_stub

# Other mocks
mock_flask.session = {}
mock_flask.url_for = MagicMock(return_value='/url')
mock_flask.redirect = MagicMock(return_value='redirected')
mock_flask.flash = MagicMock()
mock_flask.render_template = MagicMock()
mock_flask.make_response = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql_connector

# 2. Import app
import app as app_module

# The failure `AttributeError: __globals__` on `app_module.cash_payment_submit` means
# `cash_payment_submit` IS A MOCK OBJECT!
# Why?
# Did we mock `app_module` somewhere?
# No.
# `login_required` decorator wraps `cash_payment_submit`.
# Is `login_required` a mock?
# `app.py`: `def login_required(f): ...`
# It returns `decorated_function`.
# If `flask` mocks were active when `app.py` was imported, `wraps` (functools) might have behaved normally.
# UNLESS `app.py` failed to import properly and we got a mock module?
# Or `mock_flask.Flask` returns a mock, but `app = Flask(__name__)` is fine.

# Wait, `app.py` code:
# @app.route(...)
# @login_required
# def cash_payment_submit(): ...

# `app.route` is a decorator.
# `mock_app.route` is a MagicMock.
# When used as `@app.route(...)`, it returns a decorator function.
# This decorator function is called with `cash_payment_submit`.
# MagicMock decorator returns... a MagicMock!
# So `cash_payment_submit` BECOMES a MagicMock because `app.route` mock replaced it!

# FIX: `mock_app.route` should behave like a pass-through decorator.
# We need to configure `mock_app.route` to return a decorator that returns the function.

def route_side_effect(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_app.route.side_effect = route_side_effect

# Re-import app to apply the fix to decorators
# We need to reload because `app.py` ran once and defined functions as mocks.
import importlib
importlib.reload(app_module)

class TestCashPaymentSubmit(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Reset Session
        app_module.session.clear()
        app_module.session.update({'user_id': 'test_user', 'user_pk': 1})

        mock_flask.flash.reset_mock()

    def test_cash_payment_submit_success(self):
        form_data = {
            'supplier': 'Test Supplier',
            'cash_account': 'Petty Cash',
            'payment_date': '2023-10-27',
            'narration': 'Test Payment',
            'wht_amount': '10',
            'payment_123': '1000'
        }

        req_mock = MagicMock()
        req_mock.form = form_data
        req_mock.method = 'POST'

        self.mock_cursor.fetchone.side_effect = [
            (100,), (5001,), (1000,)
        ]
        self.mock_cursor.lastrowid = 2023

        # Inject request into globals. Now it should work because function is real.
        # However, `login_required` wraps it. `__globals__` is on the wrapper.
        # `decorated_function` (from login_required) is what `cash_payment_submit` refers to.
        # It should have `__globals__`.
        app_module.cash_payment_submit.__globals__['request'] = req_mock

        with patch('app.get_current_user_id', return_value=1):
            app_module.cash_payment_submit()

        # Verify
        self.mock_cursor.execute.assert_any_call(
            "INSERT INTO cash_voucher_no (id, cash_voucher_link, cash_voucher_number) VALUES (0, %s, %s)",
            ('Petty Cash', 101)
        )
        self.mock_conn.commit.assert_called()
        flashed = [c[0][0] for c in mock_flask.flash.call_args_list]
        self.assertTrue(any("Cash Payment processed successfully" in msg for msg in flashed))

    def test_cash_payment_submit_missing_fields(self):
        form_data = {'cash_account': 'Petty Cash'}
        req_mock = MagicMock()
        req_mock.form = form_data
        req_mock.method = 'POST'

        app_module.cash_payment_submit.__globals__['request'] = req_mock

        app_module.cash_payment_submit()

        mock_flask.flash.assert_called_with('Missing supplier or cash account', 'danger')
        self.mock_conn.commit.assert_not_called()

    def test_cash_payment_submit_no_payment_amounts(self):
        form_data = {
            'supplier': 'Test Supplier',
            'cash_account': 'Petty Cash',
            'payment_date': '2023-10-27',
            'payment_123': '0'
        }
        req_mock = MagicMock()
        req_mock.form = form_data
        req_mock.method = 'POST'

        app_module.cash_payment_submit.__globals__['request'] = req_mock

        app_module.cash_payment_submit()

        mock_flask.flash.assert_called_with('No payment amounts entered', 'warning')
        self.mock_conn.commit.assert_not_called()

    def test_cash_payment_submit_transaction_failure(self):
        form_data = {
            'supplier': 'Test Supplier',
            'cash_account': 'Petty Cash',
            'payment_date': '2023-10-27',
            'payment_123': '1000'
        }
        req_mock = MagicMock()
        req_mock.form = form_data
        req_mock.method = 'POST'

        app_module.cash_payment_submit.__globals__['request'] = req_mock

        self.mock_cursor.fetchone.side_effect = Exception("DB Error")

        app_module.cash_payment_submit()

        self.mock_conn.rollback.assert_called_once()
        flashed = [c[0][0] for c in mock_flask.flash.call_args_list]
        self.assertTrue(any("Transaction failed" in msg for msg in flashed))

if __name__ == '__main__':
    unittest.main()
