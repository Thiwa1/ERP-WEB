
import sys
from unittest.mock import MagicMock
if 'requests' not in sys.modules:
    sys.modules['requests'] = MagicMock()
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock dependencies
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Mock Flask components
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask

# Configure Flask Mock to return a usable app mock
mock_app = MagicMock()
mock_flask.Flask.return_value = mock_app

# Configure app.route to be an identity decorator (returns function as is)
# app.route('...')(func) -> func
mock_app.route.side_effect = lambda *args, **kwargs: lambda f: f

# Setup other Flask mocks
mock_flask.render_template = MagicMock(return_value="template")
mock_flask.redirect = MagicMock(return_value="redirect")
mock_flask.url_for = MagicMock(return_value="/url")
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()
mock_flask.request = MagicMock()

# Now import app - this will execute app.py
import app as app_module

# Since we control mock_app (which is 'app' in app.py), we can set config there
mock_app.config = {'SECRET_KEY': 'test', 'TESTING': True}

# app.py's global imports (request, flash, etc) need to be patched if they were imported 'from flask import ...'
# They point to attributes of the mock_flask object we created.
# We ensure we can control them.

class TestAddSupplier(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        self.patcher_perm = patch('app.check_permission', return_value=True)
        self.mock_check_permission = self.patcher_perm.start()

        mock_flask.session.clear()
        mock_flask.session['user_id'] = 'ADM001'
        mock_flask.session['user_pk'] = 1

        mock_flask.request.reset_mock()
        mock_flask.flash.reset_mock()
        mock_flask.redirect.reset_mock()

        # Default
        mock_flask.request.method = 'GET'

    def tearDown(self):
        self.patcher_perm.stop()

    def test_add_supplier_success(self):
        form_data = {
            'supplier_name': 'Test Supplier',
            'salutation': 'Mr.',
            'supplier_code': 'SUP001',
            'credit_limit': '5000',
            'vat_no': 'VAT123',
            'address_no': '10',
            'address_line_1': 'Test St',
            'address_line_2': 'Colombo',
            'address_line_3': '',
            'address_line_4': '',
            'contact_1': '0771234567',
            'contact_2': '',
            'email': 'sup@test.com',
            'tin_no': 'TIN999',
            'nic_no': 'NIC888'
        }

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 50

        # Configure request
        mock_flask.request.method = 'POST'
        mock_flask.request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        app_module.add_supplier()

        calls = mock_cursor.execute.call_args_list
        self.assertTrue(len(calls) >= 3, f"Expected 3 DB calls, got {len(calls)}")

        insert_sup_call = calls[0]
        self.assertIn("INSERT INTO suppliers", insert_sup_call[0][0])
        self.assertEqual(insert_sup_call[0][1][1], 'Test Supplier')
        self.assertEqual(insert_sup_call[0][1][2], 'SUP001')

        mock_conn.commit.assert_called_once()
        mock_flask.flash.assert_called_with('Supplier added successfully!', 'success')

    def test_add_supplier_validation_error(self):
        form_data = {
            'supplier_name': 'Test Supplier',
            'supplier_code': ''
        }

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn

        mock_flask.request.method = 'POST'
        mock_flask.request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        app_module.add_supplier()

        mock_flask.flash.assert_called_with('Supplier Name and Code are required.', 'danger')
        mock_conn.commit.assert_not_called()

    def test_add_supplier_db_exception(self):
        form_data = {
            'supplier_name': 'Test Supplier',
            'supplier_code': 'SUP001'
        }

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Fail")

        mock_flask.request.method = 'POST'
        mock_flask.request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        app_module.add_supplier()

        # Debug if flash call args mismatch
        # print(mock_flask.flash.call_args_list)

        mock_flask.flash.assert_called_with('Error adding supplier: DB Fail', 'danger')
        mock_conn.rollback.assert_called_once()

if __name__ == '__main__':
    unittest.main()
