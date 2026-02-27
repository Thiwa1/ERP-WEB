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

            app_module.bulk_upload_tb()

            if self.mock_flash.call_args:
                args, _ = self.mock_flash.call_args
                self.assertIn('TB Uploaded successfully', args[0])
            else:
                self.fail("flash was not called")

if __name__ == '__main__':
    unittest.main()
