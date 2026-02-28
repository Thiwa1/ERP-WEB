# Add mock setup first
from tests import mock_setup
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask
mock_app = MagicMock()
mock_app.config = {}
mock_flask.Flask.return_value = mock_app

sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['database'] = MagicMock()

import app as app_module
# Mock app import or use mock_setup
# Since app.py imports Flask, we must use mock_setup FIRST.
# `from flask import Flask` inside test_bulk_upload will use the mocked Flask.

class TestBulkUpload(unittest.TestCase):
    def setUp(self):
        # Use app_module.app directly since we mocked Flask
        self.app = app_module.app
        self.app.config = {'TESTING': True, 'SECRET_KEY': 'test'}

        # Test client from MockFlask might not work as expected for routing
        # We should invoke functions directly with mocked request
        pass

    def test_bulk_upload_tally_check_fail(self):
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.files = {}

            form_mock = MagicMock()
            # The app checks `if 'save_tb' in request.form:`
            # Mocking __contains__ is tricky on MagicMock sometimes.
            # Let's mock request.form as a real dict subclass but with getlist mock?
            # Or use a real dictionary and patch getlist?

            class MockForm(dict):
                def getlist(self, key):
                    return {
                        'account_name[]': ['Acc1', 'Acc2'],
                        'dr[]': ['100', '0'],
                        'cr[]': ['0', '50']
                    }.get(key, [])

            mock_request.form = MockForm({
                'save_tb': '1',
                'opening_date': '2023-01-01'
            })

            with patch('app.check_permission', return_value=True):
                with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                        with patch('app.url_for') as mock_url_for:
                             app_module.bulk_upload_tb()
                             mock_flash.assert_called_with('Totals do not match! Debit: 100.0, Credit: 50.0. Difference: 50.0', 'danger')

    def test_bulk_upload_tally_check_pass(self):
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.files = {}

            class MockForm(dict):
                def getlist(self, key):
                    return {
                        'account_name[]': ['Acc1', 'Acc2'],
                        'dr[]': ['100', '0'],
                        'cr[]': ['0', '100']
                    }.get(key, [])

            mock_request.form = MockForm({
                'save_tb': '1',
                'opening_date': '2023-01-01'
            })

            with patch('app.check_permission', return_value=True):
                with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                        with patch('app.url_for') as mock_url_for:
                            # Mock DB
                            mock_conn = MagicMock()
                            app_module.db.get_connection.return_value = mock_conn
                            mock_cursor = MagicMock()
                            mock_conn.cursor.return_value = mock_cursor
                            mock_cursor.lastrowid = 123

                            app_module.bulk_upload_tb()

                            mock_flash.assert_called_with('TB Uploaded successfully. 2 entries posted to JV 123', 'success')

                            # Verify DB calls
                            found_date = False
                            for call in mock_cursor.execute.call_args_list:
                                args = call[0]
                                if "INSERT INTO entry_details" in args[0]:
                                    params = args[1]
                                    # params: name, dr, cr, effect_date, create_date, ...
                                    # effect_date is index 3
                                    if params[3] == '2023-01-01':
                                        found_date = True

                            self.assertTrue(found_date, "Should use provided opening date")

class TestBulkUpload(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('app.db')
        self.mock_db = self.patcher.start()

        self.request_patcher = patch('app.request')
        self.mock_request = self.request_patcher.start()

        self.flash_patcher = patch('app.flash')
        self.mock_flash = self.flash_patcher.start()

        self.redirect_patcher = patch('app.redirect')
        self.mock_redirect = self.redirect_patcher.start()

        self.url_for_patcher = patch('app.url_for')
        self.mock_url_for = self.url_for_patcher.start()

        self.render_template_patcher = patch('app.render_template')
        self.mock_render = self.render_template_patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.request_patcher.stop()
        self.flash_patcher.stop()
        self.redirect_patcher.stop()
        self.url_for_patcher.stop()
        self.render_template_patcher.stop()

    def test_bulk_upload_tally_check_fail(self):
        self.mock_request.method = 'POST'

        form_data = {
            'save_tb': '1',
            'account_name[]': ['Acc1', 'Acc2'],
            'dr[]': ['100', '0'],
            'cr[]': ['0', '50'],
            'opening_date': '2023-01-01'
        }

        mock_form = MagicMock()
        # Mock request.form behavior to act like a MultiDict/dict
        mock_form.__contains__.side_effect = lambda k: k in form_data
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)
        mock_form.getlist.side_effect = lambda k: form_data.get(k, [])

        self.mock_request.form = mock_form

        # Patch permissions and session
        with patch('app.check_permission', return_value=True), \
             patch('app.session', {'user_id': 1}):

             # The function decorator `login_required` checks session.
             # `has_permission` checks permission.
             # We patched check_permission, but we need session to have user_id for login_required.

             app_module.bulk_upload_tb()

             # Check if flash was called
             if self.mock_flash.call_args:
                 args, _ = self.mock_flash.call_args
                 self.assertIn('Totals do not match', args[0])
             else:
                 self.fail("flash was not called")

    def test_bulk_upload_tally_check_pass(self):
        self.mock_request.method = 'POST'

        form_data = {
            'save_tb': '1',
            'account_name[]': ['Acc1', 'Acc2'],
            'dr[]': ['100', '0'],
            'cr[]': ['0', '100'],
            'opening_date': '2023-01-01'
        }

        mock_form = MagicMock()
        mock_form.__contains__.side_effect = lambda k: k in form_data
        mock_form.get.side_effect = lambda k, d=None: form_data.get(k, d)
        mock_form.getlist.side_effect = lambda k: form_data.get(k, [])

        self.mock_request.form = mock_form

        with patch('app.check_permission', return_value=True), \
             patch('app.session', {'user_id': 1}), \
             patch('app.get_current_user_id', return_value=1):

            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn

            data = {
                'save_tb': '1',
                'account_name[]': ['Acc1', 'Acc2'],
                'dr[]': ['100', '0'],
                'cr[]': ['0', '100'], # Balanced
                'opening_date': '2023-01-01'
            }

            response = self.client.post('/bulk_upload_tb', data=data, follow_redirects=True)

            # Should succeed and redirect to trial_balance
            self.assertIn(b'TB Uploaded successfully', response.data)

            # Verify DB calls
            # Check if date was used in executemany
            found_date = False

            # Check executemany call
            if mock_cursor.executemany.called:
                for call in mock_cursor.executemany.call_args_list:
                    args = call[0]
                    if "INSERT INTO entry_details" in args[0]:
                        params_list = args[1]
                        # Check first item in list
                        if params_list and params_list[0][3] == '2023-01-01':
                            found_date = True

            # Fallback check for execute if optimization reverted (for backward compat if needed, but we expect executemany)
            if not found_date and mock_cursor.execute.called:
                 for call in mock_cursor.execute.call_args_list:
                    args = call[0]
                    if "INSERT INTO entry_details" in args[0]:
                        params = args[1]
                        if params[3] == '2023-01-01':
                            found_date = True

            self.assertTrue(found_date, "Should use provided opening date")
            # Verify executemany was used for optimization
            self.assertTrue(mock_cursor.executemany.called, "Should use executemany for batch insertion")
            app_module.bulk_upload_tb()

            if self.mock_flash.call_args:
                args, _ = self.mock_flash.call_args
                self.assertIn('TB Uploaded successfully', args[0])
            else:
                self.fail("flash was not called")

if __name__ == '__main__':
    unittest.main()
