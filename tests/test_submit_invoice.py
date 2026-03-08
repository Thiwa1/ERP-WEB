import unittest
from unittest.mock import MagicMock, patch, call
import sys

# Mock Flask and mysql.connector BEFORE importing app or database
mock_flask = MagicMock()
class MockFlask:
    def __init__(self, *args, **kwargs):
        self.config = {}
        self.secret_key = None
        self.context_processor_funcs = []
        self.template_filter_funcs = {}
        self.view_functions = {}
        self.before_request_funcs = {}

    def context_processor(self, f): return f
    def template_filter(self, name=None):
        def decorator(f): return f
        return decorator
    def route(self, rule, **options):
        def decorator(f): return f
        return decorator
    def before_request(self, f): return f
    def run(self, *args, **kwargs): pass
    def test_client(self): return MagicMock() # Mock test_client

mock_flask.Flask = MockFlask
mock_flask.render_template = MagicMock(return_value="RENDERED_TEMPLATE")
mock_flask.request = MagicMock()
mock_flask.redirect = MagicMock(return_value="REDIRECT")
mock_flask.url_for = MagicMock(return_value="URL")
mock_flask.flash = MagicMock()
mock_flask.session = {}
mock_flask.make_response = MagicMock()
mock_flask.Response = MagicMock()
mock_flask.stream_with_context = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

import tests.mock_env

import app as app_module
from app import app
import json
from datetime import datetime, date

class TestSubmitInvoice(unittest.TestCase):
    def setUp(self):
        # We don't need app.config['TESTING'] = True because we are mocking everything
        # self.client = app.test_client()

        # Mock session in app_module
        app_module.session = {
            'user_id': 'ADM001',
            'user_pk': 1,
            'username': 'admin'
        }

        # Mock DB
        self.mock_db = MagicMock()
        app_module.db = self.mock_db

        # Mock get_current_user_id
        self.user_id_patcher = patch('app.get_current_user_id', return_value=1)
        self.mock_get_user_id = self.user_id_patcher.start()

        self.submit_invoice = app_module.submit_invoice

    def tearDown(self):
        self.user_id_patcher.stop()

    def test_submit_invoice_success(self):
        inv_items = [
            {'name': 'Item A', 'code': 'IA', 'qty': 2, 'price': 100, 'cost': 80, 'unit': 'Nos'}
        ]
        non_inv_items = [
            {'name': 'Service B', 'qty': 1, 'price': 500, 'unit': 'Hrs'}
        ]

        form_data = {
            'customer': 'Customer X',
            'location': 'Store 1',
            'invoice_date': '2023-10-27',
            'due_date': '2023-11-27',
            'job_no': 'JOB-001',
            'vat_rate': '18',
            'apply_vat': '1',
            'inventory_items_json': json.dumps(inv_items),
            'non_inventory_items_json': json.dumps(non_inv_items)
        }

        # Set request form data on the mocked request object in app module
        app_module.request.form = form_data
        app_module.request.method = 'POST'

        # Mock DB Connection and Cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.lastrowid = 100

        # side_effect for fetchone
        # 1. Customer ID select -> (5,)
        # 2. Warranty select -> None
        mock_cursor.fetchone.side_effect = [
            (5,),
            None,
        ]

        self.submit_invoice()

        self.assertTrue(mock_conn.commit.called)

        calls = mock_cursor.execute.call_args_list
        sql_calls = [str(c) for c in calls]

        self.assertTrue(any("INSERT INTO Credit_Invoice_No" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO jv_numbers" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO Invoice_Oustanding" in s for s in sql_calls))
        executemany_calls = mock_cursor.executemany.call_args_list
        exec_sql_calls = [str(c) for c in executemany_calls]
        self.assertTrue(any("INSERT INTO Invoice_Recode" in s and "Item A" in s for s in exec_sql_calls))
        self.assertTrue(any("INSERT INTO inventory_recod" in s and "Item A" in s for s in exec_sql_calls))
        self.assertTrue(any("INSERT INTO Invoice_Recode" in s and "Service B" in s for s in exec_sql_calls))

        self.assertTrue(any("INSERT INTO entry_details" in s and "Account Receivable" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO entry_details" in s and "Sales" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO entry_details" in s and "VAT Control" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO entry_details" in s and "Cost Of Goods Sold" in s for s in sql_calls))
        self.assertTrue(any("INSERT INTO entry_details" in s and "Inventory" in s for s in sql_calls))

    def test_submit_invoice_no_items(self):
        form_data = {
            'customer': 'Customer X',
            'inventory_items_json': '[]',
            'non_inventory_items_json': '[]'
        }
        app_module.request.form = form_data
        app_module.request.method = 'POST'

        mock_conn = MagicMock()
        self.mock_db.get_connection.return_value = mock_conn

        self.submit_invoice()

        self.assertFalse(mock_conn.commit.called)

if __name__ == '__main__':
    unittest.main()
