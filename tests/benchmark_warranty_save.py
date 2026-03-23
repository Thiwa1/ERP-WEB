import sys
import os
import time
from unittest.mock import MagicMock, patch
import unittest

sys.path.append('.')

# Instead of mocking everything manually, we use the app context or just run tests/run_tests.py style
class BenchmarkWarrantySave(unittest.TestCase):
    def setUp(self):
        # We need to mock the db connection and cursor to measure time
        self.patcher_db = patch('app.db.get_connection')
        self.mock_get_connection = self.patcher_db.start()
        self.mock_conn = MagicMock()
        self.mock_get_connection.return_value = self.mock_conn
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Add latency to execute to simulate real db wait time
        def simulate_db_latency(*args, **kwargs):
            time.sleep(0.001) # 1ms latency per query

        def simulate_db_latency_many(*args, **kwargs):
            time.sleep(0.005) # 5ms for an executemany call (bulk latency)

        self.mock_cursor.execute.side_effect = simulate_db_latency
        self.mock_cursor.executemany.side_effect = simulate_db_latency_many

        # Setup form data
        self.num_items = 1000
        self.ids = []
        self.names = []
        self.years = []
        self.months = []
        self.days = []
        for i in range(self.num_items):
            if i < self.num_items / 2:
                self.ids.append("0")
            else:
                self.ids.append(str(i))
            self.names.append(f"Test item {i}")
            self.years.append("1")
            self.months.append("0")
            self.days.append("0")

        self.patcher_request = patch('app.request')
        self.mock_request = self.patcher_request.start()

        def getlist(key):
            if key == 'id[]': return self.ids
            if key == 'name[]': return self.names
            if key == 'year[]': return self.years
            if key == 'month[]': return self.months
            if key == 'day[]': return self.days
            return []

        self.mock_request.form.getlist.side_effect = getlist

    def tearDown(self):
        self.patcher_db.stop()
        self.patcher_request.stop()

    def test_benchmark_warranty_save(self):
        from app import warranty_save

        start_time = time.time()

        # We need to handle app decorators and logic. Since it has @login_required, we might need to patch it or patch session.
        # But wait, warranty_save might be getting wrapped, which might need session to be set.
        # Let's bypass login_required or set a fake user.
        with patch('app.session', {'user_id': 1, 'user_pk': 1}), patch('app.get_session_db_name', return_value='test_db'):
            with patch('app.flash'), patch('app.redirect'), patch('app.url_for'):
                # warranty_save is wrapped. If we mocked Flask previously, it might be a MagicMock.
                # Let's just call it.
                warranty_save()

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"\nExecution time for {self.num_items} items: {execution_time:.4f} seconds")
        print(f"Number of individual queries: {self.mock_cursor.execute.call_count}")
        print(f"Number of executemany calls: {self.mock_cursor.executemany.call_count}")

if __name__ == '__main__':
    # We will use run_tests.py to handle Flask mocks
    unittest.main()
