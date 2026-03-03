import time
import unittest
import sys
import os
import datetime
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up the mock environment
import tests.mock_env

# Replace session with a MagicMock that acts like a dict but we can intercept __contains__
mock_session_obj = MagicMock()
mock_session_obj.__contains__.side_effect = lambda k: k == 'user_id'
tests.mock_env.mock_flask.session = mock_session_obj

import app
app.session = mock_session_obj

class BenchmarkDepreciation(unittest.TestCase):
    @patch('app.db')
    @patch('app.get_current_user_id')
    @patch('app.get_current_user_pk')
    @patch('app.check_permission', return_value=True)
    def test_benchmark_depreciation(self, mock_check, mock_get_pk, mock_get_id, mock_db):
        app.request.form.get.return_value = '2023-10'
        mock_get_pk.return_value = 1
        mock_get_id.return_value = 1

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1

        # Setup fake data: 1000 assets
        num_assets = 1000
        assets = []
        for i in range(num_assets):
            assets.append({
                'id': i,
                'status': 'Active',
                'purchasing_date': datetime.date(2023, 1, 1),
                'depreciable_life_months': 60,
                'cost_value': 10000,
                'expense_account_id': 1,
                'accumulated_dep_account_id': 2,
                'asset_class': 'Equipment',
                'serial_no': f'SN{i}'
            })

        def fetchall_side_effect():
            query = mock_cursor.execute.call_args[0][0]
            if "SELECT * FROM fixed_assets_register" in query:
                return assets
            elif "SELECT asset_id FROM asset_depreciation_history" in query:
                return []
            return []

        def fetchone_side_effect():
            query = mock_cursor.execute.call_args[0][0]
            if "SELECT SUM(amount)" in query:
                return {'total': 1000}
            elif "SELECT account_name" in query:
                return {'account_name': 'Test Account'}
            return None

        mock_cursor.fetchall.side_effect = fetchall_side_effect
        mock_cursor.fetchone.side_effect = fetchone_side_effect

        start_time = time.time()
        result = app.calculate_depreciation()
        end_time = time.time()

        print(f"\nResult: {result}")

        insert_calls = sum(1 for call in mock_cursor.execute.call_args_list if "INSERT INTO entry_details" in call[0][0])
        executemany_calls = sum(1 for call in mock_cursor.executemany.call_args_list if "INSERT INTO entry_details" in call[0][0])

        print(f"\nTime taken for {num_assets} assets: {end_time - start_time:.4f} seconds")
        print(f"execute calls for INSERT: {insert_calls}")
        print(f"executemany calls for INSERT: {executemany_calls}")

if __name__ == '__main__':
    unittest.main()
