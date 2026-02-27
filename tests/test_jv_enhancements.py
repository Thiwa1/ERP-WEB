import unittest
from unittest.mock import MagicMock, patch
import app as app_module
# from app import app # Cannot import app directly as it triggers Flask instantiation which fails without mock in this env
import json

class TestJVEnhancements(unittest.TestCase):
    def setUp(self):
        # We rely on the MockFlask setup from test_add_new_account if running in suite
        # Or we need to setup mock app here if running standalone.
        # But `app.test_client()` in `app` module now returns our MockTestClient if sys.modules was patched.

        # If sys.modules['flask'] is patched, app_module.app is MockFlask.
        self.client = app_module.app.test_client()

        # Setup session using the mock client's way or direct access if known
        # MockTestClient doesn't fully support 'with client.session_transaction()',
        # but our MockTestClient implementation DOES return a context manager for session.
        # However, it accesses `mock_flask.session`.

        # Let's just set the session directly on the mock_flask object if accessible,
        # or via the context manager if it works.
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'ADM001'
            sess['user_pk'] = 1
            sess['username'] = 'admin'

        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_get_sub_accounts(self):
        # Mock sub accounts
        self.mock_db.execute_query.return_value = [
            {'code': 101, 'name': 'Sub A'},
            {'code': 102, 'name': 'Sub B'}
        ]

        with patch('app.check_permission', return_value=True):
            response = self.client.get('/api/get_sub_accounts?account_name=TestAccount')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['name'], 'Sub A')

    def test_jv_print_route(self):
        # Mock Header
        self.mock_db.execute_query.side_effect = [
            # Header query
            [{'jv_user_code': 'JV001', 'jv_naration': 'Test JV', 'entry_date': '2023-01-01', 'total_amount': 100}],
            # Details query
            [{'account_name': 'Acc 1', 'enty_values_DR': 100, 'enty_values_CR': 0, 'entry_sub_account_code': 0, 'entry_naration': 'Line 1'}],
            # Company Info
            [{'company_name': 'Test Co'}]
        ]

        with patch('app.check_permission', return_value=True):
            response = self.client.get('/journal_entry/print/1')
            self.assertEqual(response.status_code, 200)
            # Check for RENDERED_TEMPLATE because that's what our MockFlask returns
            self.assertIn(b'RENDERED_TEMPLATE', response.data)

if __name__ == '__main__':
    unittest.main()
