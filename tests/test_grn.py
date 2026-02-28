import unittest
from unittest.mock import MagicMock
import sys
import types
import json

# --- Mocking sys.modules for missing dependencies ---

# Mock mysql and mysql.connector
mock_mysql_pkg = types.ModuleType('mysql')
sys.modules['mysql'] = mock_mysql_pkg

mock_mysql_connector = types.ModuleType('mysql.connector')
mock_mysql_connector.connect = MagicMock()
mock_mysql_connector.Error = Exception
sys.modules['mysql.connector'] = mock_mysql_connector
mock_mysql_pkg.connector = mock_mysql_connector


# Mock flask
mock_flask = types.ModuleType('flask')
mock_flask.Flask = MagicMock
mock_flask.render_template = MagicMock(return_value="rendered_template")

# Create persistent mocks for objects imported by app.py
# app.py: from flask import ..., request, session, ...
global_request_mock = MagicMock()
global_session_mock = {}

mock_flask.request = global_request_mock
mock_flask.session = global_session_mock

mock_flask.redirect = MagicMock(return_value="redirected")
mock_flask.url_for = MagicMock(return_value="/url")
mock_flask.flash = MagicMock()
mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()
mock_flask.wraps = lambda f: f

# Custom Mock App to support attribute assignment
class MockApp(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = {'TESTING': True, 'SECRET_KEY': 'test_secret'}
        self.secret_key = 'test_secret'

mock_app_obj = MockApp()

def route_mock(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

mock_app_obj.route = MagicMock(side_effect=route_mock)
mock_app_obj.context_processor = MagicMock(side_effect=route_mock)
mock_app_obj.template_filter = MagicMock(side_effect=route_mock)
mock_app_obj.before_request = MagicMock(side_effect=route_mock)

mock_flask.current_app = mock_app_obj
mock_flask.Flask = MagicMock(return_value=mock_app_obj)

sys.modules['flask'] = mock_flask

# Import app after mocking
import app as app_module

class TestGRN(unittest.TestCase):
    def setUp(self):
        # Reset DB Mock
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        # Reset Session
        global_session_mock.clear()
        global_session_mock.update({
            'user_id': 'ADM001',
            'user_pk': 1,
            'username': 'admin',
            'tenant_db': 'test_db'
        })

        # Reset Request
        global_request_mock.reset_mock()
        global_request_mock.method = 'GET'
        global_request_mock.form = {}
        global_request_mock.args = {}

        # Reset Flask Mocks
        mock_flask.flash.reset_mock()
        mock_flask.redirect.reset_mock()
        mock_flask.render_template.reset_mock()

        # Mock Permission Check
        app_module.check_permission = MagicMock(return_value=True)
        app_module.app_initialized = True

    def tearDown(self):
        pass

    def test_grn_get(self):
        # Simulate GET request
        global_request_mock.method = 'GET'

        # Call route
        response = app_module.grn()

        # Verify DB queries
        calls = self.mock_db.execute_query.call_args_list
        queries = [call[0][0] for call in calls]

        self.assertTrue(any("SELECT supplier_name FROM suppliers" in q for q in queries))
        self.assertTrue(any("SELECT inventoy_name, inventoy_code" in q for q in queries))
        self.assertTrue(any("SELECT job_number FROM jobs_unit" in q for q in queries))
        self.assertTrue(any("SELECT inventory_locations_name" in q for q in queries))

        mock_flask.render_template.assert_called()
        self.assertEqual(mock_flask.render_template.call_args[0][0], 'grn.html')

    def test_grn_post_success(self):
        # Simulate POST request
        global_request_mock.method = 'POST'

        items = [
            {'name': 'Item 1', 'code': 'I001', 'unit': 'Nos', 'cost': 100, 'qty': 10},
            {'name': 'Item 2', 'code': 'I002', 'unit': 'Kg', 'cost': 50, 'qty': 20}
        ]

        # Configure form data on the global request mock
        global_request_mock.form = {
            'supplier': 'Test Supplier',
            'items_json': json.dumps(items),
            'invoice_no': 'INV-001',
            'invoice_date': '2023-10-27',
            'due_date': '2023-11-27',
            'narration': 'Test GRN',
            'job_no': 'JOB-101',
            'location': 'Warehouse A',
            'total_value': '2000',
            'vat_rate': '18',
            'vat_amount': '360',
            'grand_total': '2360'
        }

        # Mock Database Responses
        def execute_query_side_effect(query, params=None, commit=False):
            if "SELECT supplier_code, sup_id FROM suppliers" in query:
                return [{'supplier_code': 'SUP001', 'sup_id': 5}]
            return []

        self.mock_db.execute_query.side_effect = execute_query_side_effect

        # Mock Connection & Cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 123

        # Execute
        response = app_module.grn()

        # Verify Transaction
        mock_conn.start_transaction.assert_called_once()
        mock_conn.commit.assert_called_once()

        # Verify Insertions
        cursor_calls = mock_cursor.execute.call_args_list
        queries = [call[0][0] for call in cursor_calls]
        params = [call[0][1] for call in cursor_calls]

        self.assertTrue(any("INSERT INTO jv_numbers" in q for q in queries))
        self.assertTrue(any("INSERT INTO suppliers_invoice_data" in q for q in queries))

        # Creditors
        found_ap = False
        for q, p in zip(queries, params):
            if "INSERT INTO entry_details" in q and p and "Account Payable" in p:
                found_ap = True
                break
        self.assertTrue(found_ap, "AP Entry missing")

        # Inventory
        found_inv = False
        for q, p in zip(queries, params):
            if "INSERT INTO entry_details" in q and p and "Inventory" in p:
                found_inv = True
                break
        self.assertTrue(found_inv, "Inventory Entry missing")

        # VAT
        found_vat = False
        for q, p in zip(queries, params):
            if "INSERT INTO entry_details" in q and p and "VAT Control" in p:
                found_vat = True
                break
        self.assertTrue(found_vat, "VAT Entry missing")

        # Items
        inv_record_calls = [q for q in queries if "INSERT INTO inventory_recod" in q]
        self.assertEqual(len(inv_record_calls), 2)

    def test_grn_post_invalid_supplier(self):
        global_request_mock.method = 'POST'

        items = [{'name': 'Item 1', 'code': 'I001', 'unit': 'Nos', 'cost': 100, 'qty': 10}]
        global_request_mock.form = {
            'supplier': 'NonExistent',
            'items_json': json.dumps(items) # Must provide items to pass first check
        }

        # Mock failure to find supplier
        self.mock_db.execute_query.return_value = []
        # Clear side effect to ensure it returns empty list
        self.mock_db.execute_query.side_effect = None

        response = app_module.grn()

        mock_flask.redirect.assert_called()

        flash_calls = mock_flask.flash.call_args_list
        self.assertTrue(any('Invalid Supplier' in str(call) for call in flash_calls))

    def test_grn_post_db_error(self):
        global_request_mock.method = 'POST'
        items = [{'name': 'Item 1', 'code': 'I001', 'unit': 'Nos', 'cost': 100, 'qty': 10}]

        global_request_mock.form = {
            'supplier': 'Test Supplier',
            'items_json': json.dumps(items),
            'invoice_no': 'INV-001',
            'grand_total': '100'
        }

        self.mock_db.execute_query.return_value = [{'supplier_code': 'SUP001', 'sup_id': 5}]
        self.mock_db.execute_query.side_effect = None

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        def raise_exception(*args, **kwargs):
            raise Exception("DB Fail")

        mock_cursor.execute.side_effect = raise_exception

        response = app_module.grn()

        mock_conn.rollback.assert_called_once()
        flash_calls = mock_flask.flash.call_args_list
        self.assertTrue(any('Transaction failed' in str(call) for call in flash_calls))

if __name__ == '__main__':
    unittest.main()
