import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from flask import Flask

class TestBulkUpload(unittest.TestCase):
    def setUp(self):
        # Create a test Flask app context
        self.app = Flask(__name__)
        self.app.secret_key = 'test'
        self.app.config['TESTING'] = True

        # Patch db
        self.patcher = patch('app.db')
        self.mock_db = self.patcher.start()
        app_module.db = self.mock_db

        # Patch session and other helpers if needed
        # We need to test the logic inside bulk_upload_tb route.
        # Since it's a route, it's easier to test logic functions or use test_client.
        # We'll use test_client.

        # Register route to test app (or just import app from app.py if possible, but app.py has global side effects)
        # Better to mock the request context and call the function directly if possible, or use app.app.test_client()
        # Given app.py structure, app is available.
        app_module.app.config['TESTING'] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.patcher.stop()

    def test_bulk_upload_tally_check_fail(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        # Mock permission check
        with patch('app.check_permission', return_value=True):
            # Submit unbalanced data
            data = {
                'save_tb': '1',
                'account_name[]': ['Acc1', 'Acc2'],
                'dr[]': ['100', '0'],
                'cr[]': ['0', '50'], # Difference of 50
                'opening_date': '2023-01-01'
            }

            response = self.client.post('/bulk_upload_tb', data=data, follow_redirects=True)

            # Check for error message
            self.assertIn(b'Totals do not match!', response.data)
            # Should redirect to bulk_upload_tb (GET) which renders the upload page
            self.assertIn(b'BULK UPLOAD TRIAL BALANCE', response.data)

    def test_bulk_upload_tally_check_pass(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'admin'
            sess['user_pk'] = 1

        with patch('app.check_permission', return_value=True):
            # Mock DB connection for transaction
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 123

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
            # Check if date was used
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
