import unittest
from unittest.mock import MagicMock
import sys
import datetime

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
        # 1. SELECT ... suppliers_invoice_data (Outstanding check) -> (10000.0, 0.0)
        # 2. SELECT ... system_settings (Workflow) -> ('0',)
        # 3. SELECT ... bank_book_voucher_no (Max ID) -> (100,)
        # 4. SELECT ... sub_accont_for_new_account (Sub Code) -> (555,)

        # The first call in the loop is fetchone()
        # The subsequent calls are also fetchone()

        cursor.fetchone.side_effect = [
            (10000.0, 0.0), # 1. Outstanding Check
            ('0',),         # 2. Workflow Check
            (100,),         # 3. Max Voucher
            (555,),         # 4. Sub Account Code
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
        cursor.fetchone.return_value = (10000.0, 0.0)

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
