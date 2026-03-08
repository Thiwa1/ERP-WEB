import sys
from unittest.mock import MagicMock, patch
import importlib

# 1. Setup global mocks before import
mock_flask_module = MagicMock()
mock_request = MagicMock()
mock_flash = MagicMock()
mock_render = MagicMock()
mock_redirect = MagicMock()
mock_url_for = MagicMock()

# Assign them to the module mock
mock_flask_module.request = mock_request
mock_flask_module.flash = mock_flash
mock_flask_module.render_template = mock_render
mock_flask_module.redirect = mock_redirect
mock_flask_module.url_for = mock_url_for

# Mock session as a dict
mock_session = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}
mock_flask_module.session = mock_session

# Apply to sys.modules
sys.modules['flask'] = mock_flask_module

sys.modules['jinja2'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Import app (this might pick up a cached version)
import app as app_module

# Force reload to ensure it picks up our sys.modules['flask']
importlib.reload(app_module)

import unittest

app_module.app.config = {'TESTING': True}

class TestAddCustomer(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_request.reset_mock()
        mock_flash.reset_mock()
        mock_render.reset_mock()
        mock_redirect.reset_mock()
        mock_url_for.reset_mock()

        # Reset Session
        mock_session.clear()
        mock_session.update({'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'})

        # Patch app.db (Instance)
        self.mock_db = MagicMock()
        self.db_patcher = patch('app.db', self.mock_db)
        self.db_patcher.start()

        # Update our references to the mocks used by the app
        self.actual_request_mock = app_module.request
        self.actual_flash_mock = app_module.flash
        self.actual_render_mock = app_module.render_template
        self.actual_redirect_mock = app_module.redirect
        self.actual_url_for_mock = app_module.url_for

    def tearDown(self):
        self.db_patcher.stop()

    def test_add_customer_post_success(self):
        # Setup Request
        self.actual_request_mock.method = 'POST'

        form_data = {
            'supplier_name': 'TestCust',
            'supplier_code': 'C001',
            'credit_limit': '1000',
            'address_no': '10',
            'address_line_1': 'Lane',
            'contact_1': '123'
        }

        # Mocking .form.get()
        # Since `request` is a MagicMock, `request.form` is also a MagicMock.
        # We set side_effect on `get` method of that mock.
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        # Setup DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 123

        # Execute
        app_module.add_customer()

        # Assertions
        # Use actual mocks that app module uses
        self.actual_flash_mock.assert_called_with('Customer added successfully!', 'success')
        self.actual_url_for_mock.assert_called_with('add_customer')
        self.actual_redirect_mock.assert_called()

        calls = mock_cursor.execute.call_args_list
        self.assertTrue(len(calls) >= 3, "DB execute not called enough times")
        self.assertIn("INSERT INTO suppliers", calls[0][0][0])

        mock_conn.commit.assert_called_once()

    def test_add_customer_validation_error(self):
        self.actual_request_mock.method = 'POST'

        # Missing name
        form_data = {'supplier_code': 'C001'}
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        app_module.add_customer()

        self.actual_flash_mock.assert_called_with('Supplier Name and Code are required.', 'danger')
        mock_cursor.execute.assert_not_called()

    def test_add_customer_transaction_rollback(self):
        self.actual_request_mock.method = 'POST'

        form_data = {
            'supplier_name': 'TestCust',
            'supplier_code': 'C001'
        }
        self.actual_request_mock.form = MagicMock()
        self.actual_request_mock.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        def side_effect(*args, **kwargs):
            if "INSERT INTO sub_accont_for_new_account" in args[0]:
                raise Exception("DB Error")
            return None
        mock_cursor.execute.side_effect = side_effect

        app_module.add_customer()

        mock_conn.rollback.assert_called_once()
        self.actual_flash_mock.assert_called_with('Error adding customer: DB Error', 'danger')

    def test_add_customer_get(self):
        self.actual_request_mock.method = 'GET'
        self.mock_db.execute_query.return_value = [{'salutation': 'Mr.'}, {'salutation': 'Mrs.'}]

        app_module.add_customer()

        self.actual_render_mock.assert_called()
        args, kwargs = self.actual_render_mock.call_args
        self.assertEqual(args[0], 'add_customer.html')
        self.assertEqual(kwargs['salutations'], ['Mr.', 'Mrs.'])

if __name__ == '__main__':
    unittest.main()
