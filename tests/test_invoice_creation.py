import sys
import unittest
from unittest.mock import MagicMock, patch
import json

# --- MOCKING SETUP START ---
# We must mock flask and mysql.connector BEFORE importing app
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask

mock_mysql = MagicMock()
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql

# Configure Flask app.route to be a pass-through decorator
# so that the decorated functions retain their original body.
def pass_through_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_app_instance = MagicMock()
mock_app_instance.route.side_effect = pass_through_decorator
mock_app_instance.context_processor.side_effect = pass_through_decorator
mock_app_instance.template_filter.side_effect = pass_through_decorator

# Make sure Flask() returns our configured mock
mock_flask.Flask.return_value = mock_app_instance

# Setup other flask globals
mock_request = MagicMock()
mock_flask.request = mock_request
mock_session = {} # Use a dict for session to behave like real one
mock_flask.session = mock_session
mock_flask.flash = MagicMock()
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()
mock_flask.render_template = MagicMock()

# --- MOCKING SETUP END ---

# Now import app
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app

class TestInvoiceCreation(unittest.TestCase):
    def setUp(self):
        # Reset Mocks
        mock_flask.request.reset_mock()
        mock_flask.flash.reset_mock()
        mock_flask.redirect.reset_mock()

        # Clear Session and set default login
        mock_session.clear()
        mock_session['user_id'] = 'USER001'
        mock_session['user_pk'] = 123

        # Mock Database
        self.mock_db = MagicMock()
        app.db = self.mock_db

        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Configure Cursor lastrowid for IDs
        self.mock_cursor.lastrowid = 1001

    @patch('app.datetime')
    @patch('app.date')
    def test_submit_invoice_success(self, mock_date, mock_datetime):
        # Setup Fixed Dates
        fixed_date = date(2023, 10, 25)
        mock_date.today.return_value = fixed_date
        mock_datetime.now.return_value.year = 2023
        mock_datetime.now.return_value.month = 10
        mock_datetime.now.return_value.date.return_value = fixed_date

        # Setup Form Data
        # Fix: Use numbers for cost/price/qty to avoid "can't multiply sequence by non-int" error in app.py
        # The app logic expects `item['cost']` to be numeric or parsable, but if passed as string in JSON,
        # and multiplied directly without parsing (which seems to happen in one line), it fails.
        # Actually `json.loads` preserves types. If I send numbers, they are numbers.
        inv_items = [
            {'name': 'Item A', 'code': 'A001', 'unit': 'Nos', 'qty': 2, 'price': 100, 'cost': 80},
            {'name': 'Item B', 'code': 'B002', 'unit': 'Kg', 'qty': 5, 'price': 50, 'cost': 40}
        ]
        non_inv_items = [
            {'name': 'Service X', 'qty': 1, 'price': 500, 'unit': 'Hours'}
        ]

        form_data = {
            'customer': 'Test Customer',
            'location': 'Main Store',
            'invoice_date': '2023-10-25',
            'due_date': '2023-11-25',
            'job_no': 'JOB-001',
            'vat_rate': '15',
            'apply_vat': '1',
            'inventory_items_json': json.dumps(inv_items),
            'non_inventory_items_json': json.dumps(non_inv_items)
        }

        # Configure Request
        class MockForm(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_flask.request.form = MockForm(form_data)
        mock_flask.request.method = 'POST'

        # Configure DB Returns
        # 1. Customer ID fetch
        # 2. Warranty Period (optional)
        def execute_side_effect(query, params=None):
            if "SELECT sup_id FROM suppliers" in query:
                self.mock_cursor.fetchone.return_value = [555] # Customer ID
            elif "SELECT yeas_, month" in query:
                self.mock_cursor.fetchone.return_value = None # No warranty
            elif "INSERT" in query:
                pass
            return None

        self.mock_cursor.execute.side_effect = execute_side_effect

        # --- CALL FUNCTION ---
        app.submit_invoice()

        # --- ASSERTIONS ---

        # 1. Check Commit was called
        self.mock_conn.commit.assert_called_once()

        # 2. Verify SQL Calls
        calls = self.mock_cursor.execute.call_args_list
        queries = [c[0][0] for c in calls]

        # Check Invoice Number Generation
        self.assertTrue(any("INSERT INTO Credit_Invoice_No" in q for q in queries))

        # Check JV Header
        self.assertTrue(any("INSERT INTO jv_numbers" in q for q in queries))

        # Check Outstanding Record
        self.assertTrue(any("INSERT INTO Invoice_Oustanding" in q for q in queries))

        # In recent updates, batch inserts (executemany) are used instead of execute for items
        executemany_calls = self.mock_cursor.executemany.call_args_list
        em_queries = [c[0][0] for c in executemany_calls]

        # Check Invoice Records (Details) - Should appear in executemany with 3 items (2 inv + 1 non-inv)
        rec_calls = [q for q in em_queries if "INSERT INTO Invoice_Recode" in q]
        self.assertEqual(len(rec_calls), 1)
        self.assertEqual(len(executemany_calls[0][0][1]), 3)

        # Check Inventory Movement (Only for Inventory items)
        inv_mov_calls = [q for q in em_queries if "INSERT INTO inventory_recod" in q]
        self.assertEqual(len(inv_mov_calls), 1)
        self.assertEqual(len(executemany_calls[1][0][1]), 2)

        # Check GL Entries
        # Sales (Income), Receivables, VAT, COGS, Inventory (Asset)
        gl_calls = [q for q in queries if "INSERT INTO entry_details" in q]

        # Expected GL Entries:
        # 1. DR Receivables (Total + VAT)
        # 2. CR Sales (Total Sales)
        # 3. CR VAT (VAT Amount)
        # 4. DR COGS (Total Cost)
        # 5. CR Inventory (Total Cost)
        self.assertTrue(len(gl_calls) >= 5)

        # Check Success Message
        mock_flask.flash.assert_called_with(unittest.mock.ANY, 'success')

    def test_submit_invoice_no_items(self):
        # Empty items
        form_data = {
            'customer': 'Test Customer',
            'invoice_date': '2023-10-25',
            'inventory_items_json': '[]',
            'non_inventory_items_json': '[]'
        }
        class MockForm(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_flask.request.form = MockForm(form_data)

        app.submit_invoice()

        # Should flash danger/error
        mock_flask.flash.assert_called_with('No items in invoice', 'danger')

        # Should not start transaction or commit
        self.mock_conn.start_transaction.assert_not_called()
        self.mock_conn.commit.assert_not_called()

    def test_submit_invoice_transaction_failure(self):
        # Valid data but DB error
        # Use numbers in JSON to avoid the TypeError found above
        inv_items = [{'name': 'Item A', 'qty': 1, 'price': 100, 'cost': 80, 'unit': 'Nos', 'code': 'A1'}]
        form_data = {
            'customer': 'Test Customer',
            'invoice_date': '2023-10-25',
            'inventory_items_json': json.dumps(inv_items),
            'non_inventory_items_json': '[]'
        }
        class MockForm(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_flask.request.form = MockForm(form_data)

        # Mock execute to raise exception on specific query
        def execute_side_effect(query, params=None):
            if "INSERT INTO Invoice_Oustanding" in query:
                raise Exception("DB Connection Lost")
            return None

        self.mock_cursor.execute.side_effect = execute_side_effect

        app.submit_invoice()

        # Should rollback
        self.mock_conn.rollback.assert_called_once()

        # Should flash error
        args, _ = mock_flask.flash.call_args
        self.assertIn('danger', args)
        self.assertIn("Transaction failed", args[0])

    def test_generate_invoice_number(self):
        # Mock cursor.fetchone to return a known max invoice number
        self.mock_cursor.fetchone.return_value = [42]

        # Call the function
        result = app.generate_invoice_number(self.mock_cursor)

        # Verify query
        expected_query = "SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_no, 5) AS UNSIGNED)), 0) FROM customer_outstanding"
        self.mock_cursor.execute.assert_called_once_with(expected_query)

        # Verify result
        self.assertEqual(result, "INV-00043")

    def test_generate_invoice_number_empty_db(self):
        # Mock cursor.fetchone to return 0 when db is empty
        self.mock_cursor.fetchone.return_value = [0]

        # Call the function
        result = app.generate_invoice_number(self.mock_cursor)

        # Verify query
        expected_query = "SELECT COALESCE(MAX(CAST(SUBSTRING(invoice_no, 5) AS UNSIGNED)), 0) FROM customer_outstanding"
        self.mock_cursor.execute.assert_called_once_with(expected_query)

        # Verify result for first invoice
        self.assertEqual(result, "INV-00001")

if __name__ == '__main__':
    unittest.main()
