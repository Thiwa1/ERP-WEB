import tests.mock_env
import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import json

import app as app_module
from app import app

class TestFixedAssets(unittest.TestCase):
    def setUp(self):
        self.patchers = []

        # PATCH DB
        p_db = patch('app.db')
        self.mock_db = p_db.start()
        self.patchers.append(p_db)

        # PATCH REQUEST
        p_req = patch('app.request')
        self.mock_request = p_req.start()
        self.patchers.append(p_req)

        # PATCH FLASH
        p_flash = patch('app.flash')
        self.mock_flash = p_flash.start()
        self.patchers.append(p_flash)

        # PATCH CURRENT USER
        p_user = patch('app.get_current_user_id', return_value=1)
        self.mock_user = p_user.start()
        self.patchers.append(p_user)
        p_user_pk = patch('app.get_current_user_pk', return_value=1)
        self.mock_user_pk = p_user_pk.start()
        self.patchers.append(p_user_pk)

        # PATCH SESSION
        p_sess = patch('app.session')
        self.mock_session = p_sess.start()
        self.patchers.append(p_sess)
        self.mock_session.__contains__.side_effect = lambda k: k == 'user_id'
        self.mock_session.get.side_effect = lambda k, d=None: 'admin' if k == 'user_id' else d

        app.config['TESTING'] = True
        app_module.session = {'user_id': 'ADM001', 'user_pk': 1, 'username': 'admin'}

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_add_asset_with_supplier_and_gl(self):
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.form = MagicMock()
            mock_request.form.get.side_effect = lambda k, d=None: {
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
                'accumulated_dep_account_id': '3',
                'post_gl': '1',
                'credit_account_id': '4',
                'supplier_id': '5'
            }.get(k, d)

            mock_request.files = {}

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 100

            def cursor_execute_side_effect(*args, **kwargs):
                query = args[0]
                if "SELECT account_name FROM new_account_table WHERE id = %s" in query:
                    # Provide an account payable match to test supplier invoice mapping
                    if args[1][0] == '4':
                        mock_cursor.fetchone.return_value = {'account_name': 'Account Payable'}
                    else:
                        mock_cursor.fetchone.return_value = {'account_name': 'Asset Acc'}
                elif "SELECT supplier_code" in query:
                    mock_cursor.fetchone.return_value = {'supplier_code': 'SUP-01'}

            mock_cursor.execute.side_effect = cursor_execute_side_effect

            def side_effect(query, params=None, commit=False):
                if "SELECT Access_Accounting FROM User_Rights" in query:
                    return [{'Access_Accounting': 1}]
                return None
            self.mock_db.execute_query.side_effect = side_effect

            with patch('app.check_permission', return_value=True):
                 with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                         app_module.add_fixed_asset()
                         mock_flash.assert_called_with('Asset added successfully', 'success')

                         queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
                         self.assertTrue(any("INSERT INTO entry_details" in q for q in queries))
                         self.assertTrue(any("INSERT INTO suppliers_invoice_data" in q for q in queries))
                         self.assertTrue(any("INSERT INTO fixed_assets_register" in q for q in queries))

    def test_calculate_depreciation(self):
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.form = MagicMock()
            mock_request.form.get.side_effect = lambda k, d=None: {'month': '2023-02'}.get(k, d)

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.lastrowid = 999

            self.last_row_id = 999
            mock_cursor.lastrowid = 0

            self.mock_db.execute_query.return_value = [{'Access_Accounting': 1}]

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

            def cursor_execute_side_effect(*args, **kwargs):
                query = args[0]
                if "INSERT" in query.upper():
                    self.last_row_id += 1
                    mock_cursor.lastrowid = self.last_row_id

                if "SELECT * FROM fixed_assets_register" in query:
                    mock_cursor.fetchall.return_value = [asset]
                elif "SELECT asset_id FROM asset_depreciation_history" in query:
                    mock_cursor.fetchall.return_value = []
                elif "SELECT id FROM asset_depreciation_history" in query:
                    mock_cursor.fetchone.return_value = None
                elif "SELECT SUM(amount)" in query:
                    mock_cursor.fetchone.return_value = {'total': 0}
                elif "SELECT account_name FROM new_account_table" in query:
                    mock_cursor.fetchone.return_value = {'account_name': 'Test Account'}

            mock_cursor.execute.side_effect = cursor_execute_side_effect

            with patch('app.check_permission', return_value=True):
                 res = app_module.calculate_depreciation()
                 self.assertEqual(res['success'], True)

                 found = False
                 for call in mock_cursor.execute.call_args_list:
                     query = call[0][0]
                     if "INSERT INTO asset_depreciation_history" in query:
                         params = call[0][1]
                         if params[2] == 50.0:
                             found = True
                             break
                 self.assertTrue(found, "Depreciation calculation failed or not inserted")

    def test_delete_fixed_asset_write_off(self):
        with patch('app.request') as mock_request:
            mock_request.method = 'POST'
            mock_request.form = MagicMock()
            mock_request.form.get.side_effect = lambda k, d=None: {
                'action': 'write_off',
                'loss_account_id': '6'
            }.get(k, d)

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            self.mock_db.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            def cursor_execute_side_effect(*args, **kwargs):
                query = args[0]
                if "SELECT * FROM fixed_assets_register WHERE id" in query:
                    mock_cursor.fetchone.return_value = {
                        'id': 1, 'is_written_off': 0, 'jv_id': 100,
                        'asset_account_id': 1, 'accumulated_dep_account_id': 2,
                        'cost_value': 1000.0, 'asset_class': 'Class1', 'serial_no': 'S1'
                    }
                elif "SELECT suppliers_invoice_total_payment" in query:
                    mock_cursor.fetchone.return_value = {'suppliers_invoice_total_payment': 500.0}
                elif "SELECT account_name FROM new_account_table" in query:
                    mock_cursor.fetchone.return_value = {'account_name': 'Some Account'}
                elif "SELECT SUM(amount)" in query:
                    mock_cursor.fetchone.return_value = {'total': 200.0}

            mock_cursor.execute.side_effect = cursor_execute_side_effect

            def side_effect(query, params=None, commit=False):
                if "SELECT Access_Accounting FROM User_Rights" in query:
                    return [{'Access_Accounting': 1}]
                return None
            self.mock_db.execute_query.side_effect = side_effect

            with patch('app.check_permission', return_value=True):
                 with patch('app.flash') as mock_flash:
                    with patch('app.redirect') as mock_redirect:
                         app_module.delete_fixed_asset(1)

                         queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
                         self.assertTrue(any("INSERT INTO jv_numbers" in q for q in queries))
                         self.assertTrue(any("UPDATE fixed_assets_register SET status" in q for q in queries))

if __name__ == '__main__':
    unittest.main()
