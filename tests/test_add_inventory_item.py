import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock dependencies
mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['werkzeug.utils'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

import app

class TestAddInventoryItem(unittest.TestCase):

    @patch('app.db')
    @patch('app.get_current_user_id')
    @patch('app.get_current_user_pk')
    @patch('app.check_permission')
    def test_add_inventory_item_success(self, mock_check_permission, mock_get_current_user_pk, mock_get_current_user_id, mock_db):
        mock_check_permission.return_value = True
        mock_get_current_user_id.return_value = 1
        mock_get_current_user_pk.return_value = 1

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup db context manager properly
        class MockTransactionCursor:
            def __enter__(self):
                return mock_cursor
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_db.transaction_cursor.return_value = MockTransactionCursor()
        mock_db.get_connection.return_value = mock_conn

        app.app.config['TESTING'] = True
        with app.app.test_client() as client:
            with app.app.test_request_context('/add_inventory_item', method='POST', data={
                'item_name': 'Test Item',
                'item_code': 'TI-001',
                'measurement_unit': 'PCS',
                'selling_price': '100',
                'cost_price': '50'
            }):
                app.session['user_id'] = '1001'

                # Setup request mock manually to avoid issues with test_request_context and files attribute
                app.request = MagicMock()
                app.request.method = 'POST'

                class MockForm(dict):
                    def get(self, key, default=None):
                        return {
                            'item_name': 'Test Item',
                            'item_code': 'TI-001',
                            'measurement_unit': 'PCS',
                            'selling_price': '100',
                            'cost_price': '50'
                        }.get(key, default)

                app.request.form = MockForm()
                app.request.files = {}

                app.add_inventory_item()

                # Check that execute was called twice (once for item, once for price)
                # and NOT four times (as it would have with the duplicate block)
                self.assertEqual(mock_cursor.execute.call_count, 2)

                first_call_query = mock_cursor.execute.call_args_list[0][0][0]
                self.assertIn("INSERT INTO inventoy_items", first_call_query)

                second_call_query = mock_cursor.execute.call_args_list[1][0][0]
                self.assertIn("INSERT INTO inventory_price_recod", second_call_query)

if __name__ == '__main__':
    unittest.main()
