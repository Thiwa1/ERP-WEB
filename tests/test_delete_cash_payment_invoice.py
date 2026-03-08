import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import MagicMock, patch
import json

import tests.mock_env

# Since app is usually already imported or the decorators were already executed during tests.mock_env mock setup,
# capturing the routes requires parsing app's namespace or importing app normally and letting our mock_env logic handle it.
# We'll just map the route manually since it's only one.

import app

class MockTestClient:
    def __init__(self, app_module):
        self.app_module = app_module

    def session_transaction(self):
        class SessionContext:
            def __enter__(self):
                return tests.mock_env.mock_flask.session
            def __exit__(self, *args):
                pass
        return SessionContext()

    def post(self, url, data=None, **kwargs):
        tests.mock_env.mock_flask.request.method = 'POST'
        tests.mock_env.mock_flask.request.form = MagicMock()
        tests.mock_env.mock_flask.request.form.get = lambda k, d=None: data.get(k, d) if data else d

        if url == '/cash_payment/delete_invoice':
            handler = self.app_module.delete_cash_payment_invoice
        else:
            return MagicMock(status_code=404, data=b"Not Found")

        try:
            resp = handler()
            if isinstance(resp, tuple):
                return MagicMock(status_code=resp[1], data=json.dumps(resp[0]).encode('utf-8'))
            return MagicMock(status_code=200, data=json.dumps(resp).encode('utf-8'))
        except Exception as e:
            return MagicMock(status_code=500, data=str(e).encode('utf-8'))

class TestDeleteCashPaymentInvoice(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        app.db = self.mock_db

        # Override the test_client specifically for our test

        self.client = MockTestClient(app)

        # Set session
        tests.mock_env.mock_flask.session['user_id'] = 1
        tests.mock_env.mock_flask.session['db_name'] = 'test_db'

    @patch('app.check_permission', return_value=True)
    def test_delete_cash_payment_invoice_success(self, mock_check_perm):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        self.mock_db.get_connection.return_value = mock_conn

        response = self.client.post('/cash_payment/delete_invoice', data={'jv_no': 'JV-2023-001'})

        # Check actual queries executed
        mock_cursor.execute.assert_any_call("CALL Sup_Delete_Invoice(%s)", ('JV-2023-001',))
        mock_cursor.execute.assert_any_call("CALL Inventory_Delete(%s)", ('JV-2023-001',))

        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"success": true', response.data.lower())

    @patch('app.check_permission', return_value=True)
    def test_delete_cash_payment_invoice_no_jv(self, mock_check_perm):
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn

        response = self.client.post('/cash_payment/delete_invoice', data={})

        self.mock_db.get_connection.assert_not_called()
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'no jv number provided', response.data.lower())

    @patch('app.check_permission', return_value=True)
    def test_delete_cash_payment_invoice_exception(self, mock_check_perm):
        self.mock_db.get_connection.side_effect = Exception("DB Connection Error")

        response = self.client.post('/cash_payment/delete_invoice', data={'jv_no': 'JV-2023-001'})

        self.assertEqual(response.status_code, 500)
        self.assertIn(b'db connection error', response.data.lower())

if __name__ == '__main__':
    unittest.main()
