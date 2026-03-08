import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module

class TestBulkUpload(unittest.TestCase):
    def test_bulk_upload_tally_check_fail(self):
        class MockForm(dict):
            def getlist(self, key):
                return {
                    'account_name[]': ['Acc1', 'Acc2'],
                    'dr[]': ['100', '0'],
                    'cr[]': ['0', '50']
                }.get(key, [])
            def get(self, key, default=None):
                return super().get(key, default)

        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.files = {}
            mock_request.form = MockForm({
                'save_tb': '1',
                'opening_date': '2023-01-01'
            })

            with patch('app.check_permission', return_value=True):
                with patch('app.session', {'user_id': 1}):
                    with patch('app.get_current_user_pk', return_value=1):
                        with patch('app.flash') as mock_flash:
                            app_module.bulk_upload_tb()

                            found = False
                            for call in mock_flash.call_args_list:
                                if 'Totals do not match' in str(call):
                                    found = True
                            self.assertTrue(found, "Flash message for totals mismatch not found")

    def test_bulk_upload_tally_check_pass(self):
        class MockForm(dict):
            def getlist(self, key):
                return {
                    'account_name[]': ['Acc1', 'Acc2'],
                    'dr[]': ['100', '0'],
                    'cr[]': ['0', '100']
                }.get(key, [])
            def get(self, key, default=None):
                return super().get(key, default)

        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.files = {}
            mock_request.form = MockForm({
                'save_tb': '1',
                'opening_date': '2023-01-01'
            })

            with patch('app.check_permission', return_value=True):
                with patch('app.session', {'user_id': 1}):
                    with patch('app.get_current_user_pk', return_value=1):
                        with patch('app.flash') as mock_flash:
                            with patch('app.db') as mock_db:
                                mock_conn = MagicMock()
                                mock_db.get_connection.return_value = mock_conn
                                mock_cursor = MagicMock()
                                mock_conn.cursor.return_value = mock_cursor
                                mock_cursor.lastrowid = 123

                                app_module.bulk_upload_tb()

                                found = False
                                for call in mock_flash.call_args_list:
                                    if 'TB Uploaded successfully' in str(call):
                                        found = True
                                self.assertTrue(found, "Flash message for success not found")

if __name__ == '__main__':
    unittest.main()
