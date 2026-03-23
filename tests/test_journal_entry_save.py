import unittest
from unittest.mock import MagicMock, patch
import sys
import json

# 1. Mock dependencies BEFORE importing app
mock_flask = MagicMock()
mock_mysql = MagicMock()

# Setup flask.request mock
mock_request = MagicMock()
mock_flask.request = mock_request

# Setup other flask globals
mock_session = {}
mock_flask.session = mock_session

# Setup Flask app.route decorator to be a pass-through
# This ensures the function isn't replaced by a Mock object
def route_mock(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_flask.Flask.return_value.route.side_effect = route_mock

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# 2. Import app
import app as app_module

class TestJournalEntrySave(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_request.reset_mock()
        app_module.flash = MagicMock()
        app_module.redirect = MagicMock(return_value="REDIRECTED")
        app_module.url_for = MagicMock(return_value="/url")

        # Setup session for login_required
        # Note: app.py imports session from flask.
        # Since we mocked flask, app.session IS mock_session dict we created above.
        mock_session.clear()
        mock_session['user_id'] = 'ADM001'
        mock_session['user_pk'] = 1

        # Mock Database
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_save_journal_entry_success(self):
        with patch('app.check_permission', return_value=True):
            # Mock DB connection
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Mock System Settings (Workflow Disabled -> Status 1)
            mock_cursor.fetchone.return_value = ('0',)
            mock_cursor.lastrowid = 100 # JV ID

            entries = [
                {'account': 'Acc A', 'dr': 100, 'cr': 0, 'narration': 'Test DR'},
                {'account': 'Acc B', 'dr': 0, 'cr': 100, 'narration': 'Test CR'}
            ]

            form_data = {
                'jv_user_code': 'JV-TEST-001',
                'entry_date': '2023-10-27',
                'main_narration': 'Test Journal Entry',
                'entries_json': json.dumps(entries)
            }
            mock_request.form.get.side_effect = lambda k, default=None: form_data.get(k, default)

            # Call function directly
            response = app_module.save_journal_entry()

            # Verify Result
            self.assertEqual(response, "REDIRECTED") # It redirects on success
            app_module.flash.assert_called_with('Journal Entry created successfully. System JV: 100', 'success')

            # Verify DB Inserts
            # 1. JV Header
            found_header = False
            for call in mock_cursor.execute.call_args_list:
                args = call[0]
                if "INSERT INTO jv_numbers" in args[0]:
                    params = args[1]
                    if params[0] == 'JV-TEST-001' and params[2] == 1:
                        found_header = True
            self.assertTrue(found_header, "Should insert JV header")

            # 2. Details
            detail_inserts = 0
            for call in mock_cursor.executemany.call_args_list:
                args = call[0]
                if "INSERT INTO entry_details" in args[0]:
                    detail_inserts += len(args[1])
            self.assertEqual(detail_inserts, 2, "Should insert 2 entry details via executemany")

    def test_save_journal_entry_unbalanced(self):
        with patch('app.check_permission', return_value=True):
            entries = [
                {'account': 'Acc A', 'dr': 100, 'cr': 0},
                {'account': 'Acc B', 'dr': 0, 'cr': 50} # Unbalanced
            ]

            form_data = {
                'jv_user_code': 'JV-TEST-002',
                'entry_date': '2023-10-27',
                'main_narration': 'Unbalanced JV',
                'entries_json': json.dumps(entries)
            }
            mock_request.form.get.side_effect = lambda k, default=None: form_data.get(k, default)

            response = app_module.save_journal_entry()

            self.assertEqual(response, "REDIRECTED")
            # Verify check
            args, _ = app_module.flash.call_args
            self.assertIn('Entries not balanced', args[0])

    def test_save_journal_entry_no_entries(self):
        with patch('app.check_permission', return_value=True):
            form_data = {
                'jv_user_code': 'JV-TEST-003',
                'entry_date': '2023-10-27',
                'main_narration': 'Empty JV',
                'entries_json': ''
            }
            mock_request.form.get.side_effect = lambda k, default=None: form_data.get(k, default)

            response = app_module.save_journal_entry()

            self.assertEqual(response, "REDIRECTED")
            app_module.flash.assert_called_with('No entries provided', 'danger')

    def test_save_journal_entry_missing_fields(self):
        with patch('app.check_permission', return_value=True):
            entries = [{'account': 'A', 'dr': 100, 'cr': 0}, {'account': 'B', 'dr': 0, 'cr': 100}]

            # Missing jv_user_code
            form_data = {
                'entry_date': '2023-10-27',
                'main_narration': 'Missing Code',
                'entries_json': json.dumps(entries)
            }
            mock_request.form.get.side_effect = lambda k, default=None: form_data.get(k, default)

            response = app_module.save_journal_entry()

            self.assertEqual(response, "REDIRECTED")
            app_module.flash.assert_called_with('JV Number and Main Narration are required', 'danger')

    def test_save_journal_entry_db_error(self):
        with patch('app.check_permission', return_value=True):
            # Mock DB to raise exception
            mock_conn = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Raise exception on execute
            mock_cursor.execute.side_effect = Exception("DB Fail")

            entries = [
                {'account': 'Acc A', 'dr': 100, 'cr': 0},
                {'account': 'Acc B', 'dr': 0, 'cr': 100}
            ]

            form_data = {
                'jv_user_code': 'JV-TEST-FAIL',
                'entry_date': '2023-10-27',
                'main_narration': 'Fail JV',
                'entries_json': json.dumps(entries)
            }
            mock_request.form.get.side_effect = lambda k, default=None: form_data.get(k, default)

            response = app_module.save_journal_entry()

            self.assertEqual(response, "REDIRECTED")
            # First flash call is usually the error
            args, _ = app_module.flash.call_args
            self.assertIn('Database Error', args[0])
            mock_conn.rollback.assert_called()

if __name__ == '__main__':
    unittest.main()
