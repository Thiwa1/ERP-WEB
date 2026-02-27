# Add mock setup first
from tests import mock_setup
import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from app import app
import json

class TestJVEnhancements(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        # Mock Session
        app_module.session = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_get_sub_accounts(self):
        # Mock sub accounts
        self.mock_db.execute_query.return_value = [
            {'code': 101, 'name': 'Sub A'},
            {'code': 102, 'name': 'Sub B'}
        ]

        with patch('app.request') as mock_request:
            mock_request.args = {'account_name': 'TestAccount'}
            with patch('app.check_permission', return_value=True):
                 res = app_module.api_get_sub_accounts()
                 data = json.loads(res)
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

        with patch('app.render_template', return_value="Template Rendered"):
            with patch('app.check_permission', return_value=True):
                 res = app_module.print_journal_voucher(1)
                 self.assertEqual(res, "Template Rendered")

if __name__ == '__main__':
    unittest.main()
