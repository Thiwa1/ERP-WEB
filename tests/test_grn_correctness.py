import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
import json
from datetime import date

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Setup Mocks BEFORE importing app
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Configure Flask app.route to be a passthrough decorator
def route_decorator(rule, **options):
    def decorator(f):
        return f
    return decorator

# Configure the Flask instance returned by Flask(__name__)
mock_app_instance = MagicMock()
mock_app_instance.route.side_effect = route_decorator
mock_app_instance.context_processor.return_value = lambda x: x
mock_app_instance.template_filter.return_value = lambda x: x

mock_flask.Flask.return_value = mock_app_instance

# Mock request and session objects in flask module
mock_request = MagicMock()
mock_session = {} # Use a real dict for session to support item access
mock_flask.request = mock_request
mock_flask.session = mock_session

# Now import app
import app

class TestGRNCorrectness(unittest.TestCase):
    def setUp(self):
        # Setup mock DB
        self.mock_db = MagicMock()
        # Patch the module-level db variable in app.py
        app.db = self.mock_db
        app.app_initialized = True # Bypass initialization

        # Config mock request
        # Important: app.request refers to the mock_request we set up earlier
        app.request.method = 'POST'

        # Create test items
        self.items = [
            {
                'name': 'Item 1',
                'code': 'C1',
                'unit': 'PCS',
                'cost': 100.0,
                'qty': 10.0
            },
            {
                'name': 'Item 2',
                'code': 'C2',
                'unit': 'KG',
                'cost': 50.0,
                'qty': 5.0
            }
        ]

        # Configure request.form
        # We use a MagicMock for form but it behaves like a dict for get()
        # However, app.py uses request.form.get().

        form_data = {
            'supplier': 'Test Supplier',
            'items_json': json.dumps(self.items),
            'invoice_no': 'INV-TEST',
            'invoice_date': '2023-10-27',
            'due_date': '2023-11-27',
            'narration': 'Test GRN',
            'job_no': 'JOB-TEST',
            'location': 'Store 1',
            'total_value': '1250',
            'vat_rate': '0',
            'vat_amount': '0',
            'grand_total': '1250'
        }

        app.request.form = MagicMock()
        app.request.form.get.side_effect = lambda k, d=None: form_data.get(k, d)

        # Configure session
        app.session.update({
            'user_id': 'admin',
            'user_pk': 1,
            'username': 'admin'
        })

    def test_grn_executemany_usage(self):
        # Mock connection and cursor
        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Setup supplier check query result
        # The grn function calls execute_query to check supplier
        self.mock_db.execute_query.return_value = [{'supplier_code': 'SUP001', 'sup_id': 1}]

        mock_cursor.lastrowid = 999 # Mock JV ID

        # Patch check_permission to allow access
        with patch('app.check_permission', return_value=True), \
             patch('app.get_current_user_id', return_value=1):

            # Execute the function
            try:
                app.grn()
            except Exception as e:
                self.fail(f"app.grn() raised exception: {e}")

            # Verify executemany was called
            self.assertTrue(mock_cursor.executemany.called, "cursor.executemany was not called")

            # Verify the call arguments
            args, _ = mock_cursor.executemany.call_args
            query, params = args

            # Check Query
            self.assertIn("INSERT INTO inventory_recod", query)
            self.assertIn("VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)", query)

            # Check Params
            # Params should be a list of tuples
            self.assertEqual(len(params), 2)

            # Check first item
            # (name, code, unit, cost, qty, invoice_no, user, date, location, jv, inv_date, jv)
            item1 = params[0]
            self.assertEqual(item1[0], 'Item 1') # name
            self.assertEqual(item1[1], 'C1')     # code
            self.assertEqual(item1[2], 'PCS')    # unit
            self.assertEqual(item1[3], 100.0)    # cost
            self.assertEqual(item1[4], 10.0)     # qty (moument_in)

            # Check second item
            item2 = params[1]
            self.assertEqual(item2[0], 'Item 2')
            self.assertEqual(item2[4], 5.0)

            print("Test passed: executemany called correctly with batched data.")

if __name__ == '__main__':
    unittest.main()
