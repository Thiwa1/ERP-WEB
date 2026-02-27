import tests.mock_env
import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from datetime import date
import json

class TestFixedAssets(unittest.TestCase):
    def setUp(self):
        app_module.app_initialized = True
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        self.patchers = []
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        p_flash = patch('app.flash')
        self.mock_flash = p_flash.start()
        self.patchers.append(p_flash)

        p_red = patch('app.redirect')
        self.mock_redirect = p_red.start()
        self.patchers.append(p_red)

        # Patch check_permission to always return True (bypassing DB check)
        p_perm = patch('app.check_permission', return_value=True)
        self.mock_perm = p_perm.start()
        self.patchers.append(p_perm)

        p_user = patch('app.get_current_user_id', return_value=1)
        self.mock_user = p_user.start()
        self.patchers.append(p_user)

        # PATCH SESSION
        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_add_asset(self):
        self.mock_request.method = 'POST'

        form_data = {
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

        self.mock_request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        # Call function
        app_module.add_fixed_asset()

        # Verify DB Call
        found = False
        for call in self.mock_db.execute_query.call_args_list:
            args = call[0]
            query = args[0]
            if "INSERT INTO fixed_assets_register" in query:
                params = args[1]
                if params[0] == 'Computer' and params[6] == 1200.0:
                    found = True
        self.assertTrue(found, "Insert query not called with correct params")
        self.mock_flash.assert_called_with('Asset added successfully', 'success')

    def test_calculate_depreciation(self):
        self.mock_request.form = MagicMock()
        self.mock_request.form.get.side_effect = lambda k, d=None: '2023-02' if k == 'month' else d

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 999

        import datetime
        asset = {
            'id': 10,
            'asset_class': 'Computer',
            'description': 'Laptop',
            'serial_no': 'SN123',
            'status': 'Active',
            'purchasing_date': datetime.date(2023, 1, 1),
            'cost_value': 1200.0,
            'depreciable_life_months': 24,
            'expense_account_id': 2,
            'accumulated_dep_account_id': 3,
            'quantity': 1,
            'brand_name': 'Dell',
            'location': 'Office'
        }

        def cursor_execute_side_effect(query, params=None):
            mock_cursor.fetchall.side_effect = None
            mock_cursor.fetchone.side_effect = None

            if "SELECT * FROM fixed_assets_register" in query:
                mock_cursor.fetchall.return_value = [asset]
            elif "SELECT id FROM asset_depreciation_history" in query:
                mock_cursor.fetchone.return_value = None
            elif "SELECT SUM(amount)" in query:
                mock_cursor.fetchone.return_value = {'total': 0}
            elif "SELECT account_name FROM new_account_table" in query:
                mock_cursor.fetchone.return_value = {'account_name': 'Test Account'}

        mock_cursor.execute.side_effect = cursor_execute_side_effect

        result = app_module.calculate_depreciation()

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('success'), True)
        self.assertEqual(result.get('processed'), 1)

    def test_get_data(self):
        import datetime
        assets = [{
            'id': 1, 'asset_class': 'C1', 'description': 'D1', 'brand_name': 'B1',
            'quantity': 1, 'serial_no': 'S1', 'location': 'L1',
            'cost_value': 1000.0, 'purchasing_date': datetime.date(2023,1,1), 'depreciable_life_months': 10
        }]

        history = [
            {'asset_id': 1, 'depreciation_date': datetime.date(2023,1,31), 'amount': 100.0},
            {'asset_id': 1, 'depreciation_date': datetime.date(2023,2,28), 'amount': 100.0}
        ]

        def side_effect(query, params=None):
            if "fixed_assets_register" in query:
                return assets
            if "asset_depreciation_history" in query:
                return history
            return []

        self.mock_db.execute_query.side_effect = side_effect

        json_str = app_module.fixed_assets_data()

        # Debugging
        if isinstance(json_str, MagicMock):
            print("ERROR: json_str is MagicMock. Session:", self.mock_session.get('user_id'), "Perm Check:", self.mock_perm())

        json_data = json.loads(json_str)

        self.assertIn('2023-Jan', json_data['month_headers'])
        self.assertIn('2023-Feb', json_data['month_headers'])

        row = json_data['data'][0]
        self.assertEqual(row['2023-Jan'], 100.0)
        self.assertEqual(row['total_dep'], 200.0)
        self.assertEqual(row['nbv'], 800.0)

if __name__ == '__main__':
    unittest.main()
