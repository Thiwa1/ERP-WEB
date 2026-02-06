import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from app import app
import json

class TestJVEnhancements(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'ADM001'
            sess['user_pk'] = 1
            sess['username'] = 'admin'
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_get_sub_accounts(self):
        # Mock sub accounts
        # sub_account_code, sub_sub_accaount_name
        self.mock_db.execute_query.return_value = [
            {'code': 101, 'name': 'Sub A'},
            {'code': 102, 'name': 'Sub B'}
        ]

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

        response = self.client.get('/journal_entry/print/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'JV001', response.data)
        self.assertIn(b'Test Co', response.data)

if __name__ == '__main__':
    unittest.main()
