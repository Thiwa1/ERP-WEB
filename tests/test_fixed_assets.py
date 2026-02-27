import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from app import app
from datetime import date, datetime
import json

class TestFixedAssets(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Mock Session
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'ADM001'
            sess['user_pk'] = 1
            sess['username'] = 'admin'

        # Mock DB
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

    def test_add_asset(self):
        def side_effect(query, params=None, commit=False):
            if "SELECT Access_Accounting FROM User_Rights" in query:
                return [{'Access_Accounting': 1}]
            return None

        self.mock_db.execute_query.side_effect = side_effect

        data = {
            'asset_class': 'Computer',
            'description': 'Laptop',
            'brand_name': 'Dell',
            'quantity': '1',
            'serial_no': 'SN123',
            'location': 'Office',
            'cost_value': '1200',
            'purchasing_date': '2023-01-01',
            'depreciable_life_months': '24',
            'asset_account_id': '1',
            'expense_account_id': '2',
            'accumulated_dep_account_id': '3'
        }

        response = self.client.post('/fixed_assets/add', data=data)
        self.assertEqual(response.status_code, 302)

        found = False
        for call in self.mock_db.execute_query.call_args_list:
            query = call[0][0]
            if "INSERT INTO fixed_assets_register" in query:
                params = call[0][1]
                if params[0] == 'Computer' and params[6] == 1200.0:
                    found = True
        self.assertTrue(found, "Insert query not called with correct params")

    def test_calculate_depreciation(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Initialize ID counter
        self.last_row_id = 999
        mock_cursor.lastrowid = 0

        self.mock_db.execute_query.return_value = [{'Access_Accounting': 1}]

        asset = {
            'id': 10,
            'asset_class': 'Computer',
            'description': 'Laptop',
            'serial_no': 'SN123',
            'status': 'Active',
            'purchasing_date': date(2023, 1, 1),
            'cost_value': 1200.0,
            'depreciable_life_months': 24,
            'expense_account_id': 2,
            'accumulated_dep_account_id': 3,
            'quantity': 1,
            'brand_name': 'Dell',
            'location': 'Office'
        }

        def side_effect(*args, **kwargs):
            query = args[0]
            if "INSERT" in query.upper():
                self.last_row_id += 1
                mock_cursor.lastrowid = self.last_row_id

            if "SELECT * FROM fixed_assets_register" in query:
                mock_cursor.fetchall.return_value = [asset]
            elif "SELECT id FROM asset_depreciation_history" in query:
                mock_cursor.fetchone.return_value = None
            elif "SELECT SUM(amount)" in query:
                mock_cursor.fetchone.return_value = {'total': 0}
            elif "SELECT account_name FROM new_account_table" in query:
                mock_cursor.fetchone.return_value = {'account_name': 'Test Account'}

        mock_cursor.execute.side_effect = side_effect

        response = self.client.post('/fixed_assets/calculate_depreciation', data={'month': '2023-02'})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'success', response.data)

        found = False
        for call in mock_cursor.execute.call_args_list:
            query = call[0][0]
            if "INSERT INTO asset_depreciation_history" in query:
                params = call[0][1]
                if params[2] == 50.0:
                    found = True
                    break
        self.assertTrue(found, "Depreciation calculation failed or not inserted")

    def test_get_data(self):
        assets = [{
            'id': 1, 'asset_class': 'C1', 'description': 'D1', 'brand_name': 'B1',
            'quantity': 1, 'serial_no': 'S1', 'location': 'L1',
            'cost_value': 1000.0, 'purchasing_date': date(2023,1,1), 'depreciable_life_months': 10
        }]

        history = [
            {'asset_id': 1, 'depreciation_date': date(2023,1,31), 'amount': 100.0},
            {'asset_id': 1, 'depreciation_date': date(2023,2,28), 'amount': 100.0}
        ]

        def side_effect(query, params=None):
            if "User_Rights" in query:
                return [{'Access_Accounting': 1}]
            if "fixed_assets_register" in query:
                return assets
            if "asset_depreciation_history" in query:
                return history
            return []

        self.mock_db.execute_query.side_effect = side_effect

        response = self.client.get('/fixed_assets/data')
        self.assertEqual(response.status_code, 200)

        json_data = json.loads(response.data)

        self.assertIn('2023-Jan', json_data['month_headers'])
        self.assertIn('2023-Feb', json_data['month_headers'])

        row = json_data['data'][0]
        self.assertEqual(row['2023-Jan'], 100.0)
        self.assertEqual(row['total_dep'], 200.0)
        self.assertEqual(row['nbv'], 800.0)

if __name__ == '__main__':
    unittest.main()
