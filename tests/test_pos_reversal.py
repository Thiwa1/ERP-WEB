import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock modules
mock_flask = MagicMock()
class MockFlask:
    def __init__(self, *args, **kwargs):
        pass
    def context_processor(self, f): return f
    def template_filter(self, name=None):
        def decorator(f): return f
        return decorator
    def route(self, rule, **options):
        def decorator(f): return f
        return decorator
    def before_request(self, f): return f

mock_flask.Flask = MockFlask
mock_flask.request = MagicMock()
mock_flask.session = {}
mock_flask.flash = MagicMock()
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

import tests.mock_env
import app as app_module

class TestPosReversal(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        app_module.session = {
            'user_id': 'ADM001',
            'user_pk': 1,
            'username': 'admin'
        }

        self.patchers = []

        # Mock get_current_user_id
        p_user = patch('app.get_current_user_id', return_value=1)
        self.mock_user = p_user.start()
        self.patchers.append(p_user)

        # Replace decorators by extracting closure logic if needed?
        # pos_reversal_process doesn't take arguments, so it's easily callable

        # Patch Flask request
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        # Patch Flash
        p_flash = patch('app.flash')
        self.mock_flash = p_flash.start()
        self.patchers.append(p_flash)

        # Patch Redirect
        p_red = patch('app.redirect')
        self.mock_redirect = p_red.start()
        self.patchers.append(p_red)

        # Patch url_for
        p_url = patch('app.url_for')
        self.mock_url_for = p_url.start()
        self.patchers.append(p_url)

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_pos_reversal_process_success(self):
        # 1. Setup form data
        self.mock_request.form.get.return_value = '100' # jv = 100

        # 2. Mock DB interactions
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 3. Call function
        app_module.pos_reversal_process()

        # 4. Assertions
        self.mock_db.get_connection.assert_called_once()
        mock_conn.start_transaction.assert_called_once()

        # Verify cursor executes
        self.assertEqual(mock_cursor.execute.call_count, 3)

        # Check specific procedure calls
        calls = mock_cursor.execute.call_args_list
        sql_calls = [c[0][0] for c in calls]

        self.assertTrue(any("CALL JV_Entry_Revers" in s for s in sql_calls))
        self.assertTrue(any("CALL POS_Customer_Delete" in s for s in sql_calls))
        self.assertTrue(any("CALL Inventory_Items_Revers_OUT" in s for s in sql_calls))

        mock_conn.commit.assert_called_once()
        self.mock_flash.assert_called_with('Transaction 100 reversed successfully.', 'success')
        self.mock_redirect.assert_called()

    def test_pos_reversal_process_missing_jv(self):
        self.mock_request.form.get.return_value = None

        app_module.pos_reversal_process()

        self.mock_flash.assert_called_with('No transaction selected', 'danger')
        self.mock_db.get_connection.assert_not_called()
        self.mock_redirect.assert_called()

    def test_pos_reversal_process_db_error(self):
        self.mock_request.form.get.return_value = '100'

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Trigger exception
        mock_cursor.execute.side_effect = Exception("DB Error")

        app_module.pos_reversal_process()

        mock_conn.rollback.assert_called_once()
        self.mock_flash.assert_called_with('Error reversing transaction: DB Error', 'danger')
        self.mock_redirect.assert_called()

if __name__ == '__main__':
    unittest.main()
