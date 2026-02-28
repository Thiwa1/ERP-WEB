import sys
from unittest.mock import MagicMock, patch

# 1. Mock External Dependencies BEFORE importing app
mock_flask = MagicMock()
sys.modules['flask'] = mock_flask
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()

# Setup Flask Mock properly
mock_app = MagicMock()
mock_app.config = {}
mock_flask.Flask.return_value = mock_app

mock_flask.request = MagicMock()
mock_flask.session = {}
mock_flask.redirect = MagicMock()
mock_flask.url_for = MagicMock()
mock_flask.flash = MagicMock()
mock_flask.render_template = MagicMock()

# Mock wraps
def mock_wraps(f):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
mock_functools = MagicMock()
mock_functools.wraps = mock_wraps
sys.modules['functools'] = mock_functools

import unittest
import app as app_module

class BenchmarkInventoryTransfer(unittest.TestCase):
    def setUp(self):
        # Setup Session
        app_module.session['user_id'] = 'ADM001'
        app_module.session['user_pk'] = 1
        app_module.session['username'] = 'admin'

        # Mock DB (The critical part)
        self.mock_db = MagicMock()
        # Force replace the global db object in app.py
        app_module.db = self.mock_db

        # Also patch db_config just in case
        app_module.db_config = {}

        # Bypass permission check
        self.patcher = patch('app.check_permission', return_value=True)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        app_module.session.clear()

    def test_benchmark_transfer_performance(self):
        # Prepare request form data
        item_count = 100

        # When request.form.get is called
        def form_get(key, default=None):
            if key == 'transfer_date': return '2023-10-27'
            if key == 'job_no': return 'JOB001'
            if key == 'from_location': return 'Warehouse A'
            if key == 'to_location': return 'Warehouse B'
            if key == 'narration': return 'Benchmark Transfer'
            return default

        # When request.form.getlist is called
        def form_getlist(key):
            if key == 'item_name[]': return [f'Item {i}' for i in range(item_count)]
            if key == 'item_code[]': return [f'CODE{i}' for i in range(item_count)]
            if key == 'item_unit[]': return ['pcs' for _ in range(item_count)]
            if key == 'item_cost[]': return ['10.0' for _ in range(item_count)]
            if key == 'qty[]': return ['5' for _ in range(item_count)]
            return []

        # We must set side_effect on the mocks attached to the imported app_module's request object
        app_module.request.form.get.side_effect = form_get
        app_module.request.form.getlist.side_effect = form_getlist

        # Mock DB Connection and Cursor Setup
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Important: The code calls db.get_connection()
        self.mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1001

        print("Calling submit_inventory_transfer...")
        # Verify db is replaced
        print(f"App DB is mock: {isinstance(app_module.db, MagicMock)}")

        app_module.submit_inventory_transfer()

        # Debugging Output
        print("Flash calls:", mock_flask.flash.call_args_list)

        # Check execute calls
        execute_calls = mock_cursor.execute.call_count
        executemany_calls = mock_cursor.executemany.call_count

        print(f"Cursor Execute Calls: {execute_calls}")
        print(f"Cursor Executemany Calls: {executemany_calls}")

        # Assertions
        self.assertEqual(execute_calls, 1, f"Should have 1 execute call (header), got {execute_calls}")
        self.assertEqual(executemany_calls, 1, f"Should have 1 executemany call (batch items), got {executemany_calls}")

        if executemany_calls > 0:
            args = mock_cursor.executemany.call_args
            query, params = args[0]
            self.assertEqual(len(params), item_count * 2, f"Should batch {item_count * 2} records, got {len(params)}")

if __name__ == '__main__':
    unittest.main()
