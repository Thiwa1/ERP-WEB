import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock Flask and mysql.connector before importing app
mock_flask = MagicMock()
mock_app_instance = MagicMock()
mock_app_instance.config = {}
mock_app_instance.secret_key = 'test_secret'

# Fix @app.route decorator to return the function
def route_side_effect(*args, **kwargs):
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
            mock_cursor.fetchone.side_effect = [
                (1000.0, 0.0), # Outstanding
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
            for call_args in mock_cursor.execute.call_args_list:
                query = call_args[0][0]
                if "UPDATE suppliers_invoice_data" in query:
                    params = call_args[0][1]
                    if params[0] == 500.0 and params[1] == '1':
                        found_update = True
                        break
            self.assertTrue(found_update, "Should update supplier invoice payment")

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
            mock_cursor.fetchone.return_value = (100.0, 0.0)

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

            mock_cursor.fetchone.side_effect = [
                (1000.0, 0.0), # Outstanding
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

if __name__ == '__main__':
    unittest.main()
