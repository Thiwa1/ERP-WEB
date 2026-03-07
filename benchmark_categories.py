import time
import sys
from unittest.mock import MagicMock

# Mock necessary modules
sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['flask_mysqldb'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['num2words'] = MagicMock()

import app

# Set up fake DB interactions for benchmark
class FakeCursor:
    def __init__(self):
        self.bs_data = {}
        self.pl_data = {}
        self.cf_data = {}
        self.queries = 0
        self._last_fetched = None

    def execute(self, query, params=None):
        self.queries += 1
        if "SELECT id FROM balance_sheet_category" in query:
            pos = params[0]
            if pos in self.bs_data:
                self._last_fetched = {'id': self.bs_data[pos]}
            else:
                self._last_fetched = None
        elif "INSERT INTO balance_sheet_category" in query:
            pos = params[1]
            self.bs_data[pos] = len(self.bs_data) + 1

        elif "SELECT id FROM `p&l_category`" in query:
            pos = params[0]
            if pos in self.pl_data:
                self._last_fetched = {'id': self.pl_data[pos]}
            else:
                self._last_fetched = None
        elif "INSERT INTO `p&l_category`" in query:
            pos = params[1]
            self.pl_data[pos] = len(self.pl_data) + 1

        elif "SELECT id FROM cf_catogory" in query:
            name = params[0]
            if name in self.cf_data:
                self._last_fetched = {'id': self.cf_data[name]}
            else:
                self._last_fetched = None
        elif "INSERT INTO cf_catogory" in query:
            name = params[0]
            self.cf_data[name] = len(self.cf_data) + 1

    def fetchone(self):
        return self._last_fetched

    def fetchall(self):
        return getattr(self, '_last_fetched_all', [])

    def close(self):
        pass

class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
    def cursor(self, dictionary=False):
        return self.cursor_obj
    def commit(self):
        pass
    def close(self):
        pass

def run_benchmark():
    conn = FakeConn()
    app.db.get_connection = lambda: conn

    start = time.time()
    for _ in range(10000):
        app.ensure_default_categories()
    end = time.time()

    print(f"Time taken for 10000 iterations: {end - start:.4f} seconds")
    print(f"Total queries: {conn.cursor_obj.queries}")

if __name__ == "__main__":
    run_benchmark()
