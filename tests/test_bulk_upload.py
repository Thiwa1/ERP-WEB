# Add mock setup first
from tests import mock_setup
import unittest
from unittest.mock import MagicMock, patch
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

if __name__ == '__main__':
    unittest.main()
