import unittest
import sys
import tests.mock_env
from unittest.mock import MagicMock, patch

# Mock Flask and mysql.connector before importing app
mock_flask = MagicMock()
mock_app_instance = MagicMock()
mock_app_instance.config = {}
mock_app_instance.secret_key = 'test_secret'

# Fix @app.route decorator to return the function
def route_side_effect(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    def decorator(f):
        return f
    return decorator

mock_app_instance.route.side_effect = route_side_effect

# Fix @app.context_processor
def context_processor_side_effect(f):
    return f

mock_app_instance.context_processor.side_effect = context_processor_side_effect

# Fix @app.template_filter
def template_filter_side_effect(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    def decorator(f):
        return f
    return decorator
mock_app_instance.template_filter.side_effect = template_filter_side_effect


mock_flask.Flask.return_value = mock_app_instance

# Setup global mocks
mock_request = MagicMock()
mock_flash = MagicMock()
mock_redirect = MagicMock()
mock_url_for = MagicMock()
mock_session = MagicMock()

mock_flask.request = mock_request
mock_flask.flash = mock_flash
mock_flask.redirect = mock_redirect
mock_flask.url_for = mock_url_for
mock_flask.session = mock_session

sys.modules['flask'] = mock_flask
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql'] = MagicMock()

import app as app_module

class TestBankPayment(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        mock_request.reset_mock()
        mock_flash.reset_mock()
        mock_redirect.reset_mock()
        mock_session.reset_mock()

        mock_session.__contains__.side_effect = lambda key: key == 'user_id'
        mock_session.get.return_value = 1

        mock_request.form = MagicMock()

    def test_bank_payment_submit(self):
        with patch('app.get_current_user_id', return_value=1):
            # Setup Request
            mock_request.form.getlist.return_value = ['1']

            def get_side_effect(key, default=None):
                data = {
                    'supplier': 'Test Supplier',
                    'bank_account': 'Bank 1',
                    'payment_date': '2023-10-27',
                    'narration': 'Test Payment',
                    'cheque_no': 'CHK001',
                    'payment_1': '500',
                    'wht_amount': '0'
                }
                return data.get(key, default)
            mock_request.form.get.side_effect = get_side_effect

            # Setup DB
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Mock Responses
            mock_cursor.fetchall.return_value = [
                ('1', 1000.0, 0.0) # Outstanding
            ]
            mock_cursor.fetchone.side_effect = [
                None,          # Workflow
                (5,),          # Max Voucher
                (123,),        # Sub Account
            ]
            self.mock_db.execute_query.return_value = [{'sup_id': 10}]

            # Execute
            app_module.bank_payment_submit()

            # Assertions
            mock_flash.assert_called()
            args, _ = mock_flash.call_args
            self.assertIn('Payment processed successfully', args[0])

            # Verify Invoices Update (500 paid)
            found_update = False
            for call_args in mock_cursor.executemany.call_args_list:
                query = call_args[0][0]
                if "UPDATE suppliers_invoice_data" in query:
                    params_list = call_args[0][1]
                    for params in params_list:
                        if params[0] == 500.0 and params[1] == '1':
                            found_update = True
                            break
            self.assertTrue(found_update, "Should update supplier invoice payment via executemany")

            # Verify Entry Details (AP Debit 500)
            found_ap = False
            for call_args in mock_cursor.execute.call_args_list:
                query = call_args[0][0]
                if "INSERT INTO entry_details" in query and "enty_values_DR" in query:
                    params = call_args[0][1]
                    if params[0] == 'Account Payable' and params[1] == 500.0:
                        found_ap = True
                        break
            self.assertTrue(found_ap, "Should debit Account Payable")

            # Verify Entry Details (Bank Credit 500)
            found_bank = False
            for call_args in mock_cursor.execute.call_args_list:
                query = call_args[0][0]
                if "INSERT INTO entry_details" in query and "enty_values_CR" in query:
                    params = call_args[0][1]
                    if params[0] == 'Bank 1' and params[1] == 500.0:
                        found_bank = True
                        break
            self.assertTrue(found_bank, "Should credit Bank Account")

    def test_bank_payment_overpayment(self):
        with patch('app.get_current_user_id', return_value=1):
            mock_request.form.getlist.return_value = ['1']

            def get_side_effect(key, default=None):
                data = {
                    'supplier': 'Test Supplier',
                    'bank_account': 'Bank 1',
                    'payment_1': '500',
                    'wht_amount': '0'
                }
                return data.get(key, default)
            mock_request.form.get.side_effect = get_side_effect

            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Outstanding < Payment
            mock_cursor.fetchall.return_value = [
                ('1', 100.0, 0.0)
            ]

            app_module.bank_payment_submit()

            # Verify Failure
            mock_flash.assert_called()
            args, _ = mock_flash.call_args
            self.assertIn('Transaction failed', args[0])
            mock_conn.rollback.assert_called()

    def test_bank_payment_wht(self):
        with patch('app.get_current_user_id', return_value=1):
            mock_request.form.getlist.return_value = ['1']

            def get_side_effect(key, default=None):
                data = {
                    'supplier': 'Test Supplier',
                    'bank_account': 'Bank 1',
                    'payment_date': '2023-10-27',
                    'narration': 'Test Payment',
                    'cheque_no': 'CHK001',
                    'payment_1': '500',
                    'wht_amount': '50'
                }
                return data.get(key, default)
            mock_request.form.get.side_effect = get_side_effect

            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            mock_cursor.fetchall.return_value = [
                ('1', 1000.0, 0.0) # Outstanding
            ]
            mock_cursor.fetchone.side_effect = [
                None,          # Workflow
                (5,),          # Max Voucher
                (123,),        # Sub Account
            ]
            self.mock_db.execute_query.return_value = [{'sup_id': 10}]

            app_module.bank_payment_submit()

            # Verify WHT Credit
            found_wht = False
            for call_args in mock_cursor.execute.call_args_list:
                query = call_args[0][0]
                if "INSERT INTO entry_details" in query and "enty_values_CR" in query:
                    params = call_args[0][1]
                    if params[0] == 'WHT Payable' and params[1] == 50.0:
                        found_wht = True
                        break
            self.assertTrue(found_wht, "Should credit WHT Payable")

            # Verify Bank Credit (Net: 450)
            found_bank = False
            for call_args in mock_cursor.execute.call_args_list:
                query = call_args[0][0]
                if "INSERT INTO entry_details" in query and "enty_values_CR" in query:
                    params = call_args[0][1]
                    if params[0] == 'Bank 1' and params[1] == 450.0:
                        found_bank = True
                        break
            self.assertTrue(found_bank, "Should credit Bank Account with Net Amount")
from unittest.mock import MagicMock
import sys

# --- 1. Mocks for Missing Dependencies ---

class MockFlask:
    def __init__(self, import_name):
        self.config = {}
        self.secret_key = None
        self.view_functions = {}

    def context_processor(self, f):
        return f

    def template_filter(self, name=None):
        def decorator(f):
            return f
        return decorator

    def route(self, rule, **options):
        def decorator(f):
            self.view_functions[rule] = f
            return f
        return decorator

    def before_request(self, f):
        return f

flask_mock = MagicMock()
flask_mock.Flask = MockFlask
sys.modules['flask'] = flask_mock

mysql_mock = MagicMock()
sys.modules['mysql.connector'] = mysql_mock
sys.modules['mysql'] = MagicMock()

database_mock = MagicMock()
sys.modules['database'] = database_mock

import app

# --- 3. Test Class ---
class TestBankPayment(unittest.TestCase):
    def setUp(self):
        app.db = MagicMock()
        app.session = {}
        app.request = MagicMock()
        # Mocking login_required and has_permission decorators properly is tricky if they are already applied.
        # But app.py imports them. If we modify app.login_required, it might not affect already decorated functions.
        # However, the functions are decorated in app.py.
        # We can bypass the decorators by extracting the original function closure, OR simpler:
        # Mock check_permission to return True and session to have user_id.
        app.session['user_id'] = 'test_user'
        app.check_permission = MagicMock(return_value=True)

        app.flash = MagicMock()
        app.redirect = MagicMock(return_value='redirected')
        app.url_for = MagicMock(return_value='/url')

    def test_bank_payment_submit_success(self):
        """Test successful bank payment submission with Master Voucher Number."""

        # 1. Setup Form Data
        form_data = {
            'supplier': 'Test Supplier',
            'bank_account': 'Bank Account A',
            'payment_date': '2023-10-27',
            'narration': 'Payment for Invoice 1',
            'cheque_no': 'CHQ123',
            'wht_amount': '0',
            'payment_1': '5000'
        }

        def form_get(key, default=None):
            if key.startswith('payment_'):
                pid = key.split('_')[1]
                return form_data.get(f'payment_{pid}', default)
            return form_data.get(key, default)

        def form_getlist(key):
            if key == 'inv_id[]':
                return ['1']
            return []

        app.request.form.get = MagicMock(side_effect=form_get)
        app.request.form.getlist = MagicMock(side_effect=form_getlist)

        # 2. Mock Database Interactions
        conn = MagicMock()
        cursor = MagicMock()
        app.db.get_connection.return_value = conn
        conn.cursor.return_value = cursor

        # Mock fetchone responses
        # Logic calls:
        # 1. SELECT ... system_settings (Workflow) -> ('0',)
        # 2. SELECT ... bank_book_voucher_no (Max ID) -> (100,)
        # 3. SELECT ... sub_accont_for_new_account (Sub Code) -> (555,)

        cursor.fetchall.return_value = [
            ('1', 10000.0, 0.0) # 1. Outstanding Check
        ]

        cursor.fetchone.side_effect = [
            ('0',),         # 1. Workflow Check
            (100,),         # 2. Max Voucher
            (555,),         # 3. Sub Account Code
        ]

        # Mock lastrowid for Master Voucher ID
        cursor.lastrowid = 500

        app.db.execute_query.return_value = [{'sup_id': 99}]

        # 3. Execute
        # We call the function. Because decorators wrap it, and we mocked session/check_permission,
        # it should proceed to the logic.
        response = app.bank_payment_submit()

        # 4. Assertions
        app.redirect.assert_called_with('/url')

        # Verify Flash Success Message includes Master Voucher
        flash_args = app.flash.call_args
        self.assertIsNotNone(flash_args, "Flash was not called")
        msg = flash_args[0][0]
        self.assertIn('Payment processed successfully', msg)
        self.assertIn('Voucher No: 101', msg)
        self.assertIn('Master Voucher: 500', msg)

        # Verify Master Voucher Insertion
        found_master_insert = False
        for call in cursor.execute.call_args_list:
            sql = call[0][0]
            if "INSERT INTO master_payment_voucher_no" in sql:
                found_master_insert = True
                break
        self.assertTrue(found_master_insert, "Did not find Master Voucher insertion")

        # Verify Bank Book Record Insertion contains Master Voucher
        found_bank_insert = False
        for call in cursor.execute.call_args_list:
            sql = call[0][0]
            if "INSERT INTO bank_book_recod" in sql:
                params = call[0][1]
                # Check that master_voucher_no (last param) is 500
                if len(params) == 12 and params[11] == 500:
                    found_bank_insert = True
                    break
        self.assertTrue(found_bank_insert, "Did not find correct Bank Book insertion with Master Voucher No")

    def test_bank_payment_submit_overpayment(self):
        """Test validation when payment exceeds outstanding amount."""
        form_data = {
            'supplier': 'Test Supplier',
            'bank_account': 'Bank Account A',
            'payment_date': '2023-10-27',
            'payment_1': '20000' # Exceeds outstanding
        }

        def form_get(key, default=None):
            if key == 'payment_1': return '20000'
            return form_data.get(key, default)

        app.request.form.get = MagicMock(side_effect=form_get)
        app.request.form.getlist = MagicMock(return_value=['1'])

        conn = MagicMock()
        cursor = MagicMock()
        app.db.get_connection.return_value = conn
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [
            ('1', 10000.0, 0.0)
        ]

        app.bank_payment_submit()

        flash_args = app.flash.call_args
        self.assertIsNotNone(flash_args, "Flash was not called on error")
        msg = flash_args[0][0]
        self.assertIn('Transaction failed', msg)
        self.assertIn('exceeds outstanding', msg)

    def test_bank_payment_submit_no_data(self):
        """Test submission with missing required fields."""
        form_data = {'supplier': 'Test Supplier'}
        app.request.form.get = MagicMock(side_effect=lambda k, d=None: form_data.get(k, d))
        app.bank_payment_submit()
        app.flash.assert_called_with('Missing supplier or bank account', 'danger')

if __name__ == '__main__':
    unittest.main()
