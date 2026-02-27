import unittest
from unittest.mock import MagicMock, patch
import app as app_module
# from flask import Flask # Handled by sys.modules mock in test_add_new_account

class TestBulkUpload(unittest.TestCase):
    def setUp(self):
        # We assume mocked Flask env from test_add_new_account runs first or we need to setup?
        # Ideally setup should be robust.

        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        # Reset Request Mock
        app_module.request.method = 'GET'
        app_module.request.form = MagicMock()
        app_module.request.form.get = lambda k, d=None: d
        app_module.request.form.getlist = lambda k: []
        app_module.request.files = {}
        app_module.request.args = {}
        app_module.session = {'user_id': 'admin', 'user_pk': 1}

        self.client = app_module.app.test_client()

    def test_bulk_upload_tally_check_fail(self):
        with patch('app.check_permission', return_value=True):
            data = {
                'save_tb': '1',
                'account_name[]': ['Acc1', 'Acc2'],
                'dr[]': ['100', '0'],
                'cr[]': ['0', '50'],
                'opening_date': '2023-01-01'
            }

            # Custom getlist helper
            class FormData(dict):
                def getlist(self, key):
                    if key in self:
                        val = self[key]
                        return val if isinstance(val, list) else [val]
                    return []
                def get(self, key, default=None):
                    return self[key] if key in self else default

            response = self.client.post('/bulk_upload_tb', data=FormData(data), follow_redirects=True)

            # In the mock client, flash messages are returned in response.data for simple assertions
            self.assertIn(b'Totals do not match!', response.data)

    def test_bulk_upload_tally_check_pass(self):
        with patch('app.check_permission', return_value=True):
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 123

            data = {
                'save_tb': '1',
                'account_name[]': ['Acc1', 'Acc2'],
                'dr[]': ['100', '0'],
                'cr[]': ['0', '100'],
                'opening_date': '2023-01-01'
            }

            class FormData(dict):
                def getlist(self, key):
                    if key in self:
                        val = self[key]
                        return val if isinstance(val, list) else [val]
                    return []
                def get(self, key, default=None):
                    return self[key] if key in self else default

            response = self.client.post('/bulk_upload_tb', data=FormData(data), follow_redirects=True)

            self.assertIn(b'TB Uploaded successfully', response.data)

            # Verify DB calls
            found_date = False
            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                if "INSERT INTO entry_details" in args[0]:
                    params = args[1]
                    if params[3] == '2023-01-01':
                        found_date = True

            self.assertTrue(found_date, "Should use provided opening date")

if __name__ == '__main__':
    unittest.main()
