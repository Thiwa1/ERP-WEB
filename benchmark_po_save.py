import time
import os
import sys

# Ensure SECRET_KEY is set so app can be imported
os.environ['SECRET_KEY'] = 'test_secret'

import unittest
from unittest.mock import MagicMock, patch

from tests import mock_env

import app
from flask import Flask, session
import json

class POTest(unittest.TestCase):
    def test_po_benchmark(self):
        # We need to manually set the route to be available in the mock context
        app.get_current_user_id = MagicMock(return_value=1)
        app.get_current_user_pk = MagicMock(return_value=1)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Simulate an insert ID
        mock_cursor.lastrowid = 123
        mock_cursor.fetchone.return_value = (456,)

        app.db = MagicMock()
        app.db.get_connection.return_value = mock_conn

        # We need a custom mock for the execute method to simulate a slow network connection
        def mock_execute(*args, **kwargs):
            time.sleep(0.001) # Simulate 1ms latency per query

        mock_cursor.execute.side_effect = mock_execute

        # We need a custom mock for executemany
        def mock_executemany(*args, **kwargs):
            time.sleep(0.005) # Simulate 5ms latency per batch

        mock_cursor.executemany.side_effect = mock_executemany

        # Prepare request data with 500 items to not be too slow
        items = [{'item': f'Item {i}', 'description': f'Desc {i}', 'qty': 10, 'price': 5.5, 'unit': 'pcs'} for i in range(500)]

        app.app.config['SECRET_KEY'] = 'test'

        # The save_purchase_order function is decorated with @app.route and @login_required, which might be causing issues
        # with mock_env depending on how it's implemented. Let's just call the underlying function if possible, or
        # mock the request context properly.

        with app.app.test_request_context(
            '/purchase_orders/save',
            method='POST',
            data={
                'supplier': 'Test Supplier',
                'po_number': 'PO-001',
                'delivery_date': '2023-12-01',
                'location': 'Loc 1',
                'comments': 'Test',
                'vat_rate': '0',
                'items_json': json.dumps(items)
            }
        ):
            # Because save_purchase_order might be wrapped by decorators that are mocked to do nothing
            # Let's inspect mock_env or bypass decorators

            # Re-apply the mock session to satisfy @login_required if it's not stripped
            session['user_id'] = 1

            start = time.time()
            # If save_purchase_order is a MagicMock (because of mock_env's route decorator mock),
            # we need to find the original function.
            original_func = app.save_purchase_order

            # If it has a __wrapped__ attribute (from functools.wraps)
            while hasattr(original_func, '__wrapped__'):
                original_func = original_func.__wrapped__

            original_func()
            end = time.time()

            print(f"Time taken to process {len(items)} items: {end - start:.4f} seconds")

            # Verify execution count
            execute_count = mock_cursor.execute.call_count
            print(f"cursor.execute was called {execute_count} times")

            # Find executemany count if any
            executemany_count = mock_cursor.executemany.call_count
            print(f"cursor.executemany was called {executemany_count} times")

if __name__ == '__main__':
    unittest.main()
