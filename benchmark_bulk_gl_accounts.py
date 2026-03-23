import sys
import os
import time
from unittest.mock import MagicMock

class MockMySQLConnector:
    Error = Exception
    ProgrammingError = Exception

sys.modules['flask'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MockMySQLConnector()
sys.modules['dotenv'] = MagicMock()
sys.modules['werkzeug'] = MagicMock()
sys.modules['werkzeug.security'] = MagicMock()
sys.modules['werkzeug.datastructures'] = MagicMock()
sys.modules['PyPDF2'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['num2words'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
os.environ['SECRET_KEY'] = 'test-secret-key-for-mock-env'

import app

# Mock MultiDict
class MultiDict:
    def __init__(self):
        self.data = {}
    def setlist(self, key, value):
        self.data[key] = value
    def getlist(self, key):
        return self.data.get(key, [])

# Replace database calls with mocks
mock_db = MagicMock()
app.db = mock_db
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_conn.cursor.return_value = mock_cursor
mock_db.get_connection.return_value = mock_conn

# Setup data for benchmark
num_accounts = 5000
form_data = MultiDict()
names = [f"Account {i}" for i in range(num_accounts)]
types = ["Income"] * num_accounts
categories = ["Sales"] * num_accounts
cfs = ["Operating"] * num_accounts
actions = ["save"] * num_accounts

form_data.setlist('account_name[]', names)
form_data.setlist('account_type[]', types)
form_data.setlist('category[]', categories)
form_data.setlist('cf_category[]', cfs)
form_data.setlist('action[]', actions)

# Mock fetchall to return empty (all will be inserts)
mock_cursor.fetchall.return_value = []

app._parse_gl_category = MagicMock(return_value=('Sales', 'Income', False, True))
app._process_bulk_gl_subledgers = MagicMock()

# Run the benchmark
start = time.time()
count = app.save_bulk_gl_accounts(form_data, 1)
end = time.time()

print(f"BASELINE: Processed {count} accounts in {end - start:.4f} seconds")
print(f"Execute calls: {mock_cursor.execute.call_count}")
print(f"Executemany calls: {mock_cursor.executemany.call_count}")
